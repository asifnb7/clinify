import unittest
from types import SimpleNamespace
from unittest.mock import patch

from clinify.saas import (
    control_site_identity,
    orchestrator,
    provisioning,
    tenant_bootstrap,
)


EMAIL = "admin@example.test"


class FakeUser:
    def __init__(self, values, fake):
        self.__dict__.update(values)
        self._fake = fake
        self.roles = values.get("roles", [])

    def insert(self, **_kwargs):
        self.name = self.email
        self._fake.users[self.name] = self
        self._fake.created_user_values.append(dict(self.__dict__))

    def save(self, **_kwargs):
        self._fake.saved_users.append(self.name)


class FakeRole:
    def __init__(self, values, fake):
        self.__dict__.update(values)
        self._fake = fake

    def insert(self, **_kwargs):
        self._fake.roles[self.role_name] = self

    def save(self, **_kwargs):
        self._fake.saved_roles.append(self.role_name)


class FakeFrappe:
    def __init__(self, tenant_names=None, users=None, roles=None):
        self.tenant_names = tenant_names or ["TENANT-1"]
        self.users = users or {}
        self.roles = roles or {}
        self.created_user_values = []
        self.saved_users = []
        self.saved_roles = []
        self.commit_count = 0
        self.db = SimpleNamespace(commit=self.commit, exists=self.exists)

    def commit(self):
        self.commit_count += 1

    def exists(self, doctype, name):
        if doctype == "Role":
            return name if name in self.roles else None
        raise AssertionError("unexpected exists: {}".format(doctype))

    def get_all(self, doctype, filters=None, fields=None):
        if doctype == "Clinify Tenant":
            return [{"name": name} for name in self.tenant_names]
        if doctype == "User":
            return [
                {
                    "name": user.name,
                    "email": user.email,
                    "enabled": user.enabled,
                    "user_type": user.user_type,
                }
                for user in self.users.values()
                if user.email == filters["email"]
            ]
        raise AssertionError("unexpected get_all: {}".format(doctype))

    def get_doc(self, value, name=None):
        if isinstance(value, dict):
            if value["doctype"] == "Role":
                return FakeRole(value, self)
            return FakeUser(value, self)
        if value == "User":
            return self.users[name]
        if value == "Role":
            return self.roles[name]
        raise AssertionError("unexpected get_doc: {}".format(value))


def control_user(email=EMAIL, enabled=1, user_type="System User", name=None):
    values = {
        "name": name or email,
        "email": email,
        "enabled": enabled,
        "user_type": user_type,
    }
    fake = SimpleNamespace(users={}, created_user_values=[], saved_users=[])
    return FakeUser(values, fake)


class TestControlSiteAdministrator(unittest.TestCase):
    def _ensure(self, fake, tenant_name="TENANT-1", password="transient-secret"):
        tenant = SimpleNamespace(name=tenant_name)
        with patch.object(control_site_identity, "frappe", fake), patch.object(
            control_site_identity, "_validate_email", side_effect=lambda value: value
        ):
            return control_site_identity.ensure_control_site_administrator(
                tenant=tenant,
                administrator_email=EMAIL,
                administrator_name="Ada Lovelace",
                admin_password=password,
            )

    def test_creates_enabled_system_user_with_only_control_role(self):
        fake = FakeFrappe()

        user = self._ensure(fake)

        self.assertEqual(user.name, EMAIL)
        self.assertEqual(user.user_type, "System User")
        self.assertEqual(user.enabled, 1)
        created = fake.created_user_values[0]
        self.assertEqual(created["new_password"], "transient-secret")
        self.assertEqual(
            created["roles"],
            [{"doctype": "Has Role", "role": control_site_identity.CLINIFY_CONTROL_USER_ROLE}],
        )
        self.assertIn(control_site_identity.CLINIFY_CONTROL_USER_ROLE, fake.roles)
        self.assertEqual(fake.roles[control_site_identity.CLINIFY_CONTROL_USER_ROLE].desk_access, 1)
        self.assertEqual(fake.roles[control_site_identity.CLINIFY_CONTROL_USER_ROLE].is_custom, 1)
        self.assertNotIn(tenant_bootstrap.CLINIFY_ADMIN_ROLE, str(created["roles"]))

    def test_existing_matching_system_user_is_left_intact(self):
        user = control_user()
        fake = FakeFrappe(users={EMAIL: user})

        self.assertIs(self._ensure(fake), user)
        self.assertEqual(fake.created_user_values, [])
        self.assertEqual(fake.saved_users, [])

    def test_disabled_matching_system_user_is_enabled(self):
        user = control_user(enabled=0)
        user._fake = FakeFrappe  # overwritten below; only constructor bookkeeping uses it
        fake = FakeFrappe(users={EMAIL: user})
        user._fake = fake

        self.assertIs(self._ensure(fake), user)
        self.assertEqual(user.enabled, 1)
        self.assertEqual(fake.saved_users, [EMAIL])

    def test_rejects_user_collision_and_ambiguous_tenant_mapping(self):
        collision = control_user(name="different-user@example.test")
        fake = FakeFrappe(users={collision.name: collision})
        with self.assertRaisesRegex(RuntimeError, "different control-site user"):
            self._ensure(fake)

        fake = FakeFrappe(tenant_names=["TENANT-1", "TENANT-2"])
        with self.assertRaisesRegex(RuntimeError, "exactly this Clinify Tenant"):
            self._ensure(fake)

    def test_new_provisioning_rejects_an_email_already_mapped_to_a_tenant(self):
        fake = SimpleNamespace(
            db=SimpleNamespace(
                exists=lambda doctype, filters: (
                    doctype == "Clinify Plan"
                    or (
                        doctype == "Clinify Tenant"
                        and filters == {"administrator_email": EMAIL}
                    )
                ),
                get_value=lambda *_args, **_kwargs: None,
            ),
            throw=lambda message: (_ for _ in ()).throw(RuntimeError(message)),
        )
        with patch.object(provisioning, "frappe", fake), patch.object(
            provisioning, "_validate_email", return_value=EMAIL
        ):
            with self.assertRaisesRegex(RuntimeError, "Administrator Email"):
                provisioning.validate_provision_request(
                    tenant_name="Example Clinic",
                    tenant_code="EXAMPLE",
                    site_name="example.salniz.com",
                    administrator_email=EMAIL,
                    plan="TRIAL",
                )

    def test_rejects_non_system_user_instead_of_promoting_it(self):
        user = control_user(user_type="Website User")
        fake = FakeFrappe(users={EMAIL: user})
        with self.assertRaisesRegex(RuntimeError, "non-System"):
            self._ensure(fake)
        self.assertEqual(user.user_type, "Website User")

    def test_retry_is_idempotent_and_password_is_not_a_clinify_record_field(self):
        fake = FakeFrappe()

        self._ensure(fake, password="first-transient-secret")
        self._ensure(fake, password="second-transient-secret")

        self.assertEqual(len(fake.created_user_values), 1)
        self.assertEqual(fake.created_user_values[0]["new_password"], "first-transient-secret")
        self.assertEqual(len(fake.roles), 1)
        self.assertEqual(fake.tenant_names, ["TENANT-1"])
        self.assertTrue(all(values["doctype"] == "User" for values in fake.created_user_values))

    def test_verifying_provisioning_retry_rechecks_control_identity(self):
        tenant = SimpleNamespace(
            name="TENANT-1",
            tenant_name="Example Clinic",
            tenant_code="EXAMPLE",
            site_name="example.salniz.com",
            domain="example.salniz.com",
            administrator_name="Ada Lovelace",
            administrator_email=EMAIL,
            plan="TRIAL",
            contact_person="",
            registered_phone="",
            registered_email="",
            address_line_1="",
            address_line_2="",
            registered_city="",
            registered_state="",
            postal_code="",
            registered_country="",
            provisioning_status="Verifying",
            tenant_id=None,
            save=lambda **_kwargs: None,
        )
        fake = SimpleNamespace(
            db=SimpleNamespace(
                get_value=lambda *_args, **_kwargs: tenant,
                commit=lambda: None,
            ),
            get_doc=lambda *_args: tenant,
        )
        verification = {
            "subscription": {
                "name": "SUB-1",
                "subscription_status": "Trial",
                "end_date": "2099-01-01",
                "start_date": "2026-01-01",
            }
        }
        with patch.object(orchestrator, "frappe", fake), patch.object(
            orchestrator, "validate_control_site_administrator"
        ) as validate, patch.object(
            orchestrator, "ensure_control_site_administrator"
        ) as ensure, patch.object(
            orchestrator, "_verify_site", return_value=verification
        ), patch.object(orchestrator, "generate_tenant_id", return_value="C01EXA0126"), patch.object(
            orchestrator, "now_datetime", return_value="2026-01-01 00:00:00"
        ):
            result = orchestrator.provision_tenant(
                tenant_name=tenant.tenant_name,
                tenant_code=tenant.tenant_code,
                site_name=tenant.site_name,
                administrator_email=EMAIL,
                plan=tenant.plan,
                admin_password="retry-transient-secret",
            )

        validate.assert_called_once_with(tenant=tenant, administrator_email=EMAIL)
        ensure.assert_called_once_with(
            tenant=tenant,
            administrator_email=EMAIL,
            administrator_name="Ada Lovelace",
            admin_password="retry-transient-secret",
        )
        self.assertEqual(result["status"], "Ready")

    def test_tenant_local_administrator_role_remains_tenant_only(self):
        self.assertEqual(tenant_bootstrap.CLINIFY_ADMIN_ROLE, "Clinify Clinic Admin")
        with open(tenant_bootstrap.__file__, encoding="utf-8") as source:
            source = source.read()
        local_admin = source[source.index("def _ensure_admin_user"):source.index("def bootstrap_tenant")]
        self.assertIn('"role": CLINIFY_ADMIN_ROLE', local_admin)


if __name__ == "__main__":
    unittest.main()

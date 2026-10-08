import json
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import frappe

from clinify.saas import tenant_bootstrap


class TestTenantBootstrapSetupFinalization(unittest.TestCase):
    def test_bootstrap_tenant_invokes_required_foundation_helpers(self):
        helper_names = (
            "_ensure_admin_role",
            "_ensure_admin_permissions",
            "_ensure_gender_master_data",
            "_ensure_erpnext_foundation",
            "_ensure_healthcare_dental_foundation",
            "_ensure_clinify_catalogue",
            "_ensure_clinic_configuration",
            "_ensure_plan",
            "_ensure_subscription",
            "_ensure_admin_user",
            "_finalize_frappe_setup",
            "verify_tenant",
        )
        patches = {
            name: patch.object(tenant_bootstrap, name)
            for name in helper_names
        }
        mocks = {name: value.start() for name, value in patches.items()}
        for value in patches.values():
            self.addCleanup(value.stop)

        mocks["_ensure_clinic_configuration"].return_value = SimpleNamespace(
            name="Clinic Configuration"
        )
        mocks["_ensure_plan"].return_value = SimpleNamespace(plan_code="GATE2")
        mocks["_ensure_subscription"].return_value = SimpleNamespace(
            name="GATE2-SUBSCRIPTION"
        )
        mocks["_ensure_admin_user"].return_value = SimpleNamespace(
            name="gate2@example.invalid"
        )
        mocks["verify_tenant"].return_value = {"verified": True}

        with patch.object(tenant_bootstrap, "_validate_tenant_code", side_effect=lambda value: value), \
             patch.object(tenant_bootstrap, "_validate_email", side_effect=lambda value: value), \
             patch.object(tenant_bootstrap.frappe.db, "commit"), \
             patch("clinify.patches.install_clinify_prescription_print_format_v6.execute"), \
             patch("clinify.patches.install_clinify_invoice_print_format_v1.execute"):
            result = tenant_bootstrap.bootstrap_tenant(
                tenant_name="Gate 2 Test Clinic",
                tenant_code="GATE2",
                administrator_email="gate2@example.invalid",
                plan="GATE2",
                plan_definition={"plan_code": "GATE2", "plan_type": "Trial"},
                registered_country="India",
            )

        for name in (
            "_ensure_admin_role",
            "_ensure_admin_permissions",
            "_ensure_gender_master_data",
            "_ensure_healthcare_dental_foundation",
            "_ensure_clinify_catalogue",
        ):
            mocks[name].assert_called_once()
        self.assertTrue(result["success"])

    def test_finalize_frappe_setup_calls_native_update(self):
        class InstalledApps:
            def update_versions(self):
                self.called = True

        installed_apps = InstalledApps()

        with patch.object(
            frappe,
            "get_single",
            return_value=installed_apps,
        ) as get_single, patch.object(
            frappe.db,
            "exists",
            return_value=True,
        ), patch.object(
            frappe.db,
            "set_value",
        ), patch.object(
            frappe.db,
            "set_single_value",
        ), patch.object(
            frappe,
            "clear_cache",
        ), patch.object(
            frappe.db,
            "commit",
        ):
            tenant_bootstrap._finalize_frappe_setup()

        get_single.assert_called_once_with("Installed Applications")
        self.assertTrue(installed_apps.called)

    def test_finalize_frappe_setup_fails_closed_when_required_app_is_missing(self):
        class InstalledApps:
            def update_versions(self):
                self.called = True

        installed_apps = InstalledApps()

        def app_exists(doctype, filters):
            return filters["app_name"] == "frappe"

        with patch.object(
            frappe,
            "get_single",
            return_value=installed_apps,
        ) as get_single, patch.object(
            frappe.db,
            "exists",
            side_effect=app_exists,
        ):
            with self.assertRaises(frappe.ValidationError):
                tenant_bootstrap._finalize_frappe_setup()

        get_single.assert_called_once_with("Installed Applications")
        self.assertTrue(installed_apps.called)


    def test_ensure_admin_permissions_uses_canonical_clinify_matrix(self):
        role_name = tenant_bootstrap.CLINIFY_ADMIN_ROLE

        expected = tenant_bootstrap.ADMIN_PERMISSIONS

        self.assertEqual(
            set(tenant_bootstrap.ADMIN_PERMISSIONS),
            set(expected),
        )

        class FakeDB:
            def __init__(self):
                self.docperms = {}
                self.committed = False

            def exists(self, doctype, filters):
                if doctype == "Role":
                    return filters == role_name

                if doctype == "DocType":
                    return filters in expected

                if doctype == "Custom DocPerm":
                    return None

                if doctype == "DocPerm":
                    key = (
                        filters["parent"],
                        filters["role"],
                        filters["permlevel"],
                    )
                    docperm = self.docperms.get(key)
                    return docperm.name if docperm else None

                raise AssertionError(
                    f"Unexpected frappe.db.exists call: {doctype!r}, {filters!r}"
                )

            def commit(self):
                self.committed = True

        class FakeDocPerm:
            def __init__(self, db, name=None, **values):
                self._db = db
                self.name = name
                self.values = dict(values)
                self.save_count = 0
                self.insert_count = 0

            def __getattr__(self, name):
                if name in self.values:
                    return self.values[name]
                raise AttributeError(name)

            def __setattr__(self, name, value):
                if name in {"_db", "name", "values"}:
                    object.__setattr__(self, name, value)
                else:
                    self.values[name] = value

            def save(self, ignore_permissions=False):
                self.save_count += 1
                key = (
                    self.values["parent"],
                    self.values["role"],
                    self.values["permlevel"],
                )
                self._db.docperms[key] = self
                self.name = self.name or f"DP-{self.values['parent']}"
                self.values["name"] = self.name

            def insert(self, ignore_permissions=False):
                self.insert_count += 1
                key = (
                    self.values["parent"],
                    self.values["role"],
                    self.values["permlevel"],
                )
                self._db.docperms[key] = self
                self.name = self.name or f"DP-{self.values['parent']}"
                self.values["name"] = self.name

        fake_db = FakeDB()

        def fake_get_doc(*args, **kwargs):
            if args and isinstance(args[0], dict):
                values = dict(args[0])
                if values.get("doctype") == "DocPerm":
                    return FakeDocPerm(fake_db, **values)

            if args and args[0] == "DocPerm":
                for docperm in fake_db.docperms.values():
                    if docperm.name == args[1]:
                        return docperm
                raise AssertionError(f"Unknown DocPerm: {args[1]!r}")

            raise AssertionError(
                f"Unexpected frappe.get_doc call: args={args!r}, kwargs={kwargs!r}"
            )

        with patch.object(tenant_bootstrap.frappe, "db", fake_db), \
             patch.object(tenant_bootstrap.frappe, "get_doc", side_effect=fake_get_doc):
            tenant_bootstrap._ensure_admin_permissions()
            initial_save_counts = {
                key: docperm.save_count
                for key, docperm in fake_db.docperms.items()
            }
            tenant_bootstrap._ensure_admin_permissions()

        self.assertTrue(fake_db.committed)
        self.assertEqual(
            initial_save_counts,
            {
                key: docperm.save_count
                for key, docperm in fake_db.docperms.items()
            },
        )

        for doctype, permissions in expected.items():
            key = (doctype, role_name, 0)
            self.assertIn(key, fake_db.docperms)

            actual = fake_db.docperms[key].values

            for field, value in permissions.items():
                self.assertEqual(
                    actual.get(field),
                    value,
                    f"{doctype}.{field} mismatch",
                )


    def test_reconcile_tenant_foundation_invokes_only_scoped_helpers(self):
        with patch.object(tenant_bootstrap.frappe, "only_for") as only_for, \
             patch.object(tenant_bootstrap.frappe.local, "site", "beta-final-e2e-071026.localhost"), \
             patch.object(tenant_bootstrap.frappe, "conf", {"clinify_control_site": "clinify.localhost"}), \
             patch("clinify.saas.sso._is_control_site", return_value=False), \
             patch.object(tenant_bootstrap, "_ensure_admin_role") as ensure_role, \
             patch.object(tenant_bootstrap, "_ensure_admin_permissions") as ensure_permissions, \
             patch.object(tenant_bootstrap, "_ensure_gender_master_data") as ensure_gender, \
             patch.object(tenant_bootstrap, "_ensure_healthcare_dental_foundation") as ensure_healthcare, \
             patch.object(tenant_bootstrap, "_ensure_clinify_catalogue") as ensure_catalogue, \
             patch.object(tenant_bootstrap, "bootstrap_tenant") as bootstrap, \
             patch.object(tenant_bootstrap.frappe, "clear_cache") as clear_cache:
            result = tenant_bootstrap.reconcile_tenant_foundation()

        only_for.assert_called_once_with("System Manager")
        ensure_role.assert_called_once_with()
        ensure_permissions.assert_called_once_with()
        ensure_gender.assert_called_once_with()
        ensure_healthcare.assert_called_once_with()
        ensure_catalogue.assert_not_called()
        bootstrap.assert_not_called()
        clear_cache.assert_called_once_with()
        self.assertEqual(result["site"], "beta-final-e2e-071026.localhost")

    def test_reconcile_tenant_foundation_refuses_control_site(self):
        def raise_without_frappe_translation(message):
            raise RuntimeError(message)

        with patch.object(tenant_bootstrap.frappe, "only_for"), \
             patch.object(tenant_bootstrap.frappe.local, "site", "clinify.localhost"), \
             patch.object(tenant_bootstrap.frappe, "conf", {"clinify_control_site": "clinify.localhost"}), \
             patch("clinify.saas.sso._is_control_site", return_value=False), \
             patch.object(tenant_bootstrap.frappe, "throw", side_effect=raise_without_frappe_translation), \
             patch.object(tenant_bootstrap, "_ensure_admin_role") as ensure_role:
            with self.assertRaisesRegex(
                RuntimeError,
                "^Tenant foundation reconciliation cannot run on the control site\\.$",
            ):
                tenant_bootstrap.reconcile_tenant_foundation()

        ensure_role.assert_not_called()


    def test_healthcare_workspace_fixture_allows_clinify_clinic_admin(self):
        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "workspace.json"

        with fixture_path.open(encoding="utf-8") as handle:
            records = json.load(handle)

        healthcare = [
            record
            for record in records
            if record.get("doctype") == "Workspace"
            and record.get("name") == "Healthcare"
        ]

        self.assertEqual(
            len(healthcare),
            1,
            "Expected exactly one Healthcare Workspace fixture",
        )

        workspace = healthcare[0]

        self.assertEqual(workspace.get("public"), 1)
        self.assertEqual(workspace.get("is_hidden"), 0)
        self.assertEqual(
            workspace.get("restrict_to_domain"),
            "Healthcare",
        )

        workspace_roles = {
            row.get("role")
            for row in workspace.get("roles", [])
        }

        self.assertIn("Physician", workspace_roles)
        self.assertIn("Clinify Clinic Admin", workspace_roles)


def run():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestTenantBootstrapSetupFinalization
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    if not result.wasSuccessful():
        raise RuntimeError("Tenant bootstrap setup-finalization tests failed.")

    print("ALL TENANT BOOTSTRAP SETUP TESTS PASSED")


def _gate2_foundation_snapshot():
    role = frappe.db.get_value(
        "Role",
        tenant_bootstrap.CLINIFY_ADMIN_ROLE,
        ["name", "desk_access", "is_custom", "modified"],
        as_dict=True,
    )
    assert role, "Clinify Clinic Admin role is missing"

    permission_rows = {}
    for doctype, expected in tenant_bootstrap.ADMIN_PERMISSIONS.items():
        assert frappe.db.exists("DocType", doctype), f"Missing DocType: {doctype}"
        permission_doctype = (
            "Custom DocPerm"
            if frappe.db.exists("Custom DocPerm", {"parent": doctype})
            else "DocPerm"
        )
        filters = {
            "parent": doctype,
            "role": tenant_bootstrap.CLINIFY_ADMIN_ROLE,
            "permlevel": 0,
        }
        row = frappe.db.get_value(
            permission_doctype,
            filters,
            [*expected.keys(), "modified"],
            as_dict=True,
        )
        assert row, f"Missing {permission_doctype} for {doctype}"
        for field, value in expected.items():
            assert row[field] == value, (
                f"Unexpected {doctype}.{field}: {row[field]!r} != {value!r}"
            )
        permission_rows[doctype] = (
            permission_doctype,
            tuple(row[field] for field in expected),
            row.modified,
        )

    records = {
        "role": tuple(role[field] for field in role),
        "permissions": permission_rows,
    }
    for doctype, name, fields in (
        ("Gender", "MALE", ("gender",)),
        ("Gender", "FEMALE", ("gender",)),
        ("Medical Department", "Dental", ("department",)),
        (
            "Appointment Type",
            "OPD",
            ("allow_booking_for", "default_duration", "price_list"),
        ),
        (
            "Healthcare Service Unit Type",
            "OPD",
            ("allow_appointments", "overlap_appointments"),
        ),
    ):
        row = frappe.db.get_value(
            doctype,
            name,
            [*fields, "modified"],
            as_dict=True,
        )
        assert row, f"Missing required foundation record: {doctype} {name}"
        if doctype == "Healthcare Service Unit Type":
            assert row.allow_appointments, "OPD service-unit type disallows appointments"
        records[(doctype, name)] = tuple(row[field] for field in (*fields, "modified"))

    service_units = frappe.get_all(
        "Healthcare Service Unit",
        filters={"healthcare_service_unit_name": "OPD"},
        fields=[
            "name",
            "company",
            "service_unit_type",
            "allow_appointments",
            "overlap_appointments",
            "modified",
        ],
        order_by="name asc",
    )
    assert service_units, "Missing OPD Healthcare Service Unit"
    assert any(
        row.service_unit_type == "OPD" and row.allow_appointments
        for row in service_units
    ), "No OPD service unit allows appointments using the OPD service-unit type"
    records["Healthcare Service Unit"] = tuple(
        tuple(row[field] for field in (
            "name",
            "company",
            "service_unit_type",
            "allow_appointments",
            "overlap_appointments",
            "modified",
        ))
        for row in service_units
    )
    return records


def _gate2_business_configuration_snapshot():
    configuration = frappe.get_single("Clinic Configuration")
    layout_fields = {
        "Section Break",
        "Column Break",
        "Tab Break",
        "HTML",
        "Button",
        "Heading",
        "Table",
        "Table MultiSelect",
    }
    values = {
        field.fieldname: configuration.get(field.fieldname)
        for field in frappe.get_meta("Clinic Configuration").fields
        if field.fieldname and field.fieldtype not in layout_fields
    }
    return configuration.name, values


def run_gate2_certification():
    """Certify the existing disposable MSI tenant without creating transactions."""
    expected_site = "beta-final-e2e-071026.localhost"
    site_name = (frappe.local.site or "").strip().lower()
    assert site_name == expected_site, (
        f"Gate 2 runner is restricted to {expected_site}, got {site_name!r}"
    )
    assert site_name != "clinify.localhost", "Refusing control-plane reconciliation"
    administrator_email = "beta.final.e2e071026@example.com.invalid"

    business_before = _gate2_business_configuration_snapshot()
    first_result = tenant_bootstrap.reconcile_tenant_foundation()
    assert first_result["success"], "First reconciliation did not succeed"
    first_foundation = _gate2_foundation_snapshot()
    business_after_first = _gate2_business_configuration_snapshot()
    assert business_before == business_after_first, (
        "Clinic Configuration changed during reconciliation"
    )

    second_result = tenant_bootstrap.reconcile_tenant_foundation()
    assert second_result["success"], "Second reconciliation did not succeed"
    second_foundation = _gate2_foundation_snapshot()
    business_after_second = _gate2_business_configuration_snapshot()
    assert first_foundation == second_foundation, (
        "Foundation identity/state or modified timestamps changed on second run"
    )
    assert business_before == business_after_second, (
        "Clinic Configuration changed after repeated reconciliation"
    )
    assert tenant_bootstrap.CLINIFY_ADMIN_ROLE in frappe.get_roles(
        administrator_email
    ), "Disposable tenant administrator is missing Clinify Clinic Admin role"

    return {
        "success": True,
        "site": site_name,
        "new_tenant_bootstrap_helpers": "covered by test_bootstrap_tenant_invokes_required_foundation_helpers",
        "first_reconciliation": first_result["success"],
        "second_reconciliation": second_result["success"],
        "admin_role_and_permission_matrix": "verified",
        "tenant_administrator_role_assignment": "verified",
        "gender_and_healthcare_dental_foundation": "verified",
        "second_run_foundation_state_unchanged": True,
        "clinic_configuration_unchanged": True,
    }


if __name__ == "__main__":
    run()
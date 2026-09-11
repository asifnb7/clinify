import json
import unittest
from pathlib import Path
from unittest.mock import patch

import frappe

from clinify.saas import tenant_bootstrap


class TestTenantBootstrapSetupFinalization(unittest.TestCase):
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

        expected = {
            "Patient": {
                "read": 1, "write": 1, "create": 1, "delete": 1,
                "submit": 0, "cancel": 0, "amend": 0,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Appointment": {
                "read": 1, "write": 1, "create": 1, "delete": 1,
                "submit": 0, "cancel": 0, "amend": 0,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Patient Appointment": {
                "read": 1, "write": 1, "create": 1, "delete": 0,
                "submit": 0, "cancel": 0, "amend": 0,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Page": {
                "read": 1, "write": 0, "create": 0, "delete": 0,
                "submit": 0, "cancel": 0, "amend": 0,
            },
            "Healthcare Practitioner": {
                "read": 1, "write": 1, "create": 1, "delete": 1,
                "submit": 0, "cancel": 0, "amend": 0,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Patient Encounter": {
                "read": 1, "write": 1, "create": 1, "delete": 0,
                "submit": 1, "cancel": 1, "amend": 1,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Clinical Procedure": {
                "read": 1, "write": 1, "create": 1, "delete": 0,
                "submit": 1, "cancel": 1, "amend": 0,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Lab Test": {
                "read": 1, "write": 1, "create": 1, "delete": 0,
                "submit": 1, "cancel": 1, "amend": 1,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Medication Request": {
                "read": 1, "write": 1, "create": 1, "delete": 0,
                "submit": 0, "cancel": 0, "amend": 0,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Sales Invoice": {
                "read": 1, "write": 1, "create": 1, "delete": 0,
                "submit": 1, "cancel": 1, "amend": 1,
                "report": 1, "export": 0, "print": 1,
                "email": 1, "share": 1,
            },
            "Payment Entry": {
                "read": 1, "write": 1, "create": 1, "delete": 0,
                "submit": 1, "cancel": 1, "amend": 1,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Item": {
                "read": 1, "write": 1, "create": 1, "delete": 0,
                "submit": 0, "cancel": 0, "amend": 0,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Company": {
                "read": 1, "write": 1, "create": 0, "delete": 0,
                "submit": 0, "cancel": 0, "amend": 0,
                "report": 1, "export": 1, "print": 1,
                "email": 1, "share": 1,
            },
            "Clinic Configuration": {
                "read": 1, "write": 1, "create": 0, "delete": 0,
                "submit": 0, "cancel": 0, "amend": 0,
            },
            "Clinify Subscription": {
                "read": 0, "write": 0, "create": 0, "delete": 0,
                "submit": 0, "cancel": 0, "amend": 0,
            },
            "Dental Service": {
                "read": 1, "write": 1, "create": 1, "delete": 1,
                "submit": 0, "cancel": 0, "amend": 0,
            },
            "Treatment Plan Template": {
                "read": 1, "write": 1, "create": 1, "delete": 1,
                "submit": 0, "cancel": 0, "amend": 0,
            },
        }

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

                if doctype == "DocPerm":
                    key = (
                        filters["parent"],
                        filters["role"],
                        filters["permlevel"],
                    )
                    return key if key in self.docperms else None

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
                key = (
                    self.values["parent"],
                    self.values["role"],
                    self.values["permlevel"],
                )
                self._db.docperms[key] = self
                self.name = self.name or f"DP-{self.values['parent']}"
                self.values["name"] = self.name

            def insert(self, ignore_permissions=False):
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
                return FakeDocPerm(fake_db, **kwargs)

            raise AssertionError(
                f"Unexpected frappe.get_doc call: args={args!r}, kwargs={kwargs!r}"
            )

        with patch.object(tenant_bootstrap.frappe, "db", fake_db), \
             patch.object(tenant_bootstrap.frappe, "get_doc", side_effect=fake_get_doc):
            tenant_bootstrap._ensure_admin_permissions()

        self.assertTrue(fake_db.committed)

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


if __name__ == "__main__":
    run()
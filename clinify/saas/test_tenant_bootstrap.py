import unittest
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
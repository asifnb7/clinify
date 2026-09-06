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
            frappe,
            "is_setup_complete",
            return_value=True,
        ):
            tenant_bootstrap._finalize_frappe_setup()

        get_single.assert_called_once_with("Installed Applications")
        self.assertTrue(installed_apps.called)

    def test_finalize_frappe_setup_fails_closed(self):
        class InstalledApps:
            def update_versions(self):
                self.called = True

        installed_apps = InstalledApps()

        with patch.object(
            frappe,
            "get_single",
            return_value=installed_apps,
        ) as get_single, patch.object(
            frappe,
            "is_setup_complete",
            return_value=False,
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

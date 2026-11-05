import unittest
from unittest.mock import patch

from clinify.medicine_catalogue_sync import (
    EnvironmentTenantSyncCredentialProvider,
)
from clinify.saas import orchestrator, sso


SITE = "acme.localhost"

CONTROL_SETTINGS = {
    "CLINIFY_CONTROL_SITE": "clinify.localhost",
    "CLINIFY_CONTROL_URL": "https://control.salniz.com",
    "CLINIFY_CATALOGUE_SYNC_USER": "clinify-catalogue-sync@example.invalid",
    "CLINIFY_SSO_SECRET": "never-propagated",
}


def control_setting(local_development=None):
    settings = dict(CONTROL_SETTINGS)

    if local_development is not None:
        settings["CLINIFY_SSO_LOCAL_DEVELOPMENT"] = local_development

    def _setting(key):
        return settings.get(key)

    return _setting


class TestTenantConfigPropagation(unittest.TestCase):
    def test_site_creation_defers_app_installation(self):
        with patch.object(orchestrator, "_site_exists", return_value=False), patch.object(
            orchestrator, "_run_bench"
        ) as run_bench, patch.dict(
            "os.environ",
            {
                "CLINIFY_DB_ADMIN_USER": "db-admin",
                "CLINIFY_DB_ADMIN_PASSWORD": "db-password",
            },
        ):
            orchestrator._create_site(SITE, "admin-password")

        command = run_bench.call_args.args[0]
        self.assertEqual(command[:2], ["new-site", SITE])
        self.assertNotIn("--install-app", command)

    def test_configured_control_plane_keys_are_propagated(self):
        calls = []

        with patch.object(sso, "_setting", side_effect=control_setting()), patch.object(
            orchestrator, "_run_bench", side_effect=calls.append
        ):
            orchestrator._configure_tenant_site_config(SITE)

        self.assertEqual(
            calls,
            [
                [
                    "--site",
                    SITE,
                    "set-config",
                    "CLINIFY_CATALOGUE_SYNC_USER",
                    "clinify-catalogue-sync@example.invalid",
                ],
                ["--site", SITE, "set-config", "CLINIFY_CONTROL_SITE", "clinify.localhost"],
                ["--site", SITE, "set-config", "CLINIFY_CONTROL_URL", "https://control.salniz.com"],
            ],
        )

    def test_the_signing_secret_is_never_propagated(self):
        calls = []
        setting = control_setting(local_development="true")

        with patch.object(sso, "_setting", side_effect=setting), patch.object(
            orchestrator, "_run_bench", side_effect=calls.append
        ):
            orchestrator._configure_tenant_site_config(SITE)

        keys = [call[3] for call in calls]

        self.assertNotIn("CLINIFY_SSO_SECRET", keys)
        self.assertNotIn("CLINIFY_TENANT_ACME_LOCALHOST_SYNC_API_SECRET", keys)
        self.assertNotIn("never-propagated", [call[-1] for call in calls])

    def test_catalogue_sync_username_is_propagated_but_not_credential_values(self):
        calls = []
        settings = control_setting()
        credential_prefix = EnvironmentTenantSyncCredentialProvider._prefix(SITE)
        settings_values = {
            "CLINIFY_CATALOGUE_SYNC_USER": "catalogue-sync@example.invalid",
            f"{credential_prefix}_API_KEY": "api-key-secret",
            f"{credential_prefix}_API_SECRET": "tenant-api-secret",
        }
        setting = lambda key: settings_values.get(key) or settings(key)

        with patch.object(sso, "_setting", side_effect=setting), patch.object(
            orchestrator,
            "_run_bench",
            side_effect=calls.append,
        ):
            orchestrator._configure_tenant_site_config(SITE)

        self.assertIn(
            [
                "--site",
                SITE,
                "set-config",
                "CLINIFY_CATALOGUE_SYNC_USER",
                "catalogue-sync@example.invalid",
            ],
            calls,
        )
        self.assertNotIn("api-key-secret", str(calls))
        self.assertNotIn("tenant-api-secret", str(calls))

    def test_local_development_waiver_is_copied_only_while_enabled(self):
        enabled, disabled = [], []
        enabled_setting = control_setting(local_development="true")
        disabled_setting = control_setting(local_development="false")

        with patch.object(sso, "_setting", side_effect=enabled_setting), patch.object(
            orchestrator, "_run_bench", side_effect=enabled.append
        ):
            orchestrator._configure_tenant_site_config(SITE)

        with patch.object(sso, "_setting", side_effect=disabled_setting), patch.object(
            orchestrator, "_run_bench", side_effect=disabled.append
        ):
            orchestrator._configure_tenant_site_config(SITE)

        self.assertIn(
            ["--site", SITE, "set-config", "CLINIFY_SSO_LOCAL_DEVELOPMENT", "true"],
            enabled,
        )
        self.assertNotIn(
            "CLINIFY_SSO_LOCAL_DEVELOPMENT",
            [call[3] for call in disabled],
        )

    def test_a_bench_without_clinify_sso_propagates_nothing(self):
        calls = []

        with patch.object(sso, "_setting", return_value=None), patch.object(
            orchestrator, "_run_bench", side_effect=calls.append
        ):
            orchestrator._configure_tenant_site_config(SITE)

        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()

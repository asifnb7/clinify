import unittest
from unittest.mock import patch

from clinify.saas import orchestrator, sso


SITE = "acme.localhost"

CONTROL_SETTINGS = {
    "CLINIFY_CONTROL_SITE": "clinify.localhost",
    "CLINIFY_CONTROL_URL": "https://control.salniz.com",
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
        self.assertNotIn("never-propagated", [call[-1] for call in calls])

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

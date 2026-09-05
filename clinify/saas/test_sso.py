import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from clinify.saas import sso


def tenant(**changes):
    values = {"name": "TENANT-1", "tenant_code": "CLINIC1", "site_name": "clinic1.salniz.com", "domain": "clinic1.salniz.com", "administrator_email": "admin@example.test", "provisioning_status": "Ready", "subscription_status": "Active", "subscription_end_date": "2099-01-01", "enabled": 1, "clinic_status": "Active"}
    values.update(changes)
    return SimpleNamespace(**values)


class TestClinifySso(unittest.TestCase):
    def test_tenant_state_and_destination_are_rejected(self):
        with patch.object(sso, "today", return_value="2026-01-01"):
            for changes in ({"enabled": 0}, {"clinic_status": "Inactive"}, {"provisioning_status": "Pending"}, {"subscription_status": "Expired"}, {"subscription_end_date": None}, {"domain": "evil.example"}, {"site_name": "other.salniz.com"}):
                with self.assertRaises(RuntimeError):
                    sso._validate_tenant(tenant(**changes))

    def test_exactly_one_tenant_is_required(self):
        with patch.object(sso.frappe, "get_all", return_value=[]):
            with self.assertRaises(RuntimeError): sso._tenant_for_user("admin@example.test")
        with patch.object(sso.frappe, "get_all", return_value=[tenant(), tenant(name="TENANT-2")]):
            with self.assertRaises(RuntimeError): sso._tenant_for_user("admin@example.test")
        with patch.object(sso.frappe, "get_all", return_value=[tenant()]), patch.object(sso, "today", return_value="2026-01-01"), patch.object(sso, "_setting", return_value=None):
            self.assertEqual(sso._tenant_for_user("admin@example.test").name, "TENANT-1")

    def test_assertion_rejects_expiry_tampering_and_malformed_input(self):
        payload = {"aud": "clinic1.salniz.com|clinic1.salniz.com", "domain": "clinic1.salniz.com", "exp": int(time.time()) + 60, "nonce": "n", "site": "clinic1.salniz.com", "tenant": "TENANT-1", "user": "admin@example.test", "sid": "s"}
        with patch.object(sso, "_secret", return_value=b"test-secret"):
            assertion = sso._encode(payload)
            self.assertEqual(sso._decode(assertion), payload)
            for value in (assertion[:-1] + "0", "***.signature", "__8.signature", "not-an-assertion"):
                with self.assertRaises(RuntimeError): sso._decode(value)
            payload["exp"] = int(time.time()) - 1
            with self.assertRaises(RuntimeError): sso._decode(sso._encode(payload))

    def test_https_and_open_redirect_policy(self):
        with patch.object(sso, "_setting", side_effect=lambda key: {"CLINIFY_CONTROL_URL": "http://control.example"}.get(key)):
            with self.assertRaises(RuntimeError): sso._control_url()
        with self.assertRaises(RuntimeError): sso._tenant_domain("evil.example")

    def test_redemption_revalidates_tenant_audience_and_destination(self):
        payload = {"tenant": "TENANT-1", "user": "admin@example.test", "site": "clinic1.salniz.com", "domain": "clinic1.salniz.com", "aud": "clinic1.salniz.com|clinic1.salniz.com"}
        fake = SimpleNamespace(db=SimpleNamespace(get_value=lambda *_a, **_k: tenant()))
        with patch.object(sso, "frappe", fake), patch.object(sso, "today", return_value="2026-01-01"), patch.object(sso, "_setting", return_value=None):
            self.assertEqual(sso._tenant_for_handoff(payload).name, "TENANT-1")
            for key, value in (("aud", "other.salniz.com|other.salniz.com"), ("site", "other.salniz.com"), ("domain", "other.salniz.com"), ("user", "other@example.test")):
                bad = dict(payload); bad[key] = value
                with self.assertRaises(RuntimeError): sso._tenant_for_handoff(bad)

    def test_local_identity_rejects_disabled_wrong_role_and_non_system_user(self):
        result = {"user": "admin@example.test", "tenant_code": "CLINIC1"}
        fake = SimpleNamespace(db=SimpleNamespace(get_value=lambda *_a, **_k: None, exists=lambda *_a, **_k: False), get_single=lambda *_: None)
        with patch.object(sso, "frappe", fake):
            with self.assertRaises(RuntimeError): sso._validate_local_identity(result)
        fake.db.get_value = lambda *_a, **_k: SimpleNamespace(enabled=1, user_type="Website User")
        with patch.object(sso, "frappe", fake):
            with self.assertRaises(RuntimeError): sso._validate_local_identity(result)
        fake.db.get_value = lambda *_a, **_k: SimpleNamespace(enabled=1, user_type="System User")
        with patch.object(sso, "frappe", fake):
            with self.assertRaises(RuntimeError): sso._validate_local_identity(result)
        fake.db.get_value = lambda *_a, **_k: SimpleNamespace(enabled=0, user_type="System User")
        with patch.object(sso, "frappe", fake):
            with self.assertRaises(RuntimeError): sso._validate_local_identity(result)

    def test_one_time_consumption_rejects_replay(self):
        class Lock:
            def __enter__(self): return self
            def __exit__(self, *_): return False
        class Cache:
            def __init__(self): self.values = {sso._handoff_key("x" * 40): "assertion"}
            def make_key(self, key, **_): return key
            def lock(self, *_args, **_): return Lock()
            def get_value(self, key, **_): return self.values.get(key)
            def delete_value(self, key, **_): self.values.pop(key, None)
        cache = Cache()
        with patch.object(sso.frappe, "cache", return_value=cache), patch.object(sso, "_decode", return_value={"nonce": "n"}):
            self.assertEqual(sso._consume_handoff("x" * 40), {"nonce": "n"})
            with self.assertRaises(RuntimeError): sso._consume_handoff("x" * 40)


if __name__ == "__main__":
    unittest.main()

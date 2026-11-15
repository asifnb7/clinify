import unittest
from copy import deepcopy
import json
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from clinify import medicine_catalogue_sync
from clinify.api import drug_search
from clinify.clinify.doctype.clinify_medicine_projection.clinify_medicine_projection import (
    ClinifyMedicineProjection,
)

REVISION_0 = "20261009020000000000"
REVISION_1 = "20261009020000000001"
REVISION_2 = "20261009020000000002"
REVISION_3 = "20261009020000000003"


def product(product_id, strength, dosage_form="Tablet", active=1):
    return {
        "central_product_id": product_id,
        "ingredient_name": "Example Ingredient",
        "strength": strength,
        "strength_uom": "mg",
        "dosage_form": dosage_form,
        "source_provider": "",
        "source_identifier": "",
        "source_revision": "source-r1",
        "source_updated_at": "",
        "is_active": active,
    }


def medicine_item_catalogue(item_code="AMLODIPINE-5-TAB", disabled=0):
    return {
        "catalogue_type": "drug_item_catalogue_v1",
        "items": [
            {
                "item_code": item_code,
                "item_name": "Amlodipine 5mg Tablet",
                "item_group": "Drug",
                "disabled": disabled,
                "is_stock_item": 1,
                "is_sales_item": 1,
                "stock_uom": "Nos",
                "description": "Amlodipine 5mg Tablet",
            }
        ],
        "medications": [
            {
                "name": "Amlodipine",
                "generic_name": "Amlodipine",
                "medication_class": "Antihypertensive",
                "strength": 5,
                "strength_uom": "Milligram",
                "dosage_form": "Tablet",
                "disabled": 0,
                "is_combination": 0,
                "default_prescription_dosage": "0-0-0",
                "default_prescription_duration": "0 Day",
                "linked_items": [
                    {
                        "item_code": item_code,
                        "item": item_code,
                        "item_group": "Drug",
                        "stock_uom": "Nos",
                        "is_billable": 1,
                    }
                ],
                "combinations": [],
            }
        ],
        "medication_classes": [
            {
                "name": "Antihypertensive",
                "medication_class": "Antihypertensive",
            }
        ],
        "dosage_forms": [{"name": "Tablet", "dosage_form": "Tablet"}],
        "uoms": [
            {
                "name": "Milligram",
                "uom_name": "Milligram",
                "must_be_whole_number": 0,
                "enabled": 1,
            },
            {
                "name": "Nos",
                "uom_name": "Nos",
                "must_be_whole_number": 1,
                "enabled": 1,
            },
        ],
        "prescription_dosages": [{"name": "0-0-0", "dosage": "0-0-0"}],
        "prescription_durations": [
            {"name": "0 Day", "number": 0, "period": "Day"}
        ],
    }


def add_catalogue_item(catalogue, item_code, item_name):
    item = deepcopy(catalogue["items"][0])
    item.update(
        {
            "item_code": item_code,
            "item_name": item_name,
            "description": item_name,
        }
    )
    catalogue["items"].append(item)


class FakeStateStore:
    def __init__(self):
        self.last_attempted_revision = None
        self.last_attempt_status = "Not Attempted"
        self.last_successful_revision = None
        self.last_counts = {}

    def record_attempt(self, tenant_site, catalogue_revision, snapshot_digest=""):
        self.last_attempted_revision = catalogue_revision
        self.last_attempted_digest = snapshot_digest
        self.last_attempt_status = "Attempting"

    def record_failure(self, tenant_site, catalogue_revision, error_code, snapshot_digest=""):
        self.last_attempted_revision = catalogue_revision
        if snapshot_digest:
            self.last_attempted_digest = snapshot_digest
        self.last_attempt_status = "Failed"
        self.last_error_code = error_code

    def record_success(self, tenant_site, catalogue_revision, counts, snapshot_digest=""):
        self.last_attempted_revision = catalogue_revision
        self.last_attempt_status = "Succeeded"
        self.last_successful_revision = catalogue_revision
        self.last_successful_digest = snapshot_digest
        self.last_counts = dict(counts)


class FakeAtomicTransport:
    def __init__(self):
        self.items = {}
        self.medications = {}
        self.prices = {"local-item": 345.0}
        self.clinic_configuration = {"currency": "INR", "clinic_name": "Local Clinic"}
        self.fail_after_first_write = False
        self.response_status = "success"
        self.apply_count = 0

    def apply_projection_batch_atomically(self, tenant_site, snapshot_manifest, products):
        self.apply_count += 1
        previous = deepcopy((self.items, self.medications))
        created_codes = []
        updated_codes = []
        skipped_codes = []
        try:
            catalogue = products
            for index, item in enumerate(catalogue["items"]):
                item_code = item["item_code"]
                if self.items.get(item_code) == item:
                    skipped_codes.append(item_code)
                elif item_code in self.items:
                    self.items[item_code] = deepcopy(item)
                    updated_codes.append(item_code)
                else:
                    self.items[item_code] = deepcopy(item)
                    created_codes.append(item_code)

                if self.fail_after_first_write and index == 0:
                    raise RuntimeError("private transport detail must not be logged")
            for medication in catalogue["medications"]:
                self.medications[medication["name"]] = deepcopy(medication)
        except Exception:
            self.items, self.medications = previous
            raise

        return {
            "status": self.response_status,
            "tenant_site": tenant_site,
            "snapshot_manifest": dict(snapshot_manifest),
            "created_item_codes": created_codes,
            "updated_item_codes": updated_codes,
            "skipped_item_codes": skipped_codes,
            "missing_item_codes": [],
            "conflicting_item_codes": [],
        }


class FakeSyncStateDoc:
    def __init__(self, values, database):
        self.__dict__.update(values)
        self.last_attempted_at = None
        self.last_attempted_revision = None
        self.last_attempted_digest = ""
        self.last_attempt_status = "Not Attempted"
        self.last_error_code = ""
        self.last_successful_at = None
        self.last_successful_revision = None
        self.last_successful_digest = ""
        self.last_created_count = 0
        self.last_updated_count = 0
        self.last_skipped_count = 0
        self._database = database
        self.flags = SimpleNamespace()
        self.name = values.get("tenant_site")
        self._is_new = (
            database.snapshot_state is None
            if hasattr(database, "snapshot_state")
            else self.name not in database.records
        )

    def is_new(self):
        return self._is_new

    def insert(self, ignore_permissions=False):
        if hasattr(self._database, "snapshot_state"):
            self._database.snapshot_state = self
        else:
            self._database.records[self.tenant_site] = self
        self._is_new = False

    def save(self, ignore_permissions=False):
        if hasattr(self._database, "snapshot_state"):
            self._database.snapshot_state = self
        else:
            self._database.records[self.tenant_site] = self


class FakeSyncStateDatabase:
    def __init__(self):
        self.records = {}

    def exists(self, doctype, tenant_site):
        return tenant_site if tenant_site in self.records else None


class FakeCallbackManager:
    def __init__(self):
        self.callbacks = []

    def add(self, callback):
        self.callbacks.append(callback)

    def run(self):
        callbacks, self.callbacks = self.callbacks, []
        for callback in callbacks:
            callback()

    def reset(self):
        self.callbacks.clear()


class FakeLockCoordinator:
    def __init__(self):
        self.owners = {}


class FakeProjectionDatabase:
    def __init__(self, fail_on_insert=None, lock_coordinator=None):
        self.records = {}
        self.snapshot_state = None
        self.fail_on_insert = fail_on_insert
        self.savepoints = {}
        self.lock_result = 1
        self.lock_acquisitions = 0
        self.lock_releases = 0
        self.lock_coordinator = lock_coordinator or FakeLockCoordinator()
        self.after_commit = FakeCallbackManager()
        self.after_rollback = FakeCallbackManager()
        self._transaction_snapshot = self._snapshot()

    def _snapshot(self):
        return deepcopy((self.records, self.snapshot_state))

    def sql(self, query, values):
        if "GET_LOCK" in query:
            self.lock_acquisitions += 1
            lock_name = values[0]
            owner = self.lock_coordinator.owners.get(lock_name)
            if self.lock_result != 1 or (owner is not None and owner is not self):
                return [(0,)]
            self.lock_coordinator.owners[lock_name] = self
            return [(1,)]
        if "RELEASE_LOCK" in query:
            self.lock_releases += 1
            lock_name = values[0]
            if self.lock_coordinator.owners.get(lock_name) is self:
                del self.lock_coordinator.owners[lock_name]
            return [(1,)]
        raise AssertionError(f"Unexpected SQL in fake projection DB: {query!r}")

    def exists(self, doctype, name):
        if doctype == "Clinify Medicine Sync State":
            return name if self.snapshot_state is not None else None
        if doctype == "Medication Linked Item":
            return None
        return name if name in self.records else None

    def savepoint(self, name):
        self.savepoints[name] = self._snapshot()

    def rollback(self, save_point):
        self.records, self.snapshot_state = self.savepoints[save_point]

    def commit(self):
        self.after_rollback.reset()
        self._transaction_snapshot = self._snapshot()
        self.after_commit.run()

    def rollback_request(self):
        self.after_commit.reset()
        self.records, self.snapshot_state = deepcopy(self._transaction_snapshot)
        self.after_rollback.run()
        self._transaction_snapshot = self._snapshot()


class FakeProjectionDocument:
    def __init__(self, values, database):
        self.__dict__.update(values)
        self._database = database
        self.flags = SimpleNamespace(get=lambda key, default=None: getattr(self.flags, key, default))
        self.name = values.get("central_product_id")

    def save(self, ignore_permissions=False):
        self._database.records[self.name] = self

    def insert(self, ignore_permissions=False):
        if self._database.fail_on_insert == self.name:
            raise RuntimeError("simulated storage failure")
        if self.name in self._database.records:
            raise RuntimeError("duplicate central product id")
        self._database.records[self.name] = self


class FakeMedicineItemDocument:
    def __init__(self, values, database):
        self.__dict__.update(values)
        self._database = database
        self.name = (
            values.get("item_code")
            or values.get("name")
            or values.get("generic_name")
            or values.get("dosage_form")
            or values.get("medication_class")
            or values.get("dosage")
            or values.get("uom_name")
        )

    def save(self, ignore_permissions=False):
        self._database.records[self.name] = self

    def insert(self, ignore_permissions=False):
        if self.name in self._database.records:
            raise RuntimeError(f"duplicate fake document: {self.doctype} {self.name}")
        self._database.records[self.name] = self

    def get(self, fieldname, default=None):
        return getattr(self, fieldname, default)

    def set(self, fieldname, values):
        setattr(self, fieldname, values)


class FakeHTTPResponse:
    status_code = 200

    def __init__(self, result):
        self.result = result

    def json(self):
        return {"message": self.result}


class FakeHTTPTransportSession:
    def __init__(self, response=None):
        self.response = response or FakeHTTPResponse({"status": "success"})
        self.post = Mock(return_value=self.response)
        self.close = Mock()


class TestCentralMedicineCatalogue(unittest.TestCase):
    def test_tenant_credential_prefixes_do_not_collide_on_dots_and_hyphens(self):
        first = medicine_catalogue_sync.tenant_sync_credential_environment_prefix(
            "a-b.c.example"
        )
        second = medicine_catalogue_sync.tenant_sync_credential_environment_prefix(
            "a.b-c.example"
        )

        self.assertNotEqual(first, second)

    def test_tenant_credential_prefix_is_stable_for_canonical_site(self):
        first = medicine_catalogue_sync.tenant_sync_credential_environment_prefix(
            "Clinic.Example.Test"
        )
        second = medicine_catalogue_sync.tenant_sync_credential_environment_prefix(
            "clinic.example.test"
        )

        self.assertEqual(first, second)

    def test_tenant_credential_prefix_rejects_invalid_site_identifiers(self):
        for site in ("", "bad_site.example", "a..example", "-bad.example", 123):
            with self.subTest(site=site), self.assertRaises(ValueError):
                medicine_catalogue_sync.tenant_sync_credential_environment_prefix(site)

    def _synchronize(self, catalogue, transport, state, revision=REVISION_1):
        with patch.object(
            medicine_catalogue_sync,
            "require_control_site_admin",
            return_value="control.example.test",
        ), patch.object(
            medicine_catalogue_sync,
            "build_central_medicine_item_catalogue",
            return_value=deepcopy(catalogue),
        ):
            result = medicine_catalogue_sync.synchronize_tenant_catalogue(
                "clinic.example.test",
                revision,
                transport,
                state,
            )
        return result

    def test_same_ingredient_supports_distinct_strengths_and_forms(self):
        validated = medicine_catalogue_sync.validate_product_batch(
            [
                product("CLM-AAAA", 500, "Tablet"),
                product("CLM-BBBB", 1000, "Tablet"),
                product("CLM-CCCC", 500, "Capsule"),
            ]
        )

        self.assertEqual(len(validated), 3)
        self.assertEqual(len({row["identity_key"] for row in validated}), 3)

    def test_duplicate_clinical_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ambiguous duplicate commercial identity"):
            medicine_catalogue_sync.validate_product_batch(
                [product("CLM-AAAA", 500), product("CLM-BBBB", "500.0", "tablet")]
            )

    def test_invalid_source_timestamp_is_rejected(self):
        source_product = product("CLM-AAAA", 500)
        source_product["source_updated_at"] = "not-a-timestamp"

        with self.assertRaisesRegex(ValueError, "invalid source update timestamp"):
            medicine_catalogue_sync.validate_product_batch([source_product])

    def test_snapshot_manifest_digest_is_order_independent_and_checks_count(self):
        products = [product("CLM-AAAA", 500), product("CLM-BBBB", 1000)]
        manifest, _ = medicine_catalogue_sync.create_snapshot_manifest(products, REVISION_1)
        reversed_manifest, _ = medicine_catalogue_sync.create_snapshot_manifest(
            list(reversed(products)),
            REVISION_1,
        )

        self.assertEqual(manifest, reversed_manifest)
        with self.assertRaisesRegex(ValueError, "does not match"):
            medicine_catalogue_sync.validate_snapshot_manifest(
                dict(manifest, product_count=1),
                products,
            )
        with self.assertRaisesRegex(ValueError, "does not match"):
            medicine_catalogue_sync.validate_snapshot_manifest(
                dict(manifest, digest="0" * 64),
                products,
            )

    def test_item_snapshot_is_deterministic_and_preserves_picker_fields(self):
        catalogue = medicine_item_catalogue()
        manifest, normalized = (
            medicine_catalogue_sync.create_medicine_item_snapshot_manifest(
                catalogue, REVISION_1
            )
        )
        reversed_catalogue = deepcopy(catalogue)
        reversed_catalogue["items"].reverse()
        reversed_manifest, _ = (
            medicine_catalogue_sync.create_medicine_item_snapshot_manifest(
                reversed_catalogue, REVISION_1
            )
        )

        self.assertEqual(manifest, reversed_manifest)
        self.assertEqual(manifest["item_count"], 1)
        self.assertEqual(normalized["items"][0]["item_group"], "Drug")
        self.assertEqual(normalized["items"][0]["item_name"], "Amlodipine 5mg Tablet")
        self.assertEqual(
            normalized["medications"][0]["linked_items"][0]["item_code"],
            "AMLODIPINE-5-TAB",
        )

    def test_item_snapshot_rejects_unresolved_medication_relationship(self):
        catalogue = medicine_item_catalogue()
        catalogue["medications"][0]["linked_items"][0]["item_code"] = "MISSING"
        catalogue["medications"][0]["linked_items"][0]["item"] = "MISSING"

        with self.assertRaisesRegex(ValueError, "invalid Item relationship"):
            medicine_catalogue_sync.create_medicine_item_snapshot_manifest(
                catalogue, REVISION_1
            )

    def test_projected_item_remains_searchable_by_the_existing_picker(self):
        catalogue = medicine_item_catalogue()
        _, normalized = medicine_catalogue_sync.create_medicine_item_snapshot_manifest(
            catalogue, REVISION_1
        )
        item = normalized["items"][0]
        item_row = SimpleNamespace(
            name=item["item_code"],
            item_name=item["item_name"],
            description=item["description"],
        )
        medication_row = SimpleNamespace(
            item_code=item["item_code"],
            generic_name="Amlodipine",
        )
        fake_frappe = SimpleNamespace(
            db=SimpleNamespace(
                sql=Mock(side_effect=[[item_row], [medication_row]])
            )
        )

        with patch.object(
            frappe.local,
            "flags",
            SimpleNamespace(in_test=True),
            create=True,
        ), patch.object(drug_search, "frappe", fake_frappe):
            results = drug_search.get_medication_item_query(
                doctype="Item",
                txt="Amlodipine",
                searchfield="item_name",
                start=0,
                page_len=20,
            )

        self.assertEqual(
            results,
            [("AMLODIPINE-5-TAB", "Amlodipine 5mg Tablet", "")],
        )

    def test_repeated_sync_upserts_by_stable_id_without_duplicates(self):
        transport = FakeAtomicTransport()
        state = FakeStateStore()
        catalogue = medicine_item_catalogue()

        first = self._synchronize(catalogue, transport, state, REVISION_1)
        second = self._synchronize(catalogue, transport, state, REVISION_1)

        self.assertEqual(first["status"], "success")
        self.assertEqual(second["status"], "success")
        self.assertEqual(len(transport.items), 1)
        self.assertEqual(len(transport.medications), 1)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(second["skipped_item_codes"], ["AMLODIPINE-5-TAB"])
        self.assertEqual(state.last_successful_revision, REVISION_1)
        self.assertEqual(transport.prices, {"local-item": 345.0})
        self.assertEqual(
            transport.clinic_configuration,
            {"currency": "INR", "clinic_name": "Local Clinic"},
        )

    def test_synchronize_splits_item_catalogue_into_validated_batches(self):
        catalogue = medicine_item_catalogue()
        second_item = deepcopy(catalogue["items"][0])
        second_item["item_code"] = "AMLODIPINE-10-TAB"
        second_item["item_name"] = "Amlodipine 10mg Tablet"
        second_item["description"] = "Amlodipine 10mg Tablet"
        catalogue["items"].append(second_item)
        catalogue["medications"][0]["linked_items"].append(
            {
                "item_code": second_item["item_code"],
                "item": second_item["item_code"],
                "item_group": "Drug",
                "stock_uom": "Nos",
                "is_billable": 1,
            }
        )
        transport = FakeAtomicTransport()
        state = FakeStateStore()

        with patch.object(
            medicine_catalogue_sync,
            "_MEDICINE_ITEM_SYNC_BATCH_SIZE",
            1,
        ):
            result = self._synchronize(catalogue, transport, state)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["created"], 2)
        self.assertEqual(transport.apply_count, 2)
        self.assertEqual(
            set(result["created_item_codes"]),
            {"AMLODIPINE-5-TAB", "AMLODIPINE-10-TAB"},
        )
        self.assertEqual(len(transport.items), 2)

    def test_synchronize_splits_conflicting_batches_and_continues_safely(self):
        catalogue = medicine_item_catalogue()
        second_item = deepcopy(catalogue["items"][0])
        second_item["item_code"] = "AMLODIPINE-10-TAB"
        second_item["item_name"] = "Amlodipine 10mg Tablet"
        second_item["description"] = "Amlodipine 10mg Tablet"
        catalogue["items"].append(second_item)
        catalogue["medications"][0]["linked_items"].append(
            {
                "item_code": second_item["item_code"],
                "item": second_item["item_code"],
                "item_group": "Drug",
                "stock_uom": "Nos",
                "is_billable": 1,
            }
        )
        state = FakeStateStore()

        class SplittingTransport:
            def __init__(self):
                self.calls = 0

            def apply_projection_batch_atomically(
                self, tenant_site, snapshot_manifest, products
            ):
                self.calls += 1
                item_codes = [
                    item["item_code"] for item in products["items"]
                ]
                if len(item_codes) > 1:
                    return {
                        "status": "conflict",
                        "tenant_site": tenant_site,
                        "snapshot_manifest": dict(snapshot_manifest),
                        "created_item_codes": [],
                        "updated_item_codes": [],
                        "skipped_item_codes": [],
                        "missing_item_codes": [],
                        "conflicting_item_codes": item_codes,
                    }
                return {
                    "status": "success",
                    "tenant_site": tenant_site,
                    "snapshot_manifest": dict(snapshot_manifest),
                    "created_item_codes": item_codes,
                    "updated_item_codes": [],
                    "skipped_item_codes": [],
                    "missing_item_codes": [],
                    "conflicting_item_codes": [],
                }

        transport = SplittingTransport()
        with patch.object(
            medicine_catalogue_sync,
            "_MEDICINE_ITEM_SYNC_BATCH_SIZE",
            2,
        ), self.assertLogs(
            "clinify.medicine_catalogue_sync",
            level="INFO",
        ) as logs:
            result = self._synchronize(catalogue, transport, state)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["created"], 2)
        self.assertEqual(transport.calls, 3)
        self.assertEqual(
            set(result["created_item_codes"]),
            {"AMLODIPINE-5-TAB", "AMLODIPINE-10-TAB"},
        )
        log_output = "\n".join(logs.output)
        self.assertIn("normal_batch_attempts=1", log_output)
        self.assertIn("batch_attempts=3", log_output)
        self.assertIn("conflict_responses=1", log_output)
        self.assertIn("split_operations=1", log_output)
        self.assertIn("smallest_batch_size=1", log_output)
        self.assertIn("successful_batch_count=2", log_output)
        self.assertIn("failed_batch_count=1", log_output)
        self.assertIn("category=item_or_snapshot", log_output)
        self.assertNotIn("AMLODIPINE-", log_output)
        self.assertNotIn("key-value", log_output)
        self.assertNotIn("secret-value", log_output)

    def test_medication_conflict_protects_affected_item_and_applies_unrelated_items(self):
        catalogue = medicine_item_catalogue()
        add_catalogue_item(catalogue, "UNRELATED-B", "Unrelated Medicine B")
        add_catalogue_item(catalogue, "UNRELATED-C", "Unrelated Medicine C")

        class MedicationConflictTransport:
            def __init__(self):
                self.calls = []

            def apply_projection_batch_atomically(
                self, tenant_site, snapshot_manifest, products
            ):
                item_codes = [
                    item["item_code"] for item in products["items"]
                ]
                self.calls.append(item_codes)
                if len(self.calls) == 1:
                    return {
                        "status": "conflict",
                        "tenant_site": tenant_site,
                        "snapshot_manifest": dict(snapshot_manifest),
                        "created_item_codes": [],
                        "updated_item_codes": [],
                        "skipped_item_codes": [],
                        "missing_item_codes": [],
                        "conflicting_item_codes": item_codes,
                        "conflicting_medications": ["Amlodipine"],
                    }
                return {
                    "status": "success",
                    "tenant_site": tenant_site,
                    "snapshot_manifest": dict(snapshot_manifest),
                    "created_item_codes": item_codes,
                    "updated_item_codes": [],
                    "skipped_item_codes": [],
                    "missing_item_codes": [],
                    "conflicting_item_codes": [],
                }

        transport = MedicationConflictTransport()
        state = FakeStateStore()
        with self.assertLogs("clinify.medicine_catalogue_sync", level="INFO") as logs:
            result = self._synchronize(catalogue, transport, state)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["created"], 2)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["skipped_item_codes"], ["AMLODIPINE-5-TAB"])
        self.assertEqual(result["conflicting_item_codes"], ["AMLODIPINE-5-TAB"])
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(
            transport.calls[1],
            ["UNRELATED-B", "UNRELATED-C"],
        )
        self.assertIn("split_operations=0", "\n".join(logs.output))

    def test_composition_medication_conflict_protects_transitively_linked_item(self):
        catalogue = medicine_item_catalogue()
        add_catalogue_item(catalogue, "UNRELATED-B", "Unrelated Medicine B")
        catalogue["medications"][0]["combinations"] = [
            {
                "medication": "Combination Ingredient",
                "strength": 1,
                "strength_uom": "Milligram",
            }
        ]
        ingredient = deepcopy(catalogue["medications"][0])
        ingredient.update(
            {
                "name": "Combination Ingredient",
                "generic_name": "Combination Ingredient",
                "strength": 1,
                "linked_items": [],
                "combinations": [],
            }
        )
        catalogue["medications"].append(ingredient)

        class MedicationConflictTransport:
            def __init__(self):
                self.calls = []

            def apply_projection_batch_atomically(
                self, tenant_site, snapshot_manifest, products
            ):
                item_codes = [
                    item["item_code"] for item in products["items"]
                ]
                self.calls.append(item_codes)
                if len(self.calls) == 1:
                    return {
                        "status": "conflict",
                        "tenant_site": tenant_site,
                        "snapshot_manifest": dict(snapshot_manifest),
                        "created_item_codes": [],
                        "updated_item_codes": [],
                        "skipped_item_codes": [],
                        "missing_item_codes": [],
                        "conflicting_item_codes": item_codes,
                        "conflicting_medications": ["Combination Ingredient"],
                    }
                return {
                    "status": "success",
                    "tenant_site": tenant_site,
                    "snapshot_manifest": dict(snapshot_manifest),
                    "created_item_codes": item_codes,
                    "updated_item_codes": [],
                    "skipped_item_codes": [],
                    "missing_item_codes": [],
                    "conflicting_item_codes": [],
                }

        transport = MedicationConflictTransport()
        result = self._synchronize(catalogue, transport, FakeStateStore())

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["skipped_item_codes"], ["AMLODIPINE-5-TAB"])
        self.assertEqual(result["created_item_codes"], ["UNRELATED-B"])
        self.assertEqual(transport.calls[1], ["UNRELATED-B"])

    def test_unmappable_conflicting_medication_fails_safely(self):
        catalogue = medicine_item_catalogue()

        class UnmappableConflictTransport:
            def __init__(self):
                self.calls = 0

            def apply_projection_batch_atomically(
                self, tenant_site, snapshot_manifest, products
            ):
                self.calls += 1
                item_codes = [
                    item["item_code"] for item in products["items"]
                ]
                return {
                    "status": "conflict",
                    "tenant_site": tenant_site,
                    "snapshot_manifest": dict(snapshot_manifest),
                    "created_item_codes": [],
                    "updated_item_codes": [],
                    "skipped_item_codes": [],
                    "missing_item_codes": [],
                    "conflicting_item_codes": item_codes,
                    "conflicting_medications": ["Not In This Catalogue"],
                }

        transport = UnmappableConflictTransport()
        state = FakeStateStore()
        result = self._synchronize(catalogue, transport, state)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "tenant_response_invalid")
        self.assertEqual(transport.calls, 1)
        self.assertIsNone(state.last_successful_revision)

    def test_api_token_transport_reuses_and_closes_one_session(self):
        tenant = SimpleNamespace(site_name="clinic.example.test")
        manifest, normalized = medicine_catalogue_sync.create_snapshot_manifest(
            [product("CLM-AAAA", 500)],
            REVISION_1,
        )
        session = FakeHTTPTransportSession(
            FakeHTTPResponse(
                {
                    "status": "success",
                    "tenant_site": "clinic.example.test",
                    "snapshot_manifest": manifest,
                }
            )
        )
        credentials = SimpleNamespace(
            get_api_credentials=Mock(return_value=("key-value", "secret-value")),
        )

        with patch.object(
            medicine_catalogue_sync.requests,
            "Session",
            return_value=session,
        ) as session_factory, patch.object(
            medicine_catalogue_sync,
            "_tenant_sync_endpoint",
            return_value=(tenant, "https://clinic.example.test/api/method/sync"),
        ), patch.object(
            medicine_catalogue_sync,
            "configured_control_site",
            return_value="control.example.test",
        ):
            with medicine_catalogue_sync.FrappeApiTokenTenantTransport(
                credential_provider=credentials,
            ) as transport:
                for _ in range(2):
                    transport.apply_projection_batch_atomically(
                        "clinic.example.test",
                        manifest,
                        normalized,
                    )

        session_factory.assert_called_once_with()
        self.assertEqual(session.post.call_count, 2)
        self.assertEqual(session.close.call_count, 1)
        request = session.post.call_args
        self.assertEqual(
            request.kwargs["headers"]["Authorization"],
            "token key-value:secret-value",
        )
        self.assertEqual(request.kwargs["timeout"], 20)
        self.assertTrue(request.kwargs["verify"])
        self.assertFalse(request.kwargs["allow_redirects"])

    def test_default_sync_closes_session_when_operation_exits_early(self):
        session = FakeHTTPTransportSession()
        with patch.object(
            medicine_catalogue_sync.requests,
            "Session",
            return_value=session,
        ), patch.object(
            medicine_catalogue_sync,
            "require_control_site_admin",
            side_effect=RuntimeError("not a control site"),
        ), self.assertRaisesRegex(RuntimeError, "not a control site"):
            medicine_catalogue_sync.synchronize_tenant_catalogue(
                "clinic.example.test",
                REVISION_1,
            )

        session.close.assert_called_once_with()

    def test_sync_preserves_tenant_medicines_outside_central_catalogue(self):
        transport = FakeAtomicTransport()
        state = FakeStateStore()
        manual_item = {
            "item_code": "SERIDON",
            "item_name": "Seridon 10mg",
            "item_group": "Drug",
            "disabled": 0,
            "is_stock_item": 0,
            "is_sales_item": 1,
            "stock_uom": "Nos",
            "description": "Tenant-created medicine",
        }
        transport.items["SERIDON"] = dict(manual_item)

        result = self._synchronize(
            medicine_item_catalogue(), transport, state
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(transport.items["SERIDON"], manual_item)
        self.assertEqual(len(transport.items), 2)

    def test_sync_accepts_tenant_owned_item_conflict_as_a_skipped_item(self):
        catalogue = medicine_item_catalogue()
        catalogue["items"].append(
            {
                "item_code": "SERIDON",
                "item_name": "Seridon",
                "item_group": "Drug",
                "disabled": 0,
                "is_stock_item": 1,
                "is_sales_item": 1,
                "stock_uom": "Nos",
                "description": "Seridon",
            }
        )
        catalogue["source_item_codes"] = [
            "AMLODIPINE-10-TAB",
            "AMLODIPINE-5-TAB",
            "SERIDON",
        ]
        state = FakeStateStore()

        class ConflictAwareTransport:
            def apply_projection_batch_atomically(
                self, tenant_site, snapshot_manifest, products
            ):
                return {
                    "status": "success",
                    "tenant_site": tenant_site,
                    "snapshot_manifest": dict(snapshot_manifest),
                    "created_item_codes": ["AMLODIPINE-5-TAB"],
                    "updated_item_codes": [],
                    "skipped_item_codes": ["SERIDON"],
                    "missing_item_codes": [],
                    "conflicting_item_codes": ["SERIDON"],
                }

        result = self._synchronize(
            catalogue,
            ConflictAwareTransport(),
            state,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["conflicting_item_codes"], ["SERIDON"])
        self.assertEqual(state.last_successful_revision, REVISION_1)

    def test_invalid_batch_fails_before_transport_application(self):
        transport = FakeAtomicTransport()
        state = FakeStateStore()
        state.last_successful_revision = REVISION_0
        catalogue = medicine_item_catalogue()
        catalogue["items"][0]["item_name"] = ""

        result = self._synchronize(catalogue, transport, state)

        self.assertEqual(result["error_code"], "invalid_central_batch")
        self.assertEqual(transport.apply_count, 0)
        self.assertEqual(transport.items, {})
        self.assertEqual(state.last_attempt_status, "Failed")
        self.assertEqual(state.last_successful_revision, REVISION_0)

    def test_transport_failure_preserves_last_projection_and_success_revision(self):
        transport = FakeAtomicTransport()
        state = FakeStateStore()
        catalogue = medicine_item_catalogue()
        first = self._synchronize(catalogue, transport, state, REVISION_1)
        previous_items = deepcopy(transport.items)
        previous_prices = dict(transport.prices)
        previous_configuration = dict(transport.clinic_configuration)
        transport.fail_after_first_write = True

        with self.assertLogs("clinify.medicine_catalogue_sync", level="WARNING") as logs:
            failed = self._synchronize(
                medicine_item_catalogue("AMLODIPINE-10-TAB"),
                transport,
                state,
                REVISION_2,
            )

        self.assertEqual(first["status"], "success")
        self.assertEqual(failed["error_code"], "tenant_sync_failed")
        self.assertEqual(transport.items, previous_items)
        self.assertEqual(transport.prices, previous_prices)
        self.assertEqual(transport.clinic_configuration, previous_configuration)
        self.assertEqual(state.last_attempted_revision, REVISION_2)
        self.assertEqual(state.last_successful_revision, REVISION_1)
        self.assertNotIn("private transport detail", " ".join(logs.output))

    def test_disabled_item_state_is_projected_without_deleting_the_item(self):
        transport = FakeAtomicTransport()
        state = FakeStateStore()
        catalogue = medicine_item_catalogue()
        self._synchronize(catalogue, transport, state)

        result = self._synchronize(
            medicine_item_catalogue(disabled=1),
            transport,
            state,
            REVISION_2,
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("AMLODIPINE-5-TAB", transport.items)
        self.assertEqual(transport.items["AMLODIPINE-5-TAB"]["disabled"], 1)

    def test_missing_or_conflicting_tenant_result_does_not_advance_success(self):
        state = FakeStateStore()
        state.last_successful_revision = REVISION_0

        class ConflictingTransport:
            def apply_projection_batch_atomically(self, tenant_site, snapshot_manifest, products):
                return {
                    "status": "failed",
                    "tenant_site": tenant_site,
                    "snapshot_manifest": dict(snapshot_manifest),
                    "created_item_codes": [],
                    "updated_item_codes": [],
                    "skipped_item_codes": [],
                    "conflicting_item_codes": ["AMLODIPINE-5-TAB"],
                    "missing_item_codes": [],
                }

        result = self._synchronize(
            medicine_item_catalogue(),
            ConflictingTransport(),
            state,
            REVISION_1,
        )

        self.assertEqual(result["error_code"], "tenant_identity_conflict")
        self.assertEqual(result["conflicting_item_codes"], ["AMLODIPINE-5-TAB"])
        self.assertEqual(state.last_successful_revision, REVISION_0)

    def test_unreported_tenant_product_is_reported_as_missing(self):
        state = FakeStateStore()

        class IncompleteTransport:
            def apply_projection_batch_atomically(self, tenant_site, snapshot_manifest, products):
                return {
                    "status": "success",
                    "tenant_site": tenant_site,
                    "snapshot_manifest": dict(snapshot_manifest),
                    "created_item_codes": [],
                    "updated_item_codes": [],
                    "skipped_item_codes": [],
                    "missing_item_codes": [],
                    "conflicting_item_codes": [],
                }

        state.last_successful_revision = REVISION_0
        result = self._synchronize(
            medicine_item_catalogue(),
            IncompleteTransport(),
            state,
            REVISION_1,
        )

        self.assertEqual(result["error_code"], "tenant_projection_incomplete")
        self.assertEqual(result["missing_item_codes"], ["AMLODIPINE-5-TAB"])
        self.assertEqual(state.last_successful_revision, REVISION_0)

    def test_tenant_projection_rejects_manual_identity_changes(self):
        projection = SimpleNamespace(flags={"clinify_catalogue_sync": False})
        fake_frappe = SimpleNamespace(
            throw=Mock(side_effect=RuntimeError("rejected")),
        )

        with patch(
            "clinify.clinify.doctype.clinify_medicine_projection.clinify_medicine_projection.frappe",
            fake_frappe,
        ), self.assertRaisesRegex(RuntimeError, "rejected"):
            ClinifyMedicineProjection.validate(projection)

    def test_guest_cannot_administer_central_catalogue(self):
        fake_frappe = SimpleNamespace(
            session=SimpleNamespace(user="Guest"),
            conf={"clinify_control_site": "control.example.test"},
            local=SimpleNamespace(site="control.example.test"),
            only_for=Mock(),
            throw=Mock(side_effect=RuntimeError("rejected")),
        )

        with patch.object(medicine_catalogue_sync, "frappe", fake_frappe), self.assertRaisesRegex(
            RuntimeError,
            "rejected",
        ):
            medicine_catalogue_sync.require_control_site_admin()

        fake_frappe.only_for.assert_not_called()

    def test_configured_control_site_is_respected(self):
        fake_frappe = SimpleNamespace(
            session=SimpleNamespace(user="Administrator"),
            conf={"clinify_control_site": "control.example.test"},
            local=SimpleNamespace(site="control.example.test"),
            only_for=Mock(),
            throw=Mock(side_effect=RuntimeError("rejected")),
        )

        with patch.object(medicine_catalogue_sync, "frappe", fake_frappe):
            self.assertEqual(
                medicine_catalogue_sync.require_control_site_admin(),
                "control.example.test",
            )

        fake_frappe.only_for.assert_called_once_with("System Manager")

    def test_system_manager_on_non_control_site_is_rejected(self):
        fake_frappe = SimpleNamespace(
            session=SimpleNamespace(user="Administrator"),
            conf={"clinify_control_site": "control.example.test"},
            local=SimpleNamespace(site="clinic.example.test"),
            only_for=Mock(),
            throw=Mock(side_effect=RuntimeError("rejected")),
        )

        with patch.object(medicine_catalogue_sync, "frappe", fake_frappe), self.assertRaisesRegex(
            RuntimeError,
            "rejected",
        ):
            medicine_catalogue_sync.require_control_site_admin()

        fake_frappe.only_for.assert_called_once_with("System Manager")

    def test_state_store_keeps_last_success_separate_from_failed_attempt(self):
        database = FakeSyncStateDatabase()

        def get_doc(*args):
            if len(args) == 1 and isinstance(args[0], dict):
                return FakeSyncStateDoc(args[0], database)
            return database.records[args[1]]

        fake_frappe = SimpleNamespace(
            db=database,
            get_doc=get_doc,
        )
        store = medicine_catalogue_sync.FrappeCatalogueSyncStateStore()

        with patch.object(medicine_catalogue_sync, "frappe", fake_frappe), patch.object(
            medicine_catalogue_sync,
            "now_datetime",
            return_value="2026-10-09 02:00:00",
        ):
            store.record_attempt("clinic.example.test", REVISION_1)
            store.record_success(
                "clinic.example.test",
                REVISION_1,
                {"created": 1, "updated": 0, "skipped": 0},
            )
            store.record_attempt("clinic.example.test", REVISION_2)
            store.record_failure(
                "clinic.example.test",
                REVISION_2,
                "tenant_sync_failed",
            )

        state = database.records["clinic.example.test"]
        self.assertEqual(state.last_attempted_revision, REVISION_2)
        self.assertEqual(state.last_attempt_status, "Failed")
        self.assertEqual(state.last_successful_revision, REVISION_1)
        self.assertEqual(state.last_created_count, 1)

    def _tenant_request_frappe(self, database, user="catalogue-sync@example.invalid", site="clinic.example.test"):
        def get_doc(*args):
            if len(args) == 1 and isinstance(args[0], dict):
                if args[0].get("doctype") == "Clinify Medicine Sync State":
                    return FakeSyncStateDoc(args[0], database)
                return FakeProjectionDocument(args[0], database)
            if args[0] == "Clinify Medicine Sync State":
                return database.snapshot_state
            return database.records[args[1]]

        return SimpleNamespace(
            request=SimpleNamespace(method="POST"),
            session=SimpleNamespace(user=user),
            local=SimpleNamespace(site=site),
            conf={
                "clinify_control_site": "control.example.test",
                "CLINIFY_CATALOGUE_SYNC_USER": "catalogue-sync@example.invalid",
            },
            db=database,
            only_for=Mock(),
            throw=Mock(side_effect=RuntimeError("rejected")),
            get_doc=get_doc,
        )

    def _apply_endpoint(
        self,
        fake_frappe,
        records,
        tenant_site="clinic.example.test",
        revision=REVISION_1,
        manifest=None,
        complete_request=True,
    ):
        if manifest is None:
            manifest, _ = medicine_catalogue_sync.create_snapshot_manifest(records, revision)
        with patch.object(
            frappe.local,
            "flags",
            SimpleNamespace(in_test=True),
            create=True,
        ), patch.object(medicine_catalogue_sync, "frappe", fake_frappe), patch.object(
            medicine_catalogue_sync,
            "now_datetime",
            return_value="2026-10-09 02:00:00",
        ):
            try:
                response = medicine_catalogue_sync.apply_tenant_projection_batch(
                    tenant_site=tenant_site,
                    control_site="control.example.test",
                    snapshot_manifest=manifest,
                    products=records,
                )
            except Exception:
                fake_frappe.db.rollback_request()
                raise
            if complete_request:
                fake_frappe.db.commit()
            return response

    def test_tenant_item_catalogue_skips_conflict_and_applies_remaining_items(self):
        database = FakeProjectionDatabase()
        manual_item = {
            "item_code": "SERIDON",
            "item_name": "Seridon 10mg",
            "item_group": "Drug",
            "disabled": 0,
            "is_stock_item": 0,
            "is_sales_item": 1,
            "stock_uom": "Nos",
            "description": "Tenant-created medicine",
        }
        database.records["SERIDON"] = dict(manual_item)
        _, normalized_catalogue = (
            medicine_catalogue_sync.create_medicine_item_snapshot_manifest(
                medicine_item_catalogue(), REVISION_1
            )
        )
        source_medication = normalized_catalogue["medications"][0]
        tenant_medication = dict(source_medication)
        tenant_medication["linked_items"] = [
            SimpleNamespace(
                item_code="AMLODIPINE-10-TAB",
                item="AMLODIPINE-10-TAB",
                item_group="Drug",
                stock_uom="Nos",
                is_billable=1,
            )
        ]
        database.records["Amlodipine"] = FakeMedicineItemDocument(
            tenant_medication, database
        )
        fake_frappe = self._tenant_request_frappe(database)

        def get_doc(*args):
            if len(args) == 1 and isinstance(args[0], dict):
                if args[0].get("doctype") == "Clinify Medicine Sync State":
                    return FakeSyncStateDoc(args[0], database)
                return FakeMedicineItemDocument(args[0], database)
            if args[0] == "Clinify Medicine Sync State":
                return database.snapshot_state
            record = database.records[args[1]]
            if isinstance(record, FakeMedicineItemDocument):
                return record
            return FakeMedicineItemDocument(record, database)

        fake_frappe.get_doc = get_doc
        catalogue = medicine_item_catalogue()
        catalogue["items"].append(
            {
                "item_code": "SERIDON",
                "item_name": "Seridon",
                "item_group": "Drug",
                "disabled": 0,
                "is_stock_item": 1,
                "is_sales_item": 1,
                "stock_uom": "Nos",
                "description": "Seridon",
            }
        )
        catalogue["source_item_codes"] = [
            "AMLODIPINE-10-TAB",
            "AMLODIPINE-5-TAB",
            "SERIDON",
        ]
        manifest, _ = medicine_catalogue_sync.create_medicine_item_snapshot_manifest(
            catalogue, REVISION_1
        )

        with patch.object(
            frappe.local,
            "flags",
            SimpleNamespace(in_test=True),
            create=True,
        ), patch.object(
            medicine_catalogue_sync, "frappe", fake_frappe
        ), patch.object(
            medicine_catalogue_sync,
            "now_datetime",
            return_value="2026-10-09 02:00:00",
        ):
            response = medicine_catalogue_sync.apply_tenant_projection_batch(
                tenant_site="clinic.example.test",
                control_site="control.example.test",
                snapshot_manifest=manifest,
                catalogue=catalogue,
            )
            database.commit()

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["created_item_codes"], ["AMLODIPINE-5-TAB"])
        self.assertEqual(response["skipped_item_codes"], ["SERIDON"])
        self.assertEqual(response["conflicting_item_codes"], ["SERIDON"])
        self.assertEqual(database.records["SERIDON"], manual_item)
        self.assertEqual(
            database.records["AMLODIPINE-5-TAB"].item_name,
            "Amlodipine 5mg Tablet",
        )
        self.assertEqual(
            {
                row["item_code"]
                for row in database.records["Amlodipine"].linked_items
            },
            {"AMLODIPINE-5-TAB", "AMLODIPINE-10-TAB"},
        )

    def test_tenant_endpoint_rejects_unauthorized_user(self):
        fake_frappe = self._tenant_request_frappe(FakeProjectionDatabase(), user="someone@example.invalid")

        with self.assertRaisesRegex(RuntimeError, "rejected"):
            self._apply_endpoint(fake_frappe, [product("CLM-AAAA", 500)])

        fake_frappe.only_for.assert_called_once_with(
            medicine_catalogue_sync.CLINIFY_CATALOGUE_SYNC_ROLE
        )

    def test_tenant_endpoint_rejects_wrong_tenant_context(self):
        fake_frappe = self._tenant_request_frappe(
            FakeProjectionDatabase(),
            site="other.example.test",
        )

        with self.assertRaisesRegex(RuntimeError, "rejected"):
            self._apply_endpoint(fake_frappe, [product("CLM-AAAA", 500)])

    def test_tenant_endpoint_duplicate_delivery_is_idempotent(self):
        database = FakeProjectionDatabase()
        fake_frappe = self._tenant_request_frappe(database)

        first = self._apply_endpoint(fake_frappe, [product("CLM-AAAA", 500)])
        second = self._apply_endpoint(fake_frappe, [product("CLM-AAAA", 500)])

        self.assertEqual(first["created_product_ids"], ["CLM-AAAA"])
        self.assertEqual(second["skipped_product_ids"], ["CLM-AAAA"])
        self.assertEqual(len(database.records), 1)
        self.assertEqual(database.snapshot_state.last_successful_revision, REVISION_1)
        self.assertEqual(
            database.snapshot_state.last_successful_digest,
            first["snapshot_manifest"]["digest"],
        )
        self.assertEqual(database.lock_acquisitions, 2)
        self.assertEqual(database.lock_releases, 2)

    def test_newer_snapshot_keeps_omitted_projection_for_history(self):
        database = FakeProjectionDatabase()
        fake_frappe = self._tenant_request_frappe(database)
        self._apply_endpoint(
            fake_frappe,
            [product("CLM-AAAA", 500), product("CLM-BBBB", 1000)],
            revision=REVISION_1,
        )

        response = self._apply_endpoint(
            fake_frappe,
            [product("CLM-AAAA", 500)],
            revision=REVISION_2,
        )

        self.assertEqual(response["status"], "success")
        self.assertEqual(set(database.records), {"CLM-AAAA", "CLM-BBBB"})
        self.assertEqual(database.snapshot_state.last_successful_revision, REVISION_2)

    def test_projection_lock_lives_until_commit_callback(self):
        database = FakeProjectionDatabase()
        fake_frappe = self._tenant_request_frappe(database)

        result = self._apply_endpoint(
            fake_frappe,
            [product("CLM-AAAA", 500)],
            complete_request=False,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(database.lock_releases, 0)
        self.assertEqual(len(database.after_commit.callbacks), 1)
        database.commit()
        self.assertEqual(database.lock_releases, 1)
        self.assertEqual(len(database.after_rollback.callbacks), 0)

    def test_projection_lock_lives_until_rollback_callback_after_failure(self):
        database = FakeProjectionDatabase(fail_on_insert="CLM-BBBB")
        fake_frappe = self._tenant_request_frappe(database)

        with self.assertRaisesRegex(RuntimeError, "simulated storage failure"):
            self._apply_endpoint(
                fake_frappe,
                [product("CLM-AAAA", 500), product("CLM-BBBB", 1000)],
            )

        self.assertEqual(database.lock_releases, 1)
        self.assertEqual(database.records, {})
        self.assertIsNone(database.snapshot_state)

    def test_request_rollback_after_endpoint_return_reverts_entire_snapshot(self):
        database = FakeProjectionDatabase()
        fake_frappe = self._tenant_request_frappe(database)
        self._apply_endpoint(
            fake_frappe,
            [product("CLM-AAAA", 500)],
            complete_request=False,
        )

        self.assertEqual(database.lock_releases, 0)
        self.assertIn("CLM-AAAA", database.records)
        self.assertIsNotNone(database.snapshot_state)
        database.rollback_request()

        self.assertEqual(database.records, {})
        self.assertIsNone(database.snapshot_state)
        self.assertEqual(database.lock_releases, 1)

    def test_competing_request_cannot_enter_until_transaction_finishes(self):
        coordinator = FakeLockCoordinator()
        first_db = FakeProjectionDatabase(lock_coordinator=coordinator)
        second_db = FakeProjectionDatabase(lock_coordinator=coordinator)
        first_frappe = self._tenant_request_frappe(first_db)
        second_frappe = self._tenant_request_frappe(second_db)

        self._apply_endpoint(
            first_frappe,
            [product("CLM-AAAA", 500)],
            revision=REVISION_2,
            complete_request=False,
        )
        with self.assertRaisesRegex(RuntimeError, "rejected"):
            self._apply_endpoint(
                second_frappe,
                [product("CLM-BBBB", 1000)],
                revision=REVISION_3,
            )

        self.assertEqual(second_db.records, {})
        self.assertEqual(first_db.lock_releases, 0)
        first_db.commit()
        self.assertEqual(first_db.lock_releases, 1)

    def test_tenant_endpoint_updates_existing_projection_without_deleting_inactive_product(self):
        database = FakeProjectionDatabase()
        fake_frappe = self._tenant_request_frappe(database)
        self._apply_endpoint(fake_frappe, [product("CLM-AAAA", 500)], revision=REVISION_1)

        result = self._apply_endpoint(
            fake_frappe,
            [product("CLM-AAAA", 500, active=0)],
            revision=REVISION_2,
        )

        self.assertEqual(result["updated_product_ids"], ["CLM-AAAA"])
        self.assertEqual(database.records["CLM-AAAA"].is_active, 0)
        self.assertEqual(database.records["CLM-AAAA"].catalogue_revision, REVISION_2)

    def test_tenant_endpoint_rejects_stale_or_changed_same_revision_delivery(self):
        database = FakeProjectionDatabase()
        fake_frappe = self._tenant_request_frappe(database)
        current = self._apply_endpoint(
            fake_frappe,
            [product("CLM-AAAA", 500)],
            revision=REVISION_2,
        )
        before = dict(database.records)

        stale = self._apply_endpoint(
            fake_frappe,
            [product("CLM-AAAA", 500), product("CLM-BBBB", 1000)],
            revision=REVISION_1,
        )
        changed = self._apply_endpoint(
            fake_frappe,
            [product("CLM-AAAA", 500, active=0)],
            revision=REVISION_2,
        )

        self.assertEqual(current["status"], "success")
        self.assertEqual(stale["conflicting_product_ids"], ["CLM-AAAA", "CLM-BBBB"])
        self.assertEqual(changed["conflicting_product_ids"], ["CLM-AAAA"])
        self.assertEqual(database.records, before)

    def test_partial_batch_does_not_match_complete_snapshot_manifest(self):
        database = FakeProjectionDatabase()
        fake_frappe = self._tenant_request_frappe(database)
        complete_products = [product("CLM-AAAA", 500), product("CLM-BBBB", 1000)]
        manifest, _ = medicine_catalogue_sync.create_snapshot_manifest(
            complete_products,
            REVISION_1,
        )

        with self.assertRaisesRegex(RuntimeError, "rejected"):
            self._apply_endpoint(
                fake_frappe,
                complete_products[:1],
                manifest=manifest,
            )

        self.assertEqual(database.records, {})
        self.assertIsNone(database.snapshot_state)

    def test_tenant_endpoint_rejects_invalid_batch_before_writes(self):
        database = FakeProjectionDatabase()
        fake_frappe = self._tenant_request_frappe(database)
        manifest, _ = medicine_catalogue_sync.create_snapshot_manifest(
            [product("CLM-AAAA", 500)],
            REVISION_1,
        )

        with self.assertRaisesRegex(RuntimeError, "rejected"):
            self._apply_endpoint(
                fake_frappe,
                [product("CLM-AAAA", None)],
                manifest=manifest,
            )

        self.assertEqual(database.records, {})
        fake_frappe.throw.assert_called_once_with(
            "Medicine catalogue snapshot failed validation."
        )

    def test_tenant_endpoint_rolls_back_partial_application(self):
        database = FakeProjectionDatabase(fail_on_insert="CLM-BBBB")
        fake_frappe = self._tenant_request_frappe(database)

        with self.assertRaisesRegex(RuntimeError, "simulated storage failure"):
            self._apply_endpoint(
                fake_frappe,
                [product("CLM-AAAA", 500), product("CLM-BBBB", 1000)],
            )

        self.assertEqual(database.records, {})
        self.assertIsNone(database.snapshot_state)
        self.assertEqual(database.lock_releases, 1)

        database.fail_on_insert = None
        retry = self._apply_endpoint(
            fake_frappe,
            [product("CLM-AAAA", 500), product("CLM-BBBB", 1000)],
        )
        self.assertEqual(retry["status"], "success")
        self.assertEqual(database.snapshot_state.last_successful_revision, REVISION_1)

    def test_tenant_endpoint_refuses_when_advisory_lock_is_unavailable(self):
        database = FakeProjectionDatabase()
        database.lock_result = 0
        fake_frappe = self._tenant_request_frappe(database)

        with self.assertRaisesRegex(RuntimeError, "rejected"):
            self._apply_endpoint(fake_frappe, [product("CLM-AAAA", 500)])

        self.assertEqual(database.records, {})
        self.assertEqual(database.lock_acquisitions, 1)
        self.assertEqual(database.lock_releases, 0)

    def test_api_token_transport_uses_registered_https_target_and_no_redirects(self):
        tenant = SimpleNamespace(site_name="clinic.example.test")
        manifest, normalized = medicine_catalogue_sync.create_snapshot_manifest(
            [product("CLM-AAAA", 500)],
            REVISION_1,
        )
        session = FakeHTTPTransportSession(
            FakeHTTPResponse(
                {
                    "status": "success",
                    "tenant_site": "clinic.example.test",
                    "snapshot_manifest": manifest,
                }
            )
        )
        credentials = SimpleNamespace(
            get_api_credentials=Mock(return_value=("key-value", "secret-value")),
        )
        transport = medicine_catalogue_sync.FrappeApiTokenTenantTransport(
            credential_provider=credentials,
            http_session=session,
        )

        with patch.object(
            medicine_catalogue_sync,
            "_tenant_sync_endpoint",
            return_value=(tenant, "https://clinic.example.test/api/method/sync"),
        ), patch.object(
            medicine_catalogue_sync,
            "configured_control_site",
            return_value="control.example.test",
        ):
            response = transport.apply_projection_batch_atomically(
                "clinic.example.test",
                manifest,
                normalized,
            )

        request = session.post.call_args
        self.assertEqual(request.args[0], "https://clinic.example.test/api/method/sync")
        self.assertEqual(
            request.kwargs["headers"]["Authorization"],
            "token key-value:secret-value",
        )
        self.assertEqual(request.kwargs["timeout"], 20)
        self.assertTrue(request.kwargs["verify"])
        self.assertFalse(request.kwargs["allow_redirects"])
        self.assertEqual(request.kwargs["json"]["products"], list(normalized))
        self.assertEqual(response["status"], "success")

    def test_api_token_transport_sends_item_catalogue_to_existing_endpoint(self):
        tenant = SimpleNamespace(site_name="clinic.example.test")
        manifest, catalogue = (
            medicine_catalogue_sync.create_medicine_item_snapshot_manifest(
                medicine_item_catalogue(), REVISION_1
            )
        )
        session = FakeHTTPTransportSession(
            FakeHTTPResponse(
                {
                    "status": "success",
                    "tenant_site": "clinic.example.test",
                    "snapshot_manifest": manifest,
                }
            )
        )
        credentials = SimpleNamespace(
            get_api_credentials=Mock(return_value=("key-value", "secret-value")),
        )
        transport = medicine_catalogue_sync.FrappeApiTokenTenantTransport(
            credential_provider=credentials,
            http_session=session,
        )

        with patch.object(
            medicine_catalogue_sync,
            "_tenant_sync_endpoint",
            return_value=(tenant, "https://clinic.example.test/api/method/sync"),
        ), patch.object(
            medicine_catalogue_sync,
            "configured_control_site",
            return_value="control.example.test",
        ):
            transport.apply_projection_batch_atomically(
                "clinic.example.test",
                manifest,
                catalogue,
            )

        payload = session.post.call_args.kwargs["json"]
        self.assertEqual(payload["catalogue"], catalogue)
        self.assertNotIn("products", payload)

    def test_control_transport_target_comes_from_tenant_registry(self):
        tenant = SimpleNamespace(
            name="CLINIC-1",
            site_name="clinic.example.test",
            domain="clinic.example.test",
            enabled=1,
            clinic_status="Active",
            provisioning_status="Ready",
        )
        fake_frappe = SimpleNamespace(
            db=SimpleNamespace(get_value=Mock(return_value=tenant)),
        )
        with patch.dict(
            os.environ,
            {
                "CLINIFY_TENANT_SYNC_ALLOWED_ORIGINS": json.dumps(
                    {"clinic.example.test": "https://clinic.example.test"}
                )
            },
        ), patch.object(medicine_catalogue_sync, "frappe", fake_frappe), patch(
            "clinify.saas.sso._tenant_domain",
            side_effect=lambda domain: domain,
        ), patch(
            "clinify.saas.sso._local_development_enabled",
            return_value=False,
        ):
            resolved_tenant, endpoint = medicine_catalogue_sync._tenant_sync_endpoint(
                "clinic.example.test"
            )

        self.assertIs(resolved_tenant, tenant)
        self.assertEqual(
            endpoint,
            "https://clinic.example.test/api/method/clinify.medicine_catalogue_sync.apply_tenant_projection_batch",
        )
        fake_frappe.db.get_value.assert_called_once_with(
            "Clinify Tenant",
            {"site_name": "clinic.example.test"},
            [
                "name",
                "site_name",
                "domain",
                "enabled",
                "clinic_status",
                "provisioning_status",
            ],
            as_dict=True,
        )

    def test_unlisted_tenant_origin_is_rejected_before_credentials_are_loaded(self):
        tenant = SimpleNamespace(
            name="CLINIC-1",
            site_name="clinic.example.test",
            domain="clinic.example.test",
            enabled=1,
            clinic_status="Active",
            provisioning_status="Ready",
        )
        fake_frappe = SimpleNamespace(
            db=SimpleNamespace(get_value=Mock(return_value=tenant)),
        )
        credentials = SimpleNamespace(get_api_credentials=Mock())
        transport = medicine_catalogue_sync.FrappeApiTokenTenantTransport(
            credential_provider=credentials,
            http_session=FakeHTTPTransportSession(),
        )

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLINIFY_TENANT_SYNC_ALLOWED_ORIGINS", None)
            with patch.object(medicine_catalogue_sync, "frappe", fake_frappe), patch(
                "clinify.saas.sso._tenant_domain",
                side_effect=lambda domain: domain,
            ), patch(
                "clinify.saas.sso._local_development_enabled",
                return_value=False,
            ), self.assertRaisesRegex(ValueError, "origins are not configured"):
                transport.apply_projection_batch_atomically(
                    "clinic.example.test",
                    {"revision": REVISION_1, "product_count": 1, "digest": "a" * 64},
                    (),
                )

        credentials.get_api_credentials.assert_not_called()

    def test_ambiguous_duplicate_origin_entry_is_rejected_before_credentials(self):
        tenant = SimpleNamespace(
            name="CLINIC-1",
            site_name="clinic.example.test",
            domain="clinic.example.test",
            enabled=1,
            clinic_status="Active",
            provisioning_status="Ready",
        )
        fake_frappe = SimpleNamespace(
            db=SimpleNamespace(get_value=Mock(return_value=tenant)),
        )
        credentials = SimpleNamespace(get_api_credentials=Mock())
        transport = medicine_catalogue_sync.FrappeApiTokenTenantTransport(
            credential_provider=credentials,
            http_session=FakeHTTPTransportSession(),
        )
        duplicate_registry = (
            '{"clinic.example.test":"https://clinic.example.test",'
            '"clinic.example.test":"https://evil.example.test"}'
        )

        with patch.dict(
            os.environ,
            {"CLINIFY_TENANT_SYNC_ALLOWED_ORIGINS": duplicate_registry},
        ), patch.object(medicine_catalogue_sync, "frappe", fake_frappe), patch(
            "clinify.saas.sso._tenant_domain",
            side_effect=lambda domain: domain,
        ), patch(
            "clinify.saas.sso._local_development_enabled",
            return_value=False,
        ), self.assertRaisesRegex(ValueError, "malformed"):
            transport.apply_projection_batch_atomically(
                "clinic.example.test",
                {"revision": REVISION_1, "product_count": 1, "digest": "a" * 64},
                (),
            )

        credentials.get_api_credentials.assert_not_called()


if __name__ == "__main__":
    unittest.main()
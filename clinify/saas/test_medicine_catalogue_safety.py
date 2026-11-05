import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from clinify import medicine_catalogue
from clinify.api import drug_search
from clinify.importers import drug_importer
from clinify.saas import tenant_bootstrap


class TestMedicineCatalogueIdentity(unittest.TestCase):
    def test_different_strengths_of_same_ingredient_do_not_match(self):
        medication = SimpleNamespace(
            name="Amlodipine",
            strength=5,
            strength_uom="Unit",
            dosage_form="Tablet",
        )

        self.assertIsNone(
            medicine_catalogue.item_medication_identity_issue(
                "Amlodipine 5 Tablet",
                medication,
            )
        )
        self.assertIn(
            "declares strength 10",
            medicine_catalogue.item_medication_identity_issue(
                "Amlodipine 10 Tablet",
                medication,
            ),
        )

    def test_dosage_form_mismatch_is_rejected(self):
        medication = SimpleNamespace(
            name="Amoxicillin",
            strength=500,
            strength_uom="Unit",
            dosage_form="Tablet",
        )

        issue = medicine_catalogue.item_medication_identity_issue(
            "Amoxicillin 500 Capsule",
            medication,
        )

        self.assertIn("dosage form capsule", issue)

    def test_unstructured_item_name_fails_closed(self):
        medication = SimpleNamespace(
            name="Paracetamol",
            strength=500,
            strength_uom="Unit",
            dosage_form="Tablet",
        )

        self.assertIsNotNone(
            medicine_catalogue.item_medication_identity_issue(
                "Paracetamol",
                medication,
            )
        )


class TestMedicineCatalogueSourceValidation(unittest.TestCase):
    def test_incomplete_batch_is_rejected_without_mutating_last_good_batch(self):
        last_good_batch = [
            {
                "generic_name": "Paracetamol",
                "strength": 500,
                "strength_uom": "Unit",
                "dosage_form": "Tablet",
            }
        ]
        snapshot = [dict(record) for record in last_good_batch]
        incomplete_batch = [
            {
                "generic_name": "Paracetamol",
                "strength": 650,
                "strength_uom": "Unit",
            }
        ]

        with self.assertRaisesRegex(ValueError, "dosage_form"):
            medicine_catalogue.validate_medicine_source_batch(incomplete_batch)

        self.assertEqual(last_good_batch, snapshot)

    def test_current_schema_rejects_multiple_strengths_in_one_batch(self):
        source_rows = [
            {
                "generic_name": "Paracetamol",
                "strength": 500,
                "strength_uom": "Unit",
                "dosage_form": "Tablet",
            },
            {
                "generic_name": "Paracetamol",
                "strength": 650,
                "strength_uom": "Unit",
                "dosage_form": "Tablet",
            },
        ]

        with self.assertRaisesRegex(ValueError, "cannot represent multiple strengths"):
            medicine_catalogue.validate_medicine_source_batch(source_rows)

    def test_existing_medication_strength_conflict_is_not_reused(self):
        medication = SimpleNamespace(
            name="Paracetamol",
            strength=650,
            strength_uom="Unit",
            dosage_form="Tablet",
        )
        fake_frappe = SimpleNamespace(
            db=SimpleNamespace(exists=lambda *args: "Paracetamol"),
            get_doc=lambda *args: medication,
            throw=unittest.mock.Mock(side_effect=RuntimeError),
        )

        with patch.object(drug_importer, "frappe", fake_frappe):
            with self.assertRaises(RuntimeError):
                drug_importer.get_or_create_medication(
                    "Paracetamol",
                    500,
                    "Unit",
                    "Tablet",
                    "Analgesic",
                )

        fake_frappe.throw.assert_called_once()


class TestDrugPrescriptionDefaults(unittest.TestCase):
    def _lookup(self, item_name, medication):
        item = SimpleNamespace(name="ITEM-1", item_name=item_name)
        fake_frappe = SimpleNamespace(
            get_doc=lambda doctype, name: item if doctype == "Item" else medication,
            get_all=lambda *args, **kwargs: [SimpleNamespace(parent=medication.name)],
        )
        with patch.object(
            frappe.local,
            "flags",
            SimpleNamespace(in_test=True),
            create=True,
        ), patch.object(drug_search, "frappe", fake_frappe):
            return drug_search.get_drug_prescription_defaults("ITEM-1")

    def test_invalid_item_mapping_returns_no_medication_defaults(self):
        result = self._lookup("Amlodipine 10 Tablet", None)

        self.assertTrue(result["mapping_valid"])
        self.assertIsNone(result["medication"])
        self.assertEqual(result["strength"], 0)
        self.assertIsNone(result["strength_uom"])
        self.assertIsNone(result["dosage_form"])
        self.assertEqual(result["dosage"], "0-0-0")
        self.assertEqual(result["period"], "0 Day")
        self.assertTrue(result["catalogue_only"])

    def test_valid_mapping_keeps_editable_dosage_and_duration_defaults(self):
        result = self._lookup("Paracetamol 500 Tablet", None)

        self.assertTrue(result["mapping_valid"])
        self.assertIsNone(result["medication"])
        self.assertEqual(result["dosage"], "0-0-0")
        self.assertEqual(result["period"], "0 Day")
        self.assertTrue(result["catalogue_only"])

        schema_path = (
            Path(__file__).resolve().parents[2]
            / ".."
            / "healthcare"
            / "healthcare"
            / "healthcare"
            / "doctype"
            / "drug_prescription"
            / "drug_prescription.json"
        ).resolve()
        with schema_path.open(encoding="utf-8") as handle:
            fields = {field["fieldname"]: field for field in json.load(handle)["fields"]}

        for fieldname in ("dosage", "period"):
            self.assertEqual(fields[fieldname].get("fetch_if_empty"), 1)
            self.assertFalse(fields[fieldname].get("read_only", 0))


class TestTenantMedicineBootstrap(unittest.TestCase):
    def test_tenant_catalogue_provisioning_does_not_seed_medicines(self):
        fake_db = SimpleNamespace(
            exists=lambda doctype, value: (
                False if doctype == "DocType" else value == "CONSULTATION"
            ),
            commit=unittest.mock.Mock(),
        )
        fake_frappe = SimpleNamespace(db=fake_db)

        with patch.object(tenant_bootstrap, "frappe", fake_frappe), \
             patch("clinify.tenant_dental_config.frappe", fake_frappe), \
             patch(
                 "clinify.importers.drug_importer.import_common_medicines"
             ) as import_common, \
             patch("clinify.patches.create_lab_test_template_dev.execute"), \
             patch("clinify.dev.dental_catalogue.install"):
            tenant_bootstrap._ensure_clinify_catalogue()

        import_common.assert_not_called()
        fake_db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
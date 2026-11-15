import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from clinify import medicine_catalogue_import
from clinify.medicine_catalogue_sync import (
    normalize_product_record,
    validate_product_batch,
)


def source_row(
    item_code="OMDB-ITEM-1",
    *,
    medication_name="Medication 1",
    medicine_name="Marketed Name 500 Tablet",
    composition="Example ingredient (500mg)",
    strength=500,
    strength_uom="Milligram",
    dosage_form="Tablet",
    manufacturer="Example Manufacturer",
    item_disabled=0,
    medication_disabled=0,
    is_combination=0,
    description="Example pack",
):
    return {
        "item_code": item_code,
        "medicine_name": medicine_name,
        "item_disabled": item_disabled,
        "item_description": description,
        "linked_item_name": f"Link-{item_code}",
        "manufacturer": manufacturer,
        "linked_item_description": description,
        "medication_name": medication_name,
        "composition": composition,
        "is_combination": is_combination,
        "strength": strength,
        "strength_uom": strength_uom,
        "dosage_form": dosage_form,
        "medication_disabled": medication_disabled,
    }


class TestCentralMedicineCataloguePopulation(unittest.TestCase):
    def _run(self, rows):
        fake_db = SimpleNamespace(
            sql=Mock(return_value=rows),
            insert=Mock(),
            set_value=Mock(),
            commit=Mock(),
            rollback=Mock(),
        )
        fake_frappe = SimpleNamespace(db=fake_db)
        with patch.object(medicine_catalogue_import, "frappe", fake_frappe):
            report = medicine_catalogue_import.build_central_medicine_product_dry_run()
        return report, fake_db

    def test_selects_only_active_openmedsdb_drug_items(self):
        report, fake_db = self._run([source_row()])

        query = fake_db.sql.call_args.args[0]
        self.assertIn("i.item_group = 'Drug'", query)
        self.assertIn("i.name LIKE 'OMDB-%'", query)
        self.assertIn("i.disabled = 0", query)
        self.assertEqual(report["summary"]["source_items"], 1)

    def test_rejects_items_without_exactly_one_linked_medication(self):
        no_link = source_row(medication_name=None)
        multiple_links = [
            source_row(item_code="OMDB-MULTI", medication_name="Medication A"),
            source_row(item_code="OMDB-MULTI", medication_name="Medication B"),
        ]

        report, _ = self._run([no_link, *multiple_links])

        self.assertEqual(report["summary"]["mapping_candidates"], 0)
        self.assertEqual(
            report["mapping_errors"],
            [
                {"item_code": "OMDB-ITEM-1", "reason": "NO_LINKED_MEDICATION"},
                {
                    "item_code": "OMDB-MULTI",
                    "reason": "MULTIPLE_LINKED_MEDICATIONS",
                },
            ],
        )

    def test_maps_marketed_name_composition_strength_form_and_manufacturer(self):
        report, _ = self._run([source_row()])
        candidate = report["candidates"][0]

        self.assertEqual(candidate["medicine_name"], "Marketed Name 500 Tablet")
        self.assertEqual(candidate["composition"], "Example ingredient (500mg)")
        self.assertEqual(candidate["ingredient_name"], "Example ingredient")
        self.assertEqual(candidate["strength"], 500)
        self.assertEqual(candidate["strength_uom"], "Milligram")
        self.assertEqual(candidate["dosage_form"], "Tablet")
        self.assertEqual(candidate["manufacturer"], "Example Manufacturer")

    def test_combination_strength_is_blank_and_ingredient_is_unresolved(self):
        row = source_row(
            item_code="OMDB-COMBO",
            composition="Ingredient A (10mg) + Ingredient B (20mg)",
            strength=0,
            strength_uom="Unit",
            is_combination=1,
        )
        report, _ = self._run([row])
        candidate = report["candidates"][0]

        self.assertEqual(candidate["ingredient_name"], "")
        self.assertEqual(candidate["strength"], "")
        self.assertEqual(candidate["strength_uom"], "")
        self.assertIn(
            "UNRESOLVED_COMBINATION_INGREDIENT",
            candidate["unresolved_reasons"],
        )
        self.assertEqual(report["summary"]["unresolved_combinations"], 1)

    def test_active_state_requires_both_source_records_active(self):
        report, _ = self._run([source_row(medication_disabled=1)])

        self.assertEqual(report["candidates"][0]["is_active"], 0)

    def test_missing_provenance_is_not_inferred_from_item_code_or_description(self):
        report, _ = self._run([source_row()])
        candidate = report["candidates"][0]

        self.assertEqual(candidate["source_provider"], "OpenMedsDB")
        self.assertEqual(candidate["source_identifier"], "")
        self.assertEqual(candidate["source_revision"], "")
        self.assertEqual(candidate["source_updated_at"], "")
        self.assertEqual(candidate["prescription_required"], "")
        self.assertEqual(candidate["source_mrp"], "")
        self.assertEqual(candidate["source_selling_price"], "")
        self.assertEqual(candidate["pack_label"], "")
        self.assertEqual(
            candidate["unresolved_provenance_fields"],
            [
                "source_identifier",
                "source_revision",
                "source_updated_at",
                "prescription_required",
                "source_mrp",
                "source_selling_price",
                "pack_label",
            ],
        )

    def test_duplicate_commercial_identities_include_every_source_record(self):
        first = source_row(item_code="OMDB-DUP-1")
        second = source_row(item_code="OMDB-DUP-2")
        second["linked_item_description"] = "Example pack"

        report, _ = self._run([first, second])

        self.assertEqual(report["summary"]["duplicate_commercial_identities"], 1)
        details = report["duplicate_commercial_identity_groups"][0]["items"]
        self.assertEqual(
            [detail["item_code"] for detail in details],
            ["OMDB-DUP-1", "OMDB-DUP-2"],
        )
        self.assertEqual(
            report["duplicate_commercial_identity_groups"][0]["classification"],
            "SAME_COMMERCIAL_IDENTITY_NO_STORED_DISTINCTION",
        )

    def test_description_difference_classifies_missing_pack_uncertainty(self):
        first = source_row(item_code="OMDB-DUP-1", description="Pack 10")
        second = source_row(item_code="OMDB-DUP-2", description="Pack 20")

        report, _ = self._run([first, second])

        self.assertEqual(
            report["duplicate_commercial_identity_groups"][0]["classification"],
            "POSSIBLY_DISTINCT_PRODUCTS_PACK_INFORMATION_MISSING",
        )

    def test_duplicate_source_identifier_detection_uses_provider_and_identifier(self):
        duplicate_records = [
            {
                "central_product_id": "CLM-AAAA",
                "source_provider": "OpenMedsDB",
                "source_identifier": "slug-1",
            },
            {
                "central_product_id": "CLM-BBBB",
                "source_provider": "openmedsdb",
                "source_identifier": "SLUG-1",
            },
        ]

        groups = medicine_catalogue_import._duplicate_source_identifier_groups(
            duplicate_records
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["central_product_ids"], ["CLM-AAAA", "CLM-BBBB"])
        self.assertEqual(
            medicine_catalogue_import._duplicate_source_identifier_groups(
                [{"source_provider": "OpenMedsDB", "source_identifier": ""}]
            ),
            [],
        )

    def test_candidate_passes_existing_product_normalizer_and_batch_validator(self):
        report, _ = self._run([source_row()])
        candidate = report["candidates"][0]

        normalized = normalize_product_record(candidate)
        validated = validate_product_batch([candidate])

        self.assertEqual(normalized["medicine_name"], "Marketed Name 500 Tablet")
        self.assertEqual(len(validated), 1)
        self.assertEqual(
            report["central_product_id_strategy"]["dry_run_id_label"],
            "DRY_RUN_ONLY_ID",
        )
        self.assertIsNone(report["central_product_id_strategy"]["persisted_id_policy"])

    def test_repeated_dry_runs_are_deterministic_and_do_not_write(self):
        rows = [source_row()]
        first, first_db = self._run(rows)
        second, second_db = self._run(rows)

        self.assertEqual(first, second)
        for fake_db in (first_db, second_db):
            fake_db.insert.assert_not_called()
            fake_db.set_value.assert_not_called()
            fake_db.commit.assert_not_called()
            fake_db.rollback.assert_not_called()


if __name__ == "__main__":
    unittest.main()

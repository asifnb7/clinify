import unittest
from decimal import Decimal

from clinify.importers.openmedsdb_importer import (
    DEFAULT_PRESCRIPTION_DOSAGE,
    DEFAULT_PRESCRIPTION_DURATION,
    make_item_display_name,
    make_item_identity,
    make_medication_identity,
    needs_item_name_repair,
    normalize_row,
    normalize_uom,
    parse_strength,
    parse_item_medicine_identity,
    row_medication_identity_check,
    split_ingredient_text,
    verify_batch_invariants,
)


class TestOpenMedsDBImporter(unittest.TestCase):

    def test_uom_normalization(self):
        self.assertEqual(normalize_uom("mg"), "Milligram")
        self.assertEqual(normalize_uom("g"), "Gram")
        self.assertEqual(normalize_uom("mcg"), "Microgram")
        self.assertEqual(normalize_uom("µg"), "Microgram")
        self.assertEqual(normalize_uom("ml"), "Millilitre")

    def test_unknown_uom_is_not_silently_converted(self):
        self.assertIsNone(normalize_uom("xyz"))

    def test_strength_parsing(self):
        strength, uom = parse_strength("Amlodipine 5 mg Tablet")
        self.assertEqual(strength, Decimal("5"))
        self.assertEqual(uom, "mg")

    def test_percentage_strength_parsing(self):
        identity = parse_item_medicine_identity("Hydrocortisone 1% w/w Cream")
        self.assertIsNone(identity["strength"])
        self.assertIsNone(identity["strength_uom"])
        self.assertEqual(identity["dosage_form"], "cream")

    def test_strength_specific_identities_are_distinct(self):
        five = make_medication_identity(
            "Amlodipine",
            "5 mg",
            "Tablet",
        )
        ten = make_medication_identity(
            "Amlodipine",
            "10 mg",
            "Tablet",
        )
        self.assertNotEqual(five, ten)

    def test_dosage_forms_are_part_of_identity(self):
        tablet = make_medication_identity(
            "Amlodipine",
            "5 mg",
            "Tablet",
        )
        capsule = make_medication_identity(
            "Amlodipine",
            "5 mg",
            "Capsule",
        )
        self.assertNotEqual(tablet, capsule)

    def test_source_id_is_deterministic(self):
        first = make_item_identity("OPENMEDSDB-12345")
        second = make_item_identity("OPENMEDSDB-12345")
        self.assertEqual(first, second)

    def test_different_source_ids_have_different_item_identity(self):
        first = make_item_identity("OPENMEDSDB-12345")
        second = make_item_identity("OPENMEDSDB-12346")
        self.assertNotEqual(first, second)

    def test_item_display_name_uses_generic_identity_not_brand(self):
        row = {
            "Medicine Name": "Voriad 200mg Tablet",
            "Generic/Composition": "Voriconazole (200mg)",
            "Dosage Form": "Tablet",
            "Manufacturer": "Test Manufacturer",
            "Pack": "10 Tablets",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-DISPLAY-001",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

        normalized = normalize_row(row)

        self.assertEqual(
            make_item_display_name(normalized),
            "Voriad 200mg Tablet",
        )

    def test_combination_item_display_name_does_not_duplicate_form(self):
        row = {
            "Medicine Name": "Benidin CH 4mg/12.5mg Tablet",
            "Generic/Composition": (
                "Benidipine (4mg)+ Chlorthalidone (12.5mg)"
            ),
            "Dosage Form": "Tablet",
            "Manufacturer": "Test Manufacturer",
            "Pack": "10 Tablets",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-DISPLAY-002",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

        normalized = normalize_row(row)

        self.assertEqual(
            make_item_display_name(normalized),
            "Benidin CH 4mg/12.5mg Tablet",
        )

    def test_item_display_name_adds_missing_strength_and_form(self):
        row = {
            "Medicine Name": "Example Medicine",
            "Generic/Composition": "Example Medicine 20 mg",
            "Dosage Form": "Tablet",
            "Manufacturer": "Test Manufacturer",
            "Pack": "10 Tablets",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-DISPLAY-003",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

        normalized = normalize_row(row)

        self.assertEqual(
            make_item_display_name(normalized),
            "Example Medicine Tablet",
        )

    def test_combination_is_preserved(self):
        ingredients = split_ingredient_text(
            "Amoxicillin 500 mg + Clavulanic Acid 125 mg"
        )
        self.assertEqual(len(ingredients), 2)

        row = {
            "Medicine Name": "Amoxicillin + Clavulanic Acid Tablet",
            "Generic/Composition": (
                "Amoxicillin 500 mg + Clavulanic Acid 125 mg"
            ),
            "Dosage Form": "Tablet",
            "Manufacturer": "Test Manufacturer",
            "Pack": "10 Tablets",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-001",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

        normalized = normalize_row(row)

        self.assertTrue(normalized.is_combination)
        self.assertIn("Amoxicillin 500 mg", normalized.ingredient_text)
        self.assertIn("Clavulanic Acid 125 mg", normalized.ingredient_text)

    def test_multi_strength_is_flagged(self):
        row = {
            "Medicine Name": "Test Combination",
            "Generic/Composition": "Drug A 5 mg + Drug B 10 mg",
            "Dosage Form": "Tablet",
            "Manufacturer": "Test Manufacturer",
            "Pack": "10 Tablets",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-002",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

        normalized = normalize_row(row)

        self.assertTrue(normalized.is_multi_strength)
        self.assertEqual(
            normalized.ingredient_strengths,
            (
                ("Drug A 5 mg", "5 mg", "mg"),
                ("Drug B 10 mg", "10 mg", "mg"),
            ),
        )
        self.assertNotIn(
            "multiple_strength_expressions",
            normalized.review_reasons,
        )

    def test_unknown_uom_requires_review(self):
        row = {
            "Medicine Name": "Test Medicine",
            "Generic/Composition": "Test Medicine 5 xyz",
            "Dosage Form": "Tablet",
            "Manufacturer": "Test Manufacturer",
            "Pack": "10 Tablets",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-003",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

        normalized = normalize_row(row)

        self.assertTrue(normalized.review_required)

    def test_normalized_record_has_stable_identities(self):
        row = {
            "Medicine Name": "Amlodipine 5 mg Tablet",
            "Generic/Composition": "Amlodipine 5 mg",
            "Dosage Form": "Tablet",
            "Manufacturer": "Test Manufacturer",
            "Pack": "10 Tablets",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-004",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

        first = normalize_row(row)
        second = normalize_row(row)

        self.assertEqual(
            first.medication_identity,
            second.medication_identity,
        )
        self.assertEqual(
            first.item_identity,
            second.item_identity,
        )


    def test_item_display_name_uses_generic_not_brand(self):
        row = {
            "Medicine Name": "3 Cef 250mg Tablet",
            "Generic/Composition": "Cefprozil (250mg)",
            "Dosage Form": "Tablet",
            "Manufacturer": "Alkem Laboratories Ltd",
            "Pack": "10 tablets",
            "Prescription Required": "prescription",
            "Source ID": "3-cef-250mg-tablet-58257",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

        normalized = normalize_row(row)

        self.assertFalse(normalized.review_required)
        self.assertEqual(
            make_item_display_name(normalized),
            "3 Cef 250mg Tablet",
        )

    def test_item_identity_is_deterministic_omdb_code(self):
        identity = make_item_identity("3-cef-250mg-tablet-58257")

        self.assertRegex(identity, r"^OMDB-[0-9A-F]{20}$")
        self.assertEqual(
            identity,
            make_item_identity("3-cef-250mg-tablet-58257"),
        )

    def test_item_display_name_is_deterministic_and_strength_specific(self):
        first = make_item_display_name(normalize_row(self._amlodipine_10_row()))
        second = make_item_display_name(normalize_row(self._amlodipine_10_row()))

        self.assertEqual(first, second)
        self.assertEqual(first, "Amlong 10 Tablet")

    def test_identity_safety_accepts_generated_item_name(self):
        normalized = normalize_row(self._amlodipine_10_row())

        self.assertIsNone(
            row_medication_identity_check(
                normalized,
                make_item_display_name(normalized),
            )
        )

    def test_identity_safety_rejects_technical_item_name(self):
        normalized = normalize_row(self._amlodipine_10_row())

        self.assertIsNotNone(
            row_medication_identity_check(
                normalized,
                "OMDB-6AB77065BE5DE69C1C75",
            )
        )

    def test_needs_item_name_repair_only_for_technical_names(self):
        self.assertTrue(needs_item_name_repair("OMDB-ABC123", "OMDB-ABC123"))
        self.assertTrue(needs_item_name_repair("", "OMDB-ABC123"))
        self.assertFalse(
            needs_item_name_repair("Cefprozil 250 mg Tablet", "OMDB-ABC123")
        )
        # Legacy brand-based names are human-readable: never overwritten.
        self.assertFalse(
            needs_item_name_repair("3 Cef 250mg Tablet", "OMDB-ABC123")
        )

    def test_batch_gate_passes_clean_rows(self):
        rows = [
            normalize_row(self._amlodipine_10_row()),
            normalize_row(self._cefprozil_row()),
        ]

        self.assertEqual(verify_batch_invariants(rows), [])

    def test_batch_gate_excludes_review_and_combination_rows(self):
        review_row = {
            "Medicine Name": "Test Medicine",
            "Generic/Composition": "Test Medicine 5 xyz",
            "Dosage Form": "Tablet",
            "Manufacturer": "Test Manufacturer",
            "Pack": "10 Tablets",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-GATE-001",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }
        combination_row = {
            "Medicine Name": "Amoxicillin + Clavulanic Acid Tablet",
            "Generic/Composition": (
                "Amoxicillin 500 mg + Clavulanic Acid 125 mg"
            ),
            "Dosage Form": "Tablet",
            "Manufacturer": "Test Manufacturer",
            "Pack": "10 Tablets",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-GATE-002",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

        self.assertEqual(
            verify_batch_invariants(
                [normalize_row(review_row), normalize_row(combination_row)]
            ),
            [],
        )

    def test_batch_gate_allows_percent_strength_rows(self):
        row = {
            "Medicine Name": "Hydrocortisone 1% Cream",
            "Generic/Composition": "Hydrocortisone 1% w/w",
            "Dosage Form": "Cream",
            "Manufacturer": "Test Manufacturer",
            "Pack": "15 g",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-GATE-003",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

        normalized = normalize_row(row)

        self.assertFalse(normalized.review_required)
        self.assertEqual(normalized.strength, Decimal("1"))
        self.assertEqual(normalized.strength_uom, "Percent")
        self.assertEqual(verify_batch_invariants([normalized]), [])

    def test_prescription_default_constants(self):
        self.assertEqual(DEFAULT_PRESCRIPTION_DOSAGE, "0-0-0")
        self.assertEqual(DEFAULT_PRESCRIPTION_DURATION, "0 Day")

    @staticmethod
    def _amlodipine_10_row():
        return {
            "Medicine Name": "Amlong 10",
            "Generic/Composition": "Amlodipine 10 mg",
            "Dosage Form": "Tablet",
            "Manufacturer": "Test Manufacturer",
            "Pack": "10 Tablets",
            "Prescription Required": "prescription",
            "Source ID": "OMDB-TEST-GATE-AML-10",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }

    @staticmethod
    def _cefprozil_row():
        return {
            "Medicine Name": "3 Cef 250mg Tablet",
            "Generic/Composition": "Cefprozil (250mg)",
            "Dosage Form": "Tablet",
            "Manufacturer": "Alkem Laboratories Ltd",
            "Pack": "10 tablets",
            "Prescription Required": "prescription",
            "Source ID": "3-cef-250mg-tablet-58257",
            "Source": "OpenMedsDB",
            "Source Revision": "test",
        }


if __name__ == "__main__":
    unittest.main()

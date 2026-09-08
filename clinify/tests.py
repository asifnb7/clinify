import frappe
import frappe.test_runner


def before_tests():
    """Prepare shared master data and test-runner compatibility for Clinify/Healthcare tests."""

    # Healthcare Patient tests require the standard Gender records.
    for gender in ("MALE", "FEMALE"):
        if not frappe.db.exists("Gender", gender):
            frappe.get_doc(
                {
                    "doctype": "Gender",
                    "gender": gender,
                }
            ).insert(ignore_permissions=True)

    # Some Healthcare dependency graphs eventually reach Payment Gateway
    # through Payment Gateway Account. The Payment Gateway DocType is not
    # present in this ERPNext installation, so exclude that unsupported
    # test dependency wherever it occurs in the dependency graph.
    #
    # This affects only the Frappe test-runner process and does not change
    # application/runtime behavior.
    if not getattr(frappe.test_runner, "_clinify_dependency_patch", False):
        original_get_dependencies = frappe.test_runner.get_dependencies

        def clinify_get_dependencies(doctype):
            dependencies = original_get_dependencies(doctype)

            return [
                dependency
                for dependency in dependencies
                if dependency not in ("Payment Gateway", "Payment Gateway Account")
            ]

        frappe.test_runner.get_dependencies = clinify_get_dependencies
        frappe.test_runner._clinify_dependency_patch = True

    # ERPNext's generic Opportunity test fixture omits the mandatory
    # company field, even though ERPNext's own make_opportunity() helper
    # defaults it to "_Test Company". The generic Frappe test-record loader
    # inserts the fixture directly before the Opportunity test module can
    # supply that default.
    #
    # During tests only, populate the missing company on the copied test
    # record. This does not modify ERPNext core or production/runtime data.
    # Healthcare v15 test helpers create a few mandatory-company documents
    # without assigning the standard _Test Company. Keep this compatibility
    # adjustment strictly inside Clinify's test process; never alter Healthcare
    # core or real tenant provisioning.
    if not getattr(frappe, "_clinify_healthcare_company_patch", False):
        original_new_doc = frappe.new_doc

        def clinify_new_doc(doctype, *args, **kwargs):
            doc = original_new_doc(doctype, *args, **kwargs)

            if doctype in (
                "Healthcare Service Unit",
                "Therapy Plan",
                "Lab Test",
                "Therapy Session",
            ):
                if not doc.get("company"):
                    doc.company = "_Test Company"

            return doc

        frappe.new_doc = clinify_new_doc
        frappe._clinify_healthcare_company_patch = True

    if not getattr(frappe.test_runner, "_clinify_opportunity_company_patch", False):
        original_make_test_objects = frappe.test_runner.make_test_objects

        def clinify_make_test_objects(
            doctype, test_records=None, verbose=None, reset=False, commit=False
        ):
            if doctype in ("Opportunity", "BOM") and test_records:
                test_records = [
                    dict(record, company="_Test Company")
                    if not record.get("company")
                    else record
                    for record in test_records
                ]

            return original_make_test_objects(
                doctype, test_records, verbose, reset, commit=commit
            )

        frappe.test_runner.make_test_objects = clinify_make_test_objects
        frappe.test_runner._clinify_opportunity_company_patch = True

    # Clinify intentionally makes Patient Encounter.encounter_comment
    # mandatory. Some upstream Healthcare test helpers create encounters
    # without this field.
    #
    # During tests only, provide a deterministic test comment before the
    # normal insert/mandatory validation runs. This preserves the mandatory
    # validation itself and does not alter production/runtime behavior.
    if not getattr(frappe.test_runner, "_clinify_encounter_insert_patch", False):
        from healthcare.healthcare.doctype.patient_encounter.patient_encounter import (
            PatientEncounter,
        )

        original_insert = PatientEncounter.insert

        def clinify_test_insert(self, *args, **kwargs):
            if frappe.flags.in_test and not self.encounter_comment:
                self.encounter_comment = "Clinify automated test encounter"

            return original_insert(self, *args, **kwargs)

        PatientEncounter.insert = clinify_test_insert
        frappe.test_runner._clinify_encounter_insert_patch = True

    frappe.db.commit()

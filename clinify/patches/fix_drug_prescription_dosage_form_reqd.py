import frappe


def execute():
    field_name = frappe.db.get_value(
        "DocField",
        {
            "parent": "Drug Prescription",
            "fieldname": "dosage_form",
        },
        "name",
    )

    if field_name:
        frappe.db.set_value(
            "DocField",
            field_name,
            "reqd",
            0,
            update_modified=False,
        )

        frappe.clear_cache(doctype="Drug Prescription")
        frappe.db.commit()

        print("Drug Prescription.dosage_form reqd set to 0")
    else:
        print("Drug Prescription.dosage_form DocField not found")

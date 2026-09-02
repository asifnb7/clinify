import frappe


def execute():
    updates = {
        "dosage_form": {
            "reqd": 0,
            "in_list_view": 0,
            "columns": 0,
        },
        "drug_code": {
            "in_list_view": 1,
            "columns": 2,
        },
        "drug_name": {
            "in_list_view": 1,
            "columns": 3,
        },
        "dosage": {
            "in_list_view": 1,
            "columns": 2,
        },
        "period": {
            "in_list_view": 1,
            "columns": 1,
        },
        "custom_instruction": {
            "in_list_view": 1,
            "columns": 3,
        },
    }

    for fieldname, values in updates.items():
        frappe.db.set_value(
            "DocField",
            {
                "parent": "Drug Prescription",
                "fieldname": fieldname,
            },
            values,
            update_modified=False,
        )

    frappe.clear_cache(doctype="Drug Prescription")
    frappe.db.commit()

    print("")
    print("========================================")
    print("DRUG PRESCRIPTION GRID FIX APPLIED")
    print("========================================")

    meta = frappe.get_meta("Drug Prescription")

    for df in meta.fields:
        if df.fieldname in updates:
            print(
                df.fieldname,
                "| reqd =", df.reqd,
                "| in_list_view =", df.in_list_view,
                "| columns =", df.columns,
            )

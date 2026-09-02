import frappe


def execute():

    fields = {

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

        "dosage_form": {
            "in_list_view": 0,
            "columns": 0,
        },

    }


    for fieldname, values in fields.items():

        frappe.db.set_value(
            "DocField",
            {
                "parent": "Drug Prescription",
                "fieldname": fieldname,
            },
            "in_list_view",
            values["in_list_view"],
            update_modified=False,
        )

        frappe.db.set_value(
            "DocField",
            {
                "parent": "Drug Prescription",
                "fieldname": fieldname,
            },
            "columns",
            values["columns"],
            update_modified=False,
        )


    frappe.clear_cache()

    print("")
    print("==========================================")
    print("CLINIFY PRESCRIPTION GRID UPDATED")
    print("==========================================")


if __name__ == "__main__":
    execute()
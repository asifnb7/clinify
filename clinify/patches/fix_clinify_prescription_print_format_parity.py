import frappe


def execute():
    if frappe.db.exists("Print Format", "Clinify Prescription"):
        frappe.db.set_value(
            "Print Format",
            "Clinify Prescription",
            "custom_format",
            1,
            update_modified=False,
        )

        frappe.clear_cache(doctype="Print Format")
        frappe.db.commit()

        print("Clinify Prescription custom_format set to 1")
    else:
        print("Clinify Prescription Print Format not found")

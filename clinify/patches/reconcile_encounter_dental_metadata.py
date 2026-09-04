import frappe


PROPERTY_SETTER_NAME = "Patient Encounter-custom_dental_services-hidden"


def execute():
    if frappe.db.exists("Property Setter", PROPERTY_SETTER_NAME):
        frappe.delete_doc(
            "Property Setter",
            PROPERTY_SETTER_NAME,
            force=True,
            ignore_permissions=True,
        )

    frappe.clear_cache(doctype="Patient Encounter")
import frappe


@frappe.whitelist()
def get_active_dental_services():

    return frappe.get_all(
        "Dental Service",
        filters={
            "is_active": 1
        },
        fields=[
            "name",
            "service_code",
            "service_name",
            "erpnext_item",
            "default_qty",
            "requires_tooth",
            "description"
        ],
        order_by="service_name asc"
    )
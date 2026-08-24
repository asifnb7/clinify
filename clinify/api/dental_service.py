import frappe


@frappe.whitelist()
def get_active_dental_services():
    """
    Return the complete active Clinify Dental Service catalogue.

    Dental Service is the single authoritative catalogue.
    """

    return frappe.get_all(
        "Dental Service",
        filters={
            "is_active": 1,
        },
        fields=[
            "name",
            "service_code",
            "service_name",
            "default_qty",
            "minimum_price",
            "maximum_price",
            "pricing_basis",
            "requires_tooth",
            "erpnext_item",
        ],
        order_by="service_name asc",
    )

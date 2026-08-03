import frappe


@frappe.whitelist()
def create_invoice_from_dental_plan(plan_name):
    # Load Treatment Plan
    plan = frappe.get_doc("Dental Treatment Plan", plan_name)

    # Read directly from Dental Planned Procedure
    rows = frappe.get_all(
        "Dental Planned Procedure",
        filters={
            "parent": plan_name,
            "planned_status": "Completed",
            "billed_invoice": ["is", "not set"],
        },
        fields=[
            "name",
            "procedure_type",
        ],
    )

    if not rows:
        frappe.throw("No completed, unbilled procedures found.")

    invoice = frappe.new_doc("Sales Invoice")
    invoice.patient = plan.patient
    invoice.customer = plan.patient
    invoice.custom_primary_doctor = plan.primary_doctor
    invoice.set_posting_time = 1

    for row in rows:

        service = frappe.get_value(
            "Dental Service",
            {
                "service_name": row.procedure_type,
                "is_active": 1,
            },
            ["erpnext_item"],
            as_dict=True,
        )

        if not service:
            frappe.throw(
                f"Procedure '{row.procedure_type}' in Treatment Plan "
                f"'{plan_name}' is not configured in Dental Service."
            )

        invoice.append(
            "items",
            {
                "item_code": service.erpnext_item,
                "qty": 1,
                "description": row.procedure_type,
            },
        )

    invoice.insert(ignore_permissions=True)

    # Leave the invoice in Draft.
    # Reception will review, edit and submit manually.

    # Mark procedures as billed
    for row in rows:
        frappe.db.set_value(
            "Dental Planned Procedure",
            row.name,
            "billed_invoice",
            invoice.name,
        )

    frappe.db.commit()

    return invoice.name
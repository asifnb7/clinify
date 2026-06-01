import frappe

@frappe.whitelist()
def create_invoice_from_dental_plan(plan_name):
    # Load the dental plan
    plan = frappe.get_doc("Dental Treatment Plan", plan_name)

    # Fetch all completed and unbilled billable procedures
    rows = frappe.get_all(
        "Clinify Billable Procedure",
        filters={
            "parent": plan_name,
            "status": "Completed",
            "billed_invoice": ["is", "not set"]
        },
        fields=["name", "procedure_type", "qty"]
    )

    if not rows:
        frappe.throw("No completed, unbilled procedures found.")

    # Create Sales Invoice
    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = plan.patient
    invoice.custom_primary_doctor = plan.primary_doctor
    invoice.set_posting_time = 1

    # Add items to invoice
    for row in rows:
        item = frappe.get_value(
            "Dental Procedure Item Map",
            {"procedure_type": row.procedure_type},
            "item"
        )

        if not item:
            frappe.throw(f"No Item mapping found for {row.procedure_type}")

        invoice.append("items", {
            "item_code": item,
            "qty": row.qty or 1
        })

    # Save and submit invoice
    invoice.insert(ignore_permissions=True)
    invoice.submit()

    # Mark billable procedures as billed
    for row in rows:
        frappe.db.set_value(
            "Clinify Billable Procedure",
            row.name,
            "billed_invoice",
            invoice.name
        )

    frappe.db.commit()

    return invoice.name

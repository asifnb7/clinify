import frappe
from frappe.utils import nowdate


@frappe.whitelist()
def get_todays_appointments():
    """
    Return today's appointments for the Reception Dashboard.
    """

    appointments = frappe.get_all(
        "Patient Appointment",
        filters={
            "appointment_date": nowdate(),
            "docstatus": ["!=", 2]
        },
        fields=[
            "name",
            "appointment_time",
            "patient",
            "patient_name",
            "practitioner",
            "status"
        ],
        order_by="appointment_time asc"
    )

    return appointments

@frappe.whitelist()
def get_billing_queue():
    """
    Return billing queue for the Reception Dashboard.
    """

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"docstatus": 1},
        fields=[
            "name",
            "customer_name",
            "custom_primary_doctor",
            "grand_total",
            "outstanding_amount",
            "posting_date",
            "status",
        ],
        order_by="posting_date desc, creation desc",
    )

    # Get all practitioner IDs used in the invoices
    practitioner_ids = {
        inv["custom_primary_doctor"]
        for inv in invoices
        if inv.get("custom_primary_doctor")
    }

    # Build a lookup dictionary: { practitioner_id: practitioner_name }
    doctor_lookup = {}

    if practitioner_ids:
        practitioners = frappe.get_all(
            "Healthcare Practitioner",
            filters={"name": ["in", list(practitioner_ids)]},
            fields=["name", "practitioner_name"],
        )

        doctor_lookup = {
            p["name"]: p["practitioner_name"]
            for p in practitioners
        }

    # Enrich invoice data
    for invoice in invoices:
        invoice["paid_amount"] = (
            invoice["grand_total"] - invoice["outstanding_amount"]
        )

        invoice["doctor_name"] = doctor_lookup.get(
            invoice.get("custom_primary_doctor"),
            "",
        )

    return invoices

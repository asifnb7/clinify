import frappe
from frappe.utils import nowdate


@frappe.whitelist()
def get_todays_appointments():
    """
    Return today's appointments for the Reception Dashboard.
    """

    from clinify.scripts.dev import doctor_name, patient_journey

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
    "status",
    "custom_reception_status",
    "reference_doctype",
    "reference_docname",
    "ref_sales_invoice",
    "invoiced",
],

       order_by="appointment_time asc"
    )

    for appt in appointments:

        appt["doctor_name"] = doctor_name(
            appt.get("practitioner")
        )

        journey = patient_journey(appt)

        appt["journey_label"] = journey["label"]
        appt["journey_color"] = journey["color"]

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

    practitioner_ids = {
        inv["custom_primary_doctor"]
        for inv in invoices
        if inv.get("custom_primary_doctor")
    }

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

    for invoice in invoices:

        invoice["paid_amount"] = (
            invoice["grand_total"] - invoice["outstanding_amount"]
        )

        invoice["doctor_name"] = doctor_lookup.get(
            invoice.get("custom_primary_doctor"),
            "",
        )

    return invoices


@frappe.whitelist()
def check_in_patient(appointment):

    appt = frappe.get_doc("Patient Appointment", appointment)

    appt.custom_reception_status = "Checked In"

    appt.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success": True,
        "status": appt.custom_reception_status
    }

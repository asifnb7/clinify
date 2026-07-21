import frappe
from frappe.utils import nowdate

from clinify.billing import create_invoice_from_dental_plan


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
    """
    Check in a patient from the Reception Dashboard.
    """

    appt = frappe.get_doc("Patient Appointment", appointment)

    appt.custom_reception_status = "Checked In"

    appt.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success": True,
        "status": appt.custom_reception_status
    }


@frappe.whitelist()
def get_ready_for_billing():
    """
    Return today's appointments that are ready
    for billing but have not yet been invoiced.
    """

    from clinify.scripts.dev import doctor_name

    appointments = frappe.get_all(
        "Patient Appointment",
        filters={
            "appointment_date": nowdate(),
            "custom_reception_status": "Ready for Billing",
            "docstatus": ["!=", 2],
            "ref_sales_invoice": ["in", ["", None]],
        },
        fields=[
            "name",
            "patient",
            "patient_name",
            "appointment_time",
            "practitioner",
            "custom_reception_status",
        ],
        order_by="appointment_time asc",
    )

    for appt in appointments:

        appt["doctor_name"] = doctor_name(
            appt.get("practitioner")
        )

    return appointments


@frappe.whitelist()
def create_invoice_from_ready_appointment(appointment):
    """
    Create Sales Invoice for a ready appointment using the mapped Dental Treatment Plan.
    """

    appt = frappe.get_doc("Patient Appointment", appointment)

    if appt.reference_doctype != "Dental Treatment Plan" or not appt.reference_docname:
        frappe.throw(
            "This appointment is not mapped to a Dental Treatment Plan."
        )

    invoice_name = create_invoice_from_dental_plan(appt.reference_docname)

    appt.ref_sales_invoice = invoice_name
    appt.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success": True,
        "invoice": invoice_name,
    }

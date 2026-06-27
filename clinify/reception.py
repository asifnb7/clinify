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

import frappe
from frappe.utils import nowdate

from clinify.scripts.dev import doctor_name


@frappe.whitelist()
def get_todays_patients():
    """
    Return today's appointments.

    Administrator:
        Returns all today's appointments.

    Doctor:
        Returns only that doctor's appointments.
    """

    filters = {
        "appointment_date": nowdate(),
        "docstatus": ["!=", 2],
    }

    if frappe.session.user != "Administrator":

        practitioner = frappe.db.get_value(
            "Healthcare Practitioner",
            {"user_id": frappe.session.user},
            "name",
        )

        if not practitioner:
            return []

        filters["practitioner"] = practitioner

    appointments = frappe.get_all(
        "Patient Appointment",
        filters=filters,
        fields=[
            "name",
            "patient",
            "patient_name",
            "appointment_time",
            "custom_reception_status",
            "practitioner",
        ],
        order_by="appointment_time asc",
    )

    for appt in appointments:
        appt["doctor_name"] = doctor_name(
            appt.get("practitioner")
        )

    return appointments


@frappe.whitelist()
def launch_consultation(appointment):
    """
    Return whether an encounter already exists
    for this appointment.
    
    Populates practitioner_department before returning
    the mapped document as unsaved for the Doctor to complete.
    """

    existing = frappe.db.get_value(
        "Patient Encounter",
        {
            "appointment": appointment
        },
        "name",
    )

    if existing:
        return {
            "exists": True,
            "encounter": existing
        }

    encounter = frappe.get_doc(
        "Patient Appointment",
        appointment,
    ).run_method(
        "make_encounter"
    )

    if not encounter:
        return {
            "exists": False
        }

    # Populate practitioner_department before returning unsaved document
    if not getattr(encounter, "practitioner_department", None):
        department = getattr(encounter, "department", None)
        if department:
            encounter.practitioner_department = department
        else:
            practitioner = getattr(encounter, "practitioner", None)
            if practitioner:
                practitioner_department = frappe.db.get_value(
                    "Healthcare Practitioner",
                    practitioner,
                    "department",
                )
                if practitioner_department:
                    encounter.practitioner_department = practitioner_department

    return {
        "exists": True,
        "encounter": encounter.name,
    }

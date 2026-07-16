import frappe


def _get_or_create_treatment_plan(doc):
    """Create or reuse a Dental Treatment Plan for the linked appointment."""

    appointment_name = getattr(doc, "appointment", None)
    if not appointment_name:
        return None

    try:
        appointment = frappe.get_doc("Patient Appointment", appointment_name)
    except Exception:
        return None

    if getattr(appointment, "reference_doctype", None) and getattr(appointment, "reference_docname", None):
        return appointment.reference_docname

    plan = frappe.new_doc("Dental Treatment Plan")
    plan.status = "Active"
    plan.patient = doc.patient
    plan.primary_doctor = doc.practitioner
    plan.insert(ignore_permissions=True)

    appointment.reference_doctype = "Dental Treatment Plan"
    appointment.reference_docname = plan.name
    appointment.save(ignore_permissions=True)

    return plan.name


def after_save(doc, method=None):
    """
    When a Dental Patient Encounter is saved, create or reuse a
    Dental Treatment Plan for the linked Patient Appointment,
    link the appointment to that plan, and then move the appointment
    to the Reception Billing Queue.

    This handler is intentionally idempotent so repeated saves
    do not perform unnecessary database writes.
    """

    if not getattr(doc, "appointment", None):
        return

    plan_name = _get_or_create_treatment_plan(doc)
    if not plan_name:
        return

    current_status = frappe.db.get_value(
        "Patient Appointment",
        doc.appointment,
        "custom_reception_status"
    )

    if current_status == "Ready for Billing":
        return

    frappe.db.set_value(
        "Patient Appointment",
        doc.appointment,
        "custom_reception_status",
        "Ready for Billing",
        update_modified=False,
    )


def before_insert(doc, method=None):
    """
    Populate Clinify-specific practitioner_department before insert.
    """

    if getattr(doc, "practitioner_department", None):
        return

    department = getattr(doc, "department", None)
    if department:
        doc.practitioner_department = department
        return

    practitioner = getattr(doc, "practitioner", None)
    if practitioner:
        practitioner_department = frappe.db.get_value(
            "Healthcare Practitioner",
            practitioner,
            "department",
        )
        if practitioner_department:
            doc.practitioner_department = practitioner_department

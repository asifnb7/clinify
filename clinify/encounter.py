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

def _append_planned_procedure(doc, plan_name):
    """Append one planned procedure row to the Dental Treatment Plan."""

    if not plan_name:
        return

    try:
        plan = frappe.get_doc("Dental Treatment Plan", plan_name)
    except Exception:
        return

    # Prevent duplicate rows for the same Encounter
    if any(
        getattr(row, "linked_encounter", None) == doc.name
        for row in getattr(plan, "dental_planned_procedures", [])
    ):
        return

    # Procedure Type is mandatory
    if not getattr(doc, "custom_procedure_type", None):
        frappe.throw(
            "Please select a Procedure Type before saving the Encounter."
        )

    plan.append(
        "dental_planned_procedures",
        {
            "procedure_type": doc.custom_procedure_type,
            "tooth_number": doc.custom_tooth_area,
            "tooth_surface": "O",
            "planned_status": "Completed",
            "linked_encounter": doc.name,
        },
    )

    plan.save(ignore_permissions=True)

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

    _append_planned_procedure(doc, plan_name)

    current_status = frappe.db.get_value(
        "Patient Appointment",
        doc.appointment,
        "custom_reception_status"
    )
    if current_status == "Billing":
        return

    frappe.db.set_value(
        "Patient Appointment",
        doc.appointment,
        "custom_reception_status",
        "Billing",
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

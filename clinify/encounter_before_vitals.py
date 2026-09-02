import frappe

from clinify.billing import create_invoice_from_dental_plan

def _get_or_create_treatment_plan(doc):
    """Create or reuse a Dental Treatment Plan for the linked appointment."""

    appointment_name = getattr(doc, "appointment", None)
    if not appointment_name:
        return None

    try:
        appointment = frappe.get_doc("Patient Appointment", appointment_name)
    except Exception:
        return None

    if (
        getattr(appointment, "reference_doctype", None)
        and getattr(appointment, "reference_docname", None)
    ):
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
    """Append completed procedures to the Dental Treatment Plan."""

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

    # -------------------------------------------------------
    # DS2 : Multi Dental Service workflow
    # -------------------------------------------------------

    if getattr(doc, "custom_dental_services", None):

        for service in doc.custom_dental_services:

            if not service.dental_service:
                continue

            dental_service = frappe.get_doc(
                "Dental Service",
                service.dental_service,
            )

            qty = service.qty or 1

            for _ in range(int(qty)):

                plan.append(
                    "dental_planned_procedures",
                    {
                        "dental_service": dental_service.name,
                        "procedure_type": dental_service.service_name,
                        "tooth_number": service.tooth_area,
                        "tooth_surface": "O",
                        "planned_status": "Completed",
                        "estimated_cost": dental_service.minimum_price or 0,
                        "linked_encounter": doc.name,
                    },
                )

    # -------------------------------------------------------
    # Legacy Single Procedure Workflow
    # -------------------------------------------------------

    else:

        if not getattr(doc, "custom_procedure_type", None):
            frappe.throw(
                "Please select at least one Dental Service."
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

    # Save only once
    plan.save(ignore_permissions=True)


def after_save(doc, method=None):
    """
    Doctor saves the Encounter.

    Workflow:
        1. Create / Reuse Dental Treatment Plan
        2. Synchronize Planned Procedures
        3. Create Draft Invoice
        4. Link Invoice to Appointment
        5. Move Appointment to View Invoice
    """

    if not getattr(doc, "appointment", None):
        return

    # -------------------------------------------------
    # Create / Reuse Treatment Plan
    # -------------------------------------------------

    plan_name = _get_or_create_treatment_plan(doc)

    if not plan_name:
        return

    # -------------------------------------------------
    # Synchronize Planned Procedures
    # -------------------------------------------------

    _append_planned_procedure(doc, plan_name)

    # -------------------------------------------------
    # Create Draft Invoice
    # -------------------------------------------------

    try:
        invoice_name = create_invoice_from_encounter(doc.name)
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Automatic Invoice Creation",
        )

        frappe.msgprint(
            "Automatic draft invoice could not be created. "
            "Please contact the administrator."
        )
        return
    if not invoice_name:
        return
    # -------------------------------------------------
    # Move Appointment to View Invoice
    # -------------------------------------------------

    frappe.db.set_value(
        "Patient Appointment",
        doc.appointment,
        "custom_reception_status",
        "View Invoice",
        update_modified=False,
    )

    frappe.db.commit()
    
def before_insert(doc, method=None):
    """
    Populate practitioner_department automatically.
    """

    if getattr(doc, "practitioner_department", None):
        return

    if getattr(doc, "department", None):
        doc.practitioner_department = doc.department
        return

    if getattr(doc, "practitioner", None):

        department = frappe.db.get_value(
            "Healthcare Practitioner",
            doc.practitioner,
            "department",
        )

        if department:
            doc.practitioner_department = department


@frappe.whitelist()
def create_invoice_from_encounter(encounter_name):
    """
    Create a Sales Invoice for the submitted Encounter.
    Reuses the existing Dental Billing engine.
    """

    encounter = frappe.get_doc("Patient Encounter", encounter_name)

    if not encounter.appointment:
        frappe.throw("This Encounter is not linked to an Appointment.")

    appointment = frappe.get_doc(
        "Patient Appointment",
        encounter.appointment
    )

    if (
        appointment.reference_doctype != "Dental Treatment Plan"
        or not appointment.reference_docname
    ):
        frappe.throw(
            "No Dental Treatment Plan is linked to this Appointment."
        )

    invoice = create_invoice_from_dental_plan(
        appointment.reference_docname
    )

    # Store invoice reference on Appointment
    frappe.db.set_value(
        "Patient Appointment",
        appointment.name,
        "ref_sales_invoice",
        invoice,
        update_modified=False,
    )

    
    return invoice
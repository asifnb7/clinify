import frappe

from clinify.billing import _append_consultation_item


# =========================================================
# VITAL SIGNS
# =========================================================

def _get_matching_vital_for_encounter(doc):
    """
    Find the correct Vital Signs record for a Patient Encounter.

    Matching priority:

    1. Same Patient Appointment
    2. Same Patient + Same Encounter Date

    Older historical vitals are never returned.
    """

    if not doc.patient:
        return None

    vital_fields = [
        "name",
        "patient",
        "appointment",
        "encounter",
        "signs_date",
        "signs_time",
        "temperature",
        "pulse",
        "respiratory_rate",
        "bp_systolic",
        "bp_diastolic",
        "bp",
        "height",
        "weight",
        "bmi",
        "vital_signs_note",
    ]

    # -----------------------------------------------------
    # PRIORITY 1
    # Exact Appointment Match
    # -----------------------------------------------------

    if getattr(doc, "appointment", None):

        vitals = frappe.get_all(
            "Vital Signs",
            filters={
                "appointment": doc.appointment,
                "patient": doc.patient,
            },
            fields=vital_fields,
            order_by="signs_date desc, signs_time desc, creation desc",
            limit_page_length=1,
        )

        if vitals:
            return vitals[0]

    # -----------------------------------------------------
    # PRIORITY 2
    # Same Patient + Same Encounter Date
    # -----------------------------------------------------

    if getattr(doc, "encounter_date", None):

        vitals = frappe.get_all(
            "Vital Signs",
            filters={
                "patient": doc.patient,
                "signs_date": doc.encounter_date,
            },
            fields=vital_fields,
            order_by="signs_time desc, creation desc",
            limit_page_length=1,
        )

        if vitals:
            return vitals[0]

    return None


@frappe.whitelist()
def get_matching_vitals(encounter_name):
    """
    Return the Vital Signs belonging to the current patient visit.

    Priority:
        1. Same Appointment
        2. Same Patient + Same Encounter Date

    Returns None when no vitals exist for the current visit.
    """

    if not encounter_name:
        return None

    doc = frappe.get_doc(
        "Patient Encounter",
        encounter_name,
    )

    return _get_matching_vital_for_encounter(doc)
@frappe.whitelist()
def get_matching_vitals_for_context(
    patient=None,
    encounter_date=None,
    appointment=None,
):
    """
    Find the Vital Signs relevant to the Encounter currently being created.

    Priority:
        1. Same Patient + same Appointment
        2. Same Patient + same Encounter Date

    This allows Vital Signs to appear on a NEW Patient Encounter
    before the Encounter has been saved.
    """

    if not patient:
        return None

    if appointment:

        vitals = frappe.get_all(
            "Vital Signs",
            filters={
                "patient": patient,
                "appointment": appointment,
            },
            fields=[
                "name",
                "patient",
                "appointment",
                "encounter",
                "signs_date",
                "signs_time",
                "temperature",
                "pulse",
                "respiratory_rate",
                "bp_systolic",
                "bp_diastolic",
                "bp",
                "height",
                "weight",
                "bmi",
                "vital_signs_note",
            ],
            order_by="signs_date desc, signs_time desc",
            limit_page_length=1,
        )

        if vitals:
            return vitals[0]

    if encounter_date:

        vitals = frappe.get_all(
            "Vital Signs",
            filters={
                "patient": patient,
                "signs_date": encounter_date,
            },
            fields=[
                "name",
                "patient",
                "appointment",
                "encounter",
                "signs_date",
                "signs_time",
                "temperature",
                "pulse",
                "respiratory_rate",
                "bp_systolic",
                "bp_diastolic",
                "bp",
                "height",
                "weight",
                "bmi",
                "vital_signs_note",
            ],
            order_by="signs_time desc, creation desc",
            limit_page_length=1,
        )

        if vitals:
            return vitals[0]

    return None

# =========================================================
# DENTAL TREATMENT PLAN
# =========================================================

# =========================================================
# ENCOUNTER SAVE
# =========================================================

def after_save(doc, method=None):
    """
    Doctor saves the Encounter.

    Workflow:

        1. Require a linked Appointment.
        2. Create one Sales Invoice when billable services exist.
        3. Consultation billing remains centralized.
        4. Dental billing uses:
               Patient Encounter.custom_dental_services
                   -> Clinify Encounter Service
                   -> Dental Service
                   -> ERPNext Item
        5. Link Invoice to Appointment.
        6. Move Appointment to View Invoice.

    Legacy Dental Treatment Plan architecture is intentionally
    no longer part of the active Encounter workflow.
    """

    if not getattr(
        doc,
        "appointment",
        None,
    ):
        return

    try:

        invoice_name = create_invoice_from_encounter(
            doc.name,
        )

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

    frappe.db.set_value(
        "Patient Appointment",
        doc.appointment,
        "custom_reception_status",
        "View Invoice",
        update_modified=False,
    )

    frappe.db.commit()


# =========================================================
# BEFORE INSERT
# =========================================================



def before_insert(doc, method=None):
    """
    Populate practitioner_department automatically.
    """

    if getattr(
        doc,
        "practitioner_department",
        None,
    ):
        return

    if getattr(
        doc,
        "department",
        None,
    ):

        doc.practitioner_department = doc.department

        return

    if getattr(
        doc,
        "practitioner",
        None,
    ):

        department = frappe.db.get_value(
            "Healthcare Practitioner",
            doc.practitioner,
            "department",
        )

        if department:

            doc.practitioner_department = department


# =========================================================
# INVOICE CREATION
# =========================================================

@frappe.whitelist()
def create_invoice_from_encounter(encounter_name):
    """
    Create the Encounter Sales Invoice.

    The transaction source is the Patient Encounter.

    Dental services are taken directly from:

        Patient Encounter.custom_dental_services
            -> Clinify Encounter Service
            -> Dental Service
            -> ERPNext Item

    Consultation billing remains centralized in
    clinify.billing._append_consultation_item().

    Legacy Dental Treatment Plan objects are not required.
    """

    encounter = frappe.get_doc(
        "Patient Encounter",
        encounter_name,
    )

    if not encounter.appointment:

        frappe.throw(
            "This Encounter is not linked to an Appointment."
        )

    appointment = frappe.get_doc(
        "Patient Appointment",
        encounter.appointment,
    )

    # ---------------------------------------------------------
    # IDEMPOTENCY
    # ---------------------------------------------------------

    existing_invoice = getattr(
        appointment,
        "ref_sales_invoice",
        None,
    )

    if (
        existing_invoice
        and frappe.db.exists(
            "Sales Invoice",
            existing_invoice,
        )
    ):
        return existing_invoice

    # ---------------------------------------------------------
    # NEW DENTAL BILLING ENGINE
    # ---------------------------------------------------------

    from clinify.dental_billing import (
        create_invoice_from_encounter_dental,
    )

    invoice_name = create_invoice_from_encounter_dental(
        encounter,
    )

    if not invoice_name:
        return None

    # ---------------------------------------------------------
    # STORE INVOICE REFERENCE
    # ---------------------------------------------------------

    frappe.db.set_value(
        "Patient Appointment",
        appointment.name,
        "ref_sales_invoice",
        invoice_name,
        update_modified=False,
    )

    return invoice_name


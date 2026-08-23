import frappe
from frappe.utils import getdate, today


CONSULTATION_ITEM = "CONSULTATION"


def _get_clinic_configuration():
    """
    Return the clinic-wide consultation/follow-up policy.

    Consultation price remains doctor-specific.
    Follow-up policy remains clinic-specific.
    """
    config = frappe.get_single("Clinic Configuration")

    return {
        "free_followup_days": int(
            getattr(config, "free_followup_days", 0) or 0
        ),
        "allow_multiple_free_followups": bool(
            getattr(config, "allow_multiple_free_followups", 0)
        ),
    }


def _get_practitioner_consultation(practitioner):
    """
    Return the doctor's consultation configuration.

    The consultation charge is stored on Healthcare Practitioner,
    allowing every doctor to have an independent consultation fee.
    """

    if not practitioner:
        return {
            "practitioner": None,
            "practitioner_name": None,
            "consultation_charge": 0.0,
            "consultation_item": CONSULTATION_ITEM,
        }

    doctor = frappe.db.get_value(
        "Healthcare Practitioner",
        practitioner,
        [
            "practitioner_name",
            "op_consulting_charge",
            "op_consulting_charge_item",
        ],
        as_dict=True,
    )

    if not doctor:
        frappe.throw(
            f"Healthcare Practitioner '{practitioner}' was not found."
        )

    consultation_item = (
        doctor.get("op_consulting_charge_item")
        or CONSULTATION_ITEM
    )

    return {
        "practitioner": practitioner,
        "practitioner_name": doctor.get("practitioner_name"),
        "consultation_charge": float(
            doctor.get("op_consulting_charge") or 0
        ),
        "consultation_item": consultation_item,
    }


def _is_free_followup(
    patient,
    practitioner,
    consultation_date=None,
):
    """
    Determine whether this consultation qualifies as the single
    free follow-up after the latest PAID consultation.

    Rules:

    1. The clinic controls the free-follow-up window.
    2. The doctor controls the consultation fee.
    3. A submitted consultation invoice with a positive consultation
       rate establishes a paid consultation.
    4. The free follow-up must occur within the configured window
       after the latest paid consultation.
    5. By default, only one free follow-up is allowed.
    6. A free follow-up does not become a new paid-consultation anchor.
    7. A later paid consultation starts a new follow-up window.
    """

    if not patient or not practitioner:
        return False

    policy = _get_clinic_configuration()

    free_followup_days = policy["free_followup_days"]

    if free_followup_days <= 0:
        return False

    consultation_date = getdate(
        consultation_date or today()
    )

    # Find submitted consultation invoices that contain the
    # consultation item for this patient and doctor.
    #
    # A positive rate identifies a PAID consultation.
    # Free follow-up lines have rate = 0 and therefore must NOT
    # become a new follow-up anchor.
    paid_consultations = frappe.db.sql(
        """
        SELECT
            si.name,
            si.posting_date,
            sii.rate
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii
            ON sii.parent = si.name
        WHERE
            si.docstatus = 1
            AND si.customer = %s
            AND si.custom_primary_doctor = %s
            AND sii.item_code = %s
            AND sii.rate > 0
            AND si.posting_date <= %s
        ORDER BY
            si.posting_date DESC,
            si.creation DESC
        """,
        (
            patient,
            practitioner,
            CONSULTATION_ITEM,
            consultation_date,
        ),
        as_dict=True,
    )

    if not paid_consultations:
        return False

    # The latest PAID consultation establishes the current
    # follow-up window.
    latest_paid = paid_consultations[0]
    latest_paid_date = getdate(latest_paid.posting_date)

    days_since_paid = (
        consultation_date - latest_paid_date
    ).days

    if days_since_paid < 0 or days_since_paid > free_followup_days:
        return False

    # If multiple free follow-ups are explicitly allowed by the
    # clinic, every consultation within the window is free.
    if policy["allow_multiple_free_followups"]:
        return True

    # Default policy: exactly ONE free follow-up after the latest
    # paid consultation.
    #
    # A submitted zero-rate consultation after the latest paid
    # consultation means the free follow-up has already been used.
    existing_followups = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT si.name)
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii
            ON sii.parent = si.name
        WHERE
            si.docstatus = 1
            AND si.customer = %s
            AND si.custom_primary_doctor = %s
            AND sii.item_code = %s
            AND sii.rate = 0
            AND si.posting_date > %s
            AND si.posting_date <= %s
        """,
        (
            patient,
            practitioner,
            CONSULTATION_ITEM,
            latest_paid_date,
            consultation_date,
        ),
    )[0][0]

    return int(existing_followups or 0) == 0

def _append_consultation_item(
    invoice,
    patient,
    practitioner,
    consultation_date=None,
):
    """
    Append the consultation line to the central Sales Invoice.

    The amount is determined by the doctor.
    The free/paid decision is determined by the clinic follow-up policy.
    """

    doctor = _get_practitioner_consultation(practitioner)

    charge = doctor["consultation_charge"]

    # No configured doctor fee means there is nothing to bill.
    if charge <= 0:
        return {
            "added": False,
            "free": False,
            "rate": 0.0,
            "doctor": doctor["practitioner_name"],
        }

    item_code = doctor["consultation_item"]

    if not frappe.db.exists("Item", item_code):
        frappe.throw(
            f"Consultation Item '{item_code}' configured for "
            f"{doctor['practitioner_name']} does not exist."
        )

    free_followup = _is_free_followup(
        patient=patient,
        practitioner=practitioner,
        consultation_date=consultation_date,
    )

    rate = 0.0 if free_followup else charge

    description = (
        f"Free Follow-up Consultation - "
        f"{doctor['practitioner_name']}"
        if free_followup
        else f"Consultation - {doctor['practitioner_name']}"
    )

    invoice.append(
        "items",
        {
            "item_code": item_code,
            "qty": 1,
            "rate": rate,
            "description": description,
            "practitioner": practitioner,
        },
    )

    return {
        "added": True,
        "free": free_followup,
        "rate": rate,
        "doctor": doctor["practitioner_name"],
    }


@frappe.whitelist()
def create_invoice_from_dental_plan(plan_name):
    """
    Central Clinify billing engine.

    Creates ONE Sales Invoice containing:
    - Doctor consultation fee
    - Completed dental procedures

    Consultation pricing:
    - Doctor-specific via Healthcare Practitioner.op_consulting_charge

    Follow-up policy:
    - Clinic-specific via Clinic Configuration.free_followup_days
    - Optional multiple free follow-ups via
      Clinic Configuration.allow_multiple_free_followups

    Existing Dental Planned Procedure billing remains the source
    for dental services.
    """

    plan = frappe.get_doc(
        "Dental Treatment Plan",
        plan_name,
    )

    rows = frappe.get_all(
        "Dental Planned Procedure",
        filters={
            "parent": plan_name,
            "planned_status": "Completed",
            "billed_invoice": ["is", "not set"],
        },
        fields=[
            "name",
            "dental_service",
            "procedure_type",
        ],
    )

    if not rows:
        frappe.throw(
            "No completed, unbilled procedures found."
        )

    invoice = frappe.new_doc("Sales Invoice")

    invoice.patient = plan.patient
    invoice.customer = plan.patient
    invoice.custom_primary_doctor = plan.primary_doctor
    invoice.set_posting_time = 1

    # =========================================================
    # CONSULTATION
    # =========================================================

    consultation = _append_consultation_item(
        invoice=invoice,
        patient=plan.patient,
        practitioner=plan.primary_doctor,
        consultation_date=today(),
    )

    # =========================================================
    # DENTAL SERVICES
    # =========================================================

    for row in rows:

        # -----------------------------------------------------
        # DENTAL SERVICE IS THE AUTHORITATIVE BILLING LINK
        # -----------------------------------------------------

        if not row.dental_service:
            frappe.throw(
                f"Dental Planned Procedure '{row.name}' "
                f"has no Dental Service linked. "
                f"Legacy procedure type '{row.procedure_type}' "
                f"cannot be billed automatically."
            )

        service = frappe.get_value(
            "Dental Service",
            {
                "name": row.dental_service,
                "is_active": 1,
            },
            [
                "name",
                "service_code",
                "service_name",
                "erpnext_item",
            ],
            as_dict=True,
        )

        if not service:
            frappe.throw(
                f"Dental Service '{row.dental_service}' "
                f"linked to procedure '{row.name}' "
                f"is missing or inactive."
            )

        if not service.erpnext_item:
            frappe.throw(
                f"Dental Service '{service.service_name}' "
                f"has no ERPNext Item configured."
            )

        invoice.append(
            "items",
            {
                "item_code": service.erpnext_item,
                "qty": 1,
                "description": service.service_name,
            },
        )

    # =========================================================
    # CREATE ONE SALES INVOICE
    # =========================================================

    invoice.insert(
        ignore_permissions=True
    )

    # =========================================================
    # MARK DENTAL PROCEDURES AS BILLED
    # =========================================================

    for row in rows:
        frappe.db.set_value(
            "Dental Planned Procedure",
            row.name,
            "billed_invoice",
            invoice.name,
        )

    frappe.db.commit()

    return invoice.name


@frappe.whitelist()
def complete_dental_procedure(procedure_name):
    """
    Mark a Dental Planned Procedure as Completed.
    """

    frappe.db.set_value(
        "Dental Planned Procedure",
        procedure_name,
        "planned_status",
        "Completed",
    )

    frappe.db.commit()

    return {
        "status": "success",
        "procedure": procedure_name,
    }

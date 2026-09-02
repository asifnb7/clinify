import frappe
from frappe import _
from frappe.utils import flt, today


def _get_dental_services_from_encounter(encounter):
    """
    Return Dental Service rows attached to a Patient Encounter.

    Source of truth:

        Patient Encounter.custom_dental_services
            -> Clinify Encounter Service
            -> Dental Service
    """

    return getattr(
        encounter,
        "custom_dental_services",
        None,
    ) or []


def _validate_dental_service(row):
    """
    Validate one Clinify Encounter Service row.

    Returns:
        (Dental Service document, quantity)
    """

    if not row.dental_service:
        frappe.throw(
            _("Dental Service is required for each dental service row.")
        )

    if not frappe.db.exists(
        "Dental Service",
        row.dental_service,
    ):
        frappe.throw(
            _("Dental Service '{0}' does not exist.").format(
                row.dental_service
            )
        )

    service = frappe.get_doc(
        "Dental Service",
        row.dental_service,
    )

    if not service.is_active:
        frappe.throw(
            _("Dental Service '{0}' is inactive.").format(
                service.service_name or service.name
            )
        )

    if not service.erpnext_item:
        frappe.throw(
            _(
                "Dental Service '{0}' has no ERPNext Item configured."
            ).format(
                service.service_name or service.name
            )
        )

    if not frappe.db.exists(
        "Item",
        service.erpnext_item,
    ):
        frappe.throw(
            _(
                "ERPNext Item '{0}' configured for Dental Service "
                "'{1}' does not exist."
            ).format(
                service.erpnext_item,
                service.service_name or service.name,
            )
        )

    qty = flt(row.qty)

    if qty <= 0:
        qty = flt(service.default_qty) or 1

    if qty <= 0:
        frappe.throw(
            _(
                "Quantity must be greater than zero for Dental Service '{0}'."
            ).format(
                service.service_name or service.name
            )
        )

    if service.requires_tooth and not row.tooth_area:
        frappe.throw(
            _(
                "Tooth Area is required for Dental Service '{0}'."
            ).format(
                service.service_name or service.name
            )
        )

    return service, qty


def append_dental_items(invoice, encounter):
    """
    Append dental services from the Patient Encounter
    to an existing Sales Invoice.
    """

    rows = _get_dental_services_from_encounter(
        encounter
    )

    for row in rows:

        service, qty = _validate_dental_service(
            row
        )

        item = {
            "item_code": service.erpnext_item,
            "qty": qty,
            "description": service.service_name,
        }

        if row.remarks:
            item["description"] = row.remarks

        invoice.append(
            "items",
            item,
        )


def create_invoice_from_encounter_dental(encounter):
    """
    Create ONE Sales Invoice for a Patient Encounter.

    Dental source:

        Patient Encounter.custom_dental_services
            -> Clinify Encounter Service
            -> Dental Service
            -> ERPNext Item

    This function intentionally does NOT reference:

        Dental Treatment Plan
        Dental Planned Procedure
        Dental Procedure Item Map
    """

    if isinstance(encounter, str):

        encounter = frappe.get_doc(
            "Patient Encounter",
            encounter,
        )

    if encounter.doctype != "Patient Encounter":
        frappe.throw(
            _("Invalid Patient Encounter.")
        )

    if not encounter.patient:
        frappe.throw(
            _("Patient Encounter has no Patient.")
        )

    # ---------------------------------------------------------
    # APPOINTMENT / IDEMPOTENCY
    # ---------------------------------------------------------

    appointment = None

    if getattr(
        encounter,
        "appointment",
        None,
    ):

        appointment = frappe.get_doc(
            "Patient Appointment",
            encounter.appointment,
        )

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
    # PATIENT CUSTOMER
    # ---------------------------------------------------------

    customer = frappe.db.get_value(
        "Patient",
        encounter.patient,
        "customer",
    )

    if not customer:
        frappe.throw(
            _(
                "Patient '{0}' does not have an ERPNext Customer."
            ).format(
                encounter.patient
            )
        )

    # ---------------------------------------------------------
    # CREATE ONE INVOICE
    # ---------------------------------------------------------

    invoice = frappe.new_doc(
        "Sales Invoice"
    )

    invoice.customer = customer

    if (
        hasattr(encounter, "company")
        and encounter.company
    ):
        invoice.company = encounter.company

    invoice.set_posting_time = 1

    # ---------------------------------------------------------
    # PRIMARY DOCTOR
    # ---------------------------------------------------------

    practitioner = getattr(
        encounter,
        "practitioner",
        None,
    )

    if practitioner:
        invoice.custom_primary_doctor = practitioner

    # ---------------------------------------------------------
    # CONSULTATION
    # ---------------------------------------------------------

    from clinify.billing import (
        _append_consultation_item,
    )

    _append_consultation_item(
        invoice=invoice,
        patient=customer,
        practitioner=practitioner,
        consultation_date=today(),
    )

    # ---------------------------------------------------------
    # DENTAL SERVICES
    # ---------------------------------------------------------

    append_dental_items(
        invoice,
        encounter,
    )

    # ---------------------------------------------------------
    # NOTHING TO BILL
    # ---------------------------------------------------------

    if not invoice.items:
        return None

    # ---------------------------------------------------------
    # INSERT ONE INVOICE
    # ---------------------------------------------------------

    invoice.insert(
        ignore_permissions=True
    )

    # ---------------------------------------------------------
    # LINK INVOICE TO APPOINTMENT
    # ---------------------------------------------------------

    if appointment:

        frappe.db.set_value(
            "Patient Appointment",
            appointment.name,
            "ref_sales_invoice",
            invoice.name,
            update_modified=False,
        )

    frappe.db.commit()

    return invoice.name

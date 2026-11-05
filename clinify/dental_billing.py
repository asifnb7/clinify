import frappe
from frappe import _
from frappe.utils import flt, today

from clinify.tenant_dental_config import (
    CONFIG_DOCTYPE,
    SERVICE_TYPE_CUSTOM,
    DentalPriceResolutionError,
    get_current_clinic_code,
    resolve_tenant_dental_price,
    tenant_config_for_standard_service,
)


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



def _config_display_name(config):
    """Human-readable name for a tenant dental service configuration."""
    if config.service_type == SERVICE_TYPE_CUSTOM:
        return config.custom_service_name or config.name
    central_name = frappe.db.get_value(
        "Dental Service",
        config.dental_service,
        "service_name",
    )
    return central_name or config.dental_service or config.name


def _resolve_tenant_config(row):
    """
    Resolve the tenant-owned configuration for one encounter service row.

    Standard services are resolved through the central catalogue link;
    custom services are referenced directly by their tenant configuration.
    A server-side tenant isolation guard rejects any configuration whose
    clinic code does not match the current tenant.
    """

    config_name = getattr(row, "tenant_dental_service", None)

    if config_name:
        if not frappe.db.exists(CONFIG_DOCTYPE, config_name):
            frappe.throw(
                _("Dental service configuration '{0}' does not exist.").format(
                    config_name
                )
            )
        config = frappe.get_doc(CONFIG_DOCTYPE, config_name)
    else:
        if not row.dental_service:
            frappe.throw(
                _("Dental Service is required for each dental service row.")
            )
        config = tenant_config_for_standard_service(row.dental_service)
        if config is None:
            frappe.throw(
                _(
                    "Dental Service '{0}' is not configured for this clinic."
                ).format(row.dental_service)
            )

    # Defense-in-depth tenant isolation. The per-site architecture already
    # isolates tenants; this explicit guard never trusts UI alone and fails
    # closed when the current tenant's clinic identity cannot be established.
    current_clinic_code = get_current_clinic_code()
    if not current_clinic_code:
        frappe.throw(
            _(
                "Tenant clinic identity is not configured; refusing to "
                "resolve dental pricing."
            )
        )

    if config.clinic_code and config.clinic_code != current_clinic_code:
        frappe.throw(
            _("This dental service belongs to another clinic.")
        )

    return config


def _resolve_item_and_qty(row, config):
    """Validate the billable item and resolve a positive quantity."""

    # Standard services keep their central-catalogue validation.
    if config.service_type != SERVICE_TYPE_CUSTOM:
        if not frappe.db.exists("Dental Service", config.dental_service):
            frappe.throw(
                _("Dental Service '{0}' does not exist.").format(
                    config.dental_service
                )
            )
        central = frappe.get_doc("Dental Service", config.dental_service)
        if not central.is_active:
            frappe.throw(
                _("Dental Service '{0}' is inactive.").format(
                    central.service_name or central.name
                )
            )

    if not config.erpnext_item:
        frappe.throw(
            _(
                "Dental service '{0}' has no ERPNext Item configured."
            ).format(_config_display_name(config))
        )

    if not frappe.db.exists("Item", config.erpnext_item):
        frappe.throw(
            _(
                "ERPNext Item '{0}' configured for dental service '{1}' "
                "does not exist."
            ).format(
                config.erpnext_item,
                _config_display_name(config),
            )
        )

    qty = flt(row.qty)

    if qty <= 0:
        qty = flt(config.default_qty) or 1

    if qty <= 0:
        frappe.throw(
            _(
                "Quantity must be greater than zero for dental service '{0}'."
            ).format(_config_display_name(config))
        )

    if config.requires_tooth and not row.tooth_area:
        frappe.throw(
            _(
                "Tooth / Area is required for dental service '{0}'."
            ).format(_config_display_name(config))
        )

    return qty


def _resolve_price(row, config):
    """
    Resolve the tenant selling rate for the row.

    Never silently returns zero and never falls back to the central
    minimum/maximum price or another tenant's price. A missing or invalid
    tenant price stops billing with a clear validation error.
    """

    selected_option = getattr(row, "selected_price_option", None)

    try:
        return resolve_tenant_dental_price(
            config.as_dict(),
            selected_option,
        )
    except DentalPriceResolutionError as error:
        frappe.throw(str(error))



def append_dental_items(invoice, encounter):
    """
    Append dental services from the Patient Encounter
    to an existing Sales Invoice.
    """

    rows = _get_dental_services_from_encounter(
        encounter
    )

    for row in rows:

        config = _resolve_tenant_config(row)
        qty = _resolve_item_and_qty(row, config)
        rate = _resolve_price(row, config)

        item = {
            "item_code": config.erpnext_item,
            "qty": qty,
            # The resolved tenant selling price is written explicitly so the
            # invoice preserves the actual historical rate. Later tenant price
            # changes never alter an already-created invoice.
            "rate": rate,
            "description": _config_display_name(config),
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
    try:
        if getattr(
            encounter,
            "appointment",
            None,
        ):

            locked_appointment = frappe.db.sql(
                """
                SELECT name
                FROM `tabPatient Appointment`
                WHERE name = %s
                FOR UPDATE
                """,
                (encounter.appointment,),
                as_dict=True,
            )

            if not locked_appointment:
                frappe.throw(
                    _(
                        "Patient Appointment '{0}' does not exist."
                    ).format(encounter.appointment)
                )

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
    except Exception:
        raise

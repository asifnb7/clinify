import re

import frappe


DEFAULT_CLINIC_BRAND_COLOR = "#173B82"


def get_current_clinic():
    """
    Return the current Clinic Configuration document.
    """

    return frappe.get_single("Clinic Configuration")


def get_clinic_identity():
    """
    Return the basic identity of the current clinic.
    """

    clinic = get_current_clinic()

    return {
        "clinic_name": clinic.clinic_name,
        "clinic_code": clinic.clinic_code,
        "clinic_email": clinic.clinic_email,
        "clinic_phone": clinic.clinic_phone,
    }


def get_clinic_status():
    """
    Return the current clinic and subscription status.
    """

    clinic = get_current_clinic()

    return {
        "clinic_status": clinic.clinic_status,
        "subscription_status": clinic.subscription_status,
        "activation_date": clinic.activation_date,
    }


def is_clinic_active():
    """
    Return True when the clinic is active.
    """

    clinic = get_current_clinic()

    return clinic.clinic_status == "Active"


def get_clinic_configuration():
    """
    Return the complete clinic configuration required
    by Clinify application services.
    """

    clinic = get_current_clinic()

    return {
        "clinic_name": clinic.clinic_name,
        "clinic_code": clinic.clinic_code,
        "clinic_email": clinic.clinic_email,
        "clinic_phone": clinic.clinic_phone,
        "clinic_website": clinic.get("clinic_website"),
        "clinic_logo": clinic.get("clinic_logo"),
        "brand_primary_color": clinic.get("brand_primary_color") or "#173B82",
        "clinic_address": clinic.clinic_address,
        "city": clinic.city,
        "state": clinic.state,
        "country": clinic.country,
        "pincode": clinic.pincode,
        "clinic_status": clinic.clinic_status,
        "subscription_status": clinic.subscription_status,
        "activation_date": clinic.activation_date,
        "free_followup_days": clinic.free_followup_days,
        "allow_multiple_free_followups": clinic.allow_multiple_free_followups,
    }


def get_print_branding():
    """Return validated, current-site branding values for print formats."""
    import json

    clinic = get_current_clinic()

    color = (clinic.get("brand_primary_color") or "").strip()
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        color = DEFAULT_CLINIC_BRAND_COLOR

    logo_url = (clinic.get("clinic_logo") or "").strip()
    if not logo_url.startswith(("/files/", "/private/files/")):
        logo_url = None
    elif not frappe.db.exists(
        "File",
        {
            "file_url": logo_url,
            "attached_to_doctype": "Clinic Configuration",
            "attached_to_name": "Clinic Configuration",
        },
    ):
        logo_url = None

    from clinify.saas.print_footer_config import (
        PRINT_FOOTER_SITE_CONFIG_KEY,
        normalize_print_footer_config,
    )

    footer_config = frappe.conf.get(PRINT_FOOTER_SITE_CONFIG_KEY)
    if isinstance(footer_config, str):
        try:
            footer_config = json.loads(footer_config)
        except (TypeError, ValueError):
            footer_config = None

    platform_footer = normalize_print_footer_config(footer_config)

    return {
        "clinic": clinic,
        "logo_url": logo_url,
        "brand_primary_color": color,
        "platform_footer": platform_footer,
    }


def get_legacy_platform_footer_settings():
    """Read tenant-local legacy footer fields for the one-time control-site migration."""
    clinic = get_current_clinic()
    return {
        "platform_attribution_text": clinic.get("platform_attribution_text"),
        "platform_attribution_position": clinic.get("platform_attribution_position"),
    }

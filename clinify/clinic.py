import frappe


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

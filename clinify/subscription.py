from clinify.clinic import get_current_clinic


def get_subscription_state():
    """
    Return the current clinic subscription state.
    """

    clinic = get_current_clinic()

    return {
        "clinic_status": clinic.clinic_status,
        "subscription_status": clinic.subscription_status,
        "activation_date": clinic.activation_date,
    }


def is_subscription_active():
    """
    Return True when the clinic subscription permits access.

    Current allowed subscription states:
    - Trial
    - Active
    """

    clinic = get_current_clinic()

    allowed_statuses = {
        "Trial",
        "Active",
    }

    return clinic.subscription_status in allowed_statuses


def can_access_clinify():
    """
    Return True only when both:

    1. The clinic itself is Active.
    2. The subscription permits access.
    """

    clinic = get_current_clinic()

    if clinic.clinic_status != "Active":
        return False

    return is_subscription_active()


def get_access_status():
    """
    Return a complete access decision that can later be
    used by SaaS enforcement, APIs, dashboards, and UI.
    """

    clinic = get_current_clinic()

    subscription_active = is_subscription_active()

    clinic_active = (
        clinic.clinic_status == "Active"
    )

    access_allowed = (
        clinic_active
        and subscription_active
    )

    return {
        "clinic_active": clinic_active,
        "subscription_active": subscription_active,
        "access_allowed": access_allowed,
        "clinic_status": clinic.clinic_status,
        "subscription_status": clinic.subscription_status,
        "activation_date": clinic.activation_date,
    }

import frappe

from clinify.subscription import (
    can_access_clinify,
    get_access_status,
)


class ClinifyAccessError(frappe.PermissionError):
    """
    Raised when the current clinic is not permitted
    to access Clinify.
    """


def require_clinify_access():
    """
    Require the current clinic to have valid access.

    Returns the current access status when access is allowed.

    Raises:
        ClinifyAccessError:
            When the clinic or subscription does not
            permit access.
    """

    access_status = get_access_status()

    if not can_access_clinify():
        raise ClinifyAccessError(
            "Clinify access is currently unavailable. "
            "Please contact your administrator."
        )

    return access_status


def has_clinify_access():
    """
    Return True when the current clinic has access.

    This function does not raise an exception.
    """

    return can_access_clinify()


def get_clinify_access_status():
    """
    Return the complete current Clinify access status.
    """

    return get_access_status()

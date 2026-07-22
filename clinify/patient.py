from frappe.model.naming import getseries
from frappe.utils import nowdate, getdate


def assign_clinify_patient_id(doc, method=None):
    """
    Automatically assign a Clinify Patient ID.

    Format:
        CLN-YYMMDDNNNN

    Example:
        CLN-2607220001
    """

    # Don't regenerate if already assigned
    if doc.custom_clinify_patient_id:
        return

    today = getdate(nowdate())
    date_part = today.strftime("%y%m%d")

    # Internal daily series
    series_key = f"CLN-{date_part}-"

    sequence = getseries(series_key, 4)

    # Final stored/displayed Patient ID
    doc.custom_clinify_patient_id = f"CLN-{date_part}{sequence}"
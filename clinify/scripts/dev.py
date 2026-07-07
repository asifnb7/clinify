import frappe


def doctor_name(practitioner):
    if not practitioner:
        return ""

    return (
        frappe.db.get_value(
            "Healthcare Practitioner",
            practitioner,
            "practitioner_name",
        )
        or ""
    )


def patient_journey(appointment):
    """
    Returns the current patient journey based on reception status.
    """

    status = appointment.get("custom_reception_status") or "Waiting"

    journey = {
        "Waiting": {
            "label": "Waiting",
            "color": "blue",
        },
        "Checked In": {
            "label": "Checked In",
            "color": "green",
        },
        "With Doctor": {
            "label": "With Doctor",
            "color": "orange",
        },
        "Billing": {
            "label": "Billing",
            "color": "purple",
        },
        "Completed": {
            "label": "Completed",
            "color": "gray",
        },
    }

    return journey.get(
        status,
        {
            "label": status,
            "color": "blue",
        },
    )

import frappe


def after_save(doc, method=None):
    """
    Update the linked Patient Appointment when a
    Patient Encounter is saved.
    """

    if not doc.appointment:
        return

    frappe.db.set_value(
        "Patient Appointment",
        doc.appointment,
        "custom_reception_status",
        "Ready for Billing",
        update_modified=False
    )

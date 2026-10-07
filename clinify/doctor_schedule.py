import frappe
from frappe.utils import getdate, add_days


DEFAULT_FROM_TIME = "09:00:00"
DEFAULT_TO_TIME = "17:00:00"
DEFAULT_DURATION = 20

# Sunday is intentionally excluded from the default OPD schedule.
DEFAULT_DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]


def _get_opd_service_unit():
    rows = frappe.get_all(
        "Healthcare Service Unit",
        filters={
            "healthcare_service_unit_name": "OPD",
            "allow_appointments": 1,
        },
        fields=["name", "company"],
        order_by="name asc",
        limit=1,
    )

    return rows[0] if rows else None


def ensure_default_schedule(doc, method=None):
    """
    Create the native Healthcare scheduling foundation for a new Doctor.

    Clinify does not replace Healthcare scheduling.
    The Doctor remains linked to a native Practitioner Schedule.
    The schedule's duration remains editable through native Healthcare.
    """

    if not doc or doc.doctype != "Healthcare Practitioner":
        return

    if not frappe.db.exists("DocType", "Practitioner Schedule"):
        return

    if not frappe.db.exists("DocType", "Practitioner Service Unit Schedule"):
        return

    service_unit = _get_opd_service_unit()

    if not service_unit:
        return

    # Never overwrite an already-configured Doctor.
    if doc.get("practitioner_schedules"):
        return

    schedule_name = f"OPD - {doc.name}"

    if not frappe.db.exists("Practitioner Schedule", schedule_name):
        schedule = frappe.get_doc({
            "doctype": "Practitioner Schedule",
            "schedule_name": schedule_name,
            "disabled": 0,
        })

        for day in DEFAULT_DAYS:
            schedule.append("time_slots", {
                "day": day,
                "from_time": DEFAULT_FROM_TIME,
                "to_time": DEFAULT_TO_TIME,
                "duration": DEFAULT_DURATION,
                "maximum_appointments": 24,
            })

        schedule.insert(ignore_permissions=True)
    else:
        schedule = frappe.get_doc(
            "Practitioner Schedule",
            schedule_name,
        )

    practitioner = frappe.get_doc(
        "Healthcare Practitioner",
        doc.name,
    )

    if practitioner.get("practitioner_schedules"):
        return

    practitioner.append("practitioner_schedules", {
        "schedule": schedule.name,
        "service_unit": service_unit.name,
    })

    practitioner.save(ignore_permissions=True)
    frappe.db.commit()

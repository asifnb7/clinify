import frappe
from frappe.utils import nowdate

from clinify.billing import create_invoice_from_dental_plan


@frappe.whitelist()
def get_todays_appointments():
    """
    Return today's appointments for the Reception Dashboard.
    """

    from clinify.scripts.dev import doctor_name, patient_journey

    appointments = frappe.get_all(
        "Patient Appointment",
        filters={
            "appointment_date": nowdate(),
            "docstatus": ["!=", 2]
        },

fields=[
    "name",
    "appointment_time",
    "patient",
    "patient_name",
    "practitioner",
    "status",
    "custom_reception_status",
    "reference_doctype",
    "reference_docname",
    "ref_sales_invoice",
    "invoiced",
],

       order_by="appointment_time asc"
    )

    for appt in appointments:

        appt["doctor_name"] = doctor_name(
            appt.get("practitioner")
        )

        journey = patient_journey(appt)

        appt["journey_label"] = journey["label"]
        appt["journey_color"] = journey["color"]

    return appointments


@frappe.whitelist()
def get_billing_queue():
    """
    Return billing queue for the Reception Dashboard.
    """

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"docstatus": ["!=", 2]},
fields=[
    "name",
    "patient",
    "customer",
    "customer_name",
    "custom_primary_doctor",
    "grand_total",
    "outstanding_amount",
    "posting_date",
    "status",
],

order_by="posting_date desc, creation desc",
    )

    practitioner_ids = {
        inv["custom_primary_doctor"]
        for inv in invoices
        if inv.get("custom_primary_doctor")
    }

    doctor_lookup = {}

    if practitioner_ids:
        practitioners = frappe.get_all(
            "Healthcare Practitioner",
            filters={"name": ["in", list(practitioner_ids)]},
            fields=["name", "practitioner_name"],
        )

        doctor_lookup = {
            p["name"]: p["practitioner_name"]
            for p in practitioners
        }
    for invoice in invoices:

        invoice["paid_amount"] = (
            invoice["grand_total"] - invoice["outstanding_amount"]
        )

        if invoice["status"] == "Draft":
            invoice["workflow_stage"] = "Draft"

        elif invoice["outstanding_amount"] > 0:
            invoice["workflow_stage"] = "Pending Payment"

        else:
            invoice["workflow_stage"] = "Completed"

        invoice["doctor_name"] = doctor_lookup.get(
            invoice.get("custom_primary_doctor"),
            "",
        )

    return invoices

@frappe.whitelist()
def check_in_patient(appointment):
    """
    Check in a patient from the Reception Dashboard.
    """

    appt = frappe.get_doc("Patient Appointment", appointment)

    appt.custom_reception_status = "Checked In"

    appt.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success": True,
        "status": appt.custom_reception_status
    }


@frappe.whitelist()
def get_ready_for_billing():
    """
    Return today's appointments that are ready
    for billing but have not yet been invoiced.
    """

    from clinify.scripts.dev import doctor_name

    appointments = frappe.get_all(
        "Patient Appointment",
    
 filters={
    "appointment_date": nowdate(),
    "custom_reception_status": "Billing",
    "docstatus": ["!=", 2],
    "ref_sales_invoice": ["in", ["", None]],
},

        fields=[
            "name",
            "patient",
            "patient_name",
            "appointment_time",
            "practitioner",
            "custom_reception_status",
        ],
        order_by="appointment_time asc",
    )

    for appt in appointments:

        appt["doctor_name"] = doctor_name(
            appt.get("practitioner")
        )

    return appointments


@frappe.whitelist()
def create_invoice_from_ready_appointment(appointment):
    """
    Create Sales Invoice for a ready appointment using the mapped Dental Treatment Plan.
    """

    appt = frappe.get_doc("Patient Appointment", appointment)

    if appt.reference_doctype != "Dental Treatment Plan" or not appt.reference_docname:
        frappe.throw(
            "This appointment is not mapped to a Dental Treatment Plan."
        )

    invoice_name = create_invoice_from_dental_plan(appt.reference_docname)

    appt.ref_sales_invoice = invoice_name
    appt.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success": True,
        "invoice": invoice_name,
    }

@frappe.whitelist()
def search_patients(search_text):
    """
    Smart Patient Search

    Search by:
    - Clinify Patient ID
    - Patient Name
    - Mobile Number
    """

    search_text = (search_text or "").strip()

    if not search_text:
        return []

    return frappe.get_all(
        "Patient",
        or_filters=[
            {
                "custom_clinify_patient_id": ["like", f"%{search_text}%"]
            },
            {
                "patient_name": ["like", f"%{search_text}%"]
            },
            {
                "mobile": ["like", f"%{search_text}%"]
            },
            {
                "phone": ["like", f"%{search_text}%"]
            },
        ],
        fields=[
            "name",
            "patient_name",
            "mobile",
            "custom_clinify_patient_id",
            "sex",
            "dob",
        ],
        limit_page_length=20,
        order_by="modified desc",
    )


@frappe.whitelist()
def get_reception_patient(patient):
    """
    Return the basic patient details required by the Reception Patient Workspace.
    """

    if not patient:
        frappe.throw("Patient is required.")

    if not frappe.has_permission("Patient", "read", patient):
        frappe.throw("Not permitted.", frappe.PermissionError)

    patient_details = frappe.db.get_value(
        "Patient",
        patient,
        [
            "name",
            "patient_name",
            "mobile",
            "phone",
            "custom_clinify_patient_id",
            "sex",
            "dob",
        ],
        as_dict=True,
    )

    if not patient_details:
        frappe.throw("Patient not found.")

    # ---------------------------------------------------------
    # Calculate TOTAL Outstanding Balance
    # (Same logic used by Billing)
    # ---------------------------------------------------------

    outstanding = frappe.db.sql(
        """
        SELECT COALESCE(SUM(outstanding_amount), 0)

        FROM `tabSales Invoice`

        WHERE
            patient = %s
            AND docstatus != 2
        """,
        (patient,),
    )[0][0]

    patient_details["account_balance"] = float(outstanding or 0)

    return patient_details

@frappe.whitelist()
def get_patient_appointments(patient):
    """
    Returns the latest 5 appointments for a patient
    together with doctor name and billing information.
    """

    appointments = frappe.get_all(
        "Patient Appointment",
        filters={"patient": patient},
        fields=[
            "name",
            "appointment_date",
            "appointment_time",
            "practitioner",
            "department",
            "status",
            "custom_reception_status",
            "ref_sales_invoice",
        ],
        order_by="appointment_date desc, appointment_time desc",
        limit_page_length=5,
    )

    practitioner_cache = {}

    for row in appointments:

        practitioner = row.get("practitioner")

        if practitioner:

            if practitioner not in practitioner_cache:
                practitioner_cache[practitioner] = frappe.db.get_value(
                    "Healthcare Practitioner",
                    practitioner,
                    "practitioner_name"
                ) or practitioner

            row["doctor_name"] = practitioner_cache[practitioner]

        invoice = row.get("ref_sales_invoice")

        if invoice:

            invoice_data = frappe.db.get_value(
                "Sales Invoice",
                invoice,
                ["grand_total", "outstanding_amount", "status"],
                as_dict=True,
            )

            row["billing_status"] = "Billable"
            row["invoice_total"] = float(invoice_data.grand_total or 0)
            row["account_balance"] = float(invoice_data.outstanding_amount or 0)
            row["invoice_status"] = invoice_data.status

        else:

            row["billing_status"] = "Pending"
            row["invoice_total"] = 0
            row["account_balance"] = 0
            row["invoice_status"] = ""

    return appointments


@frappe.whitelist()
def get_patient_encounters(patient):
    """
    Return the latest Patient Encounters for the selected patient.
    """

    encounters = frappe.get_all(
        "Patient Encounter",
        filters={
            "patient": patient,
            "docstatus": ["!=", 2]
        },
        fields=[
            "name",
            "encounter_date",
            "encounter_time",
            "practitioner",
            "practitioner_name",
            "medical_department",
            "encounter_comment",
            "status",
        ],
        order_by="encounter_date desc, encounter_time desc",
        limit_page_length=10,
    )

    return encounters

@frappe.whitelist()
def get_patient_billing(patient):
    """
    Return all Sales Invoices for the selected patient.
    """

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "patient": patient,
            "docstatus": ["!=", 2],
        },
        fields=[
            "name",
            "posting_date",
            "status",
            "grand_total",
            "outstanding_amount",
        ],
        order_by="posting_date desc, creation desc",
    )

    total_outstanding = 0

    for invoice in invoices:

        grand_total = float(invoice.get("grand_total") or 0)
        outstanding = float(invoice.get("outstanding_amount") or 0)

        invoice["paid_amount"] = grand_total - outstanding

        total_outstanding += outstanding

    return {
        "invoices": invoices,
        "total_outstanding": total_outstanding,
    }

@frappe.whitelist()
def get_patient_payments(patient):
    """
    Return all Payment Entries linked to the patient's Sales Invoices.
    """

    # Get all submitted Sales Invoices for this patient
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "patient": patient,
            "docstatus": 1,
        },
        pluck="name",
    )

    if not invoices:
        return []

    payments = frappe.db.sql(
        """
        SELECT
            pe.name AS payment_entry,
            pe.posting_date,
            pe.mode_of_payment,
            per.reference_name AS invoice,
            per.allocated_amount,
            pe.paid_amount

        FROM `tabPayment Entry Reference` per

        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent

        WHERE
            per.reference_doctype = 'Sales Invoice'
            AND per.reference_name IN %(invoices)s
            AND pe.docstatus = 1

        ORDER BY
            pe.posting_date DESC,
            pe.creation DESC
        """,
        {
            "invoices": tuple(invoices),
        },
        as_dict=True,
    )

    return payments


@frappe.whitelist()
def get_dashboard_summary():
    """
    Return Reception Dashboard summary statistics.
    """

    appointments = frappe.get_all(
        "Patient Appointment",
        filters={
            "appointment_date": nowdate(),
            "docstatus": ["!=", 2],
        },
        fields=[
            "custom_reception_status",
        ],
    )

    summary = {
        "today": len(appointments),
        "waiting": 0,
        "checked_in": 0,
        "ready_for_billing": 0,
    }

    for row in appointments:

        status = row.get("custom_reception_status")

        if status == "Waiting":
            summary["waiting"] += 1

        elif status == "Checked In":
            summary["checked_in"] += 1

        elif status == "Billing":
            summary["ready_for_billing"] += 1

    return summary

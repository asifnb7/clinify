import frappe


def _field_exists(doctype, fieldname):
    return frappe.db.exists(
        "Custom Field",
        {
            "dt": doctype,
            "fieldname": fieldname,
        },
    )


def _create_field(
    *,
    doctype,
    fieldname,
    label,
    fieldtype,
    insert_after,
    **kwargs,
):
    if _field_exists(doctype, fieldname):
        print(
            f"Clinify schema: {doctype}.{fieldname} already exists"
        )
        return

    doc = frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": doctype,
            "fieldname": fieldname,
            "label": label,
            "fieldtype": fieldtype,
            "insert_after": insert_after,
            **kwargs,
        }
    )

    doc.insert(ignore_permissions=True)

    print(
        f"Clinify schema: created "
        f"{doctype}.{fieldname}"
    )


def execute():
    """
    Install Clinify custom fields required by the
    active encounter and billing architecture.

    The patch is intentionally idempotent.

    Patient Encounter structure:

        custom_dental_services_section
                    |
                    v
        custom_dental_services
                    |
                    v
        Clinify Encounter Service

    Sales Invoice structure:

        customer
            |
            v
        custom_primary_doctor
    """

    # ---------------------------------------------------------
    # PATIENT — CLINIFY PATIENT ID
    # ---------------------------------------------------------

    _create_field(
        doctype="Patient",
        fieldname="custom_clinify_patient_id",
        label="Clinify Patient ID",
        fieldtype="Data",
        insert_after="patient_name",
        in_list_view=1,
        is_system_generated=1,
    )

    # ---------------------------------------------------------
    # PATIENT ENCOUNTER — DENTAL SERVICES SECTION
    # ---------------------------------------------------------

    _create_field(
        doctype="Patient Encounter",
        fieldname="custom_dental_services_section",
        label="Dental Services",
        fieldtype="Section Break",
        insert_after="custom_doctor_notes",
    )

    # ---------------------------------------------------------
    # PATIENT ENCOUNTER — DENTAL SERVICES TABLE
    # ---------------------------------------------------------

    _create_field(
        doctype="Patient Encounter",
        fieldname="custom_dental_services",
        label="Dental Services",
        fieldtype="Table",
        insert_after="custom_dental_services_section",
        options="Clinify Encounter Service",
    )

    # ---------------------------------------------------------
    # SALES INVOICE — PRIMARY DOCTOR
    # ---------------------------------------------------------

    _create_field(
        doctype="Sales Invoice",
        fieldname="custom_primary_doctor",
        label="Primary Doctor",
        fieldtype="Link",
        insert_after="customer",
        options="Healthcare Practitioner",
        read_only=1,
        in_list_view=1,
    )

    frappe.clear_cache()

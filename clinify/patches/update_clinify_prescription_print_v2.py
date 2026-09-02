import re
import frappe


PRINT_FORMAT_NAME = "Clinify Prescription"


def execute():

    print_format = frappe.get_doc(
        "Print Format",
        PRINT_FORMAT_NAME
    )

    html = print_format.html or ""

    # ---------------------------------------------------------
    # Compact 6-value patient/doctor header
    # ---------------------------------------------------------

    new_patient_table = r"""
<table class="patient-table">

    <tr>

        <td class="patient-label">Patient:</td>
        <td>{{ doc.patient_name or doc.patient or "-" }}</td>

        <td class="patient-label">Age:</td>
        <td>{{ doc.patient_age or "-" }}</td>

        <td class="patient-label">Gender:</td>
        <td>{{ doc.patient_sex or "-" }}</td>

    </tr>

    <tr>

        <td class="patient-label">Doctor:</td>
        <td>{{ doc.practitioner_name or doc.practitioner or "-" }}</td>

        <td class="patient-label">Department:</td>
        <td>{{ doc.medical_department or "-" }}</td>

        <td class="patient-label">Date:</td>
        <td>{{ doc.encounter_date or "-" }}</td>

    </tr>

</table>
"""

    html, replaced = re.subn(
        r'<table class="patient-table">.*?</table>',
        new_patient_table,
        html,
        count=1,
        flags=re.DOTALL,
    )

    if replaced != 1:
        frappe.throw(
            "Could not locate the existing patient header in Clinify Prescription."
        )


    # ---------------------------------------------------------
    # Chief Complaint
    # ---------------------------------------------------------

    complaint_block = r"""
<div class="section-title">
    Chief Complaint
</div>

<div class="advice-box">
    {% if doc.encounter_comment %}
        {{ doc.encounter_comment }}
    {% else %}
        <span class="empty-note">No chief complaint recorded.</span>
    {% endif %}
</div>

"""


    prescription_marker = """<div class="section-title">
    PRESCRIPTION
</div>"""


    if "Chief Complaint" not in html:

        if prescription_marker not in html:

            frappe.throw(
                "Could not locate the PRESCRIPTION section."
            )

        html = html.replace(
            prescription_marker,
            complaint_block + prescription_marker,
            1
        )


    # ---------------------------------------------------------
    # Save Print Format
    # ---------------------------------------------------------

    print_format.custom_format = 1
    print_format.print_format_type = "Jinja"
    print_format.disabled = 0
    print_format.html = html

    print_format.save(
        ignore_permissions=True
    )

    frappe.db.commit()

    print("")
    print("==============================================")
    print("CLINIFY PRESCRIPTION PRINT FORMAT V2 UPDATED")
    print("==============================================")
    print("Patient + Age + Gender + Doctor + Department + Date")
    print("Chief Complaint added")
    print("custom_format =", print_format.custom_format)
    print("==============================================")

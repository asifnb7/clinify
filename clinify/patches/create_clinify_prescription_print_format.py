import frappe


PRINT_FORMAT_NAME = "Clinify Prescription"


PRINT_HTML = r"""
<style>
    @page {
        size: A4;
        margin: 12mm;
    }

    body {
        font-family: Arial, Helvetica, sans-serif;
        color: #222;
        font-size: 12px;
        line-height: 1.45;
    }

    .clinify-header {
        text-align: center;
        margin-bottom: 18px;
        padding-bottom: 10px;
        border-bottom: 2px solid #222;
    }

    .clinify-title {
        font-size: 24px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    .clinify-subtitle {
        font-size: 11px;
        color: #666;
        margin-top: 2px;
    }

    .patient-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 18px;
    }

    .patient-table td {
        padding: 4px 6px;
        vertical-align: top;
    }

    .patient-label {
        font-weight: 700;
        width: 16%;
    }

    .section-title {
        font-size: 14px;
        font-weight: 700;
        margin: 12px 0 7px 0;
        padding-bottom: 4px;
        border-bottom: 1px solid #555;
    }

    .prescription-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 6px;
        table-layout: fixed;
    }

    .prescription-table th,
    .prescription-table td {
        border: 1px solid #999;
        padding: 6px 7px;
        vertical-align: top;
    }

    .prescription-table th {
        font-weight: 700;
        text-align: left;
        background: #f3f3f3;
    }

    .medicine-col {
        width: 31%;
    }

    .strength-col {
        width: 15%;
    }

    .dosage-col {
        width: 16%;
    }

    .period-col {
        width: 14%;
    }

    .instruction-col {
        width: 24%;
    }

    .advice-box {
        border: 1px solid #aaa;
        min-height: 55px;
        padding: 8px;
        margin-top: 6px;
        white-space: pre-wrap;
    }

    .followup-box {
        border: 1px solid #aaa;
        padding: 8px;
        margin-top: 6px;
    }

    .signature-section {
        margin-top: 45px;
        width: 100%;
    }

    .signature-line {
        width: 220px;
        border-top: 1px solid #444;
        padding-top: 5px;
        text-align: center;
        margin-left: auto;
    }

    .empty-note {
        color: #777;
        font-style: italic;
    }
</style>

<div class="clinify-header">
    <div class="clinify-title">CLINIFY</div>
    <div class="clinify-subtitle">Healthcare, Simplified</div>
</div>

<table class="patient-table">
    <tr>
        <td class="patient-label">Patient:</td>
        <td>{{ doc.patient_name or doc.patient }}</td>

        <td class="patient-label">Date:</td>
        <td>{{ doc.encounter_date or "" }}</td>
    </tr>

    <tr>
        <td class="patient-label">Doctor:</td>
        <td colspan="3">
            {{ doc.practitioner_name or doc.practitioner or "" }}
        </td>
    </tr>
</table>

<div class="section-title">
    PRESCRIPTION
</div>

<table class="prescription-table">
    <thead>
        <tr>
            <th class="medicine-col">Medicine / Description</th>
            <th class="strength-col">Strength</th>
            <th class="dosage-col">Dosage</th>
            <th class="period-col">Period</th>
            <th class="instruction-col">Instruction</th>
        </tr>
    </thead>

    <tbody>

    {% if doc.drug_prescription %}

        {% for row in doc.drug_prescription %}

        <tr>
            <td>
                {{ row.drug_name or row.drug_code or "" }}
            </td>

            <td>
                {% if row.strength %}
                    {{ row.strength }}
                    {% if row.strength_uom %}
                        {{ row.strength_uom }}
                    {% endif %}
                {% endif %}
            </td>

            <td>
                {% if row.dosage %}
                    {{ row.dosage }}
                {% elif row.interval %}
                    Every {{ row.interval }}
                    {% if row.interval_uom %}
                        {{ row.interval_uom }}
                    {% endif %}
                {% endif %}
            </td>

            <td>
                {{ row.period or "" }}
            </td>

            <td>
                {{ row.custom_instruction or "" }}
            </td>
        </tr>

        {% endfor %}

    {% else %}

        <tr>
            <td colspan="5" class="empty-note">
                No medicines prescribed.
            </td>
        </tr>

    {% endif %}

    </tbody>
</table>

<div class="section-title">
    Doctor's Advice
</div>

<div class="advice-box">
    {% if doc.encounter_comment %}
        {{ doc.encounter_comment }}
    {% else %}
        <span class="empty-note">No additional advice recorded.</span>
    {% endif %}
</div>


{% if doc.custom_follow_up_required %}

<div class="section-title">
    Follow-up
</div>

<div class="followup-box">

    {% if doc.custom_follow_up_after_days %}
        Follow up after
        <strong>{{ doc.custom_follow_up_after_days }}</strong>
        day(s).
        <br>
    {% endif %}

    {% if doc.custom_follow_up_date %}
        Follow-up date:
        <strong>{{ doc.custom_follow_up_date }}</strong>
    {% endif %}

</div>

{% endif %}


<div class="signature-section">
    <div class="signature-line">
        Doctor Signature
    </div>
</div>
"""


def execute():
    existing = frappe.db.exists(
        "Print Format",
        PRINT_FORMAT_NAME
    )

    if existing:
        doc = frappe.get_doc(
            "Print Format",
            PRINT_FORMAT_NAME
        )
        doc.doc_type = "Patient Encounter"
        doc.print_format_type = "Jinja"
        doc.raw_printing = 0
        doc.html = PRINT_HTML
        doc.disabled = 0
        doc.standard = "No"
        doc.module = "Clinify"
        doc.save(ignore_permissions=True)

        print("Updated existing Print Format:")
        print(PRINT_FORMAT_NAME)

    else:
        doc = frappe.get_doc({
            "doctype": "Print Format",
            "name": PRINT_FORMAT_NAME,
            "doc_type": "Patient Encounter",
            "print_format_type": "Jinja",
            "raw_printing": 0,
            "html": PRINT_HTML,
            "disabled": 0,
            "standard": "No",
            "module": "Clinify",
        })

        doc.insert(ignore_permissions=True)

        print("Created Print Format:")
        print(PRINT_FORMAT_NAME)

    frappe.db.commit()

    print("DocType: Patient Encounter")
    print("Type: Jinja")
    print("Status: Enabled")

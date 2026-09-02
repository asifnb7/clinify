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
        line-height: 1.4;
    }

    .clinify-header {
        text-align: center;
        margin-bottom: 14px;
        padding-bottom: 8px;
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

    .patient-table,
    .clinical-table {
        width: 100%;
        border-collapse: collapse;
    }

    .patient-table {
        margin-bottom: 10px;
    }

    .patient-table td {
        padding: 3px 5px;
        vertical-align: top;
    }

    .patient-label {
        font-weight: 700;
        white-space: nowrap;
    }

    .clinical-table {
        margin-top: 6px;
        margin-bottom: 12px;
    }

    .clinical-table > tbody > tr > td {
        vertical-align: top;
    }

    .complaint-cell {
        width: 65%;
        padding-right: 10px;
    }

    .vitals-cell {
        width: 35%;
        padding-left: 10px;
    }

    .section-title {
        font-size: 14px;
        font-weight: 700;
        margin: 10px 0 6px 0;
        padding-bottom: 4px;
        border-bottom: 1px solid #555;
    }

    .complaint-box {
        border: 1px solid #aaa;
        padding: 8px;
        min-height: 48px;
        white-space: pre-wrap;
    }

    .vitals-box {
        border: 1px solid #888;
        padding: 7px 9px;
        border-radius: 4px;
    }

    .vitals-title {
        font-weight: 700;
        margin-bottom: 4px;
        font-size: 12px;
    }

    .vitals-row {
        width: 100%;
        border-collapse: collapse;
    }

    .vitals-row td {
        padding: 2px 0;
        vertical-align: top;
    }

    .vital-label {
        font-weight: 600;
        width: 58%;
    }

    .vital-value {
        text-align: right;
        white-space: nowrap;
    }

    .prescription-table,
    .lab-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        margin-top: 6px;
    }

    .prescription-table th,
    .prescription-table td,
    .lab-table th,
    .lab-table td {
        border: 1px solid #999;
        padding: 6px 7px;
        vertical-align: top;
    }

    .prescription-table th,
    .lab-table th {
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

    .lab-name-col {
        width: 60%;
    }

    .lab-comment-col {
        width: 40%;
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
        margin-top: 40px;
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


{% set vitals = frappe.get_all(
    "Vital Signs",
    filters={"encounter": doc.name},
    fields=[
        "name",
        "signs_date",
        "signs_time",
        "temperature",
        "pulse",
        "respiratory_rate",
        "bp_systolic",
        "bp_diastolic",
        "weight",
        "bmi"
    ],
    order_by="signs_date desc, signs_time desc",
    limit_page_length=1
) %}


<table class="clinical-table">
    <tr>

        <td class="complaint-cell">

            <div class="section-title">
                Chief Complaint
            </div>

            <div class="complaint-box">
                {% if doc.encounter_comment %}
                    {{ doc.encounter_comment }}
                {% else %}
                    <span class="empty-note">
                        No chief complaint recorded.
                    </span>
                {% endif %}
            </div>

        </td>


        {% if vitals %}

        {% set vital = vitals[0] %}

        <td class="vitals-cell">

            <div class="section-title">
                Vitals
            </div>

            <div class="vitals-box">

                <div class="vitals-title">
                    Recorded Vitals
                </div>

                <table class="vitals-row">

                    {% if vital.bp_systolic or vital.bp_diastolic %}
                    <tr>
                        <td class="vital-label">BP</td>
                        <td class="vital-value">
                            {{ vital.bp_systolic or "-" }}/{{ vital.bp_diastolic or "-" }}
                            mmHg
                        </td>
                    </tr>
                    {% endif %}


                    {% if vital.pulse %}
                    <tr>
                        <td class="vital-label">Pulse</td>
                        <td class="vital-value">
                            {{ vital.pulse }}
                        </td>
                    </tr>
                    {% endif %}


                    {% if vital.temperature %}
                    <tr>
                        <td class="vital-label">Temperature</td>
                        <td class="vital-value">
                            {{ vital.temperature }}
                        </td>
                    </tr>
                    {% endif %}


                    {% if vital.respiratory_rate %}
                    <tr>
                        <td class="vital-label">Resp. Rate</td>
                        <td class="vital-value">
                            {{ vital.respiratory_rate }}
                        </td>
                    </tr>
                    {% endif %}


                    {% if vital.weight %}
                    <tr>
                        <td class="vital-label">Weight</td>
                        <td class="vital-value">
                            {{ vital.weight }} kg
                        </td>
                    </tr>
                    {% endif %}


                    {% if vital.bmi %}
                    <tr>
                        <td class="vital-label">BMI</td>
                        <td class="vital-value">
                            {{ vital.bmi }}
                        </td>
                    </tr>
                    {% endif %}

                </table>

            </div>

        </td>

        {% endif %}

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


{% if doc.lab_test_prescription %}

<div class="section-title">
    LAB TESTS
</div>

<table class="lab-table">

    <thead>
        <tr>
            <th class="lab-name-col">Lab Test</th>
            <th class="lab-comment-col">Comments</th>
        </tr>
    </thead>

    <tbody>

        {% for row in doc.lab_test_prescription %}

        <tr>

            <td>
                {{ row.lab_test_name or row.lab_test_code or "" }}
            </td>

            <td>
                {{ row.lab_test_comment or "" }}
            </td>

        </tr>

        {% endfor %}

    </tbody>

</table>

{% endif %}


<div class="section-title">
    Doctor's Advice
</div>

<div class="advice-box">

    {% if doc.encounter_comment %}
        {{ doc.encounter_comment }}
    {% else %}
        <span class="empty-note">
            No additional advice recorded.
        </span>
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

    print_format = frappe.get_doc(
        "Print Format",
        PRINT_FORMAT_NAME
    )

    print_format.custom_format = 1
    print_format.print_format_type = "Jinja"
    print_format.disabled = 0
    print_format.html = PRINT_HTML

    print_format.save(
        ignore_permissions=True
    )

    frappe.db.commit()

    print("")
    print("================================================")
    print("CLINIFY PRESCRIPTION PRINT FORMAT V2.1 UPDATED")
    print("================================================")
    print("Conditional Lab Tests: ENABLED")
    print("Conditional Vitals: ENABLED")
    print("Existing prescription layout: PRESERVED")
    print("custom_format =", print_format.custom_format)
    print("================================================")

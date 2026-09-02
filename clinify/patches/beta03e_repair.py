import re
from pathlib import Path
from datetime import datetime

import frappe


PRINT_FORMAT = "Clinify Prescription"
TEST_ENCOUNTER = "HLC-ENC-2026-00062"


def renderable(value):
    return bool(
        value is not None
        and str(value).strip()
    )


def jinja_balance(html):
    tokens = re.findall(
        r"{%\s*(if|endif|for|endfor)\b.*?%}",
        html,
        re.IGNORECASE | re.DOTALL,
    )

    stack = []

    for token in tokens:
        token = token.lower()

        if token in ("if", "for"):
            stack.append(token)

        elif token == "endif":
            if not stack or stack[-1] != "if":
                return False
            stack.pop()

        elif token == "endfor":
            if not stack or stack[-1] != "for":
                return False
            stack.pop()

    return not stack


def section_heading(title):
    return re.compile(
        r'<div\s+class=["\']section-title["\']>\s*'
        + re.escape(title)
        + r'\s*</div>',
        re.IGNORECASE,
    )


def find_region(html, start_title, end_title):
    """
    Remove the existing clinical section region without
    depending on its current internal Jinja arrangement.
    """

    start = section_heading(start_title).search(html)
    end = section_heading(end_title).search(
        html,
        start.end() if start else 0,
    )

    if not start or not end:
        return None

    # Look backwards for the nearest Jinja opening condition
    # that plausibly owns the clinical section.
    prefix_start = max(
        0,
        start.start() - 4000,
    )

    prefix = html[prefix_start:start.start()]

    matches = list(
        re.finditer(
            r"{%\s*if\s+[^%]+%}",
            prefix,
            re.IGNORECASE,
        )
    )

    if matches:
        candidate = matches[-1]
        candidate_pos = (
            prefix_start + candidate.start()
        )

        # Only use it if there is an endif after the notes
        # boundary. Otherwise keep the heading itself.
        suffix = html[end.start():]

        endif_match = re.search(
            r"{%\s*endif\s*%}",
            suffix,
            re.IGNORECASE,
        )

        if endif_match:
            possible_end = (
                end.start()
                + endif_match.end()
            )

            return candidate_pos, possible_end

    return start.start(), end.start()


def dental_block():
    return """
{% if doc.custom_dental_services %}
<div class="section-title">
    DENTAL SERVICES
</div>

<table class="prescription-table">
    <thead>
        <tr>
            <th style="width:45%;">Dental Service</th>
            <th style="width:20%;">Tooth / Area</th>
            <th style="width:10%;">Quantity</th>
            <th style="width:25%;">Remarks</th>
        </tr>
    </thead>
    <tbody>
        {% for row in doc.custom_dental_services %}
        <tr>
            <td>
                {{
                    frappe.db.get_value(
                        "Dental Service",
                        row.dental_service,
                        "service_name"
                    )
                    or row.dental_service
                    or ""
                }}
            </td>
            <td>{{ row.tooth_area or "" }}</td>
            <td>{{ row.qty or 1 }}</td>
            <td>{{ row.remarks or "" }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endif %}
"""


def lab_block():
    return """
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
"""


def prescription_block():
    return """
{% if doc.drug_prescription %}
<div class="section-title">
    PRESCRIPTION
</div>

<table class="prescription-table">
    <thead>
        <tr>
            <th class="medicine-col">Medicine / Description</th>
            <th class="dosage-col">Strength</th>
            <th class="dosage-col">Dosage</th>
            <th class="period-col">Period</th>
            <th class="instruction-col">Instruction</th>
        </tr>
    </thead>
    <tbody>
        {% for row in doc.drug_prescription %}
        <tr>
            <td>
                {{ row.drug_name or row.drug_code or "" }}
            </td>
            <td>
                {{ row.dosage_form or "" }}
            </td>
            <td>
                {{ row.dosage or "" }}
            </td>
            <td>
                {{ row.period or "" }}
            </td>
            <td>
                {{ row.custom_instruction or "" }}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endif %}
"""


def complaint_block():
    return """
{% if doc.encounter_comment %}
<div class="section-title">
    Chief Complaint
</div>

<div class="complaint-box">
    {{ doc.encounter_comment }}
</div>
{% endif %}
"""


def execute():

    print("")
    print("===== 1. LOAD PRINT FORMAT =====")

    pf = frappe.get_doc(
        "Print Format",
        PRINT_FORMAT,
    )

    if pf.doc_type != "Patient Encounter":
        frappe.throw(
            f"Unexpected DocType: {pf.doc_type}"
        )

    if pf.disabled:
        frappe.throw(
            "Clinify Prescription is disabled."
        )

    original_html = pf.html or ""

    print(
        "Print Format:",
        pf.name,
    )

    print(
        "HTML length:",
        len(original_html),
    )

    print("")
    print("===== 2. BACKUP CURRENT STATE =====")

    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_dir = (
        Path.home()
        / "clinify-backups"
        / f"BETA-03F-before-repair-{stamp}"
    )

    backup_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        backup_dir
        / "Clinify Prescription.html"
    ).write_text(
        original_html,
        encoding="utf-8",
    )

    (
        backup_dir
        / "Clinify Prescription.css"
    ).write_text(
        pf.css or "",
        encoding="utf-8",
    )

    print(
        "Backup:",
        backup_dir,
    )

    print("")
    print("===== 3. ACTUAL TEST ENCOUNTER =====")

    if not frappe.db.exists(
        "Patient Encounter",
        TEST_ENCOUNTER,
    ):
        frappe.throw(
            f"Encounter not found: {TEST_ENCOUNTER}"
        )

    encounter = frappe.get_doc(
        "Patient Encounter",
        TEST_ENCOUNTER,
    )

    dental_rows = (
        encounter.custom_dental_services
        or []
    )

    drug_rows = (
        encounter.drug_prescription
        or []
    )

    print(
        "Encounter:",
        encounter.name,
    )

    print(
        "Patient:",
        encounter.patient,
    )

    print(
        "Chief Complaint:",
        repr(encounter.encounter_comment),
    )

    print(
        "Dental rows:",
        len(dental_rows),
    )

    for row in dental_rows:
        print(
            "  DENTAL:",
            row.dental_service,
            "| tooth=",
            row.tooth_area,
            "| qty=",
            row.qty,
            "| remarks=",
            repr(row.remarks),
        )

    print(
        "Prescription rows:",
        len(drug_rows),
    )

    for row in drug_rows:
        print(
            "  DRUG:",
            row.drug_name or row.drug_code,
            "| dosage=",
            repr(row.dosage),
            "| period=",
            repr(row.period),
            "| instruction=",
            repr(row.custom_instruction),
        )

    print("")
    print("===== 4. REMOVE DAMAGED CLINICAL REGION =====")

    region = find_region(
        original_html,
        "DENTAL SERVICES",
        "Doctor's Notes / Advice",
    )

    if not region:
        frappe.throw(
            "Could not locate the existing clinical print region."
        )

    region_start, region_end = region

    print(
        "Region:",
        region_start,
        "→",
        region_end,
    )

    clinical_region = (
        complaint_block()
        + "\n"
        + dental_block()
        + "\n"
        + lab_block()
        + "\n"
        + prescription_block()
        + "\n"
    )

    new_html = (
        original_html[:region_start]
        + clinical_region
        + original_html[region_end:]
    )

    print(
        "New HTML length:",
        len(new_html),
    )

    print("")
    print("===== 5. JINJA STRUCTURE CHECK =====")

    if not jinja_balance(new_html):
        frappe.throw(
            "Jinja structure is unbalanced. "
            "REFUSING TO SAVE."
        )

    print(
        "Jinja balance: PASS"
    )

    print("")
    print("===== 6. REQUIRED FIELD MAPPINGS =====")

    required = [
        "doc.encounter_comment",
        "doc.custom_dental_services",
        "doc.lab_test_prescription",
        "doc.drug_prescription",
        "row.custom_instruction",
    ]

    for value in required:

        present = value in new_html

        print(
            value,
            "=>",
            present,
        )

        if not present:
            frappe.throw(
                f"Required mapping missing: {value}"
            )

    print("")
    print("===== 7. SAVE =====")

    pf.html = new_html

    pf.save(
        ignore_permissions=True
    )

    frappe.clear_cache(
        doctype="Print Format"
    )

    frappe.db.commit()

    print(
        "Print Format save: PASS"
    )

    print("")
    print("===== 8. RENDER REAL ENCOUNTER =====")

    rendered = frappe.get_print(
        "Patient Encounter",
        TEST_ENCOUNTER,
        print_format=PRINT_FORMAT,
        no_letterhead=1,
    )

    print(
        "Rendered length:",
        len(rendered),
    )

    complaint = (
        encounter.encounter_comment
        or ""
    )

    complaint_ok = (
        bool(complaint)
        and complaint in rendered
    )

    print(
        "Chief Complaint rendered:",
        complaint_ok,
    )

    if dental_rows:

        dental_ok = True

        for row in dental_rows:

            service_name = frappe.db.get_value(
                "Dental Service",
                row.dental_service,
                "service_name",
            )

            if not service_name:
                service_name = row.dental_service

            found = (
                bool(service_name)
                and service_name in rendered
            )

            print(
                "Dental row rendered:",
                service_name,
                "=>",
                found,
            )

            dental_ok = (
                dental_ok
                and found
            )

    else:
        dental_ok = True
        print(
            "Dental rows: none"
        )

    instruction_ok = True

    for row in drug_rows:

        instruction = (
            row.custom_instruction
            or ""
        ).strip()

        if instruction:

            found = (
                instruction in rendered
            )

            print(
                "Instruction rendered:",
                repr(instruction),
                "=>",
                found,
            )

            instruction_ok = (
                instruction_ok
                and found
            )

    print("")
    print("===== 9. FINAL ORDER =====")

    positions = {}

    for marker in [
        "Chief Complaint",
        "DENTAL SERVICES",
        "LAB TESTS",
        "PRESCRIPTION",
        "Doctor's Notes / Advice",
    ]:

        positions[marker] = rendered.find(
            marker
        )

        print(
            marker,
            "=>",
            positions[marker],
        )

    order_ok = (
        positions["Chief Complaint"] >= 0
        and positions["DENTAL SERVICES"] >= 0
        and positions["LAB TESTS"] >= 0
        and positions["PRESCRIPTION"] >= 0
        and positions["Doctor's Notes / Advice"] >= 0
        and positions["Chief Complaint"]
            < positions["DENTAL SERVICES"]
        and positions["DENTAL SERVICES"]
            < positions["LAB TESTS"]
        and positions["LAB TESTS"]
            < positions["PRESCRIPTION"]
        and positions["PRESCRIPTION"]
            < positions["Doctor's Notes / Advice"]
    )

    print(
        "Order:",
        order_ok,
    )

    print("")
    print("===== 10. ACCEPTANCE =====")

    if not complaint_ok:
        frappe.throw(
            "Chief Complaint did not render correctly."
        )

    if not dental_ok:
        frappe.throw(
            "One or more Dental Services did not render."
        )

    if not instruction_ok:
        frappe.throw(
            "One or more stored Instructions did not render."
        )

    if not order_ok:
        frappe.throw(
            "Clinical section order is incorrect."
        )

    print("")
    print("============================================================")
    print("BETA-03F COMPLETE")
    print("CHIEF COMPLAINT: PASS")
    print("DENTAL SERVICES: PASS")
    print("LAB TESTS: PASS")
    print("PRESCRIPTION: PASS")
    print("INSTRUCTION MAPPING: PASS")
    print("RENDER VALIDATION: PASS")
    print("ORDER: CHIEF → DENTAL → LAB → PRESCRIPTION → NOTES")
    print("SCHEMA: UNTOUCHED")
    print("BILLING: UNTOUCHED")
    print("SAAS: UNTOUCHED")
    print("============================================================")



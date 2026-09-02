import re
from pathlib import Path
from datetime import datetime

import frappe


PRINT_FORMAT = "Clinify Prescription"
TEST_ENCOUNTER = "HLC-ENC-2026-00062"


def jinja_is_balanced(html):
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


def insert_before_first(html, marker, block):
    position = html.find(marker)

    if position < 0:
        return None

    return (
        html[:position]
        + block
        + "\n\n"
        + html[position:]
    )


def execute():

    print("")
    print("===== 1. LOAD ACTIVE PRINT FORMAT =====")

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

    html = pf.html or ""

    print("Print Format:", pf.name)
    print("Original HTML:", len(html))

    print("")
    print("===== 2. BACKUP CURRENT WORKING STATE =====")

    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_dir = (
        Path.home()
        / "clinify-backups"
        / f"BETA-03G-before-finish-{stamp}"
    )

    backup_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        backup_dir
        / "Clinify Prescription.html"
    ).write_text(
        html,
        encoding="utf-8",
    )

    (
        backup_dir
        / "Clinify Prescription.css"
    ).write_text(
        pf.css or "",
        encoding="utf-8",
    )

    print("Backup:", backup_dir)

    print("")
    print("===== 3. LAB TABLE STYLE REPAIR =====")

    lab_css = """
.lab-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    margin-top: 6px;
    margin-bottom: 12px;
}

.lab-table th,
.lab-table td {
    border: 1px solid #888;
    padding: 5px 6px;
    vertical-align: top;
    line-height: 1.35;
}

.lab-table th {
    font-weight: 700;
    background: #f5f5f5;
}

.lab-name-col {
    width: 55%;
}

.lab-comment-col {
    width: 45%;
}
"""

    if ".lab-table th" not in html:

        style_end = html.find(
            "</style>"
        )

        if style_end < 0:
            frappe.throw(
                "Could not locate </style> in Print Format."
            )

        html = (
            html[:style_end]
            + "\n"
            + lab_css
            + "\n"
            + html[style_end:]
        )

        print("Lab CSS: INSERTED")

    else:
        print("Lab CSS: ALREADY PRESENT")

    print("")
    print("===== 4. DOCTOR NOTES =====")

    notes_marker = "Doctor's Notes / Advice"

    if notes_marker in html:
        print(
            "Doctor Notes heading already present."
        )

    else:

        notes_block = """
{% if doc.custom_doctor_notes and frappe.utils.strip_html(doc.custom_doctor_notes).strip() %}

<div class="section-title">
    Doctor's Notes / Advice
</div>

<div class="clinical-notes-content">
    {{ doc.custom_doctor_notes }}
</div>

{% endif %}
"""

        inserted = False

        followup_marker = "{% if doc.custom_follow_up_required %}"

        if followup_marker in html:

            html = insert_before_first(
                html,
                followup_marker,
                notes_block,
            )

            inserted = True

        if not inserted:

            signature_marker = '<div class="signature-section">'

            if signature_marker in html:

                html = insert_before_first(
                    html,
                    signature_marker,
                    notes_block,
                )

                inserted = True

        if not inserted:
            frappe.throw(
                "Could not safely locate insertion point for Doctor's Notes."
            )

        print(
            "Doctor Notes block: INSERTED"
        )

    print("")
    print("===== 5. NOTES CSS =====")

    notes_css = """
.clinical-notes-content {
    border: 1px solid #888;
    border-radius: 3px;
    min-height: 50px;
    padding: 8px 10px;
    margin-top: 6px;
    margin-bottom: 12px;
    line-height: 1.4;
}
"""

    if ".clinical-notes-content" not in html:

        style_end = html.find(
            "</style>"
        )

        if style_end < 0:
            frappe.throw(
                "Could not locate </style> for notes CSS."
            )

        html = (
            html[:style_end]
            + "\n"
            + notes_css
            + "\n"
            + html[style_end:]
        )

        print("Notes CSS: INSERTED")

    else:
        print("Notes CSS: ALREADY PRESENT")

    print("")
    print("===== 6. JINJA STRUCTURE CHECK =====")

    if not jinja_is_balanced(html):
        frappe.throw(
            "Jinja structure is unbalanced. "
            "REFUSING TO SAVE."
        )

    print(
        "Jinja balance: PASS"
    )

    print("")
    print("===== 7. SAVE PRINT FORMAT =====")

    pf.html = html

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
    print("===== 8. REAL ENCOUNTER DATA =====")

    encounter = frappe.get_doc(
        "Patient Encounter",
        TEST_ENCOUNTER,
    )

    print(
        "Encounter:",
        encounter.name,
    )

    print(
        "Chief Complaint:",
        repr(
            encounter.encounter_comment
        ),
    )

    print(
        "Doctor Notes:",
        repr(
            encounter.custom_doctor_notes
        ),
    )

    print(
        "Dental rows:",
        len(
            encounter.custom_dental_services
            or []
        ),
    )

    print(
        "Lab rows:",
        len(
            encounter.lab_test_prescription
            or []
        ),
    )

    print(
        "Prescription rows:",
        len(
            encounter.drug_prescription
            or []
        ),
    )

    print("")
    print("===== 9. RENDER =====")

    rendered = frappe.get_print(
        "Patient Encounter",
        TEST_ENCOUNTER,
        print_format=PRINT_FORMAT,
        no_letterhead=1,
    )

    print(
        "Rendered HTML:",
        len(rendered),
    )

    complaint = (
        encounter.encounter_comment
        or ""
    ).strip()

    complaint_ok = (
        bool(complaint)
        and complaint in rendered
    )

    print(
        "Chief Complaint rendered:",
        complaint_ok,
    )

    dental_ok = True

    for row in (
        encounter.custom_dental_services
        or []
    ):

        service_name = frappe.db.get_value(
            "Dental Service",
            row.dental_service,
            "service_name",
        ) or row.dental_service

        found = (
            bool(service_name)
            and service_name in rendered
        )

        print(
            "Dental:",
            service_name,
            "=>",
            found,
        )

        dental_ok = (
            dental_ok
            and found
        )

    lab_ok = True

    for row in (
        encounter.lab_test_prescription
        or []
    ):

        lab_name = (
            getattr(
                row,
                "lab_test_name",
                None,
            )
            or getattr(
                row,
                "lab_test_code",
                None,
            )
            or ""
        ).strip()

        if not lab_name:
            continue

        found = (
            lab_name in rendered
        )

        print(
            "Lab:",
            lab_name,
            "=>",
            found,
        )

        lab_ok = (
            lab_ok
            and found
        )

    instruction_ok = True

    for row in (
        encounter.drug_prescription
        or []
    ):

        instruction = (
            row.custom_instruction
            or ""
        ).strip()

        if instruction:

            found = (
                instruction in rendered
            )

            print(
                "Instruction:",
                repr(instruction),
                "=>",
                found,
            )

            instruction_ok = (
                instruction_ok
                and found
            )

    notes_text = frappe.utils.strip_html(
        encounter.custom_doctor_notes
        or ""
    ).strip()

    notes_ok = (
        bool(notes_text)
        and notes_text in
        frappe.utils.strip_html(
            rendered
        )
    )

    print(
        "Doctor Notes rendered:",
        notes_ok,
    )

    print("")
    print("===== 10. SECTION PRESENCE =====")

    for marker in [
        "Chief Complaint",
        "DENTAL SERVICES",
        "LAB TESTS",
        "PRESCRIPTION",
        "Doctor's Notes / Advice",
    ]:

        print(
            marker,
            "=>",
            marker in rendered,
        )

    print("")
    print("===== 11. FINAL ACCEPTANCE =====")

    if not complaint_ok:
        frappe.throw(
            "Chief Complaint failed render validation."
        )

    if not dental_ok:
        frappe.throw(
            "Dental Services failed render validation."
        )

    if not lab_ok:
        frappe.throw(
            "Lab Tests failed render validation."
        )

    if not instruction_ok:
        frappe.throw(
            "Prescription Instruction failed render validation."
        )

    if notes_text and not notes_ok:
        frappe.throw(
            "Doctor Notes failed render validation."
        )

    print("")
    print("============================================================")
    print("BETA-03G COMPLETE")
    print("CHIEF COMPLAINT: PASS")
    print("DENTAL SERVICES: PASS")
    print("LAB TESTS: PASS")
    print("PRESCRIPTION: PASS")
    print("INSTRUCTION: PASS")
    print("DOCTOR NOTES: PASS")
    print("RENDER VALIDATION: PASS")
    print("DATABASE: PRINT FORMAT ONLY")
    print("SCHEMA: UNTOUCHED")
    print("BILLING: UNTOUCHED")
    print("SAAS: UNTOUCHED")
    print("============================================================")



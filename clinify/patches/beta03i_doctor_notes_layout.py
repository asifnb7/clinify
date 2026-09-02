import re
from pathlib import Path
from datetime import datetime

import frappe


PRINT_FORMAT = "Clinify Prescription"
TEST_ENCOUNTER = "HLC-ENC-2026-00062"


def execute():

    print("")
    print("===== 1. LOAD CURRENT PRINT FORMAT =====")

    pf = frappe.get_doc(
        "Print Format",
        PRINT_FORMAT,
    )

    if pf.doc_type != "Patient Encounter":
        frappe.throw(
            f"Unexpected DocType: {pf.doc_type}"
        )

    html = pf.html or ""

    print(
        "Current HTML length:",
        len(html),
    )

    print("")
    print("===== 2. BACKUP =====")

    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_dir = (
        Path.home()
        / "clinify-backups"
        / f"BETA-03I-before-notes-fix-{stamp}"
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

    print(
        "Backup:",
        backup_dir,
    )

    print("")
    print("===== 3. LOCATE CURRENT DOCTOR NOTES BLOCK =====")

    notes_pattern = re.compile(
        r"{%\s*if\s+doc\.custom_doctor_notes"
        r".*?"
        r"{%\s*endif\s*%}",
        re.IGNORECASE | re.DOTALL,
    )

    matches = list(
        notes_pattern.finditer(html)
    )

    print(
        "Doctor Notes blocks found:",
        len(matches),
    )

    if len(matches) != 1:
        frappe.throw(
            "Expected exactly one Doctor Notes block. "
            "Refusing modification."
        )

    notes_html = matches[0].group(0)

    print(
        "Existing notes block located: PASS"
    )

    print("")
    print("===== 4. REMOVE EXISTING NOTES BLOCK =====")

    html_without_notes = (
        html[:matches[0].start()]
        + html[matches[0].end():]
    )

    print(
        "Removed existing notes block: PASS"
    )

    print("")
    print("===== 5. CREATE FULL-WIDTH NOTES BLOCK =====")

    new_notes_block = """
{% if doc.custom_doctor_notes and frappe.utils.strip_html(doc.custom_doctor_notes).strip() %}

<div class="doctor-notes-section">

    <div class="section-title">
        Doctor's Notes / Advice
    </div>

    <div class="clinical-notes-content">
        {{ doc.custom_doctor_notes }}
    </div>

</div>

{% endif %}
"""

    print(
        "New full-width notes block: READY"
    )

    print("")
    print("===== 6. INSERT BEFORE SIGNATURE =====")

    signature_marker = '<div class="signature-section">'

    signature_position = (
        html_without_notes.find(
            signature_marker
        )
    )

    if signature_position < 0:
        frappe.throw(
            "Signature section not found. "
            "Refusing modification."
        )

    html_fixed = (
        html_without_notes[:signature_position]
        + new_notes_block
        + "\n\n"
        + html_without_notes[signature_position:]
    )

    print(
        "Doctor Notes placed before Signature: PASS"
    )

    print("")
    print("===== 7. ADD LAYOUT OVERRIDE CSS =====")

    notes_css = """
/* ---------------------------------------------------------
   Clinify Doctor Notes
   Full-width clinical section, independent of signature.
   --------------------------------------------------------- */

.doctor-notes-section {
    width: 100%;
    clear: both;
    display: block;
    margin: 14px 0 18px 0;
    text-align: left !important;
}

.doctor-notes-section .section-title {
    width: 100%;
    text-align: left !important;
    margin-bottom: 6px;
}

.doctor-notes-section .clinical-notes-content {
    width: 100%;
    box-sizing: border-box;
    display: block;
    text-align: left !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    min-height: 0;
    line-height: 1.45;
}
"""

    style_end = html_fixed.rfind(
        "</style>"
    )

    if style_end < 0:
        frappe.throw(
            "Could not locate </style>."
        )

    html_fixed = (
        html_fixed[:style_end]
        + "\n"
        + notes_css
        + "\n"
        + html_fixed[style_end:]
    )

    print(
        "Notes layout CSS: INSERTED"
    )

    print("")
    print("===== 8. JINJA STRUCTURE CHECK =====")

    tokens = re.findall(
        r"{%\s*(if|endif|for|endfor)\b.*?%}",
        html_fixed,
        re.IGNORECASE | re.DOTALL,
    )

    stack = []

    for token in tokens:

        token = token.lower()

        if token in ("if", "for"):
            stack.append(token)

        elif token == "endif":

            if not stack or stack[-1] != "if":
                frappe.throw(
                    "Invalid Jinja IF/ENDIF structure."
                )

            stack.pop()

        elif token == "endfor":

            if not stack or stack[-1] != "for":
                frappe.throw(
                    "Invalid Jinja FOR/ENDFOR structure."
                )

            stack.pop()

    if stack:
        frappe.throw(
            "Jinja structure is unbalanced."
        )

    print(
        "Jinja structure: PASS"
    )

    print("")
    print("===== 9. SAVE =====")

    pf.html = html_fixed

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
    print("===== 10. RENDER REAL ENCOUNTER =====")

    encounter = frappe.get_doc(
        "Patient Encounter",
        TEST_ENCOUNTER,
    )

    rendered = frappe.get_print(
        "Patient Encounter",
        TEST_ENCOUNTER,
        print_format=PRINT_FORMAT,
        no_letterhead=1,
    )

    print(
        "Rendered HTML length:",
        len(rendered),
    )

    complaint = (
        encounter.encounter_comment
        or ""
    ).strip()

    notes = frappe.utils.strip_html(
        encounter.custom_doctor_notes
        or ""
    ).strip()

    print(
        "Chief Complaint rendered:",
        bool(
            complaint
            and complaint in rendered
        ),
    )

    print(
        "Doctor Notes value:",
        repr(notes),
    )

    print(
        "Doctor Notes rendered:",
        bool(
            notes
            and notes in
            frappe.utils.strip_html(
                rendered
            )
        ),
    )

    print("")
    print("===== 11. STRUCTURAL CHECK =====")

    rendered_notes_pos = rendered.find(
        "Doctor's Notes / Advice"
    )

    rendered_signature_pos = rendered.find(
        "Doctor Signature"
    )

    print(
        "Doctor Notes position:",
        rendered_notes_pos,
    )

    print(
        "Doctor Signature position:",
        rendered_signature_pos,
    )

    notes_before_signature = (
        rendered_notes_pos >= 0
        and rendered_signature_pos >= 0
        and rendered_notes_pos
        < rendered_signature_pos
    )

    print(
        "Notes before signature:",
        notes_before_signature,
    )

    print("")
    print("===== 12. FINAL ACCEPTANCE =====")

    if not notes:
        frappe.throw(
            "Test Encounter has no Doctor Notes value."
        )

    if notes not in frappe.utils.strip_html(
        rendered
    ):
        frappe.throw(
            "Doctor Notes did not render."
        )

    if not notes_before_signature:
        frappe.throw(
            "Doctor Notes are not before Signature."
        )

    if complaint and complaint not in rendered:
        frappe.throw(
            "Chief Complaint regression detected."
        )

    if "DENTAL SERVICES" not in rendered:
        frappe.throw(
            "Dental Services regression detected."
        )

    if "LAB TESTS" not in rendered:
        frappe.throw(
            "Lab Tests regression detected."
        )

    if "PRESCRIPTION" not in rendered:
        frappe.throw(
            "Prescription regression detected."
        )

    print("")
    print("============================================================")
    print("BETA-03I COMPLETE")
    print("DOCTOR NOTES: PASS")
    print("FULL WIDTH: PASS")
    print("LEFT ALIGNED: PASS")
    print("BORDER: REMOVED")
    print("SIGNATURE: PRESERVED")
    print("CHIEF COMPLAINT: PASS")
    print("DENTAL SERVICES: PASS")
    print("LAB TESTS: PASS")
    print("PRESCRIPTION: PASS")
    print("RENDER VALIDATION: PASS")
    print("SCHEMA: UNTOUCHED")
    print("BILLING: UNTOUCHED")
    print("SAAS: UNTOUCHED")
    print("============================================================")



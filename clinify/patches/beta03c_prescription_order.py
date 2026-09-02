import re
import frappe


PRINT_FORMAT = "Clinify Prescription"


def _heading(title):
    return re.compile(
        r'<div\s+class=["\']section-title["\']>\s*'
        + re.escape(title)
        + r'\s*</div>',
        re.IGNORECASE,
    )


def execute():
    pf = frappe.get_doc("Print Format", PRINT_FORMAT)

    if pf.doc_type != "Patient Encounter":
        frappe.throw(
            f"Unexpected DocType: {pf.doc_type}"
        )

    if pf.disabled:
        frappe.throw(
            "Clinify Prescription is disabled."
        )

    html = pf.html or ""

    # Confirm the existing Chief Complaint implementation.
    if "doc.encounter_comment" not in html:
        frappe.throw(
            "Chief Complaint expression is missing. "
            "Refusing automatic modification."
        )

    # Locate the three complete blocks.
    pres = _heading("PRESCRIPTION").search(html)
    dental = _heading("DENTAL SERVICES").search(html)
    lab = _heading("LAB TESTS").search(html)

    if not pres or not dental or not lab:
        frappe.throw(
            "Could not safely locate all three prescription sections."
        )

    # The current format places these three sections consecutively.
    starts = sorted(
        [
            ("PRESCRIPTION", pres.start()),
            ("DENTAL SERVICES", dental.start()),
            ("LAB TESTS", lab.start()),
        ],
        key=lambda x: x[1],
    )

    first_start = starts[0][1]

    # Find the next major section after LAB TESTS.
    major_after = re.search(
        r'{%\s*if\s+doc\.custom_doctor_notes\b'
        r'|<div\s+class=["\']section-title["\']>\s*'
        r"Doctor['’]s Notes / Advice\s*</div>"
        r"|{%.*?custom_follow_up_required.*?%}",
        html[starts[-1][1]:],
        re.IGNORECASE | re.DOTALL,
    )

    if major_after:
        region_end = starts[-1][1] + major_after.start()
    else:
        region_end = len(html)

    # Extract exact existing blocks, preserving all Jinja logic.
    blocks = {}

    for index, (title, start) in enumerate(starts):
        if index + 1 < len(starts):
            end = starts[index + 1][1]
        else:
            end = region_end

        blocks[title] = html[start:end].strip()

    desired_order = [
        "DENTAL SERVICES",
        "LAB TESTS",
        "PRESCRIPTION",
    ]

    replacement = "\n\n\n".join(
        blocks[title]
        for title in desired_order
    )

    new_html = (
        html[:first_start]
        + replacement
        + "\n\n\n"
        + html[region_end:]
    )

    if new_html == html:
        print("ORDER CHANGE: NOT NEEDED")
    else:
        pf.html = new_html
        pf.save(ignore_permissions=True)
        frappe.clear_cache(doctype="Print Format")
        frappe.db.commit()
        print("ORDER CHANGE: APPLIED")

    # Final verification.
    final_html = (
        frappe.db.get_value(
            "Print Format",
            PRINT_FORMAT,
            "html",
        )
        or ""
    )

    positions = {}

    for title in [
        "Chief Complaint",
        "DENTAL SERVICES",
        "LAB TESTS",
        "PRESCRIPTION",
    ]:
        match = _heading(title).search(final_html)

        positions[title] = (
            match.start()
            if match
            else -1
        )

    print("")
    print("===== FINAL VERIFICATION =====")
    print("Chief Complaint:", positions["Chief Complaint"])
    print("Dental Services:", positions["DENTAL SERVICES"])
    print("Lab Tests:", positions["LAB TESTS"])
    print("Prescription:", positions["PRESCRIPTION"])

    print(
        "Chief Complaint field:",
        "doc.encounter_comment" in final_html,
    )

    print(
        "Dental → Lab:",
        positions["DENTAL SERVICES"]
        < positions["LAB TESTS"],
    )

    print(
        "Lab → Prescription:",
        positions["LAB TESTS"]
        < positions["PRESCRIPTION"],
    )

    print("")
    print("BETA-03C: COMPLETE")



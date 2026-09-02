import frappe


PRINT_FORMAT_NAME = "Clinify Prescription"


def execute():

    print_format = frappe.get_doc(
        "Print Format",
        PRINT_FORMAT_NAME
    )

    html = print_format.html or ""

    # ---------------------------------------------------------
    # Compact the Chief Complaint / Vitals layout
    # ---------------------------------------------------------

    replacements = {

        # Give the Vitals block a little more usable width.
        ".complaint-cell {\n        width: 65%;\n        padding-right: 10px;\n    }":
        ".complaint-cell {\n        width: 62%;\n        padding-right: 8px;\n    }",

        ".vitals-cell {\n        width: 35%;\n        padding-left: 10px;\n    }":
        ".vitals-cell {\n        width: 38%;\n        padding-left: 8px;\n    }",

        # Compact Vitals box.
        ".vitals-box {\n        border: 1px solid #888;\n        padding: 7px 9px;\n        border-radius: 4px;\n    }":
        ".vitals-box {\n        border: 1px solid #888;\n        padding: 5px 7px;\n        border-radius: 4px;\n        font-size: 10.5px;\n        line-height: 1.15;\n    }",

        ".vitals-title {\n        font-weight: 700;\n        margin-bottom: 4px;\n        font-size: 12px;\n    }":
        ".vitals-title {\n        font-weight: 700;\n        margin-bottom: 2px;\n        font-size: 10.5px;\n    }",

        ".vitals-row td {\n        padding: 2px 0;\n        vertical-align: top;\n    }":
        ".vitals-row td {\n        padding: 1px 0;\n        vertical-align: middle;\n        line-height: 1.15;\n    }",

        ".vital-label {\n        font-weight: 600;\n        width: 58%;\n    }":
        ".vital-label {\n        font-weight: 600;\n        width: 58%;\n        white-space: nowrap;\n    }",
    }

    for old, new in replacements.items():

        if old not in html:
            frappe.throw(
                "Expected Vitals CSS block was not found. "
                "Print Format was not changed."
            )

        html = html.replace(old, new, 1)

    # ---------------------------------------------------------
    # Remove redundant "Recorded Vitals" text.
    # The section heading "Vitals" already identifies the box.
    # ---------------------------------------------------------

    recorded_vitals = """
                <div class="vitals-title">
                    Recorded Vitals
                </div>
"""

    if recorded_vitals not in html:
        frappe.throw(
            "Expected 'Recorded Vitals' block was not found. "
            "Print Format was not changed."
        )

    html = html.replace(
        recorded_vitals,
        "",
        1,
    )

    # ---------------------------------------------------------
    # Save
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
    print("================================================")
    print("CLINIFY PRESCRIPTION PRINT FORMAT V2.2 UPDATED")
    print("================================================")
    print("Vitals box compacted")
    print("Vitals row spacing reduced")
    print("Recorded Vitals label removed")
    print("Chief Complaint / Vitals proportions adjusted")
    print("Existing Lab Test logic preserved")
    print("Existing Prescription logic preserved")
    print("custom_format =", print_format.custom_format)
    print("================================================")

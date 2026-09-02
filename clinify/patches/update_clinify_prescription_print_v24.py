import re
import frappe


PRINT_FORMAT_NAME = "Clinify Prescription"


NEW_VITALS_CSS = r"""
    .vitals-cell {
        width: 38%;
        padding-left: 8px;
    }

    .vitals-box {
        border: 1px solid #888;
        padding: 4px 6px;
        border-radius: 3px;
        font-size: 9.5px;
        line-height: 1.05;
    }

    .vitals-grid {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }

    .vitals-grid td {
        padding: 2px 3px;
        vertical-align: middle;
        white-space: nowrap;
        line-height: 1.05;
    }

    .vitals-grid .label {
        font-weight: 600;
        width: 16%;
    }

    .vitals-grid .value {
        width: 34%;
        padding-right: 8px;
    }

    .vitals-grid .right-label {
        border-left: 1px solid #ddd;
        padding-left: 7px;
        font-weight: 600;
        width: 16%;
    }

    .vitals-grid .right-value {
        width: 34%;
        text-align: right;
    }
"""


NEW_VITALS_BLOCK = r"""
        <td class="vitals-cell">

            <div class="section-title">
                Vitals
            </div>

            <div class="vitals-box">

                <table class="vitals-grid">

                    <tr>
                        <td class="label">
                            {% if vital.bp_systolic or vital.bp_diastolic %}BP{% endif %}
                        </td>
                        <td class="value">
                            {% if vital.bp_systolic or vital.bp_diastolic %}
                                {{ vital.bp_systolic or "-" }}/{{ vital.bp_diastolic or "-" }}
                            {% endif %}
                        </td>

                        <td class="right-label">
                            {% if vital.pulse %}Pulse{% endif %}
                        </td>
                        <td class="right-value">
                            {% if vital.pulse %}{{ vital.pulse }}{% endif %}
                        </td>
                    </tr>

                    <tr>
                        <td class="label">
                            {% if vital.temperature %}Temp{% endif %}
                        </td>
                        <td class="value">
                            {% if vital.temperature %}{{ vital.temperature }}{% endif %}
                        </td>

                        <td class="right-label">
                            {% if vital.respiratory_rate %}Resp{% endif %}
                        </td>
                        <td class="right-value">
                            {% if vital.respiratory_rate %}{{ vital.respiratory_rate }}{% endif %}
                        </td>
                    </tr>

                    <tr>
                        <td class="label">
                            {% if vital.weight %}Weight{% endif %}
                        </td>
                        <td class="value">
                            {% if vital.weight %}{{ vital.weight }} kg{% endif %}
                        </td>

                        <td class="right-label">
                            {% if vital.bmi %}BMI{% endif %}
                        </td>
                        <td class="right-value">
                            {% if vital.bmi %}{{ vital.bmi }}{% endif %}
                        </td>
                    </tr>

                </table>

            </div>

        </td>
"""


def execute():

    print_format = frappe.get_doc(
        "Print Format",
        PRINT_FORMAT_NAME
    )

    html = print_format.html or ""

    # ---------------------------------------------------------
    # Replace Vitals CSS safely.
    # We stop at the known prescription-table marker.
    # ---------------------------------------------------------

    css_pattern = re.compile(
        r"\n\s*\.vitals-cell\s*\{.*?"
        r"\n\s*\.prescription-table\s*,",
        re.DOTALL,
    )

    css_replacement = (
        "\n"
        + NEW_VITALS_CSS
        + "\n    .prescription-table,\n"
    )

    html, css_count = css_pattern.subn(
        css_replacement,
        html,
        count=1,
    )

    if css_count != 1:
        frappe.throw(
            "Could not locate the existing Vitals CSS block. "
            "No changes were saved."
        )

    # ---------------------------------------------------------
    # Replace the complete Vitals cell.
    #
    # We deliberately include the closing Jinja endif and
    # table-row boundary in the search marker so inner </td>
    # tags cannot terminate the match early.
    # ---------------------------------------------------------

    start_marker = '<td class="vitals-cell">'

    end_marker = """
        {% endif %}

    </tr>

</table>
"""

    start = html.find(start_marker)

    if start == -1:
        frappe.throw(
            "Could not locate the Vitals HTML block. "
            "No changes were saved."
        )

    end = html.find(end_marker, start)

    if end == -1:
        frappe.throw(
            "Could not locate the end of the Vitals HTML block. "
            "No changes were saved."
        )

    replacement_end = end

    html = (
        html[:start]
        + NEW_VITALS_BLOCK
        + html[replacement_end:]
    )

    # ---------------------------------------------------------
    # Validate that the resulting HTML has the expected
    # compact Vitals structure.
    # ---------------------------------------------------------

    if "vitals-grid" not in html:
        frappe.throw(
            "V2.4 validation failed: vitals-grid missing."
        )

    # ---------------------------------------------------------
    # Save.
    # Frappe will perform its own Jinja validation here.
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
    print("CLINIFY PRESCRIPTION PRINT FORMAT V2.4 UPDATED")
    print("================================================")
    print("Vitals: compact 3-row / 2-pair grid")
    print("Vitals height: minimized")
    print("Prescription: preserved")
    print("Lab Tests: preserved")
    print("Clinical Notes: preserved")
    print("custom_format =", print_format.custom_format)
    print("================================================")
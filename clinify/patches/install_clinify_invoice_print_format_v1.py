"""Install the Clinify Invoice Print Format.

Uses the approved Clinify Prescription visual system:
- same A4 page
- same Clinify header
- same clinic/doctor presentation
- patient-facing invoice body

The billing engine and Sales Invoice data are not modified.
"""

import re
import frappe


PRINT_FORMAT_NAME = "Clinify Invoice"


def _get_prescription_html():
    from clinify.patches.install_clinify_prescription_print_format_v6 import (
        PRINT_HTML,
    )
    return PRINT_HTML


def _build_invoice_html():
    prescription_html = _get_prescription_html()

    style_match = re.search(
        r"(<style>.*?</style>)",
        prescription_html,
        flags=re.DOTALL,
    )

    header_match = re.search(
        r'(<div class="clinify-header">.*?)(?={#.*PATIENT INFORMATION)',
        prescription_html,
        flags=re.DOTALL,
    )

    if not style_match:
        frappe.throw(
            "Unable to extract the approved Clinify Prescription CSS."
        )

    if not header_match:
        frappe.throw(
            "Unable to extract the approved Clinify Prescription header."
        )

    style = style_match.group(1)
    header = header_match.group(1)

    invoice_body = r'''    <style>
        .clinify-invoice-meta .invoice-meta-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .clinify-invoice-meta .invoice-meta-icon {
            flex: 0 0 15px;
            width: 15px;
            min-width: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .clinify-invoice-meta .invoice-meta-icon svg {
            width: 14px;
            height: 14px;
            display: block;
        }

        .clinify-invoice-meta .invoice-meta-data {
            min-width: 0;
        }

        .clinify-invoice-meta .invoice-label,
        .clinify-invoice-meta .invoice-value {
            display: block;
        }
    </style>


    {% set clinic = frappe.get_doc("Clinic Configuration", "Clinic Configuration") %}
    {% set patient = frappe.get_doc("Patient", doc.customer)
        if doc.customer else None %}

    {% set practitioner = None %}
    {% if doc.custom_primary_doctor %}
        {% set practitioner = frappe.get_doc(
            "Healthcare Practitioner",
            doc.custom_primary_doctor
        ) %}
    {% endif %}

    {{ header_placeholder }}

    <div class="invoice-title">
        INVOICE
    </div>

    <div class="invoice-meta clinify-invoice-meta">

        <div class="invoice-meta-item">
            <div class="invoice-meta-icon"><svg viewBox="0 0 48 48" aria-hidden="true">
        <circle cx="24" cy="24" r="21"
                fill="none"
                stroke="#173b82"
                stroke-width="3"/>
        <circle cx="24" cy="17" r="7"/>
        <path d="M11 39c1-8 6-12 13-12s12 4 13 12z"/>
    </svg></div>
            <div class="invoice-meta-data">
                <span class="invoice-label">Patient</span>
                <span class="invoice-value">{{ doc.customer_name or "-" }}</span>
            </div>
        </div>

        <div class="invoice-meta-item">
            <div class="invoice-meta-icon"><svg viewBox="0 0 48 48" aria-hidden="true">
        <rect x="9" y="7" width="30" height="34"
              rx="3"
              fill="none"
              stroke="#173b82"
              stroke-width="3"/>
        <circle cx="24" cy="17" r="6"/>
        <path d="M14 32c1-6 5-9 10-9s9 3 10 9z"/>
        <path d="M18 37h12"
              fill="none"
              stroke="#173b82"
              stroke-width="2"/>
    </svg></div>
            <div class="invoice-meta-data">
                <span class="invoice-label">Invoice No.</span>
                <span class="invoice-value">{{ doc.name or "-" }}</span>
            </div>
        </div>

        <div class="invoice-meta-item">
            <div class="invoice-meta-icon"><svg viewBox="0 0 48 48" aria-hidden="true">
        <rect x="9" y="7" width="30" height="34"
              rx="3"
              fill="none"
              stroke="#173b82"
              stroke-width="3"/>
        <circle cx="24" cy="17" r="6"/>
        <path d="M14 32c1-6 5-9 10-9s9 3 10 9z"/>
        <path d="M18 37h12"
              fill="none"
              stroke="#173b82"
              stroke-width="2"/>
    </svg></div>
            <div class="invoice-meta-data">
                <span class="invoice-label">Patient ID</span>
                <span class="invoice-value">{{ patient.uid if patient and patient.uid else "-" }}</span>
            </div>
        </div>

        <div class="invoice-meta-item">
            <div class="invoice-meta-icon"><svg viewBox="0 0 48 48" aria-hidden="true">
        <rect x="7" y="10" width="34" height="31"
              rx="3"
              fill="none"
              stroke="#173b82"
              stroke-width="3"/>
        <path d="M7 19h34"
              fill="none"
              stroke="#173b82"
              stroke-width="3"/>
        <path d="M15 6v8M33 6v8"
              fill="none"
              stroke="#173b82"
              stroke-width="4"/>
        <circle cx="16" cy="26" r="2"/>
        <circle cx="24" cy="26" r="2"/>
        <circle cx="32" cy="26" r="2"/>
        <circle cx="16" cy="33" r="2"/>
        <circle cx="24" cy="33" r="2"/>
        <circle cx="32" cy="33" r="2"/>
    </svg></div>
            <div class="invoice-meta-data">
                <span class="invoice-label">Invoice Date</span>
                <span class="invoice-value">{{ frappe.format_date(doc.posting_date) if doc.posting_date else "-" }}</span>
            </div>
        </div>

        <div class="invoice-meta-item">
            <div class="invoice-meta-icon"><svg viewBox="0 0 48 48" aria-hidden="true">
        <circle cx="24" cy="24" r="21"
                fill="none"
                stroke="#173b82"
                stroke-width="3"/>
        <circle cx="24" cy="17" r="7"/>
        <path d="M11 39c1-8 6-12 13-12s12 4 13 12z"/>
    </svg></div>
            <div class="invoice-meta-data">
                <span class="invoice-label">Doctor</span>
                <span class="invoice-value">
                    {% if practitioner %}
                        Dr. {{ practitioner.practitioner_name or "-" }}
                    {% else %}
                        -
                    {% endif %}
                </span>
            </div>
        </div>

        <div class="invoice-meta-item">
            <div class="invoice-meta-icon"><svg viewBox="0 0 48 48" aria-hidden="true">
        <rect x="9" y="7" width="30" height="34"
              rx="3"
              fill="none"
              stroke="#173b82"
              stroke-width="3"/>
        <circle cx="24" cy="17" r="6"/>
        <path d="M14 32c1-6 5-9 10-9s9 3 10 9z"/>
        <path d="M18 37h12"
              fill="none"
              stroke="#173b82"
              stroke-width="2"/>
    </svg></div>
            <div class="invoice-meta-data">
                <span class="invoice-label">Department</span>
                <span class="invoice-value">
                    {% if practitioner and practitioner.department %}
                        {{ practitioner.department }}
                    {% else %}
                        -
                    {% endif %}
                </span>
            </div>
        </div>

    </div>

    <div class="section-title">
        SERVICES
    </div>

    <table class="invoice-table">
        <thead>
            <tr>
                <th class="invoice-description">
                    Service / Description
                </th>
                <th class="invoice-qty center">
                    Qty
                </th>
                <th class="invoice-rate right">
                    Rate
                </th>
                <th class="invoice-amount right">
                    Amount
                </th>
            </tr>
        </thead>

        <tbody>
            {% for row in doc.items %}
            <tr>
                <td>
                    {{ row.description or row.item_name or row.item_code or "-" }}
                </td>

                <td class="center">
                    {{ row.qty or 0 }}
                </td>

                <td class="right">
                    {{ frappe.format_value(row.rate, {"fieldtype": "Currency"}) }}
                </td>

                <td class="right">
                    {{ frappe.format_value(row.amount, {"fieldtype": "Currency"}) }}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="invoice-summary">

        <div class="summary-row">
            <span>Subtotal</span>
            <strong>
                {{ frappe.format_value(
                    doc.net_total,
                    {"fieldtype": "Currency"}
                ) }}
            </strong>
        </div>

        {% if doc.total_taxes_and_charges %}
        <div class="summary-row">
            <span>Taxes / Charges</span>
            <strong>
                {{ frappe.format_value(
                    doc.total_taxes_and_charges,
                    {"fieldtype": "Currency"}
                ) }}
            </strong>
        </div>
        {% endif %}

        <div class="summary-row summary-total">
            <span>Total Amount</span>
            <strong>
                {{ frappe.format_value(
                    doc.grand_total,
                    {"fieldtype": "Currency"}
                ) }}
            </strong>
        </div>

        <div class="summary-row">
            <span>Paid Amount</span>
            <strong>
                {{ frappe.format_value(
                    doc.grand_total - doc.outstanding_amount,
                    {"fieldtype": "Currency"}
                ) }}
            </strong>
        </div>

        <div class="summary-row summary-balance">
            <span>Balance Due</span>
            <strong>
                {{ frappe.format_value(
                    doc.outstanding_amount,
                    {"fieldtype": "Currency"}
                ) }}
            </strong>
        </div>

    </div>

    <div class="payment-status">
        <strong>Payment Status:</strong>
        {{ doc.status or "Unpaid" }}
    </div>

    <div class="invoice-footer">
        Thank you for choosing Clinify.
    </div>

    <div class="signature-area">
        <div class="signature-line">
            Doctor Signature
        </div>
    </div>

    </div>
'''

    header_with_placeholder = header

    # The prescription header contains its own opening/closing structure.
    # Replace the complete practitioner-dependent header variables by
    # retaining the approved header template exactly.
    invoice_body = invoice_body.replace(
        "{{ header_placeholder }}",
        header_with_placeholder,
    )

    invoice_css = r'''
<style>
.invoice-title {
    margin: 18px 0 12px 0;
    text-align: center;
    color: #173b82;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 1px;
}

.invoice-meta {
    width: 100%;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 0;
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: stretch;
    justify-content: stretch;
}

.invoice-meta-item {
    flex: 1 1 16.666%;
    width: 16.666%;
    min-width: 0;
    box-sizing: border-box;
    vertical-align: middle;
    padding: 6px 8px;
    border-right: 1px solid #cccccc;
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 6px;
}

.invoice-meta-item:last-child {
    border-right: none;
}

.invoice-meta-icon {
    flex: 0 0 24px;
    width: 24px;
    text-align: center;
}

.invoice-meta-data {
    flex: 1 1 auto;
    min-width: 0;
}

.invoice-meta-item:last-child {
    border-right: none;
}

.invoice-label {
    display: block;
    font-size: 8px;
    color: #555555;
    margin-bottom: 3px;
}

.invoice-value {
    display: block;
    font-size: 11px;
    color: #111111;
    font-weight: 400;
    word-break: break-word;
}

.invoice-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 10.5px;
}

.invoice-table th {
    background: #f1f1f1;
    border: 1px solid #b9b9b9;
    padding: 9px 10px;
    text-align: left;
    font-weight: 700;
    color: #333333;
}

.invoice-table td {
    border: 1px solid #b9b9b9;
    padding: 10px;
    min-height: 34px;
    color: #111111;
    vertical-align: middle;
}

.invoice-description {
    width: 54%;
}

.invoice-qty {
    width: 10%;
}

.invoice-rate {
    width: 18%;
}

.invoice-amount {
    width: 18%;
}

.right {
    text-align: right !important;
}

.invoice-summary {
    width: 42%;
    margin-left: auto;
    margin-top: 18px;
    border-top: 1px solid #888888;
}

.summary-row {
    display: table;
    width: 100%;
    padding: 6px 0;
    font-size: 11px;
}

.summary-row span,
.summary-row strong {
    display: table-cell;
}

.summary-row strong {
    text-align: right;
}

.summary-total {
    border-top: 1px solid #888888;
    font-size: 14px;
    font-weight: 700;
    padding-top: 9px;
}

.summary-balance {
    border-top: 1px solid #cccccc;
    font-weight: 700;
}

.payment-status {
    margin-top: 18px;
    padding: 9px 12px;
    border: 1px solid #888888;
    border-radius: 3px;
    font-size: 11px;
}

.invoice-footer {
    margin-top: 28px;
    text-align: center;
    font-size: 10px;
    color: #555555;
}

@media print {
    .invoice-table,
    .invoice-table tr,
    .invoice-table td,
    .invoice-table th {
        page-break-inside: avoid;
    }

    .invoice-meta,
    .invoice-summary,
    .payment-status {
        page-break-inside: avoid;
    }
}
</style>
'''

    # Remove the prescription's body after the header and use the
    # approved page shell/header with the new invoice content.
    return (
        style
        + "\n"
        + invoice_css
        + "\n"
        + '<div class="clinify-page">\n'
        + invoice_body
    )


PRINT_HTML = _build_invoice_html()


def execute():
    import hashlib

    actual_sha256 = hashlib.sha256(
        PRINT_HTML.encode("utf-8")
    ).hexdigest()

    if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
        doc = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
    else:
        doc = frappe.new_doc("Print Format")
        doc.name = PRINT_FORMAT_NAME

    doc.doc_type = "Sales Invoice"
    doc.print_format_type = "Jinja"
    doc.custom_format = 1
    doc.disabled = 0
    doc.standard = "No"
    doc.module = "Clinify"
    doc.html = PRINT_HTML

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": PRINT_FORMAT_NAME,
        "sha256": actual_sha256,
        "bytes": len(PRINT_HTML.encode("utf-8")),
    }

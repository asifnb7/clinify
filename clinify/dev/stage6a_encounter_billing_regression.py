import frappe
from frappe.utils import flt


def run():
    print("")
    print("=" * 80)
    print("CLINIFY STAGE 6-A — ENCOUNTER BILLING REGRESSION")
    print("=" * 80)

    source_encounter_name = "HLC-ENC-2026-00072"
    source_appointment_name = "HLC-APP-2026-00133"
    protected_invoice = "ACC-SINV-2026-00084"

    # Safety: prove the historical UAT invoice exists before proceeding.
    if not frappe.db.exists("Sales Invoice", protected_invoice):
        frappe.throw(
            f"Protected historical invoice {protected_invoice} was not found."
        )

    source_encounter = frappe.get_doc(
        "Patient Encounter",
        source_encounter_name,
    )

    source_appointment = frappe.get_doc(
        "Patient Appointment",
        source_appointment_name,
    )

    if source_appointment.ref_sales_invoice != protected_invoice:
        frappe.throw(
            "Protected UAT appointment invoice reference changed unexpectedly."
        )

    print("Protected invoice:", protected_invoice)
    print("Protected invoice state preserved: PASS")

    # Work entirely inside a savepoint.
    frappe.db.savepoint("stage6a")

    try:
        # ---------------------------------------------------------
        # Clone appointment
        # ---------------------------------------------------------
        appointment = frappe.copy_doc(source_appointment)
        appointment.name = None
        appointment.ref_sales_invoice = None
        appointment.insert(ignore_permissions=True)

        print("Temporary appointment:", appointment.name)

        # ---------------------------------------------------------
        # Clone encounter
        # ---------------------------------------------------------
        encounter = frappe.copy_doc(source_encounter)
        encounter.name = None
        encounter.appointment = appointment.name
        encounter.insert(ignore_permissions=True)

        print("Temporary encounter:", encounter.name)

        # ---------------------------------------------------------
        # Confirm dental rows
        # ---------------------------------------------------------
        rows = getattr(
            encounter,
            "custom_dental_services",
            None,
        ) or []

        if len(rows) != 2:
            frappe.throw(
                f"Expected 2 dental rows, found {len(rows)}."
            )

        print("Dental service rows: 2 — PASS")

        clear_aligners_row = next(
            (
                row
                for row in rows
                if row.dental_service == "DENT-CLEAR-ALIGNERS"
            ),
            None,
        )

        if clear_aligners_row is None:
            frappe.throw(
                "Clear Aligners dental service row was not found."
            )

        clear_aligners_row.selected_price_option = "70ma04rnd1"

        # ---------------------------------------------------------
        # Execute actual Encounter billing engine
        # ---------------------------------------------------------
        from clinify.dental_billing import (
            create_invoice_from_encounter_dental,
        )

        invoice_name = create_invoice_from_encounter_dental(
            encounter
        )

        if not invoice_name:
            frappe.throw(
                "Encounter billing returned no invoice."
            )

        invoice = frappe.get_doc(
            "Sales Invoice",
            invoice_name,
        )

        print("Temporary invoice:", invoice_name)

        # ---------------------------------------------------------
        # Expected lines
        # ---------------------------------------------------------
        expected_rates = {
            "CONSULTATION": 500.0,
            "DENT-BLEACHING-SINGLE": 1000.0,
            "DENT-CLEAR-ALIGNERS": 80000.0,
        }

        if len(invoice.items) != 3:
            frappe.throw(
                f"Expected exactly 3 invoice lines, found {len(invoice.items)}."
            )

        for item_code, expected_rate in expected_rates.items():
            matches = [
                item
                for item in invoice.items
                if item.item_code == item_code
            ]

            if len(matches) != 1:
                frappe.throw(
                    f"Expected one line for {item_code}; found {len(matches)}."
                )

            actual_rate = flt(matches[0].rate)

            print(
                f"{item_code}: expected ₹{expected_rate:,.2f}, "
                f"actual ₹{actual_rate:,.2f}"
            )

            if actual_rate != expected_rate:
                frappe.throw(
                    f"Incorrect rate for {item_code}: "
                    f"expected {expected_rate}, got {actual_rate}"
                )

        expected_total = 81500.0

        if flt(invoice.grand_total) != expected_total:
            frappe.throw(
                f"Expected total ₹{expected_total:,.2f}; "
                f"got ₹{flt(invoice.grand_total):,.2f}"
            )

        print("Consultation ₹500 — PASS")
        print("Bleaching ₹1,000 — PASS")
        print("Clear Aligners ₹80,000 — PASS")
        print("Grand total ₹81,500 — PASS")

        # ---------------------------------------------------------
        # Appointment linkage
        # ---------------------------------------------------------
        linked_invoice = frappe.db.get_value(
            "Patient Appointment",
            appointment.name,
            "ref_sales_invoice",
        )

        if linked_invoice != invoice_name:
            frappe.throw(
                "Appointment was not linked to the generated invoice."
            )

        print("Appointment → Invoice linkage — PASS")

        # ---------------------------------------------------------
        # Idempotency inside the actual engine
        # ---------------------------------------------------------
        second_result = create_invoice_from_encounter_dental(
            encounter
        )

        if second_result != invoice_name:
            frappe.throw(
                f"Idempotency failed: {invoice_name} != {second_result}"
            )

        print("Repeated billing → same invoice — PASS")

        # ---------------------------------------------------------
        # Verify protected historical invoice untouched
        # ---------------------------------------------------------
        protected = frappe.db.get_value(
            "Sales Invoice",
            protected_invoice,
            ["docstatus", "status", "grand_total"],
            as_dict=True,
        )

        if (
            protected.docstatus != 1
            or protected.status != "Paid"
            or flt(protected.grand_total) != 500
        ):
            frappe.throw(
                "Protected historical invoice changed unexpectedly."
            )

        print("Protected historical invoice unchanged — PASS")

        print("")
        print("=" * 80)
        print("STAGE 6-A — PASS")
        print("=" * 80)

    finally:
        # Remove ALL temporary test records created by this run.
        frappe.db.rollback()
        print("")
        print("Temporary regression transaction rolled back.")
        print("No temporary records retained.")


if __name__ == "__main__":
    run()

from types import SimpleNamespace
from unittest.mock import Mock, patch

import clinify.dental_billing as dental_billing


def _encounter(appointment=None):
    return SimpleNamespace(
        doctype="Patient Encounter",
        patient="PATIENT-TEST",
        appointment=appointment,
        company="Test Company",
        practitioner="PRACTITIONER-TEST",
        custom_dental_services=[],
    )


def test_existing_invoice_is_returned_after_appointment_lock():
    appointment = SimpleNamespace(
        name="APPOINTMENT-TEST",
        ref_sales_invoice="ACC-SINV-TEST",
    )

    frappe_double = _frappe_double(
        sql_return_value=[{"name": appointment.name}],
        exists_return_value=True,
        get_doc_return_value=appointment,
    )

    def assert_lock_precedes_invoice_check(*args, **kwargs):
        assert frappe_double.db.sql.call_count == 1
        return True

    frappe_double.db.exists.side_effect = assert_lock_precedes_invoice_check

    with patch.object(dental_billing, "frappe", frappe_double):
        result = dental_billing.create_invoice_from_encounter_dental(
            _encounter(appointment.name)
        )

    assert result == appointment.ref_sales_invoice
    frappe_double.db.sql.assert_called_once()
    assert frappe_double.db.sql.call_args.args[0].find("FOR UPDATE") >= 0
    frappe_double.db.exists.assert_called_once_with(
        "Sales Invoice",
        appointment.ref_sales_invoice,
    )
    frappe_double.new_doc.assert_not_called()
    frappe_double.db.commit.assert_not_called()


def test_missing_invoice_reference_continues_to_invoice_creation():
    appointment = SimpleNamespace(
        name="APPOINTMENT-TEST",
        ref_sales_invoice=None,
    )
    invoice = Mock(items=[{"item_code": "CONSULTATION"}], name="SINV-TEST")

    frappe_double = _frappe_double(
        sql_return_value=[{"name": appointment.name}],
        get_doc_return_value=appointment,
        get_value_return_value="CUSTOMER-TEST",
        new_doc_return_value=invoice,
    )

    with patch.object(dental_billing, "frappe", frappe_double), patch.object(
        dental_billing,
        "today",
        return_value="2026-09-03",
    ), patch(
        "clinify.billing._append_consultation_item",
    ) as consultation, patch.object(
        frappe_double.db,
        "commit",
    ) as commit:
        result = dental_billing.create_invoice_from_encounter_dental(
            _encounter(appointment.name)
        )

    assert result == invoice.name
    invoice.insert.assert_called_once_with(ignore_permissions=True)
    consultation.assert_called_once()
    commit.assert_called_once_with()


def test_appointmentless_encounter_remains_supported():
    invoice = Mock(items=[{"item_code": "CONSULTATION"}], name="SINV-TEST")

    frappe_double = _frappe_double(
        get_value_return_value="CUSTOMER-TEST",
        new_doc_return_value=invoice,
    )

    with patch.object(dental_billing, "frappe", frappe_double), patch.object(
        dental_billing,
        "today",
        return_value="2026-09-03",
    ), patch(
        "clinify.billing._append_consultation_item",
    ), patch.object(
        frappe_double.db,
        "commit",
    ) as commit:
        result = dental_billing.create_invoice_from_encounter_dental(_encounter())

    assert result == invoice.name
    invoice.insert.assert_called_once_with(ignore_permissions=True)
    commit.assert_called_once_with()


def _frappe_double(
    sql_return_value=None,
    exists_return_value=False,
    get_doc_return_value=None,
    get_value_return_value=None,
    new_doc_return_value=None,
):
    database = Mock()
    database.sql.return_value = sql_return_value or []
    database.exists.return_value = exists_return_value
    database.get_value.return_value = get_value_return_value
    database.commit = Mock()
    return SimpleNamespace(
        db=database,
        get_doc=Mock(return_value=get_doc_return_value),
        new_doc=Mock(return_value=new_doc_return_value),
        throw=Mock(side_effect=RuntimeError),
    )


def run_test():
    test_existing_invoice_is_returned_after_appointment_lock()
    test_missing_invoice_reference_continues_to_invoice_creation()
    test_appointmentless_encounter_remains_supported()
    print("Invoice idempotency tests passed.")
    print("No production records were created or modified.")


if __name__ == "__main__":
    run_test()
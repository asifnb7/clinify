from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

import clinify.clinify.doctype.clinify_tenant.clinify_tenant as tenant_id


def _frappe_double(sequence_result=None, lock_result=1):
    database = Mock()
    database.sql.side_effect = [
        [(lock_result,)],
        sequence_result if sequence_result is not None else [(0,)],
        [(1,)],
    ]
    database.exists.return_value = False

    def throw(message):
        raise RuntimeError(message)

    return SimpleNamespace(
        db=database,
        throw=Mock(side_effect=throw),
    )


def _next_sequence(existing_sequence):
    sequence_result = [(existing_sequence,)] if existing_sequence is not None else [(0,)]
    frappe_double = _frappe_double(sequence_result)

    with patch.object(tenant_id, "frappe", frappe_double):
        sequence = tenant_id._next_monthly_sequence(date(2026, 9, 3))

    return sequence, frappe_double


def test_no_existing_monthly_ids_returns_one():
    sequence, _ = _next_sequence(None)
    assert sequence == 1


def test_existing_sequences_01_and_02_returns_three():
    sequence, _ = _next_sequence(2)
    assert sequence == 3


def test_existing_sequences_01_02_and_04_returns_five():
    sequence, _ = _next_sequence(4)
    assert sequence == 5


def test_existing_sequence_98_returns_99():
    sequence, _ = _next_sequence(98)
    assert sequence == 99


def test_sequence_query_uses_correct_id_predicates():
    sequence, frappe_double = _next_sequence(4)

    assert sequence == 5

    sql_calls = frappe_double.db.sql.call_args_list
    assert "GET_LOCK(%s, 15)" in sql_calls[0].args[0]

    sequence_query = sql_calls[1].args[0]
    assert "SUBSTRING(tenant_id, 2, 2)" in sequence_query
    assert "MAX(CAST(SUBSTRING(tenant_id, 2, 2) AS UNSIGNED))" in sequence_query
    assert "SUBSTRING(tenant_id, 7, 2)" in sequence_query
    assert "SUBSTRING(tenant_id, 2, 2) = LPAD(%s, 2, '0')" not in sequence_query
    assert "RIGHT(tenant_id, 2)" in sequence_query
    assert sql_calls[1].args[1] == (9, 26)
    assert sql_calls[-1].args[0] == "SELECT RELEASE_LOCK(%s)"


def test_existing_sequence_99_returns_100_for_existing_guard():
    frappe_double = _frappe_double([(99,)])

    with patch.object(tenant_id, "frappe", frappe_double):
        try:
            tenant_id._next_monthly_sequence(date(2026, 9, 3))
        except RuntimeError as error:
            assert "reached 99" in str(error)
        else:
            raise AssertionError("Expected the monthly sequence guard to reject 100")


def test_lock_acquisition_failure_raises_existing_error():
    frappe_double = _frappe_double(lock_result=0)

    with patch.object(tenant_id, "frappe", frappe_double):
        try:
            tenant_id._next_monthly_sequence(date(2026, 9, 3))
        except RuntimeError as error:
            assert "Could not acquire the Tenant ID generation lock" in str(error)
        else:
            raise AssertionError("Expected lock acquisition failure")


def test_release_lock_runs_when_sequence_query_raises():
    database = Mock()
    database.sql.side_effect = [
        [(1,)],
        RuntimeError("sequence query failed"),
        [(1,)],
    ]
    frappe_double = SimpleNamespace(
        db=database,
        throw=Mock(side_effect=lambda message: (_ for _ in ()).throw(RuntimeError(message))),
    )

    with patch.object(tenant_id, "frappe", frappe_double):
        try:
            tenant_id._next_monthly_sequence(date(2026, 9, 3))
        except RuntimeError as error:
            assert str(error) == "sequence query failed"
        else:
            raise AssertionError("Expected the sequence query to fail")

    assert database.sql.call_count == 3
    assert database.sql.call_args_list[-1].args[0] == "SELECT RELEASE_LOCK(%s)"


def test_abbreviation_behavior_remains_unchanged():
    assert tenant_id._clinic_abbreviation("Riyaz Dental Clinic") == "RDC"
    assert tenant_id._clinic_abbreviation("Riyaz Clinic") == "RCX"
    assert tenant_id._clinic_abbreviation("Riyaz") == "RXX"


def run_test():
    test_no_existing_monthly_ids_returns_one()
    test_existing_sequences_01_and_02_returns_three()
    test_existing_sequences_01_02_and_04_returns_five()
    test_existing_sequence_98_returns_99()
    test_sequence_query_uses_correct_id_predicates()
    test_existing_sequence_99_returns_100_for_existing_guard()
    test_lock_acquisition_failure_raises_existing_error()
    test_release_lock_runs_when_sequence_query_raises()
    test_abbreviation_behavior_remains_unchanged()
    print("Tenant ID generation tests passed.")
    print("No production records were created or modified.")


if __name__ == "__main__":
    run_test()
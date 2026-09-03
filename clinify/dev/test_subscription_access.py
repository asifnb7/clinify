from datetime import date
from types import SimpleNamespace

import clinify.subscription as subscription


def run_test():
    original_get_current_subscription = subscription.get_current_subscription
    original_get_current_clinic = subscription.get_current_clinic
    original_nowdate = subscription.nowdate

    today = date.today().isoformat()
    clinic = SimpleNamespace(clinic_status="Active")

    cases = [
        ("future end date", "2099-12-31", "Active", 1, True),
        ("end date is today", today, "Active", 1, True),
        ("past end date", "2000-01-01", "Active", 1, False),
        ("missing end date", None, "Active", 1, True),
        ("inactive record", "2099-12-31", "Active", 0, False),
        ("expired status", "2099-12-31", "Expired", 1, False),
        ("cancelled status", "2099-12-31", "Cancelled", 1, False),
    ]

    try:
        subscription.get_current_clinic = lambda: clinic
        subscription.nowdate = lambda: today

        for title, end_date, status, is_active, expected in cases:
            current_subscription = SimpleNamespace(
                end_date=end_date,
                subscription_status=status,
                is_active=is_active,
            )
            subscription.get_current_subscription = lambda: current_subscription

            actual = subscription.is_subscription_active()
            assert actual is expected, f"{title}: expected {expected}, got {actual}"

            access = subscription.can_access_clinify()
            assert access is expected, f"{title}: expected access {expected}, got {access}"
    finally:
        subscription.get_current_subscription = original_get_current_subscription
        subscription.get_current_clinic = original_get_current_clinic
        subscription.nowdate = original_nowdate

    print("Subscription access tests passed.")
    print("No database records were read or modified.")


if __name__ == "__main__":
    run_test()
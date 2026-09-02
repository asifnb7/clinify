import frappe
import clinify.subscription as subscription


def show_result(title, clinic_status, subscription_status, is_active):
    print("")
    print("============================================================")
    print(title)
    print("============================================================")

    clinic = frappe.get_single("Clinic Configuration")

    current_subscription = (
        subscription.get_current_subscription()
    )

    if not current_subscription:
        print("ERROR: No active subscription found.")
        return

    # Store original in-memory values.
    original_clinic_status = clinic.clinic_status
    original_subscription_status = (
        current_subscription.subscription_status
    )
    original_is_active = (
        current_subscription.is_active
    )

    # Modify Python objects only.
    # Nothing is saved to the database.
    clinic.clinic_status = clinic_status

    current_subscription.subscription_status = (
        subscription_status
    )

    current_subscription.is_active = is_active

    # Preserve original lookup functions.
    original_get_current_clinic = (
        subscription.get_current_clinic
    )

    original_get_current_subscription = (
        subscription.get_current_subscription
    )

    # Force the service to use our in-memory objects.
    subscription.get_current_clinic = (
        lambda: clinic
    )

    subscription.get_current_subscription = (
        lambda: current_subscription
    )

    try:
        print("Clinic Status:", clinic.clinic_status)
        print(
            "Subscription Status:",
            current_subscription.subscription_status
        )
        print(
            "Subscription Record Active:",
            bool(current_subscription.is_active)
        )

        print(
            "Subscription Active:",
            subscription.is_subscription_active()
        )

        print(
            "Can Access Clinify:",
            subscription.can_access_clinify()
        )

        print("")
        print("Access Status:")

        for key, value in (
            subscription.get_access_status().items()
        ):
            print(f"{key}: {value}")

    finally:
        # Restore service functions.
        subscription.get_current_clinic = (
            original_get_current_clinic
        )

        subscription.get_current_subscription = (
            original_get_current_subscription
        )

        # Restore in-memory object values.
        clinic.clinic_status = (
            original_clinic_status
        )

        current_subscription.subscription_status = (
            original_subscription_status
        )

        current_subscription.is_active = (
            original_is_active
        )


def run_test():
    show_result(
        "TEST 1 - ACTIVE CLINIC + TRIAL",
        "Active",
        "Trial",
        1,
    )

    show_result(
        "TEST 2 - ACTIVE CLINIC + ACTIVE",
        "Active",
        "Active",
        1,
    )

    show_result(
        "TEST 3 - ACTIVE CLINIC + EXPIRED",
        "Active",
        "Expired",
        1,
    )

    show_result(
        "TEST 4 - ACTIVE CLINIC + SUSPENDED",
        "Active",
        "Suspended",
        1,
    )

    show_result(
        "TEST 5 - INACTIVE CLINIC + ACTIVE",
        "Inactive",
        "Active",
        1,
    )

    show_result(
        "TEST 6 - ACTIVE CLINIC + INACTIVE RECORD",
        "Active",
        "Active",
        0,
    )

    print("")
    print("============================================================")
    print("TEST COMPLETE")
    print("Database was NOT modified.")
    print("============================================================")

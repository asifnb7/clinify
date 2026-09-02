import frappe
import clinify.subscription as subscription


def run_test():
    clinic = frappe.get_single("Clinic Configuration")

    original_clinic_status = clinic.clinic_status
    original_subscription_status = clinic.subscription_status
    original_get_current_clinic = subscription.get_current_clinic

    def show_result(title, clinic_status, subscription_status):
        print("")
        print("=" * 60)
        print(title)
        print("=" * 60)

        # Change Python object only. Do not save.
        clinic.clinic_status = clinic_status
        clinic.subscription_status = subscription_status

        # Make subscription service use our in-memory document.
        subscription.get_current_clinic = lambda: clinic

        print("Clinic Status:", clinic.clinic_status)
        print("Subscription Status:", clinic.subscription_status)
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

        for key, value in subscription.get_access_status().items():
            print(f"{key}: {value}")

    try:
        show_result(
            "TEST 1 - ACTIVE + TRIAL",
            "Active",
            "Trial",
        )

        show_result(
            "TEST 2 - INACTIVE + TRIAL",
            "Inactive",
            "Trial",
        )

        show_result(
            "TEST 3 - ACTIVE + EXPIRED",
            "Active",
            "Expired",
        )

        show_result(
            "TEST 4 - INACTIVE + EXPIRED",
            "Inactive",
            "Expired",
        )

    finally:
        # Restore original service function.
        subscription.get_current_clinic = original_get_current_clinic

        # Restore in-memory values.
        clinic.clinic_status = original_clinic_status
        clinic.subscription_status = original_subscription_status

    print("")
    print("=" * 60)
    print("TEST COMPLETE")
    print("Database was NOT modified.")
    print("=" * 60)

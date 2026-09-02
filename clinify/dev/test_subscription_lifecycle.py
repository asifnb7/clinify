import frappe
import clinify.subscription as subscription


def print_header(title):
    print("")
    print("============================================================")
    print(title)
    print("============================================================")


def print_result():
    summary = subscription.get_subscription_summary()
    access = subscription.get_access_status()

    print("Subscription Exists:", summary["subscription_exists"])
    print("Plan:", summary["plan"])
    print("Subscription Status:", summary["subscription_status"])
    print("Record Active:", summary["is_active"])
    print("Access Allowed:", access["access_allowed"])


def run_test():
    """
    Test subscription lifecycle operations.

    The original subscription values are restored
    before the test completes.
    """

    original_subscription = subscription.get_current_subscription()

    if not original_subscription:
        frappe.throw(
            "No current Clinify Subscription exists "
            "for lifecycle testing."
        )

    original_name = original_subscription.name

    original_values = {
        "plan": original_subscription.plan,
        "subscription_status": (
            original_subscription.subscription_status
        ),
        "start_date": original_subscription.start_date,
        "end_date": original_subscription.end_date,
        "billing_cycle": original_subscription.billing_cycle,
        "price": original_subscription.price,
        "currency": original_subscription.currency,
        "is_active": original_subscription.is_active,
    }

    try:
        print_header(
            "ORIGINAL SUBSCRIPTION STATE"
        )
        print("Subscription:", original_name)
        print_result()

        print_header(
            "TEST 1 - ACTIVATE SUBSCRIPTION"
        )

        result = subscription.activate_subscription()

        print("Result Status:", result["subscription_status"])
        print_result()

        print_header(
            "TEST 2 - EXPIRE SUBSCRIPTION"
        )

        result = subscription.expire_subscription()

        print("Result Status:", result["subscription_status"])
        print_result()

        print_header(
            "TEST 3 - SUSPEND SUBSCRIPTION"
        )

        result = subscription.suspend_subscription()

        print("Result Status:", result["subscription_status"])
        print_result()

        print_header(
            "TEST 4 - REACTIVATE SUBSCRIPTION"
        )

        result = subscription.activate_subscription()

        print("Result Status:", result["subscription_status"])
        print_result()

        print_header(
            "TEST 5 - CHANGE TO STARTER MONTHLY"
        )

        result = subscription.change_subscription_plan(
            "STARTER-MONTHLY"
        )

        print("New Plan:", result["plan"])
        print("Plan Name:", result["plan_name"])
        print_result()

        print_header(
            "TEST 6 - CANCEL SUBSCRIPTION"
        )

        result = subscription.cancel_subscription()

        print(
            "Result Status:",
            result["subscription_status"]
        )

        print(
            "Record Active:",
            result["is_active"]
        )

        print(
            "Can Access Clinify:",
            subscription.can_access_clinify()
        )

    finally:
        print_header(
            "RESTORING ORIGINAL SUBSCRIPTION"
        )

        restored_subscription = frappe.get_doc(
            "Clinify Subscription",
            original_name,
        )

        for fieldname, value in original_values.items():
            setattr(
                restored_subscription,
                fieldname,
                value,
            )

        restored_subscription.save(
            ignore_permissions=True
        )

        frappe.db.commit()

        print("Subscription restored:", original_name)

        print_header(
            "FINAL RESTORED STATE"
        )

        print_result()

        print("")
        print("============================================================")
        print("SUBSCRIPTION LIFECYCLE TEST COMPLETE")
        print("Original database state was restored.")
        print("============================================================")

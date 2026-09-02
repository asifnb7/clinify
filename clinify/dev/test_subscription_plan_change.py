import frappe


def print_header(title):
    print("")
    print("============================================================")
    print(title)
    print("============================================================")


def run_test():
    subscription = frappe.get_doc(
        "Clinify Subscription",
        frappe.db.get_value(
            "Clinify Subscription",
            {
                "clinic": "Clinic Configuration",
                "is_active": 1,
            },
            "name",
        ),
    )

    original_plan = subscription.plan
    original_billing_cycle = subscription.billing_cycle
    original_price = subscription.price
    original_currency = subscription.currency
    original_status = subscription.subscription_status
    original_is_active = subscription.is_active

    print_header("SUBSCRIPTION PLAN CHANGE TEST")

    print("Subscription:", subscription.name)
    print("Original Plan:", original_plan)
    print("Original Billing Cycle:", original_billing_cycle)
    print("Original Price:", original_price)
    print("Original Currency:", original_currency)

    try:
        print_header("CHANGING PLAN TO STARTER MONTHLY")

        new_plan = frappe.get_doc(
            "Clinify Plan",
            "STARTER-MONTHLY",
        )

        subscription.plan = new_plan.name
        subscription.subscription_status = "Active"
        subscription.is_active = 1

        subscription.save(
            ignore_permissions=True
        )

        frappe.db.commit()

        print("New Plan:", subscription.plan)
        print(
            "Billing Cycle:",
            subscription.billing_cycle
        )
        print("Price:", subscription.price)
        print("Currency:", subscription.currency)

        billing_cycle_matches = (
            subscription.billing_cycle
            == new_plan.billing_cycle
        )

        price_matches = (
            subscription.price
            == new_plan.price
        )

        currency_matches = (
            subscription.currency
            == new_plan.currency
        )

        print("")
        print(
            "Billing Cycle Match:",
            billing_cycle_matches
        )
        print(
            "Price Match:",
            price_matches
        )
        print(
            "Currency Match:",
            currency_matches
        )

        if (
            billing_cycle_matches
            and price_matches
            and currency_matches
        ):
            print("")
            print(
                "PASSED: Plan change refreshed "
                "commercial snapshot."
            )
        else:
            print("")
            print(
                "FAILED: Plan change did not refresh "
                "commercial snapshot."
            )

    finally:
        print_header("RESTORING ORIGINAL SUBSCRIPTION")

        subscription.reload()

        subscription.plan = original_plan
        subscription.billing_cycle = original_billing_cycle
        subscription.price = original_price
        subscription.currency = original_currency
        subscription.subscription_status = original_status
        subscription.is_active = original_is_active

        subscription.save(
            ignore_permissions=True
        )

        frappe.db.commit()

        print("Plan restored:", subscription.plan)
        print(
            "Billing Cycle restored:",
            subscription.billing_cycle
        )
        print(
            "Price restored:",
            subscription.price
        )
        print(
            "Currency restored:",
            subscription.currency
        )

        print("")
        print("============================================================")
        print("PLAN CHANGE TEST COMPLETE")
        print("Original subscription state was restored.")
        print("============================================================")

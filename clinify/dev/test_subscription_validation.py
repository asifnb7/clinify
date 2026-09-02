import frappe
from frappe.utils import add_days, nowdate


def print_header(title):
    print("")
    print("============================================================")
    print(title)
    print("============================================================")


def run_test():
    clinic = frappe.get_single("Clinic Configuration")

    active_subscription = frappe.db.get_value(
        "Clinify Subscription",
        {
            "clinic": clinic.name,
            "is_active": 1,
        },
        "name",
    )

    print_header("CLINIFY SUBSCRIPTION VALIDATION TEST")

    print("Clinic:", clinic.name)
    print("Existing Active Subscription:", active_subscription)

    created_documents = []

    try:
        # -----------------------------------------------------
        # TEST 1
        # Existing active subscription must block another one.
        # -----------------------------------------------------

        print_header(
            "TEST 1 - PREVENT MULTIPLE ACTIVE SUBSCRIPTIONS"
        )

        try:
            doc = frappe.get_doc({
                "doctype": "Clinify Subscription",
                "clinic": clinic.name,
                "plan": "TRIAL",
                "subscription_status": "Trial",
                "start_date": nowdate(),
                "is_active": 1,
            })

            doc.insert(
                ignore_permissions=True
            )

            created_documents.append(doc.name)

            print(
                "FAILED: A second active subscription "
                "was created."
            )

        except frappe.ValidationError as e:
            print("PASSED:", str(e))

        # -----------------------------------------------------
        # TEST 2
        # Inactive subscription should be allowed.
        # -----------------------------------------------------

        print_header(
            "TEST 2 - ALLOW INACTIVE SUBSCRIPTION"
        )

        doc = frappe.get_doc({
            "doctype": "Clinify Subscription",
            "clinic": clinic.name,
            "plan": "TRIAL",
            "subscription_status": "Cancelled",
            "start_date": nowdate(),
            "is_active": 0,
        })

        doc.insert(
            ignore_permissions=True
        )

        created_documents.append(doc.name)

        print("PASSED")
        print("Created inactive subscription:", doc.name)

        print("Billing Cycle:", doc.billing_cycle)
        print("Price:", doc.price)
        print("Currency:", doc.currency)

        # -----------------------------------------------------
        # TEST 3
        # End date before start date must fail.
        # -----------------------------------------------------

        print_header(
            "TEST 3 - REJECT INVALID DATE RANGE"
        )

        try:
            doc = frappe.get_doc({
                "doctype": "Clinify Subscription",
                "clinic": clinic.name,
                "plan": "TRIAL",
                "subscription_status": "Cancelled",
                "start_date": nowdate(),
                "end_date": add_days(nowdate(), -1),
                "is_active": 0,
            })

            doc.insert(
                ignore_permissions=True
            )

            created_documents.append(doc.name)

            print(
                "FAILED: Invalid date range was accepted."
            )

        except frappe.ValidationError as e:
            print("PASSED:", str(e))

        # -----------------------------------------------------
        # TEST 4
        # New subscription must copy plan values.
        # -----------------------------------------------------

        print_header(
            "TEST 4 - PLAN SNAPSHOT VALUES"
        )

        plan = frappe.get_doc(
            "Clinify Plan",
            "STARTER-MONTHLY",
        )

        doc = frappe.get_doc({
            "doctype": "Clinify Subscription",
            "clinic": clinic.name,
            "plan": plan.name,
            "subscription_status": "Cancelled",
            "start_date": nowdate(),
            "is_active": 0,
        })

        doc.insert(
            ignore_permissions=True
        )

        created_documents.append(doc.name)

        billing_cycle_matches = (
            doc.billing_cycle == plan.billing_cycle
        )

        price_matches = (
            doc.price == plan.price
        )

        currency_matches = (
            doc.currency == plan.currency
        )

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
            print("PASSED: Plan snapshot copied correctly.")
        else:
            print("FAILED: Plan snapshot mismatch.")

    finally:
        print_header(
            "CLEANUP TEMPORARY TEST RECORDS"
        )

        for name in created_documents:
            if frappe.db.exists(
                "Clinify Subscription",
                name,
            ):
                frappe.delete_doc(
                    "Clinify Subscription",
                    name,
                    force=True,
                    ignore_permissions=True,
                )

                print("Deleted:", name)

        frappe.db.commit()

        print("")
        print("============================================================")
        print("VALIDATION TEST COMPLETE")
        print("Existing production/demo subscription was not modified.")
        print("============================================================")

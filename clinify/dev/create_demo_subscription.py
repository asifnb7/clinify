import frappe


def run():
    clinic = frappe.get_single(
        "Clinic Configuration"
    )

    existing_subscription = frappe.db.exists(
        "Clinify Subscription",
        {
            "clinic": clinic.name,
            "is_active": 1,
        }
    )

    if existing_subscription:
        print(
            "Active subscription already exists:",
            existing_subscription
        )
        return

    plan = frappe.db.get_value(
        "Clinify Plan",
        {
            "plan_code": "TRIAL",
            "is_active": 1,
        },
        [
            "name",
            "billing_cycle",
            "price",
            "currency",
        ],
        as_dict=True,
    )

    if not plan:
        frappe.throw(
            "Active TRIAL plan was not found."
        )

    subscription = frappe.get_doc({
        "doctype": "Clinify Subscription",
        "clinic": clinic.name,
        "plan": plan.name,
        "subscription_status": "Trial",
        "start_date": clinic.activation_date,
        "billing_cycle": plan.billing_cycle,
        "price": plan.price,
        "currency": plan.currency,
        "is_active": 1,
    })

    subscription.insert(
        ignore_permissions=True
    )

    frappe.db.commit()

    print("")
    print("============================================================")
    print("CLINIFY DEMO SUBSCRIPTION CREATED")
    print("============================================================")
    print("Subscription:", subscription.name)
    print("Clinic:", subscription.clinic)
    print("Plan:", subscription.plan)
    print("Status:", subscription.subscription_status)
    print("Start Date:", subscription.start_date)
    print("Billing Cycle:", subscription.billing_cycle)
    print("Price:", subscription.price)
    print("Currency:", subscription.currency)
    print("Is Active:", subscription.is_active)

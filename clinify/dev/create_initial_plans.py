import frappe


INITIAL_PLANS = [
    {
        "plan_name": "Trial",
        "plan_code": "TRIAL",
        "description": "Clinify trial plan.",
        "plan_type": "Trial",
        "billing_cycle": "Monthly",
        "price": 0,
        "currency": "INR",
        "max_users": 0,
        "max_practitioners": 0,
        "max_patients": 0,
        "is_active": 1,
    },
    {
        "plan_name": "Starter Monthly",
        "plan_code": "STARTER-MONTHLY",
        "description": "Clinify Starter plan billed monthly.",
        "plan_type": "Paid",
        "billing_cycle": "Monthly",
        "price": 0,
        "currency": "INR",
        "max_users": 0,
        "max_practitioners": 0,
        "max_patients": 0,
        "is_active": 1,
    },
    {
        "plan_name": "Starter Yearly",
        "plan_code": "STARTER-YEARLY",
        "description": "Clinify Starter plan billed yearly.",
        "plan_type": "Paid",
        "billing_cycle": "Yearly",
        "price": 0,
        "currency": "INR",
        "max_users": 0,
        "max_practitioners": 0,
        "max_patients": 0,
        "is_active": 1,
    },
]


def run():
    for plan_data in INITIAL_PLANS:

        if frappe.db.exists(
            "Clinify Plan",
            {"plan_code": plan_data["plan_code"]}
        ):
            print(
                f"Already exists: "
                f"{plan_data['plan_code']}"
            )
            continue

        plan = frappe.get_doc({
            "doctype": "Clinify Plan",
            **plan_data,
        })

        plan.insert(
            ignore_permissions=True
        )

        print(
            f"Created: "
            f"{plan.plan_name}"
        )

    frappe.db.commit()

    print("")
    print("========================================")
    print("INITIAL CLINIFY PLANS COMPLETE")
    print("========================================")

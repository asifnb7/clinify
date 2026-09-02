import frappe


def run():
    plan = frappe.db.get_value(
        "Clinify Plan",
        {
            "plan_code": "STARTER-MONTHLY",
            "is_active": 1,
        },
        [
            "name",
            "plan_name",
            "plan_code",
            "plan_type",
            "billing_cycle",
            "price",
            "currency",
            "is_active",
        ],
        as_dict=True,
    )

    print(plan if plan else "ERROR: ACTIVE STARTER-MONTHLY PLAN NOT FOUND")

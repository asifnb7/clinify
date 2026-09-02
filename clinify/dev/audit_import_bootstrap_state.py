import frappe


def run():
    print("=" * 70)
    print("CLINIFY — IMPORT BOOTSTRAP STATE AUDIT")
    print("=" * 70)

    print("\n--- CLINIC CONFIGURATION ---")
    print(
        frappe.db.sql(
            """
            SELECT field, value
            FROM `tabSingles`
            WHERE doctype = 'Clinic Configuration'
            ORDER BY field
            """,
            as_dict=True,
        )
    )

    print("\n--- CLINIFY SUBSCRIPTIONS ---")
    print(
        frappe.db.sql(
            """
            SELECT name, clinic, plan, subscription_status,
                   start_date, billing_cycle, price,
                   currency, is_active
            FROM `tabClinify Subscription`
            ORDER BY creation
            """,
            as_dict=True,
        )
    )

    print("\n--- IMPORT TEST USER ---")
    print(
        frappe.db.sql(
            """
            SELECT name, email, first_name, last_name,
                   enabled, user_type
            FROM `tabUser`
            WHERE email = 'import_test@example.com.invalid'
            """,
            as_dict=True,
        )
    )

    print("\n--- IMPORT TEST USER ROLES ---")
    print(
        frappe.db.sql(
            """
            SELECT parent, role
            FROM `tabHas Role`
            WHERE parent = 'import_test@example.com.invalid'
            """,
            as_dict=True,
        )
    )

    print("\n--- CLINIFY ADMIN ROLE ---")
    print(
        frappe.db.sql(
            """
            SELECT name, desk_access, is_custom
            FROM `tabRole`
            WHERE name = 'Clinify Clinic Admin'
            """,
            as_dict=True,
        )
    )

    print("\n" + "=" * 70)
    print("IMPORT BOOTSTRAP STATE AUDIT COMPLETE")
    print("=" * 70)

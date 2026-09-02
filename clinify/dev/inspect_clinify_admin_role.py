import frappe


def run():
    role = "Clinify Clinic Admin"

    print("=" * 70)
    print("CLINIFY BETA — CLINIC ADMIN ROLE PERMISSION AUDIT")
    print("=" * 70)

    print("\nROLE:")
    print(role)

    print("\n=== ROLE EXISTS ===")
    print(bool(frappe.db.exists("Role", role)))

    print("\n=== DOCTYPE PERMISSIONS ===")

    perms = frappe.get_all(
        "DocPerm",
        filters={
            "role": role,
        },
        fields=[
            "parent",
            "permlevel",
            "read",
            "write",
            "create",
            "delete",
            "submit",
            "cancel",
            "amend",
            "report",
            "export",
            "print",
            "email",
            "share",
        ],
        order_by="parent asc, permlevel asc",
        limit_page_length=500,
    )

    print("Permission rows:", len(perms))

    for p in perms:
        print(p)

    print("\n=== USER ROLE ASSIGNMENTS ===")

    user_roles = frappe.get_all(
        "Has Role",
        filters={
            "parent": "clinify-admin-test@example.com",
        },
        fields=[
            "role",
            "parenttype",
        ],
        order_by="role asc",
    )

    for r in user_roles:
        print(r)

    print("\n" + "=" * 70)
    print("CLINIFY CLINIC ADMIN ROLE AUDIT COMPLETE")
    print("=" * 70)

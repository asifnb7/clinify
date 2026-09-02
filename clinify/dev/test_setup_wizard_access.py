import frappe


USER = "clinify-admin-test@example.com"


def run():
    original_user = frappe.session.user

    try:
        frappe.set_user(USER)

        print("=" * 70)
        print("CLINIFY BETA — SETUP WIZARD ACCESS TEST")
        print("=" * 70)

        print("\nUSER:")
        print(frappe.session.user)

        print("\nROLES:")
        print(frappe.get_roles())

        print("\nSYSTEM MANAGER:")
        print("System Manager" in frappe.get_roles())

        print("\nWORKSPACE MANAGER:")
        print("Workspace Manager" in frappe.get_roles())

        print("\nDESK USER:")
        print("Desk User" in frappe.get_roles())

        print("\n=== USER DOCUMENT ===")

        user = frappe.get_doc("User", USER)

        print({
            "name": user.name,
            "enabled": user.enabled,
            "user_type": user.user_type,
            "roles": [r.role for r in user.roles],
        })

        print("\n=== USER PERMISSION CHECK ===")

        for doctype in ["User", "Role", "Workspace"]:
            try:
                print({
                    "doctype": doctype,
                    "read": frappe.has_permission(
                        doctype=doctype,
                        ptype="read",
                        user=USER,
                    ),
                    "write": frappe.has_permission(
                        doctype=doctype,
                        ptype="write",
                        user=USER,
                    ),
                })
            except Exception as e:
                print({
                    "doctype": doctype,
                    "error": str(e),
                })

        print("\n=== ACCESS TEST COMPLETE ===")

    finally:
        frappe.set_user(original_user)

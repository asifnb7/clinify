import frappe
from frappe.desk.desktop import Workspace


USER = "clinify-admin-test@example.com"


def run():
    original_user = frappe.session.user

    try:
        frappe.set_user(USER)

        print("=" * 70)
        print("CLINIFY BETA — DIRECT WORKSPACE ACCESS TEST")
        print("=" * 70)

        print(f"\nUSER: {frappe.session.user}")
        print(f"ROLES: {frappe.get_roles()}")

        workspaces = [
            "Administration",
            "Billing",
            "Clinify",
            "Doctor",
            "Laboratory",
            "Pharmacy",
            "Reception",
            "Reports",
            "Settings",
        ]

        for name in workspaces:
            print("")
            print("-" * 70)
            print(f"=== {name} ===")

            page = frappe.db.get_value(
                "Workspace",
                name,
                [
                    "name",
                    "title",
                    "public",
                    "is_hidden",
                    "module",
                    "for_user",
                ],
                as_dict=True,
            )

            print("PAGE:", page)

            try:
                workspace = Workspace(page, True)

                print("CONSTRUCTOR: PASS")
                print("DOC ROLES:", [d.role for d in workspace.doc.roles])
                print("MODULE:", workspace.doc.module)
                print("ALLOWED MODULE:", workspace.doc.module in workspace.allowed_modules)

                print("IS_PERMITTED:", workspace.is_permitted())

            except frappe.PermissionError as e:
                print("CONSTRUCTOR: PERMISSION ERROR")
                print("ERROR:", repr(e))

            except Exception as e:
                print("CONSTRUCTOR: OTHER ERROR")
                print("ERROR TYPE:", type(e).__name__)
                print("ERROR:", repr(e))

        print("")
        print("=" * 70)
        print("DIRECT WORKSPACE ACCESS TEST COMPLETE")
        print("=" * 70)

    finally:
        frappe.set_user(original_user)

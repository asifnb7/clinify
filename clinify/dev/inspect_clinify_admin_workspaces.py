import frappe


USER = "clinify-admin-test@example.com"


def run():
    original_user = frappe.session.user

    try:
        frappe.set_user(USER)

        print("=" * 70)
        print("CLINIFY ADMIN WORKSPACE ACCESS DIAGNOSTIC")
        print("=" * 70)

        print("\nUSER:")
        print(frappe.session.user)

        print("\nROLES:")
        print(frappe.get_roles(USER))

        print("\n=== WORKSPACE META ===")

        workspaces = frappe.get_all(
            "Workspace",
            fields=[
                "name",
                "title",
                "module",
                "public",
                "is_hidden",
            ],
            order_by="name asc",
            limit_page_length=200,
        )

        for ws in workspaces:
            print(
                {
                    "name": ws.name,
                    "title": ws.title,
                    "module": ws.module,
                    "public": ws.public,
                    "is_hidden": ws.is_hidden,
                }
            )

        print("\n=== WORKSPACE ROLE LINKS ===")

        for ws in workspaces:
            roles = frappe.get_all(
                "Has Role",
                fields=["role"],
                filters={
                    "parent": ws.name,
                },
                order_by="role asc",
            )

            if roles:
                print(
                    f"{ws.name}: "
                    + str([row.role for row in roles])
                )

        print("\n=== WORKSPACE DOCTYPE PERMISSIONS ===")

        for ws_name in (
            "Administration",
            "Billing",
            "Clinify",
            "Doctor",
            "Healthcare",
            "Laboratory",
            "Pharmacy",
            "Reception",
            "Reports",
            "Settings",
        ):
            if not frappe.db.exists("Workspace", ws_name):
                print(f"{ws_name}: NOT FOUND")
                continue

            print(f"\n--- {ws_name} ---")

            workspace = frappe.get_doc(
                "Workspace",
                ws_name,
            )

            print("Public:", workspace.public)
            print("Hidden:", workspace.is_hidden)
            print("Module:", workspace.module)

            if hasattr(workspace, "roles"):
                print("Roles:")
                for row in workspace.roles:
                    print(
                        {
                            "role": row.role,
                        }
                    )

        print("\n" + "=" * 70)
        print("WORKSPACE DIAGNOSTIC COMPLETE")
        print("=" * 70)

    finally:
        frappe.set_user(original_user)

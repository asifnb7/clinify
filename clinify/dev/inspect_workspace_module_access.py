import frappe
from frappe.desk.desktop import Workspace


USER = "clinify-admin-test@example.com"


def run():
    original_user = frappe.session.user

    try:
        frappe.set_user(USER)

        print("=" * 70)
        print("CLINIFY WORKSPACE MODULE ACCESS")
        print("=" * 70)

        print("\nUSER:")
        print(frappe.session.user)

        print("\nROLES:")
        print(frappe.get_roles())

        print("\n=== USER ALLOWED MODULES ===")
        workspace = Workspace(
            frappe._dict({
                "name": "Clinify",
                "title": "Clinify",
                "public": 1,
            }),
            True,
        )

        print(workspace.allowed_modules)

        print("\n=== ALLOWED PAGE/REPORT MODULES ===")
        allowed_page_and_report_modules = set(
            [d.get("module") for d in workspace.allowed_pages.values() if d.get("module")]
            + [d.get("module") for d in workspace.allowed_reports.values() if d.get("module")]
        )

        print(sorted(allowed_page_and_report_modules))

        print("\n=== CLINIFY WORKSPACE MODULE CHECK ===")
        for name in (
            "Administration",
            "Billing",
            "Clinify",
            "Doctor",
            "Laboratory",
            "Pharmacy",
            "Reception",
            "Reports",
            "Settings",
        ):
            page = frappe.db.get_value(
                "Workspace",
                name,
                ["name", "title", "module", "public", "is_hidden"],
                as_dict=True,
            )

            if not page:
                print(f"{name}: MISSING")
                continue

            module = page.module

            allowed_by_module = (
                not module
                or module in workspace.allowed_modules
                or module in allowed_page_and_report_modules
                or workspace.workspace_manager
            )

            print({
                "workspace": name,
                "module": module,
                "allowed_by_module": allowed_by_module,
                "workspace_manager": workspace.workspace_manager,
            })

        print("\n=== WORKSPACE ROLE CHECK ===")
        for name in (
            "Administration",
            "Billing",
            "Clinify",
            "Doctor",
            "Laboratory",
            "Pharmacy",
            "Reception",
            "Reports",
            "Settings",
        ):
            doc = frappe.get_cached_doc("Workspace", name)
            roles = [d.role for d in doc.roles]

            permitted = (
                not roles
                or bool(set(frappe.get_roles()).intersection(roles))
            )

            print({
                "workspace": name,
                "roles": roles,
                "permitted_by_role": permitted,
            })

        print("\n" + "=" * 70)
        print("MODULE ACCESS DIAGNOSTIC COMPLETE")
        print("=" * 70)

    finally:
        frappe.set_user(original_user)

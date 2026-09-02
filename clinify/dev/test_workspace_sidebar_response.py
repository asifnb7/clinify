import frappe


USER = "clinify-admin-test@example.com"


def run():
    original_user = frappe.session.user

    try:
        frappe.set_user(USER)

        from frappe.desk.desktop import get_workspace_sidebar_items

        print("=" * 70)
        print("CLINIFY BETA — ACTUAL WORKSPACE SIDEBAR RESPONSE")
        print("=" * 70)

        print("\nUSER:")
        print(frappe.session.user)

        print("\nROLES:")
        print(frappe.get_roles())

        result = get_workspace_sidebar_items()

        pages = result.get("pages", [])

        print("\n=== SIDEBAR FLAGS ===")
        print("has_access:", result.get("has_access"))
        print("has_create_access:", result.get("has_create_access"))

        print("\n=== SIDEBAR WORKSPACES ===")
        for page in pages:
            print({
                "name": page.get("name"),
                "title": page.get("title"),
                "module": page.get("module"),
                "public": page.get("public"),
                "is_hidden": page.get("is_hidden"),
                "for_user": page.get("for_user"),
            })

        print("\n=== CLINIFY WORKSPACES PRESENT ===")

        expected = {
            "Administration",
            "Billing",
            "Clinify",
            "Doctor",
            "Laboratory",
            "Pharmacy",
            "Reception",
            "Reports",
            "Settings",
        }

        actual = {
            page.get("name")
            for page in pages
            if page.get("name") in expected
        }

        print("Expected:", sorted(expected))
        print("Actual:  ", sorted(actual))
        print("Missing: ", sorted(expected - actual))
        print("Extra:   ", sorted(actual - expected))

        print("\n" + "=" * 70)
        print("SIDEBAR RESPONSE TEST COMPLETE")
        print("=" * 70)

    finally:
        frappe.set_user(original_user)

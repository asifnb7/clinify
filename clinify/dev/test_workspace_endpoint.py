import frappe


USER = "clinify-admin-test@example.com"


def run():
    original_user = frappe.session.user

    try:
        frappe.set_user(USER)

        print("=" * 70)
        print("CLINIFY BETA — WORKSPACE ENDPOINT TEST")
        print("=" * 70)

        print("\nUSER:")
        print(frappe.session.user)

        print("\nROLES:")
        print(frappe.get_roles())

        from frappe.desk.desktop import get_workspace_sidebar_items

        result = get_workspace_sidebar_items()

        print("\n=== RESULT TYPE ===")
        print(type(result).__name__)

        print("\n=== RESULT KEYS ===")
        print(sorted(result.keys()))

        print("\n=== FLAGS ===")
        print({
            "has_access": result.get("has_access"),
            "has_create_access": result.get("has_create_access"),
        })

        pages = result.get("pages", [])

        print("\n=== PAGE COUNT ===")
        print(len(pages))

        print("\n=== PAGE NAMES ===")
        print([page.get("name") for page in pages])

        clinify_pages = [
            page for page in pages
            if page.get("module") == "Clinify"
        ]

        print("\n=== CLINIFY PAGE COUNT ===")
        print(len(clinify_pages))

        print("\n=== CLINIFY PAGE DETAILS ===")
        for page in clinify_pages:
            print({
                "name": page.get("name"),
                "title": page.get("title"),
                "module": page.get("module"),
                "public": page.get("public"),
                "is_hidden": page.get("is_hidden"),
                "for_user": page.get("for_user"),
                "label": page.get("label"),
            })

        print("\n" + "=" * 70)
        print("WORKSPACE ENDPOINT TEST COMPLETE")
        print("=" * 70)

    finally:
        frappe.set_user(original_user)

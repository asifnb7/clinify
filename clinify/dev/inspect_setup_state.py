import frappe


def run():
    print("=" * 70)
    print("CLINIFY BETA — TENANT SETUP STATE")
    print("=" * 70)

    print("\nSITE:")
    print(frappe.local.site)

    print("\n=== frappe.is_setup_complete() ===")
    print(frappe.is_setup_complete())

    print("\n=== System Settings.setup_complete ===")
    print(frappe.db.get_single_value("System Settings", "setup_complete"))

    print("\n=== Installed Applications ===")
    apps = frappe.get_all(
        "Installed Application",
        fields=[
            "app_name",
            "has_setup_wizard",
            "is_setup_complete",
        ],
        order_by="app_name asc",
    )

    for app in apps:
        print(app)

    print("\n=== SETUP WIZARD HOOKS ===")
    print(frappe.get_hooks("setup_wizard_requires"))

    print("\n=== SETUP COMPLETE HOOKS ===")
    print(frappe.get_hooks("setup_wizard_complete"))

    print("\n" + "=" * 70)
    print("SETUP STATE DIAGNOSTIC COMPLETE")
    print("=" * 70)

import frappe


def run():
    print("=" * 70)
    print("CLINIFY BETA — APPLY EXISTING TENANT SETUP STATE")
    print("=" * 70)

    print("\nBEFORE:")

    print(
        "ERPNext Installed Application:",
        frappe.db.get_value(
            "Installed Application",
            {"app_name": "erpnext"},
            ["has_setup_wizard", "is_setup_complete"],
            as_dict=True,
        ),
    )

    print(
        "System Settings.setup_complete:",
        frappe.db.get_single_value("System Settings", "setup_complete"),
    )

    # This beta tenant is based on an already-configured application
    # environment. Do not execute the interactive ERPNext setup wizard.
    frappe.db.set_value(
        "Installed Application",
        {"app_name": "erpnext"},
        "is_setup_complete",
        1,
    )

    frappe.db.set_single_value(
        "System Settings",
        "setup_complete",
        1,
    )

    # Keep the non-wizard applications internally consistent.
    for app_name in ("clinify", "healthcare"):
        if frappe.db.exists(
            "Installed Application",
            {"app_name": app_name},
        ):
            frappe.db.set_value(
                "Installed Application",
                {"app_name": app_name},
                "is_setup_complete",
                1,
            )

    frappe.db.commit()
    frappe.clear_cache()

    print("\nAFTER:")

    print(
        "ERPNext Installed Application:",
        frappe.db.get_value(
            "Installed Application",
            {"app_name": "erpnext"},
            ["has_setup_wizard", "is_setup_complete"],
            as_dict=True,
        ),
    )

    print(
        "System Settings.setup_complete:",
        frappe.db.get_single_value("System Settings", "setup_complete"),
    )

    print("\nfrappe.is_setup_complete():")
    print(frappe.is_setup_complete())

    print("\n" + "=" * 70)
    print("TENANT SETUP STATE UPDATED")
    print("=" * 70)

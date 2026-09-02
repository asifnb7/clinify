import frappe


USER = "clinify-admin-test@example.com"


def run():
    original_user = frappe.session.user

    try:
        frappe.set_user(USER)

        print("=" * 70)
        print("CLINIFY BETA — ADMIN PERMISSION AUDIT")
        print("=" * 70)

        print("\nUSER:")
        print(frappe.session.user)

        print("\nROLES:")
        print(frappe.get_roles())

        doctypes = [
            "Patient",
            "Appointment",
            "Healthcare Practitioner",
            "Patient Encounter",
            "Clinical Procedure",
            "Lab Test",
            "Medication Request",
            "Sales Invoice",
            "Payment Entry",
            "Item",
            "Company",
            "User",
            "Role",
            "System Settings",
            "Installed Application",
        ]

        print("\n=== DOCTYPE PERMISSIONS ===")

        for doctype in doctypes:
            exists = frappe.db.exists("DocType", doctype)

            if not exists:
                print({
                    "doctype": doctype,
                    "exists": False,
                })
                continue

            print({
                "doctype": doctype,
                "exists": True,
                "read": frappe.has_permission(
                    doctype,
                    ptype="read",
                    user=USER,
                ),
                "create": frappe.has_permission(
                    doctype,
                    ptype="create",
                    user=USER,
                ),
                "write": frappe.has_permission(
                    doctype,
                    ptype="write",
                    user=USER,
                ),
                "delete": frappe.has_permission(
                    doctype,
                    ptype="delete",
                    user=USER,
                ),
            })

        print("\n=== SETUP WIZARD ACCESS ===")

        try:
            print(
                "setup-wizard permitted:",
                frappe.has_permission(
                    "Page",
                    ptype="read",
                    user=USER,
                ),
            )
        except Exception as e:
            print("setup-wizard permission check error:", str(e))

        print("\n" + "=" * 70)
        print("ADMIN PERMISSION AUDIT COMPLETE")
        print("=" * 70)

    finally:
        frappe.set_user(original_user)

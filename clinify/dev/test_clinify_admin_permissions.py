import frappe


def run():
    user = "clinify-admin-test@example.com"

    if not frappe.db.exists("User", user):
        frappe.throw(f"Test user does not exist: {user}")

    original_user = frappe.session.user

    try:
        frappe.set_user(user)

        doctypes = [
            "Clinic Configuration",
            "Clinify Subscription",
            "Dental Service",
            "Treatment Plan Template",
            "Clinify Plan",
            "Clinify Tenant",
            "Clinify Settings",
            "Clinify Report Anchor",
        ]

        permissions = [
            "read",
            "write",
            "create",
            "delete",
        ]

        print(f"User: {frappe.session.user}")
        print("")

        for doctype in doctypes:
            if not frappe.db.exists("DocType", doctype):
                print(f"{doctype}: DOCTYPE NOT FOUND")
                continue

            print(f"=== {doctype} ===")

            for perm in permissions:
                result = frappe.has_permission(
                    doctype,
                    ptype=perm,
                    user=user,
                )

                print(f"{perm}: {'ALLOW' if result else 'DENY'}")

            print("")

    finally:
        frappe.set_user(original_user)

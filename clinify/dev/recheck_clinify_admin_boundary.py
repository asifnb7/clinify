import frappe


USER = "clinify-admin-test@example.com"


def run():
    original_user = frappe.session.user

    try:
        frappe.set_user(USER)

        print("=" * 70)
        print("CLINIFY ADMIN BOUNDARY RECHECK")
        print("=" * 70)

        print("\nUSER:")
        print(frappe.session.user)

        print("\nROLES:")
        print(frappe.get_roles(USER))

        doctypes = [
            "Clinic Configuration",
            "Clinify Subscription",
            "Dental Service",
            "Treatment Plan Template",
            "Clinify Plan",
            "Clinify Tenant",
            "Clinify Settings",
            "User",
            "Company",
            "Customer",
            "Patient",
            "Clinical Procedure",
        ]

        for doctype in doctypes:
            print("")
            print(f"=== {doctype} ===")

            if not frappe.db.exists("DocType", doctype):
                print("DOCTYPE: NOT FOUND")
                continue

            meta = frappe.get_meta(doctype)

            print(
                "META:",
                {
                    "name": meta.name,
                    "module": meta.module,
                    "custom": meta.custom,
                    "issingle": meta.issingle,
                    "read_only": meta.read_only,
                },
            )

            role_permissions = frappe.permissions.get_role_permissions(
                meta,
                user=USER,
                debug=False,
            )

            print("ROLE PERMISSIONS:")
            print(role_permissions)

            for ptype in ("read", "write", "create", "delete"):
                result = frappe.permissions.has_permission(
                    doctype,
                    ptype,
                    user=USER,
                    raise_exception=False,
                )

                print(f"{ptype}: {result}")

        print("")
        print("=" * 70)
        print("BOUNDARY RECHECK COMPLETE")
        print("=" * 70)

    finally:
        frappe.set_user(original_user)

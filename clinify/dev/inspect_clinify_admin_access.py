import frappe


USER = "clinify-admin-test@example.com"


def run():
    print("=" * 70)
    print("CLINIFY ADMIN ACCESS FORENSICS")
    print("=" * 70)

    print("\n=== USER ROLES ===")
    print(frappe.get_roles(USER))

    for doctype in (
        "Clinify Plan",
        "Clinify Settings",
        "Clinify Tenant",
    ):
        print("")
        print("=" * 70)
        print(f"=== {doctype} ===")
        print("=" * 70)

        print("\n--- ROLE PERMISSIONS ---")
        meta = frappe.get_meta(doctype)
        print(
            frappe.permissions.get_role_permissions(
                meta,
                user=USER,
                debug=False,
            )
        )

        print("\n--- SHARED DOCUMENTS ---")
        try:
            shared = frappe.share.get_shared(
                doctype,
                USER,
                rights=["read", "write", "share"],
                limit=50,
            )
            print(shared)
        except Exception as e:
            print(f"SHARE CHECK ERROR: {type(e).__name__}: {e}")

        print("\n--- HAS PERMISSION ---")
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
    print("=== PERMISSION CACHE ===")
    print("=" * 70)

    try:
        print(frappe.local.role_permissions)
    except Exception as e:
        print(f"CACHE ERROR: {type(e).__name__}: {e}")

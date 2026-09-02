import frappe


USER = "clinify-admin-test@example.com"


def run():
    original_user = frappe.session.user

    try:
        frappe.set_user(USER)

        print("=" * 70)
        print("CLINIFY PERMISSION RESOLUTION DIAGNOSTIC")
        print("=" * 70)

        print("\nUSER:")
        print(frappe.session.user)

        print("\nROLES:")
        print(frappe.get_roles(USER))

        for doctype in (
            "Clinic Configuration",
            "Clinify Subscription",
            "Dental Service",
            "Treatment Plan Template",
            "Clinify Plan",
            "Clinify Settings",
            "Clinify Tenant",
        ):
            print("")
            print("=" * 70)
            print(doctype)
            print("=" * 70)

            meta = frappe.get_meta(doctype)

            print("\nMETA:")
            print({
                "name": meta.name,
                "issingle": meta.issingle,
                "custom": meta.custom,
                "read_only": meta.read_only,
            })

            print("\nMETA PERMISSIONS:")
            for perm in meta.permissions:
                print({
                    "role": perm.role,
                    "permlevel": perm.permlevel,
                    "read": perm.read,
                    "write": perm.write,
                    "create": perm.create,
                    "delete": perm.delete,
                    "submit": perm.submit,
                    "cancel": perm.cancel,
                    "amend": perm.amend,
                    "if_owner": perm.if_owner,
                })

            print("\nCALCULATED ROLE PERMISSIONS:")
            role_perms = frappe.permissions.get_role_permissions(
                meta,
                user=USER,
                debug=True,
            )
            print(dict(role_perms))

            print("\nFINAL HAS_PERMISSION:")
            for ptype in ("read", "write", "create", "delete"):
                try:
                    result = frappe.permissions.has_permission(
                        doctype,
                        ptype,
                        user=USER,
                        raise_exception=False,
                        debug=True,
                    )
                    print(f"{ptype}: {result}")
                except Exception as e:
                    print(f"{ptype}: ERROR — {type(e).__name__}: {e}")

    finally:
        frappe.set_user(original_user)

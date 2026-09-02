import frappe


def run():
    for doctype in (
        "Clinify Plan",
        "Clinify Settings",
        "Clinify Tenant",
    ):
        print("")
        print("=" * 70)
        print(f"=== {doctype} META PERMISSIONS ===")
        print("=" * 70)

        meta = frappe.get_meta(doctype)

        print("DocType:", meta.name)
        print("Module:", meta.module)
        print("Custom:", meta.custom)
        print("Is Single:", meta.issingle)
        print("Read Only:", meta.read_only)
        print("Permissions:")

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

        print("")
        print("=== ROLE PERMISSIONS FOR TEST USER ===")

        result = frappe.permissions.get_role_permissions(
            meta,
            user="clinify-admin-test@example.com",
            debug=True,
        )

        print(result)

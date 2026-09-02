import frappe


ROLE = "Clinify Clinic Admin"

PERMISSIONS = {
    "Clinic Configuration": {
        "read": 1,
        "write": 1,
        "create": 0,
        "delete": 0,
        "submit": 0,
        "cancel": 0,
        "amend": 0,
    },
    "Clinify Subscription": {
        "read": 1,
        "write": 1,
        "create": 0,
        "delete": 0,
        "submit": 0,
        "cancel": 0,
        "amend": 0,
    },
    "Dental Service": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "submit": 0,
        "cancel": 0,
        "amend": 0,
    },
    "Treatment Plan Template": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "submit": 0,
        "cancel": 0,
        "amend": 0,
    },
}


def run():
    if not frappe.db.exists("Role", ROLE):
        frappe.throw(f"Role does not exist: {ROLE}")

    for doctype, permissions in PERMISSIONS.items():
        if not frappe.db.exists("DocType", doctype):
            print(f"SKIPPED — DocType does not exist: {doctype}")
            continue

        existing = frappe.db.exists(
            "DocPerm",
            {
                "parent": doctype,
                "role": ROLE,
                "permlevel": 0,
            },
        )

        if existing:
            docperm = frappe.get_doc("DocPerm", existing)

            for field, value in permissions.items():
                setattr(docperm, field, value)

            docperm.save(ignore_permissions=True)

            print(f"Updated: {doctype}")
            continue

        docperm = frappe.get_doc({
            "doctype": "DocPerm",
            "parent": doctype,
            "parenttype": "DocType",
            "parentfield": "permissions",
            "role": ROLE,
            "permlevel": 0,
            **permissions,
        })

        docperm.insert(ignore_permissions=True)

        print(f"Created: {doctype}")

    frappe.db.commit()

    print("")
    print("========================================")
    print("CLINIFY ADMIN PERMISSIONS COMPLETE")
    print("========================================")

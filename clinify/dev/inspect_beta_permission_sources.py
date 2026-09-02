import frappe


TARGET_DOCTYPES = [
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
    "Clinic Configuration",
    "Clinify Subscription",
    "Dental Service",
    "Treatment Plan Template",
]


def run():
    print("=" * 70)
    print("CLINIFY BETA — PERMISSION SOURCE MAPPING")
    print("=" * 70)

    print("\n=== AVAILABLE ROLES ===")

    roles = frappe.get_all(
        "Role",
        fields=["name"],
        order_by="name asc",
        limit_page_length=500,
    )

    for role in roles:
        print(role["name"])

    print("\n=== PERMISSIONS FOR TARGET DOCTYPES ===")

    perms = frappe.get_all(
        "DocPerm",
        filters={
            "parent": ["in", TARGET_DOCTYPES],
        },
        fields=[
            "parent",
            "role",
            "permlevel",
            "read",
            "write",
            "create",
            "delete",
            "submit",
            "cancel",
            "amend",
            "report",
            "export",
            "print",
            "email",
            "share",
        ],
        order_by="parent asc, role asc, permlevel asc",
        limit_page_length=2000,
    )

    current_doctype = None

    for p in perms:
        if p["parent"] != current_doctype:
            current_doctype = p["parent"]
            print("\n---", current_doctype, "---")

        print(
            {
                "role": p["role"],
                "level": p["permlevel"],
                "read": p["read"],
                "write": p["write"],
                "create": p["create"],
                "delete": p["delete"],
                "submit": p["submit"],
                "cancel": p["cancel"],
                "amend": p["amend"],
                "report": p["report"],
                "export": p["export"],
                "print": p["print"],
                "email": p["email"],
                "share": p["share"],
            }
        )

    print("\n=== ROLE PERMISSION SUMMARY FOR IMPORTANT ROLES ===")

    important_roles = [
        "Clinify Clinic Admin",
        "Healthcare Administrator",
        "Healthcare User",
        "Physician",
        "Accounts Manager",
        "Accounts User",
        "System Manager",
        "Administrator",
    ]

    for role in important_roles:
        exists = frappe.db.exists("Role", role)

        print("\nROLE:", role)
        print("EXISTS:", bool(exists))

        if not exists:
            continue

        role_perms = [
            p
            for p in perms
            if p["role"] == role
        ]

        print("TARGET PERMISSION ROWS:", len(role_perms))

        for p in role_perms:
            print(
                p["parent"],
                "R",
                p["read"],
                "W",
                p["write"],
                "C",
                p["create"],
                "D",
                p["delete"],
                "S",
                p["submit"],
            )

    print("\n" + "=" * 70)
    print("PERMISSION SOURCE MAPPING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run()

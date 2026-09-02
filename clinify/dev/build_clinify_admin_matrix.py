import frappe

ROLE = "Clinify Clinic Admin"

TARGETS = [
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
    "Clinic Configuration",
    "Clinify Subscription",
    "Dental Service",
    "Treatment Plan Template",
]

SOURCE_ROLES = {
    "Patient": ["Physician", "Nursing User"],
    "Appointment": ["Employee", "Sales User"],
    "Healthcare Practitioner": ["Physician", "Nursing User", "Laboratory User"],
    "Patient Encounter": ["Physician"],
    "Clinical Procedure": ["Physician", "Nursing User"],
    "Lab Test": ["Laboratory User", "Physician"],
    "Medication Request": ["Healthcare Administrator", "Physician"],
    "Sales Invoice": ["Accounts Manager", "Accounts User"],
    "Payment Entry": ["Accounts Manager", "Accounts User"],
    "Item": ["Item Manager", "Accounts User"],
    "Company": ["Accounts Manager"],
    "Clinic Configuration": ["Clinify Clinic Admin"],
    "Clinify Subscription": ["Clinify Clinic Admin"],
    "Dental Service": ["Clinify Clinic Admin", "Physician"],
    "Treatment Plan Template": ["Clinify Clinic Admin", "Physician"],
}


def run():
    print("=" * 70)
    print("CLINIFY BETA — TENANT ADMIN PERMISSION MATRIX")
    print("=" * 70)

    print("\nTARGET ROLE:")
    print(ROLE)

    print("\n=== PROPOSED PERMISSION SOURCES ===")

    for doctype in TARGETS:
        print(f"\n--- {doctype} ---")

        sources = SOURCE_ROLES.get(doctype, [])

        for source_role in sources:
            rows = frappe.get_all(
                "DocPerm",
                filters={
                    "parent": doctype,
                    "role": source_role,
                    "permlevel": 0,
                },
                fields=[
                    "role",
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
                order_by="idx asc",
            )

            if rows:
                for row in rows:
                    print(dict(row))
            else:
                print(f"{source_role}: NO PERMISSION ROW")

    print("\n=== EXISTING CLINIFY CLINIC ADMIN PERMISSIONS ===")

    rows = frappe.get_all(
        "DocPerm",
        filters={"role": ROLE},
        fields=[
            "parent",
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
        order_by="parent asc, permlevel asc",
    )

    for row in rows:
        print(dict(row))

    print("\n=== PLATFORM-LEVEL ROLES TO EXCLUDE ===")

    for role in [
        "System Manager",
        "Administrator",
        "Workspace Manager",
    ]:
        print(
            role,
            "EXISTS:",
            bool(frappe.db.exists("Role", role))
        )

    print("\n" + "=" * 70)
    print("MATRIX DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run()

import frappe


USER = "clinify-admin-test@example.com"
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
]


def run():
    original_user = frappe.session.user

    try:
        print("=" * 70)
        print("CLINIFY BETA — PERMISSION ENGINE DIAGNOSTIC")
        print("=" * 70)

        print("\nUSER:")
        print(USER)

        print("\nROLE:")
        print(ROLE)

        print("\n=== ROLE ASSIGNMENT ===")
        print(
            frappe.get_all(
                "Has Role",
                filters={
                    "parent": USER,
                    "role": ROLE,
                },
                fields=["name", "parent", "role", "parenttype"],
            )
        )

        print("\n=== ACTUAL DOCPERM ROWS ===")

        for doctype in TARGETS:
            rows = frappe.get_all(
                "DocPerm",
                filters={
                    "parent": doctype,
                    "role": ROLE,
                    "permlevel": 0,
                },
                fields=[
                    "name",
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
                ],
            )

            print(f"\n--- {doctype} ---")
            print(rows)

        print("\n=== SESSION PERMISSION TEST ===")

        frappe.set_user(USER)

        print("SESSION USER:")
        print(frappe.session.user)

        print("\nROLES:")
        print(frappe.get_roles())

        for doctype in TARGETS:
            print(
                {
                    "doctype": doctype,
                    "read": frappe.has_permission(doctype, "read"),
                    "write": frappe.has_permission(doctype, "write"),
                    "create": frappe.has_permission(doctype, "create"),
                    "delete": frappe.has_permission(doctype, "delete"),
                }
            )

        print("\n=== USER-SPECIFIC PERMISSION TEST ===")

        for doctype in TARGETS:
            print(
                {
                    "doctype": doctype,
                    "read": frappe.has_permission(
                        doctype,
                        "read",
                        user=USER,
                    ),
                    "write": frappe.has_permission(
                        doctype,
                        "write",
                        user=USER,
                    ),
                    "create": frappe.has_permission(
                        doctype,
                        "create",
                        user=USER,
                    ),
                    "delete": frappe.has_permission(
                        doctype,
                        "delete",
                        user=USER,
                    ),
                }
            )

        print("\n=== PERMISSION CACHE CLEAR TEST ===")

        frappe.clear_cache(user=USER)

        print("Cache cleared for user.")

        for doctype in TARGETS:
            print(
                {
                    "doctype": doctype,
                    "read": frappe.has_permission(
                        doctype,
                        "read",
                        user=USER,
                    ),
                    "write": frappe.has_permission(
                        doctype,
                        "write",
                        user=USER,
                    ),
                    "create": frappe.has_permission(
                        doctype,
                        "create",
                        user=USER,
                    ),
                    "delete": frappe.has_permission(
                        doctype,
                        "delete",
                        user=USER,
                    ),
                }
            )

        print("\n" + "=" * 70)
        print("PERMISSION ENGINE DIAGNOSTIC COMPLETE")
        print("=" * 70)

    finally:
        frappe.set_user(original_user)


if __name__ == "__main__":
    run()

import frappe


USER = "clinify-admin-test@example.com"

EXPECTED = {
    "Clinic Configuration": {
        "read": True,
        "write": True,
        "create": False,
        "delete": False,
    },
    "Clinify Subscription": {
        "read": True,
        "write": True,
        "create": False,
        "delete": False,
    },
    "Dental Service": {
        "read": True,
        "write": True,
        "create": True,
        "delete": True,
    },
    "Treatment Plan Template": {
        "read": True,
        "write": True,
        "create": True,
        "delete": True,
    },
    "Clinify Plan": {
        "read": False,
        "write": False,
        "create": False,
        "delete": False,
    },
    "Clinify Tenant": {
        "read": False,
        "write": False,
        "create": False,
        "delete": False,
    },
    "Clinify Settings": {
        "read": False,
        "write": False,
        "create": False,
        "delete": False,
    },
}


def run():
    print("=" * 70)
    print("CLINIFY BETA — FINAL CLINIC ADMIN BOUNDARY")
    print("=" * 70)
    print(f"User: {USER}")
    print("")

    failures = []

    for doctype, expected_permissions in EXPECTED.items():
        print(f"=== {doctype} ===")

        if not frappe.db.exists("DocType", doctype):
            print("DOCTYPE NOT FOUND")
            failures.append(f"{doctype}: missing DocType")
            print("")
            continue

        for ptype, expected in expected_permissions.items():
            actual = frappe.permissions.has_permission(
                doctype,
                ptype,
                user=USER,
                raise_exception=False,
            )

            status = "PASS" if actual == expected else "FAIL"

            print(
                f"{ptype}: {status} "
                f"(expected={'ALLOW' if expected else 'DENY'}, "
                f"actual={'ALLOW' if actual else 'DENY'})"
            )

            if actual != expected:
                failures.append(
                    f"{doctype} / {ptype}: "
                    f"expected {expected}, got {actual}"
                )

        print("")

    print("=" * 70)

    if failures:
        print("FINAL RESULT: FAIL")
        print("")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("FINAL RESULT: PASS")
        print("All expected Clinic Admin permission boundaries are correct.")

    print("=" * 70)

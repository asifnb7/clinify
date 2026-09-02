import frappe


def run():
    print("=== PERMISSION QUERY CONDITIONS ===")
    print(frappe.get_hooks("permission_query_conditions"))

    print("\n=== HAS PERMISSION HOOKS ===")
    print(frappe.get_hooks("has_permission"))

    print("\n=== DOC HOOKS ===")
    doc_events = frappe.get_hooks("doc_events")

    for doctype in (
        "Clinify Plan",
        "Clinify Settings",
        "Clinify Tenant",
    ):
        print(f"\n--- {doctype} ---")
        print(doc_events.get(doctype, {}))

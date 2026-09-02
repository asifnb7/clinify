import frappe


def inspect_structure():

    doctypes = [
        "Clinic Configuration",
        "Clinify Settings",
    ]

    for doctype in doctypes:

        print("\n" + "=" * 70)
        print(f"DOCTYPE: {doctype}")
        print("=" * 70)

        meta = frappe.get_meta(doctype)

        print(f"\nMODULE: {meta.module}")
        print(f"ISSINGLE: {meta.issingle}")

        print("\nFIELDS:")

        for df in meta.fields:
            print(
                f"{df.fieldname} | "
                f"label: {df.label} | "
                f"type: {df.fieldtype} | "
                f"options: {df.options or '-'}"
            )

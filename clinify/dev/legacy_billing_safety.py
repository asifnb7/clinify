import frappe


def run():
    print("")
    print("=" * 110)
    print("CLINIFY 5B.4-D — LEGACY BILLING SAFETY CHECK")
    print("=" * 110)

    tests = {
        "Extraction": ["DENT-EXTRACTION"],
        "Filling": [
            "DENT-GIC-FILLING",
            "DENT-COMPOSITE-FILLING",
        ],
        "Scaling": ["DENT-SCALING-POLISHING"],
        "Other": [],
    }

    print("")
    print("UNBILLED COMPLETED PROCEDURES")
    print("-" * 110)

    rows = frappe.get_all(
        "Dental Planned Procedure",
        filters={
            "planned_status": "Completed",
            "billed_invoice": ["is", "not set"],
        },
        fields=[
            "name",
            "parent",
            "procedure_type",
            "tooth_number",
            "estimated_cost",
            "dental_service",
        ],
        order_by="modified asc",
    )

    print("COUNT:", len(rows))

    for row in rows:
        print(
            f"{row.name:<15} | "
            f"TYPE={row.procedure_type:<20} | "
            f"TOOTH={row.tooth_number or '-':<5} | "
            f"COST={row.estimated_cost or 0:<8} | "
            f"SERVICE={row.dental_service or '-'}"
        )

    print("")
    print("=" * 110)
    print("LEGACY TYPE → CATALOGUE MAPPING")
    print("=" * 110)

    for legacy_type, candidate_codes in tests.items():

        print("")
        print("LEGACY:", legacy_type)
        print("-" * 110)

        if not candidate_codes:
            print("NO SAFE CATALOGUE MAPPING")
            continue

        for code in candidate_codes:

            service = frappe.db.get_value(
                "Dental Service",
                {
                    "service_code": code,
                    "is_active": 1,
                },
                [
                    "name",
                    "service_code",
                    "service_name",
                    "erpnext_item",
                    "minimum_price",
                    "maximum_price",
                    "pricing_basis",
                ],
                as_dict=True,
            )

            if service:
                print(
                    f"{service.service_code:<35} | "
                    f"{service.service_name:<35} | "
                    f"ITEM={service.erpnext_item:<30} | "
                    f"PRICE={service.minimum_price}-{service.maximum_price} | "
                    f"BASIS={service.pricing_basis}"
                )
            else:
                print(code, "NOT FOUND")

    print("")
    print("=" * 110)
    print("5B.4-D LEGACY BILLING SAFETY CHECK COMPLETE")
    print("READ-ONLY — NO DATABASE CHANGES")
    print("=" * 110)

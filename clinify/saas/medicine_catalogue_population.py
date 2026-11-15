import frappe


_ITEM_FIELDS = (
    "item_code",
    "item_name",
    "item_group",
    "disabled",
    "is_stock_item",
    "is_sales_item",
    "stock_uom",
    "description",
)


def add_missing_drug_items(items):
    if not isinstance(items, list) or not items:
        raise ValueError("Medicine catalogue batch must contain Items.")

    seen_item_codes = set()
    validated_items = []

    for source in items:
        if not isinstance(source, dict):
            raise ValueError("Medicine catalogue contains an invalid Item.")

        item_code = source.get("item_code")
        if not isinstance(item_code, str) or not item_code.strip():
            raise ValueError("Medicine catalogue Item is missing its Item Code.")
        if item_code in seen_item_codes:
            raise ValueError("Medicine catalogue batch repeats an Item Code.")
        seen_item_codes.add(item_code)

        if source.get("item_group") != "Drug":
            raise ValueError("Medicine catalogue contains a non-Drug Item.")

        for field in ("item_name", "stock_uom"):
            value = source.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "Medicine catalogue Item is missing {}.".format(field)
                )

        validated_items.append(
            {field: source.get(field) for field in _ITEM_FIELDS}
        )

    created = 0
    skipped = 0
    for source in validated_items:
        item_code = source["item_code"]
        if frappe.db.exists("Item", {"item_code": item_code}):
            skipped += 1
            continue

        values = dict(source)
        values["doctype"] = "Item"
        frappe.get_doc(values).insert(ignore_permissions=True)
        created += 1

    frappe.db.commit()
    return {"created": created, "skipped": skipped}

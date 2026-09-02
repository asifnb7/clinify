import frappe


ITEM_CODE = "CLINIFY-TEST-DENTAL-SERVICE"


def run():
    existing = frappe.db.exists("Item", ITEM_CODE)

    if existing:
        print(f"Item already exists: {existing}")
        return existing

    item = frappe.get_doc({
        "doctype": "Item",
        "item_code": ITEM_CODE,
        "item_name": "Clinify Test Dental Service",
        "item_group": "Laboratory",
        "stock_uom": "Nos",
        "is_stock_item": 0,
        "disabled": 0,
    })

    item.insert(ignore_permissions=True)
    frappe.db.commit()

    print(f"Created Item: {item.name}")
    print(f"Item Code: {item.item_code}")
    print(f"Item Name: {item.item_name}")
    print(f"Item Group: {item.item_group}")
    print(f"Stock Item: {item.is_stock_item}")

    return item.name

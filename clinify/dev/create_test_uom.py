import frappe


UOM_NAME = "Nos"


def run():
    existing = frappe.db.exists("UOM", UOM_NAME)

    if existing:
        print(f"UOM already exists: {existing}")
        return existing

    uom = frappe.get_doc({
        "doctype": "UOM",
        "uom_name": UOM_NAME,
        "enabled": 1,
        "must_be_whole_number": 0,
    })

    uom.insert(ignore_permissions=True)
    frappe.db.commit()

    print(f"Created UOM: {uom.name}")
    return uom.name

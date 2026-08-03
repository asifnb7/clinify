import frappe

SERVICES = [
    ("DENT-SCALING",  "Scaling"),
    ("DENT-FILL",     "Filling"),
    ("DENT-RCT",      "RCT"),
    ("DENT-EXTRACT",  "Extraction"),
    ("DENT-CROWN",    "Crown"),
    ("DENT-IMPLANT",  "Implant"),
]


def install():
    for code, name in SERVICES:

        if frappe.db.exists("Dental Service", code):
            print(f"✓ {code} already exists")
            continue

        if not frappe.db.exists("Item", code):
            print(f"✗ ERPNext Item {code} not found")
            continue

        doc = frappe.get_doc({
            "doctype": "Dental Service",
            "service_code": code,
            "service_name": name,
            "erpnext_item": code,
            "is_active": 1,
        })

        doc.insert(ignore_permissions=True)

        print(f"✓ Created {code}")

    frappe.db.commit()
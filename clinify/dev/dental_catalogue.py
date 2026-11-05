import frappe


SERVICES = [
    {
        "code": "DENT-IOPA",
        "name": "IOPA",
        "minimum": 100,
        "maximum": 100,
        "basis": "Fixed",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-EXTRACTION",
        "name": "Extraction",
        "minimum": 1000,
        "maximum": 1000,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-OPEN-EXTRACTION",
        "name": "Open Extraction",
        "minimum": 3000,
        "maximum": 3000,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-IMPACTION",
        "name": "Impaction",
        "minimum": 3000,
        "maximum": 5000,
        "basis": "Range",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-SCALING-POLISHING",
        "name": "Scaling (Cleaning) and Polishing",
        "minimum": 1500,
        "maximum": 3000,
        "basis": "Range",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-GIC-FILLING",
        "name": "GIC Filling",
        "minimum": 800,
        "maximum": 800,
        "basis": "Per Tooth",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-COMPOSITE-FILLING",
        "name": "Composite Filling",
        "minimum": 1500,
        "maximum": 1500,
        "basis": "Per Tooth",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-CROWN-RECEMENTATION",
        "name": "Crown Recementation",
        "minimum": 500,
        "maximum": 500,
        "basis": "Per Cap",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-ANTERIOR-CROWN-BUILDUP",
        "name": "Anterior Crown Build Up",
        "minimum": 3000,
        "maximum": 3000,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-RCT-STANDARD",
        "name": "Root Canal Treatment",
        "minimum": 3500,
        "maximum": 6000,
        "basis": "Range",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-POST-FIBRE-METAL",
        "name": "Post (Fibre/Metal)",
        "minimum": 2500,
        "maximum": 2500,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-METAL-CROWN",
        "name": "Metal Crown",
        "minimum": 2500,
        "maximum": 2500,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-PFM-CROWN",
        "name": "PFM Crown",
        "minimum": 3500,
        "maximum": 3500,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-DMLS-CROWN",
        "name": "DMLS Crown",
        "minimum": 4000,
        "maximum": 4000,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-ZIRCONIA-CROWN",
        "name": "Zirconia Crown",
        "minimum": 7000,
        "maximum": 15000,
        "basis": "Range",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-REMOVABLE-DENTURE",
        "name": "Removable Denture (Single Unit)",
        "minimum": 1000,
        "maximum": 1000,
        "basis": "Fixed",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-COMPLETE-DENTURE",
        "name": "Complete Denture",
        "minimum": 30000,
        "maximum": 30000,
        "basis": "Fixed",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-BPS-DENTURE",
        "name": "Complete Denture (BPS Denture)",
        "minimum": 45000,
        "maximum": 45000,
        "basis": "Fixed",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-FLAP-SURGERY-NORMAL",
        "name": "Flap Surgery (Normal)",
        "minimum": 15000,
        "maximum": 15000,
        "basis": "Fixed",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-FLAP-SURGERY-LASER",
        "name": "Flap Surgery (Laser)",
        "minimum": 20000,
        "maximum": 20000,
        "basis": "Fixed",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-CROWN-LENGTHENING-SCALPEL",
        "name": "Crown Lengthening (Scalpel)",
        "minimum": 1500,
        "maximum": 1500,
        "basis": "Per Tooth",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-CROWN-LENGTHENING-LASER",
        "name": "Crown Lengthening (Laser)",
        "minimum": 3000,
        "maximum": 3000,
        "basis": "Per Tooth",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-CURETTAGE-LASER",
        "name": "Curettage (Laser)",
        "minimum": 6000,
        "maximum": 15000,
        "basis": "Range",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-IMPLANT-NOBEL",
        "name": "Implant (Nobel Biocare)",
        "minimum": 40000,
        "maximum": 40000,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-IMPLANT-DENTIUM",
        "name": "Implant (Dentium)",
        "minimum": 25000,
        "maximum": 25000,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-ORTHO-METAL",
        "name": "Orthodontic Treatment (Metal)",
        "minimum": 30000,
        "maximum": 35000,
        "basis": "Range",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-ORTHO-CERAMIC",
        "name": "Orthodontic Treatment (Ceramic)",
        "minimum": 40000,
        "maximum": 45000,
        "basis": "Range",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-ORTHO-SELF-LIGATING",
        "name": "Orthodontic Treatment (Self Ligating)",
        "minimum": 50000,
        "maximum": 55000,
        "basis": "Range",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-CLEAR-ALIGNERS",
        "name": "Orthodontic Clear Aligners",
        "minimum": 80000,
        "maximum": 200000,
        "basis": "Range",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-BLEACHING-SINGLE",
        "name": "Bleaching (Single Tooth)",
        "minimum": 1000,
        "maximum": 1000,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-BLEACHING-FULL-ANTERIORS",
        "name": "Bleaching (Full Anteriors)",
        "minimum": 8000,
        "maximum": 8000,
        "basis": "Fixed",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-NIGHT-GUARD",
        "name": "Night Guard",
        "minimum": 3000,
        "maximum": 3000,
        "basis": "Fixed",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-ORTHO-RETAINER",
        "name": "Orthodontic Retainer",
        "minimum": 4000,
        "maximum": 4000,
        "basis": "Fixed",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-OPERCULECTOMY-LASER",
        "name": "Operculectomy (Laser)",
        "minimum": 3000,
        "maximum": 3000,
        "basis": "Fixed",
        "requires_tooth": 1,
    },
    {
        "code": "DENT-DEPIGMENTATION-LASER",
        "name": "Depigmentation (Laser)",
        "minimum": 6000,
        "maximum": 6000,
        "basis": "Per Arch",
        "requires_tooth": 0,
    },
    {
        "code": "DENT-LESION-EXCISION-LASER",
        "name": "Lesion Excision (Laser)",
        "minimum": 3000,
        "maximum": 3000,
        "basis": "Fixed",
        "requires_tooth": 0,
    },
]


def install():

    if not frappe.db.exists("Price List", "Standard Selling"):
        raise frappe.ValidationError(
            "Standard Selling Price List does not exist."
        )

    created_items = 0
    created_services = 0
    created_prices = 0
    existing_services = 0

    for service in SERVICES:

        code = service["code"]

        existing_service = frappe.db.exists(
            "Dental Service",
            {"service_code": code},
        )

        if existing_service:
            existing_services += 1
            continue

        # -------------------------------------------------
        # ERPNext Item
        # -------------------------------------------------

        if frappe.db.exists("Item", code):
            item = frappe.get_doc("Item", code)
        else:
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": code,
                "item_name": service["name"],
                "item_group": "Dental",
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "is_sales_item": 1,
                "disabled": 0,
            })

            item.insert(ignore_permissions=True)
            created_items += 1

        # -------------------------------------------------
        # Clinify Dental Service
        # -------------------------------------------------

        dental_service = frappe.get_doc({
            "doctype": "Dental Service",
            "service_code": code,
            "service_name": service["name"],
            "erpnext_item": code,
            "is_active": 1,
            "default_qty": 1,
            "pricing_basis": service["basis"],
            "minimum_price": service["minimum"],
            "maximum_price": service["maximum"],
            "requires_tooth": service["requires_tooth"],
        })
        dental_service.insert(ignore_permissions=True)
        created_services += 1

        # -------------------------------------------------
        # ERPNext Standard Selling Price
        # -------------------------------------------------

        existing_price = frappe.db.get_value(
            "Item Price",
            {
                "item_code": code,
                "price_list": "Standard Selling",
                "selling": 1,
            },
            "name",
        )

        if not existing_price:
            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": code,
                "price_list": "Standard Selling",
                "price_list_rate": service["minimum"],
                "currency": "INR",
                "selling": 1,
            }).insert(ignore_permissions=True)

            created_prices += 1

    frappe.db.commit()

    print("")
    print("=" * 90)
    print("CLINIFY 5B.3 — DENTAL CATALOGUE INSTALLED")
    print("=" * 90)
    print("")
    print("Catalogue services :", len(SERVICES))
    print("Items created      :", created_items)
    print("Services created   :", created_services)
    print("Prices created     :", created_prices)
    print("Services preserved :", existing_services)
    print("")
    print("Consultation       : EXCLUDED")
    print("Price List         : Standard Selling")
    print("Currency           : INR")
    print("Range default      : Published lower bound")
    print("")
    print("=" * 90)

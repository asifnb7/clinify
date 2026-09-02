import frappe


CATALOGUE = [
    ("DENT-IOPA", "IOPA", 100, 100, "Fixed", 0),
    ("DENT-EXTRACTION", "Extraction", 1000, 1000, "Fixed", 1),
    ("DENT-OPEN-EXTRACTION", "Open Extraction", 3000, 3000, "Fixed", 1),
    ("DENT-IMPACTION", "Impaction", 3000, 5000, "Range", 1),
    ("DENT-SCALING-POLISHING", "Scaling (Cleaning) and Polishing", 1500, 3000, "Range", 0),
    ("DENT-GIC-FILLING", "GIC Filling", 800, 800, "Per Tooth", 1),
    ("DENT-COMPOSITE-FILLING", "Composite Filling", 1500, 1500, "Per Tooth", 1),
    ("DENT-CROWN-RECEMENTATION", "Crown Recementation", 500, 500, "Per Cap", 1),
    ("DENT-ANTERIOR-CROWN-BUILDUP", "Anterior Crown Build Up", 3000, 3000, "Fixed", 1),
    ("DENT-RCT-STANDARD", "Root Canal Treatment", 3500, 6000, "Range", 1),
    ("DENT-POST-FIBRE-METAL", "Post (Fibre/Metal)", 2500, 2500, "Fixed", 1),
    ("DENT-METAL-CROWN", "Metal Crown", 2500, 2500, "Fixed", 1),
    ("DENT-PFM-CROWN", "PFM Crown", 3500, 3500, "Fixed", 1),
    ("DENT-DMLS-CROWN", "DMLS Crown", 4000, 4000, "Fixed", 1),
    ("DENT-ZIRCONIA-CROWN", "Zirconia Crown", 7000, 15000, "Range", 1),
    ("DENT-REMOVABLE-DENTURE", "Removable Denture (Single Unit)", 1000, 1000, "Fixed", 0),
    ("DENT-COMPLETE-DENTURE", "Complete Denture", 30000, 30000, "Fixed", 0),
    ("DENT-BPS-DENTURE", "Complete Denture (BPS Denture)", 45000, 45000, "Fixed", 0),
    ("DENT-FLAP-SURGERY-NORMAL", "Flap Surgery (Normal)", 15000, 15000, "Fixed", 0),
    ("DENT-FLAP-SURGERY-LASER", "Flap Surgery (Laser)", 20000, 20000, "Fixed", 0),
    ("DENT-CROWN-LENGTHENING-SCALPEL", "Crown Lengthening (Scalpel)", 1500, 1500, "Per Tooth", 1),
    ("DENT-CROWN-LENGTHENING-LASER", "Crown Lengthening (Laser)", 3000, 3000, "Per Tooth", 1),
    ("DENT-CURETTAGE-LASER", "Curettage (Laser)", 6000, 15000, "Range", 0),
    ("DENT-IMPLANT-NOBEL", "Implant (Nobel Biocare)", 40000, 40000, "Fixed", 0),
    ("DENT-IMPLANT-DENTIUM", "Implant (Dentium)", 25000, 25000, "Fixed", 0),
    ("DENT-ORTHO-METAL", "Orthodontic Treatment (Metal)", 30000, 35000, "Range", 0),
    ("DENT-ORTHO-CERAMIC", "Orthodontic Treatment (Ceramic)", 40000, 45000, "Range", 0),
    ("DENT-ORTHO-SELF-LIGATING", "Orthodontic Treatment (Self Ligating)", 50000, 55000, "Range", 0),
    ("DENT-CLEAR-ALIGNERS", "Orthodontic Clear Aligners", 80000, 200000, "Range", 0),
    ("DENT-BLEACHING-SINGLE", "Bleaching (Single Tooth)", 1000, 1000, "Fixed", 1),
    ("DENT-BLEACHING-FULL-ANTERIORS", "Bleaching (Full Anteriors)", 8000, 8000, "Fixed", 0),
    ("DENT-NIGHT-GUARD", "Night Guard", 3000, 3000, "Fixed", 0),
    ("DENT-ORTHO-RETAINER", "Orthodontic Retainer", 4000, 4000, "Fixed", 0),
    ("DENT-OPERCULECTOMY-LASER", "Operculectomy (Laser)", 3000, 3000, "Fixed", 1),
    ("DENT-DEPIGMENTATION-LASER", "Depigmentation (Laser)", 6000, 6000, "Per Arch", 0),
    ("DENT-LESION-EXCISION-LASER", "Lesion Excision (Laser)", 3000, 3000, "Fixed", 0),
]


def install():
    updated = 0
    missing = 0

    for code, name, minimum, maximum, basis, requires_tooth in CATALOGUE:

        service_name = frappe.db.get_value(
            "Dental Service",
            {"service_code": code},
            "name",
        )

        if not service_name:
            print(f"MISSING SERVICE: {code}")
            missing += 1
            continue

        frappe.db.set_value(
            "Dental Service",
            service_name,
            {
                "service_name": name,
                "pricing_basis": basis,
                "minimum_price": minimum,
                "maximum_price": maximum,
                "requires_tooth": requires_tooth,
                "is_active": 1,
            },
            update_modified=True,
        )

        updated += 1

    frappe.db.commit()

    print("")
    print("=" * 90)
    print("CLINIFY 5B.3 — PRICING METADATA INSTALLED")
    print("=" * 90)
    print("")
    print("Catalogue entries :", len(CATALOGUE))
    print("Updated           :", updated)
    print("Missing           :", missing)
    print("Consultation      : EXCLUDED")
    print("")
    print("=" * 90)

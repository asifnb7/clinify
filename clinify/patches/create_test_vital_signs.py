import frappe


def execute():

    encounter = "HLC-ENC-2026-00044"

    existing = frappe.db.get_value(
        "Vital Signs",
        {"encounter": encounter},
        "name",
    )

    if existing:
        print("Vital Signs already exists:", existing)
        return

    doc = frappe.get_doc({
        "doctype": "Vital Signs",
        "patient": "Basheer Ahmed",
        "encounter": encounter,
        "signs_date": "2026-08-16",
        "signs_time": "19:45:00",
        "temperature": "98.6",
        "pulse": "76",
        "respiratory_rate": "18",
        "bp_systolic": "120",
        "bp_diastolic": "80",
        "weight": 68,
        "bmi": 22.5,
    })

    doc.insert(ignore_permissions=True)

    frappe.db.commit()

    print("Created Vital Signs:", doc.name)
    print("Encounter:", doc.encounter)
    print("BP:", doc.bp_systolic, "/", doc.bp_diastolic)
    print("Pulse:", doc.pulse)
    print("Temperature:", doc.temperature)
    print("Weight:", doc.weight)

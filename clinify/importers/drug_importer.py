import frappe


def get_or_create_medication_class(class_name):
    """Create Medication Class if it does not exist."""

    if frappe.db.exists("Medication Class", class_name):
        return frappe.get_doc("Medication Class", class_name)

    doc = frappe.get_doc(
        {
            "doctype": "Medication Class",
            "medication_class": class_name,
        }
    )

    doc.insert(ignore_permissions=True)

    return doc


def get_or_create_item(
    item_code,
    item_name,
    item_group="Drug",
    stock_uom="Nos",
):
    """
    Create Drug Item if it doesn't exist.
    """

    if frappe.db.exists("Item", item_code):
        return frappe.get_doc("Item", item_code)

    doc = frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_name,
            "item_group": item_group,
            "stock_uom": stock_uom,
            "is_stock_item": 1,
            "disabled": 0,
        }
    )

    doc.insert(ignore_permissions=True)

    return doc


def get_or_create_medication(
    generic_name,
    strength,
    strength_uom,
    dosage_form,
    medication_class,
    dosage="1-0-1",
    duration="5 Day",
):
    """
    Create Medication if it doesn't exist.

    Medication naming in Healthcare may use generic_name, so first
    check whether a Medication with the generated name already exists.
    """

    # First check by document name.
    # This handles existing medicines such as "Paracetamol".
    if frappe.db.exists("Medication", generic_name):
        return frappe.get_doc("Medication", generic_name)

    # Then check for an existing medication with the same details.
    existing = frappe.db.exists(
        "Medication",
        {
            "generic_name": generic_name,
            "strength": strength,
            "strength_uom": strength_uom,
            "dosage_form": dosage_form,
        },
    )

    if existing:
        return frappe.get_doc("Medication", existing)

    doc = frappe.get_doc(
        {
            "doctype": "Medication",
            "generic_name": generic_name,
            "medication_class": medication_class,
            "strength": strength,
            "strength_uom": strength_uom,
            "dosage_form": dosage_form,
            "default_prescription_dosage": dosage,
            "default_prescription_duration": duration,
            "disabled": 0,
        }
    )

    doc.insert(ignore_permissions=True)

    return doc

def link_medication_item(
    medication,
    item,
):
    """
    Link Medication with ERPNext Item.
    """

    med = frappe.get_doc("Medication", medication)

    for row in med.linked_items:
        if row.item == item:
            return med

    item_doc = frappe.get_doc("Item", item)

    med.append(
        "linked_items",
        {
            "item": item_doc.name,
            "item_code": item_doc.item_code,
            "item_group": item_doc.item_group,
            "stock_uom": item_doc.stock_uom,
            "description": item_doc.description,
            "is_billable": 1,
        },
    )

    med.save(ignore_permissions=True)

    return med


COMMON_MEDICINES = [
    # -------------------------------------------------
    # ANALGESICS / PAIN / FEVER
    # -------------------------------------------------
    {
        "item_code": "PARACETAMOL-500-TAB",
        "item_name": "Paracetamol 500 Tablet",
        "generic_name": "Paracetamol",
        "strength": 500,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Analgesic",
    },
    {
        "item_code": "PARACETAMOL-650-TAB",
        "item_name": "Paracetamol 650 Tablet",
        "generic_name": "Paracetamol",
        "strength": 650,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Analgesic",
    },
    {
        "item_code": "IBUPROFEN-400-TAB",
        "item_name": "Ibuprofen 400 Tablet",
        "generic_name": "Ibuprofen",
        "strength": 400,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Analgesic",
    },
    {
        "item_code": "DICLOFENAC-50-TAB",
        "item_name": "Diclofenac 50 Tablet",
        "generic_name": "Diclofenac",
        "strength": 50,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Analgesic",
    },
    {
        "item_code": "ACECLOFENAC-100-TAB",
        "item_name": "Aceclofenac 100 Tablet",
        "generic_name": "Aceclofenac",
        "strength": 100,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Analgesic",
    },

    # -------------------------------------------------
    # ANTIBIOTICS
    # -------------------------------------------------
    {
        "item_code": "AMOXICILLIN-500-CAP",
        "item_name": "Amoxicillin 500 Capsule",
        "generic_name": "Amoxicillin",
        "strength": 500,
        "strength_uom": "Unit",
        "dosage_form": "Capsule",
        "medication_class": "Antibiotic",
    },
    {
        "item_code": "AZITHROMYCIN-250-TAB",
        "item_name": "Azithromycin 250 Tablet",
        "generic_name": "Azithromycin",
        "strength": 250,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antibiotic",
    },
    {
        "item_code": "AZITHROMYCIN-500-TAB",
        "item_name": "Azithromycin 500 Tablet",
        "generic_name": "Azithromycin",
        "strength": 500,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antibiotic",
    },
    {
        "item_code": "CEFIXIME-200-TAB",
        "item_name": "Cefixime 200 Tablet",
        "generic_name": "Cefixime",
        "strength": 200,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antibiotic",
    },
    {
        "item_code": "DOXYCYCLINE-100-CAP",
        "item_name": "Doxycycline 100 Capsule",
        "generic_name": "Doxycycline",
        "strength": 100,
        "strength_uom": "Unit",
        "dosage_form": "Capsule",
        "medication_class": "Antibiotic",
    },

    # -------------------------------------------------
    # ACIDITY / GASTRIC
    # -------------------------------------------------
    {
        "item_code": "PANTOPRAZOLE-40-TAB",
        "item_name": "Pantoprazole 40 Tablet",
        "generic_name": "Pantoprazole",
        "strength": 40,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antacid",
    },
    {
        "item_code": "OMEPRAZOLE-20-CAP",
        "item_name": "Omeprazole 20 Capsule",
        "generic_name": "Omeprazole",
        "strength": 20,
        "strength_uom": "Unit",
        "dosage_form": "Capsule",
        "medication_class": "Antacid",
    },
    {
        "item_code": "RABEPRAZOLE-20-TAB",
        "item_name": "Rabeprazole 20 Tablet",
        "generic_name": "Rabeprazole",
        "strength": 20,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antacid",
    },

    # -------------------------------------------------
    # ANTIHISTAMINES / ALLERGY
    # -------------------------------------------------
    {
        "item_code": "CETIRIZINE-10-TAB",
        "item_name": "Cetirizine 10 Tablet",
        "generic_name": "Cetirizine",
        "strength": 10,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antihistamine",
    },
    {
        "item_code": "LEVOCETIRIZINE-5-TAB",
        "item_name": "Levocetirizine 5 Tablet",
        "generic_name": "Levocetirizine",
        "strength": 5,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antihistamine",
    },
    {
        "item_code": "FEXOFENADINE-120-TAB",
        "item_name": "Fexofenadine 120 Tablet",
        "generic_name": "Fexofenadine",
        "strength": 120,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antihistamine",
    },

    # -------------------------------------------------
    # DIABETES
    # -------------------------------------------------
    {
        "item_code": "METFORMIN-500-TAB",
        "item_name": "Metformin 500 Tablet",
        "generic_name": "Metformin",
        "strength": 500,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antidiabetic",
    },
    {
        "item_code": "METFORMIN-1000-TAB",
        "item_name": "Metformin 1000 Tablet",
        "generic_name": "Metformin",
        "strength": 1000,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antidiabetic",
    },
    {
        "item_code": "GLIMEPIRIDE-1-TAB",
        "item_name": "Glimepiride 1 Tablet",
        "generic_name": "Glimepiride",
        "strength": 1,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antidiabetic",
    },
    {
        "item_code": "GLIMEPIRIDE-2-TAB",
        "item_name": "Glimepiride 2 Tablet",
        "generic_name": "Glimepiride",
        "strength": 2,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antidiabetic",
    },

    # -------------------------------------------------
    # HYPERTENSION / CARDIAC
    # -------------------------------------------------
    {
        "item_code": "AMLODIPINE-5-TAB",
        "item_name": "Amlodipine 5 Tablet",
        "generic_name": "Amlodipine",
        "strength": 5,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antihypertensive",
    },
    {
        "item_code": "AMLODIPINE-10-TAB",
        "item_name": "Amlodipine 10 Tablet",
        "generic_name": "Amlodipine",
        "strength": 10,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antihypertensive",
    },
    {
        "item_code": "TELMISARTAN-40-TAB",
        "item_name": "Telmisartan 40 Tablet",
        "generic_name": "Telmisartan",
        "strength": 40,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antihypertensive",
    },
    {
        "item_code": "TELMISARTAN-80-TAB",
        "item_name": "Telmisartan 80 Tablet",
        "generic_name": "Telmisartan",
        "strength": 80,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Antihypertensive",
    },

    # -------------------------------------------------
    # OTHER COMMON OPD MEDICINES
    # -------------------------------------------------
    {
        "item_code": "ONDANSETRON-4-TAB",
        "item_name": "Ondansetron 4 Tablet",
        "generic_name": "Ondansetron",
        "strength": 4,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Other",
    },
    {
        "item_code": "DOMPERIDONE-10-TAB",
        "item_name": "Domperidone 10 Tablet",
        "generic_name": "Domperidone",
        "strength": 10,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "medication_class": "Other",
    },
]


def import_common_medicines():
    """
    Import the Clinify common medicine starter database.

    Safe to run repeatedly.

    One Medication document is maintained per generic medicine.
    Multiple ERPNext Items can be linked to the same Medication.
    """

    created_items = 0
    created_medications = 0
    linked_items = 0

    for medicine in COMMON_MEDICINES:
        medication_class = medicine["medication_class"]

        # Ensure Medication Class exists.
        get_or_create_medication_class(medication_class)

        # -------------------------------------------------
        # ITEM
        # -------------------------------------------------
        item_existed = frappe.db.exists(
            "Item",
            medicine["item_code"],
        )

        item = get_or_create_item(
            item_code=medicine["item_code"],
            item_name=medicine["item_name"],
        )

        if not item_existed:
            created_items += 1

        # -------------------------------------------------
        # MEDICATION
        #
        # Medication is identified primarily by generic name.
        # This avoids duplicate documents such as:
        #
        # Paracetamol 500
        # Paracetamol 650
        #
        # Both strengths can instead link to one Medication.
        # -------------------------------------------------
        medication_existed = frappe.db.exists(
            "Medication",
            medicine["generic_name"],
        )

        medication = get_or_create_medication(
            generic_name=medicine["generic_name"],
            strength=medicine["strength"],
            strength_uom=medicine["strength_uom"],
            dosage_form=medicine["dosage_form"],
            medication_class=medication_class,
        )

        if not medication_existed:
            created_medications += 1

        # -------------------------------------------------
        # LINK MEDICATION → ITEM
        # -------------------------------------------------
        already_linked = any(
            row.item == item.name
            for row in medication.linked_items
        )

        link_medication_item(
            medication=medication.name,
            item=item.name,
        )

        if not already_linked:
            linked_items += 1

    frappe.db.commit()

    summary = {
        "total_processed": len(COMMON_MEDICINES),
        "items_created": created_items,
        "medications_created": created_medications,
        "new_links_created": linked_items,
    }

    print("\nClinify Common Medicine Import Complete")
    print("--------------------------------------")

    for key, value in summary.items():
        print(f"{key}: {value}")

    return summary

# ============================================================
# CLINIFY STARTER MEDICINE CATALOGUE
# ============================================================

STARTER_MEDICINES = [

    # --------------------------------------------------------
    # ANALGESICS / ANTIPYRETICS
    # --------------------------------------------------------

    {
        "item_code": "PARA-500",
        "item_name": "Paracetamol 500 Tablet",
        "generic_name": "Paracetamol 500",
        "medication_class": "Analgesic",
        "strength": 500,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "1-0-1",
        "duration": "5 Day",
    },

    {
        "item_code": "PARA-650",
        "item_name": "Paracetamol 650 Tablet",
        "generic_name": "Paracetamol 650",
        "medication_class": "Analgesic",
        "strength": 650,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "1-0-1",
        "duration": "5 Day",
    },

    {
        "item_code": "IBUPRO-400",
        "item_name": "Ibuprofen 400 Tablet",
        "generic_name": "Ibuprofen",
        "medication_class": "Analgesic",
        "strength": 400,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "1-0-1",
        "duration": "3 Day",
    },

    {
        "item_code": "DICLO-50",
        "item_name": "Diclofenac 50 Tablet",
        "generic_name": "Diclofenac",
        "medication_class": "Analgesic",
        "strength": 50,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "1-0-1",
        "duration": "3 Day",
    },


    # --------------------------------------------------------
    # ANTIBIOTICS
    # --------------------------------------------------------

    {
        "item_code": "AMOX-500",
        "item_name": "Amoxicillin 500 Capsule",
        "generic_name": "Amoxicillin",
        "medication_class": "Antibiotic",
        "strength": 500,
        "strength_uom": "Unit",
        "dosage_form": "Capsule",
        "dosage": "1-1-1",
        "duration": "5 Day",
    },

    {
        "item_code": "AZITHRO-500",
        "item_name": "Azithromycin 500 Tablet",
        "generic_name": "Azithromycin",
        "medication_class": "Antibiotic",
        "strength": 500,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "1-0-0",
        "duration": "3 Day",
    },

    {
        "item_code": "CEFIXIME-200",
        "item_name": "Cefixime 200 Tablet",
        "generic_name": "Cefixime",
        "medication_class": "Antibiotic",
        "strength": 200,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "1-0-1",
        "duration": "5 Day",
    },


    # --------------------------------------------------------
    # ANTACIDS / GASTRO
    # --------------------------------------------------------

    {
        "item_code": "PANTO-40",
        "item_name": "Pantoprazole 40 Tablet",
        "generic_name": "Pantoprazole",
        "medication_class": "Antacid",
        "strength": 40,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "1-0-0",
        "duration": "5 Day",
    },

    {
        "item_code": "OMEPRA-20",
        "item_name": "Omeprazole 20 Capsule",
        "generic_name": "Omeprazole",
        "medication_class": "Antacid",
        "strength": 20,
        "strength_uom": "Unit",
        "dosage_form": "Capsule",
        "dosage": "1-0-0",
        "duration": "5 Day",
    },


    # --------------------------------------------------------
    # ANTIHISTAMINES
    # --------------------------------------------------------

    {
        "item_code": "CETIRIZINE-10",
        "item_name": "Cetirizine 10 Tablet",
        "generic_name": "Cetirizine",
        "medication_class": "Antihistamine",
        "strength": 10,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "0-0-1",
        "duration": "5 Day",
    },

    {
        "item_code": "LEVOCET-5",
        "item_name": "Levocetirizine 5 Tablet",
        "generic_name": "Levocetirizine",
        "medication_class": "Antihistamine",
        "strength": 5,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "0-0-1",
        "duration": "5 Day",
    },


    # --------------------------------------------------------
    # ANTIDIABETIC
    # --------------------------------------------------------

    {
        "item_code": "METFORMIN-500",
        "item_name": "Metformin 500 Tablet",
        "generic_name": "Metformin",
        "medication_class": "Antidiabetic",
        "strength": 500,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "1-0-1",
        "duration": "5 Day",
    },


    # --------------------------------------------------------
    # ANTIHYPERTENSIVE
    # --------------------------------------------------------

    {
        "item_code": "AMLODIPINE-5",
        "item_name": "Amlodipine 5 Tablet",
        "generic_name": "Amlodipine",
        "medication_class": "Antihypertensive",
        "strength": 5,
        "strength_uom": "Unit",
        "dosage_form": "Tablet",
        "dosage": "1-0-0",
        "duration": "5 Day",
    },

]


def import_starter_medicines():
    """
    Import the Clinify starter medicine catalogue.

    Safe to run multiple times.
    Existing Medication, Item, and links will not be duplicated.
    """

    results = {
        "created_or_existing": [],
        "errors": [],
    }

    for medicine in STARTER_MEDICINES:

        try:
            item = get_or_create_item(
                item_code=medicine["item_code"],
                item_name=medicine["item_name"],
            )

            medication = get_or_create_medication(
                generic_name=medicine["generic_name"],
                strength=medicine["strength"],
                strength_uom=medicine["strength_uom"],
                dosage_form=medicine["dosage_form"],
                medication_class=medicine["medication_class"],
                dosage=medicine["dosage"],
                duration=medicine["duration"],
            )

            link_medication_item(
                medication=medication.name,
                item=item.name,
            )

            results["created_or_existing"].append({
                "medication": medication.name,
                "item": item.name,
            })

        except Exception as e:
            results["errors"].append({
                "medicine": medicine["generic_name"],
                "error": str(e),
            })

    frappe.db.commit()

    return results
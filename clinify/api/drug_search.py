import frappe


@frappe.whitelist()
def get_drug_prescription_defaults(drug_code):
    """
    Return prescription defaults for a selected Drug Code (Item).

    The selected Item is matched against Medication.linked_items.
    """

    if not drug_code:
        return {}

    item = frappe.get_doc(
        "Item",
        drug_code,
    )

    linked_medications = frappe.get_all(
        "Medication Linked Item",
        filters={
            "item": item.name,
        },
        fields=[
            "parent",
        ],
        limit=1,
    )

    medication = None

    if linked_medications:
        medication = frappe.get_doc(
            "Medication",
            linked_medications[0].parent,
        )

    result = {
        "drug_code": item.name,
        "drug_name": item.item_name,
        "strength": None,
        "strength_uom": None,
        "dosage_form": None,
        "dosage": None,
        "period": None,
        "interval": None,
        "interval_uom": None,
        "comment": "",
        "medication": None,
    }

    if medication:
        result.update(
            {
                "medication": medication.name,
                "strength": medication.strength,
                "strength_uom": medication.strength_uom,
                "dosage_form": medication.dosage_form,
                "dosage": medication.default_prescription_dosage,
                "period": medication.default_prescription_duration,
                "interval": medication.default_interval,
                "interval_uom": medication.default_interval_uom,
            }
        )

    return result

@frappe.whitelist()
def get_medication_item_query(
    doctype,
    txt,
    searchfield,
    start,
    page_len,
    filters=None,
):
    """
    Return only active ERPNext Items that are linked to an active Medication.

    Drug Prescription uses Item as the Drug Code, but the clinical
    workflow requires the selected Item to resolve through
    Medication Linked Item -> Medication.
    """
    txt = txt or ""
    start = int(start or 0)
    page_len = int(page_len or 20)

    like = f"%{txt}%"

    return frappe.db.sql(
        """
        SELECT DISTINCT
            i.name,
            i.item_name
        FROM `tabItem` i
        INNER JOIN `tabMedication Linked Item` mli
            ON mli.item = i.name
        INNER JOIN `tabMedication` med
            ON med.name = mli.parent
        WHERE i.disabled = 0
          AND med.disabled = 0
          AND (
              i.name LIKE %(txt)s
              OR i.item_name LIKE %(txt)s
          )
        ORDER BY i.item_name, i.name
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "txt": like,
            "start": start,
            "page_len": page_len,
        },
    )

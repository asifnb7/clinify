import frappe
import re


@frappe.whitelist()
def get_drug_prescription_defaults(drug_code):
    """
    Return Case 1 prescription data for a selected Medicine Catalogue Item.

    The selected Item itself is the medicine catalogue record.
    Medication data is optional enrichment only and is never required
    for prescription selection.
    """

    if not drug_code:
        return {}

    item = frappe.get_doc("Item", drug_code)

    return {
        "drug_code": item.name,
        "drug_name": item.item_name,
        "strength": 0,
        "strength_uom": None,
        "dosage_form": None,
        "dosage": "0-0-0",
        "period": "0 Day",
        "interval": 0,
        "interval_uom": "Hour",
        "comment": "",
        "medication": None,
        "mapping_valid": True,
        "catalogue_only": True,
    }


def clinify_resolve_medicine_display_name(item_name, generic_name):
    """
    Resolve the safest clinician-facing medicine label.

    Prefer a clinical generic label when it contains distinguishing
    strength/composition information. Otherwise retain a useful Item
    product name rather than relying on potentially incorrect Medication
    strength fields.
    """
    item_name = (item_name or "").strip()
    generic_name = (generic_name or "").strip()

    if not generic_name:
        return item_name

    # Combination medicines must display the actual catalogue/product
    # name. The generic_name is composition data and belongs in the
    # future second row.
    if "+" in generic_name:
        return item_name

    # A clinical generic label is considered distinguishing when it
    # contains dosage/strength information.
    clinical_pattern = re.compile(
        r"""
        (
            \d+(?:\.\d+)?\s*(?:mg|milligram|mcg|microgram|g|gram|
            kg|ml|millilitre|l|iu|unit|units|%|percent)
        )
        |
        (
            \([^)]*\d+(?:\.\d+)?\s*(?:mg|mcg|g|kg|ml|iu|unit|%)?[^)]*\)
        )
        |
        (
            \+
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    if clinical_pattern.search(generic_name):
        return generic_name

    # Bare generic names such as "Amlodipine" should not erase useful
    # Item-level strength/product identity such as "Amlodipine 10 Tablet".
    if item_name:
        item_has_numeric_identity = bool(
            re.search(r"\d+(?:\.\d+)?\s*(?:mg|mcg|g|kg|ml|iu|unit|%)?",
                      item_name, re.IGNORECASE)
        )

        if item_has_numeric_identity:
            # A numeric Item name such as "Amlodipine 5 Tablet" carries
            # useful product/strength identity, but the trailing dosage
            # form must not be presented as though "5 Tablet" means
            # five tablets.
            cleaned = re.sub(
                r"\s+(?:tablet|tablets|capsule|capsules|syrup|injection|"
                r"suspension|solution|cream|ointment|drops?)\s*$",
                "",
                item_name,
                flags=re.IGNORECASE,
            ).strip()

            return cleaned or item_name

    return generic_name


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
    Return active medicine catalogue Items for Drug Prescription.

    Case 1:
    - Item is the selectable medicine record.
    - Medication is optional display enrichment only.
    - Medication resolution is never required for prescription selection.
    - The actual Item code remains the stored link value.
    - The Item name is the visible medicine name.
    - Composition is optional display enrichment.
    """

    txt = (txt or "").strip()
    start = int(start or 0)
    page_len = min(int(page_len or 20), 50)

    like = f"%{txt}%"

    # Fast primary search: search the Item catalogue only.
    # Do not join Medication here; this endpoint is used by
    # the doctor's autocomplete and must remain lightweight.
    items = frappe.db.sql(
        """
        SELECT
            i.name,
            i.item_name,
            i.description
        FROM `tabItem` i
        WHERE i.disabled = 0
          AND i.item_group = 'Drug'
          AND (
                i.name LIKE %(txt)s
                OR i.item_name LIKE %(txt)s
                OR IFNULL(i.description, '') LIKE %(txt)s
                OR EXISTS (
                    SELECT 1
                    FROM `tabMedication Linked Item` mli_search
                    INNER JOIN `tabMedication` m_search
                        ON m_search.name = mli_search.parent
                    WHERE mli_search.item_code = i.name
                      AND m_search.disabled = 0
                      AND TRIM(IFNULL(m_search.generic_name, '')) LIKE %(txt)s
                )
          )
        ORDER BY i.item_name, i.name
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "txt": like,
            "start": start,
            "page_len": page_len,
        },
        as_dict=True,
    )

    if not items:
        return []

    item_codes = [row.name for row in items]

    # Enrich only the small result set with valid Medication data.
    # Medication.generic_name is the clinical medicine name shown to the
    # doctor. The Item code remains the stored Link value.
    medications = frappe.db.sql(
        """
        SELECT
            mli.item_code,
            TRIM(m.generic_name) AS generic_name
        FROM `tabMedication Linked Item` mli
        INNER JOIN `tabMedication` m
            ON m.name = mli.parent
        WHERE mli.item_code IN %(item_codes)s
          AND m.disabled = 0
          AND TRIM(IFNULL(m.generic_name, '')) != ''
        ORDER BY mli.item_code, m.name
        """,
        {
            "item_codes": item_codes,
        },
        as_dict=True,
    )

    medication_names = {}

    for row in medications:
        medication_name = (row.generic_name or "").strip()

        if not medication_name:
            continue

        # Never expose technical identifiers as the clinical medicine name.
        if medication_name.startswith("OMDB-"):
            continue

        if medication_name.startswith("CLINIFY-PILOT-"):
            continue

        if "::CLINIFY_MEDICINE_LABEL::" in medication_name:
            continue

        # The database audit confirms active Drug Items currently have
        # at most one valid Medication mapping, so the first valid
        # clinical name is deterministic.
        medication_names.setdefault(row.item_code, medication_name)

    result = []

    for item in items:
        # The doctor-facing Medicine Name is the actual catalogue
        # product/brand name stored in Item.item_name.
        #
        # Medication.generic_name is searchable clinical/composition
        # metadata, but must not replace the product name displayed
        # in the prescription grid.
        medicine_name = (item.item_name or item.name or "").strip()

        # Return the standard Frappe Link-search tuple:
        # (stored Item code, visible medicine name, empty composition).
        #
        # Composition/salt display is intentionally deferred until
        # after beta acceptance.
        result.append(
            (
                item.name,
                medicine_name,
                "",
            )
        )

    return result

@frappe.whitelist()
def get_prescription_duration_query(
    doctype,
    txt,
    searchfield,
    start,
    page_len,
    filters=None,
):
    """
    Clinify prescription duration search.

    The doctor-facing prescription period is expressed in days.
    Numeric ordering prevents lexical ordering such as:
    1 Day, 10 Day, 15 Day, 2 Day.
    """

    txt = (txt or "").strip()
    start = int(start or 0)
    page_len = min(int(page_len or 20), 100)

    return frappe.db.sql(
        """
        SELECT name
        FROM `tabPrescription Duration`
        WHERE name LIKE %(txt)s
          AND name REGEXP '^[0-9]+ Day$'
        ORDER BY
            CAST(SUBSTRING_INDEX(name, ' ', 1) AS UNSIGNED),
            name
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len,
        },
    )

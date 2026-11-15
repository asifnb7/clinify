"""Read-only mapping of central OpenMedsDB Items to product candidates."""

from collections import defaultdict
from hashlib import sha256

import frappe

from clinify.importers.openmedsdb_importer import (
    make_ingredient_display_name,
    split_ingredient_text,
)
from clinify.medicine_catalogue_sync import (
    commercial_identity_key,
    normalize_product_record,
    validate_product_batch,
)


_SOURCE_PROVIDER = "OpenMedsDB"
_UNKNOWN_PROVENANCE_FIELDS = (
    "source_identifier",
    "source_revision",
    "source_updated_at",
    "prescription_required",
    "source_mrp",
    "source_selling_price",
    "pack_label",
)

_SOURCE_QUERY = """
    SELECT
        i.name AS item_code,
        i.item_name AS medicine_name,
        i.disabled AS item_disabled,
        i.description AS item_description,
        mli.name AS linked_item_name,
        mli.manufacturer AS manufacturer,
        mli.description AS linked_item_description,
        m.name AS medication_name,
        m.generic_name AS composition,
        m.is_combination AS is_combination,
        m.strength AS strength,
        m.strength_uom AS strength_uom,
        m.dosage_form AS dosage_form,
        m.disabled AS medication_disabled
    FROM `tabItem` i
    LEFT JOIN `tabMedication Linked Item` mli
        ON mli.item_code = i.name
    LEFT JOIN `tabMedication` m
        ON m.name = mli.parent
    WHERE i.item_group = 'Drug'
      AND i.name LIKE 'OMDB-%'
      AND i.disabled = 0
    ORDER BY i.name, m.name, mli.name
"""


def _value(row, fieldname, default=None):
    if isinstance(row, dict):
        return row.get(fieldname, default)
    return getattr(row, fieldname, default)


def _temporary_product_id(item_code):
    digest = sha256(str(item_code).encode("utf-8")).hexdigest()[:20].upper()
    return f"CLM-DRYRUN-{digest}"


def _duplicate_source_identifier_groups(products):
    groups = defaultdict(list)
    for product in products:
        provider = str(product.get("source_provider") or "").strip().casefold()
        identifier = str(product.get("source_identifier") or "").strip().casefold()
        if provider and identifier:
            groups[(provider, identifier)].append(product)
    return [
        {
            "source_provider": group[0].get("source_provider", ""),
            "source_identifier": group[0].get("source_identifier", ""),
            "central_product_ids": sorted(
                record.get("central_product_id", "") for record in group
            ),
        }
        for _, group in sorted(groups.items())
        if len(group) > 1
    ]


def _group_source_rows(rows):
    items = {}
    for row in rows:
        item_code = str(_value(row, "item_code") or "").strip()
        if item_code:
            items.setdefault(item_code, []).append(row)
    return items


def _mapping_error(item_code, item_rows):
    linked_medications = {
        str(_value(row, "medication_name") or "").strip()
        for row in item_rows
        if _value(row, "medication_name")
    }
    if not linked_medications:
        return "NO_LINKED_MEDICATION"
    if len(linked_medications) > 1:
        return "MULTIPLE_LINKED_MEDICATIONS"
    if len(item_rows) > 1:
        return "MULTIPLE_LINK_ROWS"
    return ""


def _candidate_from_source(row):
    item_code = str(_value(row, "item_code") or "").strip()
    composition = " ".join(
        str(_value(row, "composition") or "").split()
    )
    is_combination = bool(_value(row, "is_combination"))
    ingredients = split_ingredient_text(composition)

    unresolved_reasons = []
    ingredient_name = ""
    if is_combination or len(ingredients) > 1:
        unresolved_reasons.append("UNRESOLVED_COMBINATION_INGREDIENT")
    elif composition:
        ingredient_name = make_ingredient_display_name(composition)

    if is_combination:
        strength = ""
        strength_uom = ""
    else:
        strength = _value(row, "strength")
        strength_uom = str(_value(row, "strength_uom") or "").strip()

    candidate = {
        "central_product_id": _temporary_product_id(item_code),
        "central_product_id_status": "DRY_RUN_ONLY_ID",
        "source_item_code": item_code,
        "ingredient_name": ingredient_name,
        "composition": composition,
        "medicine_name": " ".join(
            str(_value(row, "medicine_name") or "").split()
        ),
        "strength": strength,
        "strength_uom": strength_uom,
        "dosage_form": " ".join(
            str(_value(row, "dosage_form") or "").split()
        ),
        "manufacturer": " ".join(
            str(_value(row, "manufacturer") or "").split()
        ),
        "pack_label": "",
        "source_mrp": "",
        "source_selling_price": "",
        "prescription_required": "",
        "source_provider": _SOURCE_PROVIDER,
        "source_identifier": "",
        "source_revision": "",
        "source_updated_at": "",
        "is_active": int(
            not bool(_value(row, "item_disabled"))
            and not bool(_value(row, "medication_disabled"))
        ),
        "unresolved_reasons": unresolved_reasons,
        "unresolved_provenance_fields": list(_UNKNOWN_PROVENANCE_FIELDS),
    }
    return candidate


def _duplicate_commercial_identity_groups(candidates):
    groups = defaultdict(list)
    for candidate in candidates:
        # For combination diagnostics only, use the complete stored composition
        # as a comparison token. It is not a proposed ingredient_name mapping.
        identity_record = dict(candidate)
        if not identity_record["ingredient_name"]:
            identity_record["ingredient_name"] = identity_record["composition"]
        if not identity_record["ingredient_name"] or not identity_record["dosage_form"]:
            continue
        try:
            key = commercial_identity_key(identity_record)
        except (KeyError, TypeError, ValueError):
            continue
        groups[key].append(candidate)

    duplicate_groups = []
    for key, group in sorted(groups.items()):
        if len(group) < 2:
            continue
        descriptions = {
            " ".join(
                str(record.get("source_description") or "").split()
            ).casefold()
            for record in group
        }
        duplicate_groups.append(
            {
                "commercial_identity_key": key,
                "classification": (
                    "POSSIBLY_DISTINCT_PRODUCTS_PACK_INFORMATION_MISSING"
                    if len(descriptions) > 1
                    else "SAME_COMMERCIAL_IDENTITY_NO_STORED_DISTINCTION"
                ),
                "reason": (
                    "The mapped commercial fields match, but structured pack "
                    "information is unavailable; descriptions differ."
                    if len(descriptions) > 1
                    else "The mapped commercial fields and stored descriptions "
                    "match; no persisted field distinguishes these records."
                ),
                "items": [
                    {
                        "item_code": record["source_item_code"],
                        "medicine_name": record["medicine_name"],
                        "ingredient_composition": record["composition"],
                        "strength": record["strength"],
                        "strength_uom": record["strength_uom"],
                        "dosage_form": record["dosage_form"],
                        "manufacturer": record["manufacturer"],
                        "description": record.get("source_description", ""),
                    }
                    for record in sorted(
                        group, key=lambda value: value["source_item_code"]
                    )
                ],
            }
        )
    return duplicate_groups


def _normalizable_candidate(candidate):
    if candidate["unresolved_reasons"]:
        return None, "UNRESOLVED_COMBINATION_INGREDIENT"
    try:
        return normalize_product_record(candidate), ""
    except (TypeError, ValueError) as exc:
        return None, str(exc)


def build_central_medicine_product_dry_run():
    """Build a deterministic candidate mapping and validation report; never writes."""
    source_rows = frappe.db.sql(_SOURCE_QUERY, as_dict=True)
    grouped_rows = _group_source_rows(source_rows)

    mapping_errors = []
    candidates = []
    linked_medication_names = set()

    for item_code, item_rows in sorted(grouped_rows.items()):
        error = _mapping_error(item_code, item_rows)
        if error:
            mapping_errors.append({"item_code": item_code, "reason": error})
            linked_medication_names.update(
                str(_value(row, "medication_name")).strip()
                for row in item_rows
                if _value(row, "medication_name")
            )
            continue

        row = item_rows[0]
        if _value(row, "medication_name"):
            linked_medication_names.add(str(_value(row, "medication_name")).strip())
        candidate = _candidate_from_source(row)
        candidate["source_description"] = str(
            _value(row, "linked_item_description")
            or _value(row, "item_description")
            or ""
        )
        candidates.append(candidate)

    duplicate_commercial_groups = _duplicate_commercial_identity_groups(candidates)
    duplicate_source_groups = _duplicate_source_identifier_groups(candidates)
    duplicate_item_codes = {
        item["item_code"]
        for group in duplicate_commercial_groups
        for item in group["items"]
    }

    normalized_candidates = []
    invalid_products = []
    for candidate in candidates:
        normalized, error = _normalizable_candidate(candidate)
        if error:
            invalid_products.append(
                {"item_code": candidate["source_item_code"], "reason": error}
            )
        elif candidate["source_item_code"] in duplicate_item_codes:
            invalid_products.append(
                {
                    "item_code": candidate["source_item_code"],
                    "reason": "DUPLICATE_COMMERCIAL_IDENTITY",
                }
            )
        else:
            normalized_candidates.append(normalized)

    batch_validation_error = ""
    if normalized_candidates:
        try:
            validated_products = validate_product_batch(normalized_candidates)
        except (TypeError, ValueError) as exc:
            batch_validation_error = str(exc)
            invalid_products.extend(
                {
                    "item_code": product.get("source_item_code", ""),
                    "reason": batch_validation_error,
                }
                for product in normalized_candidates
            )
            validated_products = ()
    else:
        validated_products = ()

    unresolved_combinations = sum(
        "UNRESOLVED_COMBINATION_INGREDIENT" in candidate["unresolved_reasons"]
        for candidate in candidates
    )
    unresolved_provenance = sum(
        bool(candidate["unresolved_provenance_fields"])
        for candidate in candidates
    )

    return {
        "summary": {
            "source_items": len(grouped_rows),
            "linked_medications": len(linked_medication_names),
            "mapping_candidates": len(candidates),
            "mapping_errors": len(mapping_errors),
            "unresolved_combinations": unresolved_combinations,
            "unresolved_provenance": unresolved_provenance,
            "duplicate_commercial_identities": len(duplicate_commercial_groups),
            "duplicate_source_identifiers": len(duplicate_source_groups),
            "valid_products": len(validated_products),
            "invalid_products": len(invalid_products),
        },
        "central_product_id_strategy": {
            "status": "UNRESOLVED",
            "existing_item_identity": "OMDB-* Item code is a hash of the source ID, not the original ID.",
            "existing_product_identity": "DocType generates random CLM-* IDs; commercial identity hashes are not record IDs.",
            "dry_run_id_label": "DRY_RUN_ONLY_ID",
            "persisted_id_policy": None,
        },
        "mapping_errors": mapping_errors,
        "duplicate_commercial_identity_groups": duplicate_commercial_groups,
        "duplicate_source_identifier_groups": duplicate_source_groups,
        "invalid_products": invalid_products,
        "batch_validation_error": batch_validation_error,
        "valid_product_ids": [
            product["central_product_id"]
            for product in validated_products
        ],
        "candidates": candidates,
    }

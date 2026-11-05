"""
OpenMedsDB -> Clinify medicine importer.

STEP 1:
    Source-only normalization and dry-run preparation.

This module intentionally performs no database writes.  The write-enabled
import path will be added only after the 100-record dry-run has been reviewed.
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable
import frappe
from clinify.medicine_catalogue import (
    item_medication_identity_issue,
    parse_item_medicine_identity,
)


# OpenMedsDB -> ERPNext UOM mappings.
DOSAGE_FORM_MAP = {
    "tablet": "Tablet",
    "tablet md": "Tablet",
    "tablet dt": "Tablet",
    "tablet sr": "Tablet",
    "capsule": "Capsule",
    "capsule sr": "Capsule",
    "soft gelatin capsule": "Capsule",
    "cream": "Cream",
    "injection": "Injection",
    "syrup": "Syrup",
}

MEDICATION_CLASS = "Medication"

# Mandatory Prescription master values written to every imported Medication.
# The batch preflight refuses to start a write run when the matching
# Prescription Dosage / Prescription Duration masters are missing.
DEFAULT_PRESCRIPTION_DOSAGE = "0-0-0"
DEFAULT_PRESCRIPTION_DURATION = "0 Day"

UOM_MAP = {
    "mg": "Milligram",
    "milligram": "Milligram",
    "milligrams": "Milligram",
    "g": "Gram",
    "gm": "Gram",
    "gram": "Gram",
    "grams": "Gram",
    "mcg": "Microgram",
    "ug": "Microgram",
    "µg": "Microgram",
    "microgram": "Microgram",
    "micrograms": "Microgram",
    "kg": "Kg",
    "kilogram": "Kg",
    "kilograms": "Kg",
    "ml": "Millilitre",
    "millilitre": "Millilitre",
    "millilitres": "Millilitre",
    "milliliter": "Millilitre",
    "milliliters": "Millilitre",
    "l": "Litre",
    "lt": "Litre",
    "litre": "Litre",
    "litres": "Litre",
    "liter": "Litre",
    "liters": "Litre",
    "%": "Percent",
    "% w/w": "Percent",
    "iu": "International Unit",
    "i.u.": "International Unit",
}


@dataclass(frozen=True)
class NormalizedMedicine:
    source_id: str
    source: str
    source_revision: str
    medicine_name: str
    composition: str
    dosage_form: str
    manufacturer: str
    pack: str
    prescription_required: str
    ingredient_text: str
    strength_text: str
    strength: Decimal | None
    strength_uom_source: str
    strength_uom: str | None
    ingredient_strengths: tuple[tuple[str, str, str], ...]
    is_combination: bool
    is_multi_strength: bool
    review_required: bool
    review_reasons: tuple[str, ...]
    medication_identity: str
    item_identity: str


@dataclass
class DryRunReport:
    source_file: str
    source_revision: str
    total_rows: int = 0
    valid_rows: int = 0
    review_rows: int = 0
    single_ingredient: int = 0
    combinations: int = 0
    multi_strength: int = 0
    unknown_uom: int = 0
    unsupported_dosage_form: int = 0
    duplicate_source_ids: int = 0
    potential_existing_collisions: int = 0
    unique_source_ids: int = 0
    future_medications: int = 0
    future_items: int = 0
    future_links: int = 0
    rows: list[NormalizedMedicine] | None = None


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _slug(value: str) -> str:
    value = _clean(value).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def normalize_uom(source_uom: str) -> str | None:
    """Return an existing ERPNext UOM name, or None if unsafe to map."""
    key = _clean(source_uom).lower()
    return UOM_MAP.get(key)


_STRENGTH_PATTERN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<uom>%|[µμu]g|mcg|mg|milligrams?|g|gm|grams?|kg|"
    r"iu|i\.u\.|millilit(?:re|er)s?|ml|litres?|liters?|l)"
    r"(?:\s*/\s*(?P<denominator>\d+(?:\.\d+)?)\s*"
    r"(?P<denom_uom>ml|millilit(?:re|er)s?|l|litres?|liters?))?"
    r"(?:\s+(?P<basis>w/w|w/v|v/v))?",
    flags=re.IGNORECASE,
)


def parse_strength(text: str) -> tuple[Decimal | None, str]:
    """
    Extract the first clinically meaningful strength expression.

    Supports simple mass/volume strengths, IU, percentages, and
    concentration expressions such as 100mg/5ml.

    The original source expression is still preserved separately.
    """
    text = _clean(text)
    if not text:
        return None, ""

    match = _STRENGTH_PATTERN.search(text)
    if not match:
        return None, ""

    try:
        value = Decimal(match.group("value"))
    except InvalidOperation:
        return None, match.group("uom")

    uom = match.group("uom")
    denominator = match.group("denominator")
    denom_uom = match.group("denom_uom")
    basis = match.group("basis")

    if denominator and denom_uom:
        return value, f"{uom}/{denominator}{denom_uom}"

    if basis:
        return value, f"{uom} {basis}"

    return value, uom


def parse_ingredient_strengths(
    composition: str,
) -> tuple[tuple[str, str, str], ...]:
    """
    Parse each composition component independently.

    Returns tuples of:
        (ingredient_text, numeric_strength_text, source_uom_text)

    This is intentionally conservative. The complete original composition
    remains authoritative and is never replaced by the parsed representation.
    """
    parts = split_ingredient_text(composition)
    parsed: list[tuple[str, str, str]] = []

    for part in parts:
        match = _STRENGTH_PATTERN.search(part)
        if not match:
            parsed.append((_clean(part), "", ""))
            continue

        value = match.group("value")
        uom = match.group("uom")
        denominator = match.group("denominator")
        denom_uom = match.group("denom_uom")
        basis = match.group("basis")

        if denominator and denom_uom:
            strength_text = f"{value} {uom}/{denominator} {denom_uom}"
        elif basis:
            strength_text = f"{value} {uom} {basis}"
        else:
            strength_text = f"{value} {uom}"

        parsed.append((_clean(part), strength_text, uom))

    return tuple(parsed)


def split_ingredient_text(composition: str) -> list[str]:
    """
    Preserve composition while providing a simple ingredient list for dry-run
    classification.  This is deliberately conservative.
    """
    composition = _clean(composition)
    if not composition:
        return []

    parts = re.split(r"\s*(?:\+|&|\band\b)\s*", composition, flags=re.IGNORECASE)
    return [_clean(part) for part in parts if _clean(part)]


def is_multi_strength(text: str) -> bool:
    """
    Return True when the composition contains more than one
    independently parsed strength expression.
    """
    text = _clean(text)
    return len(_STRENGTH_PATTERN.findall(text)) > 1


def make_medication_identity(
    composition: str,
    strength_text: str,
    dosage_form: str,
) -> str:
    """
    Deterministic strength-qualified Medication identity.

    It deliberately does NOT use generic_name alone.
    """
    parts = [
        _slug(composition),
        _slug(strength_text),
        _slug(dosage_form),
    ]
    return "-".join(part for part in parts if part)[:140]


def make_item_identity(source_id: str) -> str:
    """
    Deterministic future Item identity based on the immutable source ID.
    """
    digest = hashlib.sha256(_clean(source_id).encode("utf-8")).hexdigest()[:20]
    return f"OMDB-{digest}".upper()


def make_ingredient_display_name(composition: str) -> str:
    """
    Derive the primary ingredient name from a composition string.

    Example: 'Cefprozil (250mg)' -> 'Cefprozil'.  The strength expression
    is removed so make_item_display_name() can re-attach it in normalized
    form without duplication.
    """
    parts = split_ingredient_text(composition)
    if not parts:
        return ""

    primary = parts[0]
    match = _STRENGTH_PATTERN.search(primary)
    if match:
        raw = f"{primary[: match.start()]} {primary[match.end():]}"
    else:
        raw = primary

    raw = re.sub(r"[\(\)\[\],;:]+", " ", raw)
    return _clean(raw)


def resolve_manufacturer(manufacturer_name):
    """Return a Manufacturer name, creating the master on demand."""
    manufacturer_name = (manufacturer_name or "").strip()

    if not manufacturer_name:
        return None

    existing = frappe.db.exists(
        "Manufacturer",
        {"short_name": manufacturer_name},
    )

    if existing:
        return existing

    manufacturer = frappe.get_doc(
        {
            "doctype": "Manufacturer",
            "short_name": manufacturer_name,
            "full_name": manufacturer_name,
        }
    )
    manufacturer.insert(ignore_permissions=True)

    return manufacturer.name


def make_item_display_name(row: NormalizedMedicine) -> str:
    """
    Build the human-facing Item display name.

    Case 1 catalogue rule:
    - Preserve the marketed/source medicine name as the primary identity.
    - Do not replace a marketed name with generic/composition identity.
    - Do not append strength separately when a marketed name exists.
    - Append dosage form only when it is not already present.
    - If the marketed name is unavailable, fall back to the ingredient
      identity and then add strength/dosage form as needed.
    - Combination products remain a single selectable medicine.

    The immutable Item code remains source-ID based (make_item_identity).
    """
    name = _clean(row.medicine_name)

    if name:
        if row.dosage_form and row.dosage_form.lower() not in name.lower():
            name = f"{name} {row.dosage_form}"
        return _clean(name)[:140]

    name = make_ingredient_display_name(row.composition)
    parts = [name] if name else []

    if row.strength_text:
        parts.append(row.strength_text)

    if row.dosage_form:
        parts.append(row.dosage_form)

    return _clean(" ".join(parts))[:140]


def resolve_existing_medication(row, medication_name):
    """Resolve an existing Medication by deterministic or exact clinical identity."""
    existing = frappe.db.exists("Medication", medication_name)
    if existing:
        return frappe.get_doc("Medication", existing)

    if row.is_combination:
        combination_name = _clean(row.composition)[:140]
        if combination_name:
            existing = frappe.db.sql(
                """
                SELECT name
                FROM `tabMedication`
                WHERE is_combination = 1
                  AND (name = %s OR generic_name = %s)
                LIMIT 1
                """,
                (combination_name, combination_name),
                as_dict=True,
            )
            if existing:
                return frappe.get_doc("Medication", existing[0]["name"])
        return None

    ingredient_name = make_ingredient_display_name(row.composition)
    if not ingredient_name or row.strength is None or not row.strength_uom or not row.dosage_form:
        return None

    canonical_name = _clean(
        f"{ingredient_name} {row.strength:g} {row.strength_uom} {row.dosage_form}"
    )[:140]

    existing = frappe.db.exists("Medication", canonical_name)
    if existing:
        return frappe.get_doc("Medication", existing)

    candidates = frappe.db.sql(
        """
        SELECT name
        FROM `tabMedication`
        WHERE strength = %s
          AND strength_uom = %s
          AND dosage_form = %s
          AND is_combination = 0
          AND (
              generic_name = %s
              OR generic_name LIKE %s
              OR name = %s
              OR name LIKE %s
          )
        ORDER BY name
        """,
        (
            row.strength,
            row.strength_uom,
            row.dosage_form,
            ingredient_name,
            f"{ingredient_name}%%",
            ingredient_name,
            f"{ingredient_name}%%",
        ),
        as_dict=True,
    )

    if len(candidates) == 1:
        return frappe.get_doc("Medication", candidates[0]["name"])

    return None


def needs_item_name_repair(existing_item_name: str, item_code: str) -> bool:
    """
    Return True only when an Item still carries the technical placeholder
    display name created by Healthcare's Medication -> Item path
    (item_name == item_code) or an empty name.

    Valid human-readable names are never overwritten, so this decision is
    deterministic and safe to run repeatedly.
    """
    existing = _clean(existing_item_name)
    return not existing or existing == _clean(item_code)


def row_medication_identity_check(
    row: NormalizedMedicine,
    item_name: str,
) -> str | None:
    """
    Validate a candidate Item display name against the Medication identity
    that import_pilot() persists for this row.

    Mirrors the runtime guard used by
    clinify.api.drug_search.get_drug_prescription_defaults():
    item_medication_identity_issue() must return None before a row may be
    accepted, otherwise the medicine would import but never resolve to
    prescription defaults in the doctor workflow.
    """
    medication = SimpleNamespace(
        name=row.medication_identity[:140],
        strength=row.strength,
        strength_uom=row.strength_uom,
        dosage_form=row.dosage_form,
    )
    return item_medication_identity_issue(item_name, medication)


def verify_row_invariants(row: NormalizedMedicine) -> list[str]:
    """
    Pure batch gate for one normalized single-ingredient row.

    Returns human-readable violations; an empty list means the row is safe
    to import.  Combination and review-required rows are excluded, matching
    import_pilot()'s existing behavior.
    """
    if row.review_required or row.is_combination:
        return []

    violations = []

    item_code = row.item_identity
    item_name = make_item_display_name(row)

    if not item_code.upper().startswith("OMDB-"):
        violations.append(
            f"item code '{item_code}' is not a deterministic OMDB identity"
        )

    if not item_name or item_name == item_code:
        violations.append(
            f"item name for '{item_code}' is empty or equals the item code"
        )
        return violations

    identity = parse_item_medicine_identity(item_name)
    if identity["dosage_form"] is None:
        violations.append(
            f"item name '{item_name}' has no recognizable dosage form"
        )
    if identity["strength"] is None and row.strength_uom != "Percent":
        violations.append(
            f"item name '{item_name}' has no recognizable strength"
        )

    identity_issue = row_medication_identity_check(row, item_name)
    if identity_issue:
        violations.append(
            f"item name '{item_name}' fails identity safety: {identity_issue}"
        )

    return violations


def verify_batch_invariants(rows: Iterable[NormalizedMedicine]) -> list[str]:
    """
    Pure batch gate for a normalized batch.  An empty list means every
    importable row satisfies the permanent medicine identity rules.
    """
    violations: list[str] = []
    for row in rows:
        violations.extend(verify_row_invariants(row))
    return violations


def normalize_row(row: dict[str, str]) -> NormalizedMedicine:
    # Support both the current normalized OpenMedsDB schema and the
    # legacy Clinify importer column names.
    # Support the current raw OpenMedsDB schema, the normalized
    # OpenMedsDB schema, and the legacy Clinify importer column names.
    source_id = _clean(
        row.get("slug")
        or row.get("source_id")
        or row.get("Source ID")
    )
    source = _clean(
        row.get("_source_class_file")
        or row.get("source")
        or row.get("Source")
    )
    source_revision = _clean(
        row.get("source_revision")
        or row.get("Source Revision")
    )
    medicine_name = _clean(
        row.get("medicine")
        or row.get("medicine_name")
        or row.get("Medicine Name")
    )
    composition = _clean(
        row.get("salt_composition")
        or row.get("ingredient_composition")
        or row.get("Generic/Composition")
    )
    source_dosage_form = _clean(
        row.get("dosage_form")
        or row.get("Dosage Form")
    )
    dosage_form = DOSAGE_FORM_MAP.get(source_dosage_form.lower())
    manufacturer = _clean(
        row.get("manufacturer")
        or row.get("Manufacturer")
    )
    pack = _clean(
        row.get("pack_label")
        or row.get("Pack")
    )
    prescription_required = _clean(
        row.get("prescription_required")
        or row.get("Prescription Required")
    )

    reasons: list[str] = []

    ingredients = split_ingredient_text(composition)
    ingredient_strengths = parse_ingredient_strengths(composition)
    is_combination = len(ingredients) > 1
    multi_strength = is_multi_strength(composition)

    strength, source_uom = parse_strength(composition)

    # For concentration/IU expressions the complete source unit is retained.
    # normalize_uom() is only applied when the source expression is a simple
    # ERPNext-compatible unit.
    normalized_uom = normalize_uom(source_uom)

    if not source_id:
        reasons.append("missing_source_id")
    if not composition:
        reasons.append("missing_composition")
    if not medicine_name:
        reasons.append("missing_medicine_name")
    if not source_dosage_form:
        reasons.append("missing_dosage_form")
    elif dosage_form is None:
        reasons.append(
            f"unsupported_dosage_form:{source_dosage_form}"
        )

    if source_uom:
        simple_uom = source_uom.lower().strip()
        is_percentage = simple_uom.startswith("%")
        is_iu = simple_uom in {"iu", "i.u."}
        is_concentration = "/" in simple_uom

        if normalized_uom is None and not (
            is_percentage or is_iu or is_concentration
        ):
            reasons.append(f"unknown_strength_uom:{source_uom}")

    if not source_uom:
        reasons.append("strength_not_safely_parsed")

    # Multiple strengths are now structurally represented rather than
    # automatically rejected. They remain reviewable if an ingredient
    # component itself could not be parsed.
    if any(not strength_text for _, strength_text, _ in ingredient_strengths):
        reasons.append("ingredient_strength_not_safely_parsed")

    if is_combination:
        # A combination has no single overall strength. Its individual
        # ingredient strengths remain preserved in ingredient_strengths
        # and in the original composition.
        strength = None
        source_uom = ""
        normalized_uom = None
        strength_text = ""
    else:
        strength_text = (
            f"{strength:g} {source_uom}".strip()
            if strength is not None
            else _clean(source_uom)
        )

    medication_identity = make_medication_identity(
        composition,
        strength_text,
        dosage_form or source_dosage_form,
    )
    item_identity = make_item_identity(source_id)

    normalized = NormalizedMedicine(
        source_id=source_id,
        source=source,
        source_revision=source_revision,
        medicine_name=medicine_name,
        composition=composition,
        dosage_form=dosage_form,
        manufacturer=manufacturer,
        pack=pack,
        prescription_required=prescription_required,
        ingredient_text=" | ".join(ingredients),
        strength_text=strength_text,
        strength=strength,
        strength_uom_source=source_uom,
        strength_uom=normalized_uom,
        ingredient_strengths=ingredient_strengths,
        is_combination=is_combination,
        is_multi_strength=multi_strength,
        review_required=bool(reasons),
        review_reasons=tuple(reasons),
        medication_identity=medication_identity,
        item_identity=item_identity,
    )

    # Keep the permanent identity validator as the source of truth.
    # Standalone rows that fail the validator become review rows instead
    # of reaching the clean-row preflight gate. Combination rows remain
    # exempt by the validator's existing rules.
    if not normalized.review_required and not normalized.is_combination:
        identity_violations = verify_row_invariants(normalized)
        if identity_violations:
            normalized = replace(
                normalized,
                review_required=True,
                review_reasons=tuple(
                    list(normalized.review_reasons) + [
                        f"identity_validation:{violation}"
                        for violation in identity_violations
                    ]
                ),
            )

    return normalized


def load_csv(path: str | Path) -> list[dict[str, str]]:
    path = Path(path).expanduser()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_csv(path: str | Path) -> list[NormalizedMedicine]:
    return [normalize_row(row) for row in load_csv(path)]


def dry_run(
    path: str | Path,
    source_revision: str = "",
) -> DryRunReport:
    """
    Normalize and report a source file.

    IMPORTANT:
    This function performs no Frappe/database operations.
    """
    rows = normalize_csv(path)
    report = DryRunReport(
        source_file=str(Path(path).expanduser()),
        source_revision=source_revision,
        total_rows=len(rows),
        rows=rows,
    )

    source_ids = [row.source_id for row in rows]
    report.unique_source_ids = len(set(source_ids))
    report.duplicate_source_ids = len(source_ids) - report.unique_source_ids

    medication_ids = set()
    item_ids = set()

    for row in rows:
        if row.review_required:
            report.review_rows += 1
        else:
            report.valid_rows += 1

        if row.is_combination:
            report.combinations += 1
        else:
            report.single_ingredient += 1

        if row.is_multi_strength:
            report.multi_strength += 1

        if any(reason.startswith("unknown_strength_uom:") for reason in row.review_reasons):
            report.unknown_uom += 1

        if not row.dosage_form:
            report.unsupported_dosage_form += 1

        medication_ids.add(row.medication_identity)
        item_ids.add(row.item_identity)

    report.future_medications = len(medication_ids)
    report.future_items = len(item_ids)
    report.future_links = len(item_ids)

    return report


def _find_technical_item_names(item_codes: list[str]) -> list[str]:
    """
    Batch gate: return the Item codes whose display name still equals the
    technical item code (item_name == name) -- the signature of the
    Healthcare Medication -> Item placeholder name.

    Only used after a write run; the local frappe import keeps this module
    import-safe for source-only tests.
    """
    import frappe  # local import keeps this module import-safe without Frappe

    offenders: list[str] = []
    unique_codes = list(dict.fromkeys(item_codes))
    chunk_size = 500

    for index in range(0, len(unique_codes), chunk_size):
        chunk = tuple(unique_codes[index : index + chunk_size])
        rows = frappe.db.sql(
            """
            SELECT name
            FROM `tabItem`
            WHERE name IN %(chunk)s
              AND item_name = name
            """,
            {"chunk": chunk},
        )
        offenders.extend(row[0] for row in rows)

    return offenders


def import_pilot(
    path: str | Path,
    *,
    write: bool = False,
    limit: int | None = None,
) -> dict[str, object]:
    """
    Import clean OpenMedsDB rows into Healthcare Medication.

    SAFETY:
    - write=False is the default and performs no database writes.
    - review-required rows are never imported.
    - existing records are never deleted or disabled.
    - Item creation is delegated to Healthcare's Medication controller.
    - every imported Item keeps its deterministic OMDB item_code and must
      end with a human-readable, strength-specific item_name; technical
      placeholder names (item_name == item_code) are repaired in place and
      valid names are never overwritten.
    - every imported Medication carries default prescription dosage
      "0-0-0" and duration "0 Day"; the write run refuses to start when
      the matching Prescription masters are missing.
    - zero-rate Item Prices created by Healthcare for this catalogue import
      are removed immediately; medicine selling-price functionality remains
      deferred.
    """
    rows = normalize_csv(path)
    if limit is not None:
        rows = rows[:limit]

    review_rows = [row for row in rows if row.review_required]

    # Standalone medicines are the source of truth for component
    # Medications used by combination medicines.  Import them first so
    # combinations can resolve their component Medication identities
    # deterministically, regardless of CSV ordering.
    standalone_rows = [
        row for row in rows
        if not row.review_required and not row.is_combination
    ]
    combination_rows = [
        row for row in rows
        if not row.review_required and row.is_combination
    ]
    clean_rows = standalone_rows + combination_rows

    result = {
        "source_file": str(Path(path).expanduser()),
        "total_rows": len(rows),
        "clean_rows": len(clean_rows),
        "review_rows": len(review_rows),
        "created_medications": 0,
        "created_items": 0,
        "created_links": 0,
        "repaired_items": 0,
        "skipped_existing": 0,
        "preflight_issues": [],
        "technical_item_names": [],
        "errors": [],
        "review_source_ids": [row.source_id for row in review_rows],
        "write": write,
    }

    # Batch gate: every importable row must already produce a valid,
    # human-readable, strength-specific Item Name that passes the
    # Item/Medication identity safety check.  Drift fails fast, before any
    # database writes.
    preflight_issues = verify_batch_invariants(clean_rows)
    result["preflight_issues"] = preflight_issues

    if not write:
        return result

    if preflight_issues:
        raise RuntimeError(
            "OpenMedsDB batch preflight failed with "
            f"{len(preflight_issues)} issue(s); first issues: "
            + "; ".join(preflight_issues[:10])
        )

    import frappe

    price_list = frappe.db.get_single_value(
        "Selling Settings", "selling_price_list"
    ) or "Standard Selling"

    item_group = "Drug"
    stock_uom = "Nos"

    if not frappe.db.exists("Item Group", item_group):
        raise RuntimeError(
            f"Required Item Group does not exist: {item_group}"
        )

    if not frappe.db.exists("UOM", stock_uom):
        raise RuntimeError(
            f"Required UOM does not exist: {stock_uom}"
        )

    if not frappe.db.exists("Prescription Dosage", DEFAULT_PRESCRIPTION_DOSAGE):
        raise RuntimeError(
            f"Required Prescription Dosage does not exist: {DEFAULT_PRESCRIPTION_DOSAGE}"
        )

    if not frappe.db.exists("Prescription Duration", DEFAULT_PRESCRIPTION_DURATION):
        raise RuntimeError(
            f"Required Prescription Duration does not exist: {DEFAULT_PRESCRIPTION_DURATION}"
        )

    for row in clean_rows:
        try:
            medication_name = row.medication_identity[:140]
            item_code = row.item_identity
            item_name = make_item_display_name(row)

            description = (
                f"{row.medicine_name} | "
                f"{row.composition}"
                + (f" | Source dosage form: {row.dosage_form}"
                   if row.dosage_form else "")
                + (f" | {row.pack}" if row.pack else "")
                + (f" | Manufacturer: {row.manufacturer}"
                   if row.manufacturer else "")
            ).strip(" |")[:2000]

            manufacturer = resolve_manufacturer(row.manufacturer)

            existing_item = frappe.db.exists("Item", item_code)
            repaired_item = False

            if existing_item:
                item_doc = frappe.get_doc("Item", item_code)

                if needs_item_name_repair(item_doc.item_name, item_code):
                    # Repair the technical display name (item_name ==
                    # item_code) left behind by Healthcare's Medication ->
                    # Item creation or a native Data Import run.  The
                    # immutable item_code is never changed.
                    frappe.db.set_value(
                        "Item",
                        item_code,
                        {
                            "item_name": item_name,
                            "description": (
                                description
                                if not item_doc.description
                                or item_doc.description == item_code
                                else item_doc.description
                            ),
                        },
                    )
                    repaired_item = True
                    result["repaired_items"] += 1
                else:
                    # Idempotent re-run: this source row already has a
                    # human-readable Item.  Never overwrite it.
                    result["skipped_existing"] += 1
                    continue

            existing_medication = resolve_existing_medication(
                row, medication_name
            )

            print(
                f"RESOLVER TRACE: item={item_code} "
                f"item_name={frappe.db.get_value('Item', item_code, 'item_name')} "
                f"medication={getattr(existing_medication, 'name', None)}"
            )

            if existing_medication:
                medication = existing_medication

                linked_item_codes = {
                    d.item_code
                    for d in medication.linked_items
                    if d.item_code
                }

                if item_code in linked_item_codes:
                    print(
                        f"LINKED TRACE: item={item_code} "
                        f"linked=True "
                        f"item_name={frappe.db.get_value('Item', item_code, 'item_name')}"
                    )

                    if needs_item_name_repair(
                        frappe.db.get_value("Item", item_code, "item_name"),
                        item_code,
                    ):
                        frappe.db.set_value(
                            "Item",
                            item_code,
                            {
                                "item_name": item_name,
                                "description": description,
                            },
                        )
                        print(
                            f"REPAIR TRACE AFTER SET_VALUE: "
                            f"{item_code} -> "
                            f"{frappe.db.get_value('Item', item_code, 'item_name')}"
                        )
                        repaired_item = True
                        result["repaired_items"] += 1

                    if repaired_item:
                        frappe.db.commit()
                        print(
                            f"REPAIR TRACE AFTER COMMIT: "
                            f"{item_code} -> "
                            f"{frappe.db.get_value('Item', item_code, 'item_name')}"
                        )
                    else:
                        result["skipped_existing"] += 1
                    continue

                medication.default_prescription_dosage = (
                    DEFAULT_PRESCRIPTION_DOSAGE
                )
                medication.default_prescription_duration = (
                    DEFAULT_PRESCRIPTION_DURATION
                )
                medication.append(
                    "linked_items",
                    {
                        "item_code": item_code,
                        "item_group": item_group,
                        "stock_uom": stock_uom,
                        "manufacturer": manufacturer,
                        "is_billable": 1,
                        "rate": 0,
                        "description": description,
                    },
                )

                medication.save(ignore_permissions=True)

                # Healthcare synchronization may restore a technical Item name.
                # Re-apply the human-readable OpenMedsDB name after Medication save.
                current_item_name = frappe.db.get_value("Item", item_code, "item_name")
                if needs_item_name_repair(current_item_name, item_code):
                    frappe.db.set_value(
                        "Item",
                        item_code,
                        {
                            "item_name": item_name,
                            "description": description,
                        },
                    )
                    if not repaired_item:
                        result["repaired_items"] += 1
                result["created_links"] += 1

            else:
                # Combination Medications do not have one clinically meaningful
                # aggregate strength. Healthcare nevertheless requires the parent
                # Medication strength fields, so use a neutral technical value.
                # The actual component strengths are stored in `combinations`.
                strength = (
                    row.strength
                    if not row.is_combination
                    else 0
                )
                strength_uom = (
                    row.strength_uom
                    if not row.is_combination
                    else "Unit"
                )

                combination_ingredients = []

                if row.is_combination:
                    for ingredient_name, ingredient_strength_text, ingredient_uom_source in row.ingredient_strengths:
                        if not ingredient_strength_text:
                            raise RuntimeError(
                                f"Cannot import combination {row.source_id}: "
                                f"ingredient strength is missing for {ingredient_name}"
                            )

                        ingredient_uom = normalize_uom(ingredient_uom_source)
                        if not ingredient_uom:
                            raise RuntimeError(
                                f"Cannot import combination {row.source_id}: "
                                f"unsupported ingredient UOM for {ingredient_name}: "
                                f"{ingredient_uom_source}"
                            )

                        ingredient_strength = float(
                            ingredient_strength_text.split()[0]
                        )

                        component_name = frappe.db.get_value(
                            "Medication",
                            {
                                "generic_name": ingredient_name,
                                "strength": ingredient_strength,
                                "strength_uom": ingredient_uom,
                                "dosage_form": row.dosage_form,
                            },
                            "name",
                        )

                        if not component_name:
                            raise RuntimeError(
                                f"Cannot import combination {row.source_id}: "
                                f"component Medication does not exist for "
                                f"{ingredient_name} / "
                                f"{ingredient_strength} {ingredient_uom} / "
                                f"{row.dosage_form}"
                            )

                        combination_ingredients.append(
                            {
                                "medication": component_name,
                                "strength": float(
                                    ingredient_strength_text.split()[0]
                                ),
                                "strength_uom": ingredient_uom,
                            }
                        )

                medication = frappe.get_doc(
                    {
                        "doctype": "Medication",
                        "generic_name": row.composition,
                        "medication_class": MEDICATION_CLASS,
                        "is_combination": 1 if row.is_combination else 0,
                        "strength": strength,
                        "strength_uom": strength_uom,
                        "dosage_form": row.dosage_form,
                        "default_prescription_dosage": DEFAULT_PRESCRIPTION_DOSAGE,
                        "default_prescription_duration": DEFAULT_PRESCRIPTION_DURATION,
                        "disabled": 0,
                        "price_list": price_list,
                        "combinations": combination_ingredients,
                        "linked_items": [
                            {
                                "item_code": item_code,
                                "item_group": item_group,
                                "stock_uom": stock_uom,
                                "manufacturer": manufacturer,
                                "is_billable": 1,
                                "rate": 0,
                                "description": description,
                            }
                        ],
                    }
                )

                medication.insert(ignore_permissions=True)
                result["created_medications"] += 1
                result["created_links"] += 1

            # Healthcare creates the Item during Medication insertion and
            # forces item_name = item_code.  Enforce the human-readable
            # display name in the same transaction, without overwriting a
            # valid name unnecessarily.
            item = frappe.get_doc("Item", item_code)
            if item.item_name != item_name:
                item.item_name = item_name
                if not item.description or item.description == item.item_code:
                    item.description = description
                item.save(ignore_permissions=True)

            # Identity safety: the runtime guard used by
            # get_drug_prescription_defaults() must accept this pairing,
            # otherwise the medicine would import but never resolve to
            # prescription defaults in the doctor workflow.
            identity_issue = None

            if not getattr(medication, "is_combination", 0):
                identity_issue = item_medication_identity_issue(
                    item.item_name, medication
                )

            if identity_issue:
                raise RuntimeError(
                    f"Item/Medication identity safety check failed for "
                    f"{item_code}: {identity_issue}"
                )

            # Defaults gate: every Medication this importer writes must
            # carry the required prescription defaults.
            if (
                medication.default_prescription_dosage
                != DEFAULT_PRESCRIPTION_DOSAGE
                or medication.default_prescription_duration
                != DEFAULT_PRESCRIPTION_DURATION
            ):
                raise RuntimeError(
                    f"Medication '{medication.name}' does not carry the "
                    "required prescription defaults "
                    f"({DEFAULT_PRESCRIPTION_DOSAGE} / "
                    f"{DEFAULT_PRESCRIPTION_DURATION})."
                )

            zero_price = frappe.db.exists(
                "Item Price",
                {
                    "item_code": item_code,
                    "price_list": price_list,
                    "price_list_rate": 0,
                },
            )

            if zero_price:
                frappe.delete_doc(
                    "Item Price",
                    zero_price,
                    ignore_permissions=True,
                    force=True,
                )

            frappe.db.commit()
            if not existing_item:
                result["created_items"] += 1

        except Exception as exc:
            frappe.db.rollback()
            result["errors"].append(
                {
                    "source_id": row.source_id,
                    "medicine_name": row.medicine_name,
                    "error": str(exc),
                }
            )

    # Batch gate (validation #1): no imported OMDB Item may retain the
    # technical placeholder display name (item_name == item_code).
    technical_item_names = _find_technical_item_names(
        [row.item_identity for row in clean_rows]
    )
    result["technical_item_names"] = technical_item_names
    if technical_item_names:
        raise RuntimeError(
            "Batch gate failed: technical Item Names remain for "
            f"{len(technical_item_names)} item(s); first items: "
            + ", ".join(technical_item_names[:10])
        )

    return result

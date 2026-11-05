import re
from decimal import Decimal, InvalidOperation


_DOSAGE_FORMS = {
    "tablet": "tablet",
    "tablets": "tablet",
    "tab": "tablet",
    "capsule": "capsule",
    "capsules": "capsule",
    "cap": "capsule",
    "syrup": "syrup",
    "suspension": "suspension",
    "solution": "solution",
    "drops": "drops",
    "injection": "injection",
    "cream": "cream",
    "ointment": "ointment",
    "gel": "gel",
    "inhaler": "inhaler",
}

# Release / presentation suffixes that may follow the clinical dosage form.
_DOSAGE_FORM_SUFFIXES = {
    "sr",
    "er",
    "xr",
    "cr",
    "mr",
    "pr",
    "dr",
    "ir",
    "od",
    "cd",
    "xl",
    "la",
    "md",
    "dt",
}

# Only match a strength when it is not the denominator of a concentration.
_STRENGTH_PATTERN = re.compile(
    r"(?<![\w/])(?P<strength>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>micrograms?|mcg|milligrams?|mg|grams?|g|gm|ml|iu|units?)?"
    r"(?!\s*/)(?=\s*$)",
    re.IGNORECASE,
)

_PERCENT_STRENGTH_PATTERN = re.compile(
    r"(?<![\w/])(?P<strength>\d+(?:\.\d+)?)\s*%\s*(?P<unit>w/v|v/v|w/w)?",
    re.IGNORECASE,
)
_UNIT_ALIASES = {
    "microgram": "microgram",
    "micrograms": "microgram",
    "mcg": "microgram",
    "milligram": "milligram",
    "milligrams": "milligram",
    "mg": "milligram",
    "gram": "gram",
    "grams": "gram",
    "g": "gram",
    "gm": "gram",
    "ml": "ml",
    "iu": "international unit",
    "international unit": "international unit",
    "unit": "unit",
    "units": "unit",
}


def parse_item_medicine_identity(item_name):
    """Extract only unambiguous strength/form metadata from the Item display name."""
    remaining = (item_name or "").strip()
    identity = {"strength": None, "strength_uom": None, "dosage_form": None}

    # First remove a recognized dosage-form suffix such as "SR" after "Tablet".
    for suffix in sorted(_DOSAGE_FORM_SUFFIXES, key=len, reverse=True):
        suffix_match = re.search(
            rf"\b{re.escape(suffix)}\s*$",
            remaining,
            re.IGNORECASE,
        )
        if suffix_match:
            remaining = remaining[: suffix_match.start()].rstrip()
            break

    for label, canonical in sorted(_DOSAGE_FORMS.items(), key=lambda pair: -len(pair[0])):
        match = re.search(rf"\b{re.escape(label)}\s*$", remaining, re.IGNORECASE)
        if match:
            identity["dosage_form"] = canonical
            remaining = remaining[: match.start()].rstrip()
            break

    # A release suffix may appear immediately before the dosage form,
    # e.g. "Bigun 500 SR Tablet". Remove that suffix after removing the
    # dosage form so the existing strength parser can recognize 500.
    for suffix in sorted(_DOSAGE_FORM_SUFFIXES, key=len, reverse=True):
        suffix_match = re.search(
            rf"\b{re.escape(suffix)}\s*$",
            remaining,
            re.IGNORECASE,
        )
        if suffix_match:
            remaining = remaining[: suffix_match.start()].rstrip()
            break

    # Some marketed names put the dosage form before the strength,
    # e.g. "Agbit Tablet 0.2mg". Extract the trailing strength first,
    # then recognize a dosage form immediately before it.
    trailing_strength_match = re.search(
        r"(?<![\w/])(?P<strength>\d+(?:\.\d+)?)\s*"
        r"(?P<unit>micrograms?|mcg|milligrams?|mg|grams?|g|iu|units?)?"
        r"\s*$",
        remaining,
        re.IGNORECASE,
    )

    if trailing_strength_match:
        identity["strength"] = Decimal(str(trailing_strength_match.group("strength")))
        unit = trailing_strength_match.group("unit")
        if unit:
            identity["strength_uom"] = _UNIT_ALIASES[unit.casefold()]

        before_strength = remaining[: trailing_strength_match.start()].rstrip()

        for label, canonical in sorted(_DOSAGE_FORMS.items(), key=lambda pair: -len(pair[0])):
            match = re.search(
                rf"\b{re.escape(label)}\s*$",
                before_strength,
                re.IGNORECASE,
            )
            if match:
                identity["dosage_form"] = canonical
                break

    # Concentration forms such as "100 mg/5ml" carry the clinical strength
    # in the numerator. The denominator must never be treated as strength.
    concentration_match = re.search(
        r"(?<![\w/])(?P<strength>\d+(?:\.\d+)?)\s*"
        r"(?P<unit>micrograms?|mcg|milligrams?|mg|grams?|g|iu|units?)"
        r"\s*/\s*\d+(?:\.\d+)?\s*(?:ml|millilit(?:er|re)s?|l)\b",
        remaining,
        re.IGNORECASE,
    )
    if concentration_match:
        identity["strength"] = Decimal(str(concentration_match.group("strength")))
        identity["strength_uom"] = _UNIT_ALIASES[
            concentration_match.group("unit").casefold()
        ]
        return identity

    # Percentage concentrations such as "7 % w/v" are intentionally not
    # mapped to the scalar Medication.strength field.
    if _PERCENT_STRENGTH_PATTERN.search(remaining):
        return identity

    strength_match = _STRENGTH_PATTERN.search(remaining)
    if strength_match:
        identity["strength"] = Decimal(strength_match.group("strength"))
        unit = strength_match.group("unit")
        if unit:
            identity["strength_uom"] = _UNIT_ALIASES[unit.casefold()]

    return identity


def item_medication_identity_issue(item_name, medication):
    """Return an explanation when an Item cannot be proven to match a Medication."""
    identity = parse_item_medicine_identity(item_name)
    checked_fields = []

    # Combination Medications have multiple clinical strengths embedded in
    # their identity. Their scalar Medication.strength field is not comparable
    # to the individual strength(s) printed in the Item name.
    is_combination = bool(getattr(medication, "is_combination", False))

    if identity["strength"] is not None and not is_combination:
        checked_fields.append("strength")
        try:
            medication_strength = Decimal(str(medication.strength))
        except (AttributeError, InvalidOperation, TypeError):
            return "Medication strength is missing or invalid."
        if medication_strength != identity["strength"]:
            return (
                f"Item name declares strength {identity['strength']}, but Medication "
                f"'{medication.name}' has strength {medication_strength}."
            )

    if identity["strength_uom"] is not None and not is_combination:
        checked_fields.append("strength unit")
        medication_unit = _UNIT_ALIASES.get(
            str(getattr(medication, "strength_uom", "")).strip().casefold(),
            str(getattr(medication, "strength_uom", "")).strip().casefold(),
        )
        if medication_unit != identity["strength_uom"]:
            return (
                f"Item name declares strength unit {identity['strength_uom']}, but "
                f"Medication '{medication.name}' has unit {medication_unit or 'blank'}."
            )

    if identity["dosage_form"] is not None:
        checked_fields.append("dosage form")
        medication_form = str(getattr(medication, "dosage_form", "") or "").strip().casefold()
        medication_form = _DOSAGE_FORMS.get(medication_form, medication_form)
        if medication_form != identity["dosage_form"]:
            return (
                f"Item name declares dosage form {identity['dosage_form']}, but Medication "
                f"'{medication.name}' has form {medication_form or 'blank'}."
            )

    if not checked_fields:
        return "Item name does not state a recognizable strength or dosage form."

    return None


def validate_medicine_source_batch(records):
    """Validate source rows before any importer or synchronizer writes them."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("Medicine source batch must be a non-empty list.")

    by_generic_name = {}
    required_fields = ("generic_name", "strength", "strength_uom", "dosage_form")

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Medicine source row {index + 1} must be an object.")

        missing = [
            field for field in required_fields
            if record.get(field) is None or str(record.get(field)).strip() == ""
        ]
        if missing:
            raise ValueError(
                f"Medicine source row {index + 1} is missing: {', '.join(missing)}."
            )

        try:
            strength = Decimal(str(record["strength"]))
        except (InvalidOperation, TypeError):
            raise ValueError(f"Medicine source row {index + 1} has invalid strength.") from None
        if not strength.is_finite() or strength <= 0:
            raise ValueError(f"Medicine source row {index + 1} has invalid strength.")

        generic_name = " ".join(str(record["generic_name"]).split()).casefold()
        identity = (
            strength,
            " ".join(str(record["strength_uom"]).split()).casefold(),
            " ".join(str(record["dosage_form"]).split()).casefold(),
        )
        previous = by_generic_name.get(generic_name)
        if previous is not None and previous != identity:
            raise ValueError(
                f"The current Medication schema cannot represent multiple strengths or "
                f"dosage forms for generic name '{record['generic_name']}'."
            )
        by_generic_name[generic_name] = identity

    return tuple(dict(record) for record in records)
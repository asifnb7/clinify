import hashlib
import json
import logging
import os
import re
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Protocol
from urllib.parse import urlsplit

import frappe
import requests
from frappe.utils import now_datetime


_LOGGER = logging.getLogger(__name__)
CLINIFY_CATALOGUE_SYNC_ROLE = "Clinify Catalogue Sync"
_CATALOGUE_REVISION_PATTERN = re.compile(r"^\d{20}$")
_PRODUCT_ID_PATTERN = re.compile(r"^CLM-[A-Z0-9][A-Z0-9_-]{2,63}$")
_TENANT_SITE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]*$")
_CANONICAL_TENANT_SITE_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$"
)
_PRODUCT_FIELDS = (
    "central_product_id",
    "ingredient_name",
    "composition",
    "medicine_name",
    "strength",
    "strength_uom",
    "dosage_form",
    "manufacturer",
    "pack_label",
    "source_mrp",
    "source_selling_price",
    "prescription_required",
    "identity_hash",
    "clinical_identity_hash",
    "source_provider",
    "source_identifier",
    "source_revision",
    "source_updated_at",
    "is_active",
)


_PROJECTION_FIELDS = (
    "central_product_id",
    "ingredient_name",
    "composition",
    "medicine_name",
    "strength",
    "strength_uom",
    "dosage_form",
    "manufacturer",
    "pack_label",
    "source_mrp",
    "source_selling_price",
    "prescription_required",
    "clinical_identity_hash",
    "source_provider",
    "source_identifier",
    "source_revision",
    "source_updated_at",
    "is_active",
)
_MEDICINE_ITEM_FIELDS = (
    "item_name",
    "item_group",
    "disabled",
    "is_stock_item",
    "is_sales_item",
    "stock_uom",
    "description",
)
_MEDICATION_FIELDS = (
    "generic_name",
    "medication_class",
    "strength",
    "strength_uom",
    "dosage_form",
    "disabled",
    "is_combination",
    "default_prescription_dosage",
    "default_prescription_duration",
    "price_list",
)
_MEDICINE_ITEM_SYNC_BATCH_SIZE = 100


class TenantProjectionTransport(Protocol):
    """Authenticated transport that applies one tenant batch atomically."""

    def apply_projection_batch_atomically(
        self,
        tenant_site: str,
        snapshot_manifest: Mapping,
        products: tuple[dict, ...],
    ) -> Mapping: ...


class CatalogueSyncStateStore(Protocol):
    """Control-site persistence for attempt and last-success metadata."""

    def record_attempt(
        self,
        tenant_site: str,
        catalogue_revision: str,
        snapshot_digest: str = "",
    ) -> None: ...

    def record_failure(
        self,
        tenant_site: str,
        catalogue_revision: str,
        error_code: str,
        snapshot_digest: str = "",
    ) -> None: ...

    def record_success(
        self,
        tenant_site: str,
        catalogue_revision: str,
        counts: Mapping,
        snapshot_digest: str = "",
    ) -> None: ...


class TenantSyncCredentialProvider(Protocol):
    """Retrieve tenant API credentials from deployment-managed secret storage."""

    def get_api_credentials(self, tenant_site: str) -> tuple[str, str]: ...


def _canonical_tenant_site(tenant_site):
    if not isinstance(tenant_site, str):
        raise ValueError("Tenant site identifier must be text.")

    canonical_site = tenant_site.strip().lower()
    if (
        not canonical_site
        or len(canonical_site) > 253
        or not _CANONICAL_TENANT_SITE_PATTERN.fullmatch(canonical_site)
    ):
        raise ValueError("Tenant site identifier is invalid.")
    return canonical_site


def tenant_sync_credential_environment_prefix(tenant_site):
    """Build the credential prefix from a validated canonical site identifier."""
    canonical_site = _canonical_tenant_site(tenant_site)

    site_digest = hashlib.sha256(canonical_site.encode("ascii")).hexdigest().upper()
    return f"CLINIFY_TENANT_SYNC_{site_digest}"


class EnvironmentTenantSyncCredentialProvider:
    """Read per-tenant Frappe API credentials from process environment only."""

    @staticmethod
    def _prefix(tenant_site):
        return tenant_sync_credential_environment_prefix(tenant_site)

    def get_api_credentials(self, tenant_site):
        prefix = self._prefix(tenant_site)
        api_key = os.environ.get(f"{prefix}_API_KEY")
        api_secret = os.environ.get(f"{prefix}_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError("Tenant catalogue credentials are not configured.")
        return api_key, api_secret


class FrappeApiTokenTenantTransport:
    """Push projection batches over authenticated Frappe HTTPS APIs."""

    def __init__(self, credential_provider=None, http_session=None, timeout=20):
        self.credential_provider = (
            credential_provider or EnvironmentTenantSyncCredentialProvider()
        )
        self.http_session = (
            http_session if http_session is not None else requests.Session()
        )
        self.timeout = timeout
        self._closed = False

    def close(self):
        if not self._closed:
            self._closed = True
            self.http_session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def apply_projection_batch_atomically(
        self,
        tenant_site,
        snapshot_manifest,
        products,
    ):
        tenant, endpoint = _tenant_sync_endpoint(tenant_site)
        api_key, api_secret = self.credential_provider.get_api_credentials(tenant_site)
        if not api_key or not api_secret:
            raise RuntimeError("Tenant catalogue credentials are not configured.")

        payload = {
            "tenant_site": tenant.site_name,
            "control_site": configured_control_site(),
            "snapshot_manifest": dict(snapshot_manifest),
        }
        if isinstance(products, Mapping) and products.get("catalogue_type") == (
            "drug_item_catalogue_v1"
        ):
            payload["catalogue"] = dict(products)
        else:
            payload["products"] = [dict(product) for product in products]

        response = self.http_session.post(
            endpoint,
            headers={
                "Authorization": f"token {api_key}:{api_secret}",
                "Accept": "application/json",
            },
            json=payload,
            timeout=self.timeout,
            verify=True,
            allow_redirects=False,
        )
        if response.status_code != 200:
            raise RuntimeError("Tenant catalogue endpoint rejected synchronization.")

        try:
            body = response.json()
            result = body.get("message") if isinstance(body, Mapping) else None
        except (ValueError, AttributeError):
            result = None
        if not isinstance(result, Mapping):
            raise RuntimeError("Tenant catalogue endpoint returned an invalid response.")
        return result

class FrappeCatalogueSyncStateStore:
    """Persist sync attempts and successful revisions on the current control site."""

    def record_attempt(
        self,
        tenant_site: str,
        catalogue_revision: str,
        snapshot_digest: str = "",
    ) -> None:
        doc = self._get_doc(tenant_site)
        doc.last_attempted_at = now_datetime()
        doc.last_attempted_revision = catalogue_revision
        doc.last_attempted_digest = snapshot_digest
        doc.last_attempt_status = "In Progress"
        doc.last_error_code = ""
        self._save(doc)

    def record_failure(
        self,
        tenant_site: str,
        catalogue_revision: str,
        error_code: str,
        snapshot_digest: str = "",
    ) -> None:
        doc = self._get_doc(tenant_site)
        doc.last_attempted_revision = catalogue_revision
        if snapshot_digest:
            doc.last_attempted_digest = snapshot_digest
        doc.last_attempt_status = "Failed"
        doc.last_error_code = error_code
        self._save(doc)

    def record_success(
        self,
        tenant_site: str,
        catalogue_revision: str,
        counts: Mapping,
        snapshot_digest: str = "",
    ) -> None:
        doc = self._get_doc(tenant_site)
        doc.last_attempted_revision = catalogue_revision
        doc.last_attempt_status = "Succeeded"
        doc.last_error_code = ""
        doc.last_successful_at = now_datetime()
        doc.last_successful_revision = catalogue_revision
        doc.last_successful_digest = snapshot_digest
        doc.last_created_count = counts["created"]
        doc.last_updated_count = counts["updated"]
        doc.last_skipped_count = counts["skipped"]
        self._save(doc)

    @staticmethod
    def _get_doc(tenant_site):
        if frappe.db.exists("Clinify Medicine Sync State", tenant_site):
            doc = frappe.get_doc("Clinify Medicine Sync State", tenant_site)
        else:
            doc = frappe.get_doc(
                {
                    "doctype": "Clinify Medicine Sync State",
                    "tenant_site": tenant_site,
                }
            )
        doc.flags.clinify_catalogue_state_update = True
        return doc

    @staticmethod
    def _save(doc):
        if doc.is_new():
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)


def configured_control_site():
    """Resolve the configured Clinify control site; never guess a production site."""
    config = frappe.conf
    configured = (
        config.get("clinify_control_site")
        or config.get("CLINIFY_CONTROL_SITE")
    )
    if not configured:
        try:
            from clinify.saas.sso import _control_site

            configured = _control_site()
        except RuntimeError:
            configured = None

    configured = str(configured or "").strip().lower()
    if not configured:
        frappe.throw("Clinify control site is not configured.")
    return configured


def require_control_site_admin():
    """Require an authenticated System Manager on the configured control site."""
    if frappe.session.user == "Guest":
        frappe.throw("Authentication is required for central catalogue administration.")

    frappe.only_for("System Manager")
    current_site = str(frappe.local.site or "").strip().lower()
    if current_site != configured_control_site():
        frappe.throw("Central medicine catalogue administration is control-site only.")
    return current_site


def _tenant_sync_endpoint(tenant_site):
    """Resolve a tenant target only when its origin is infrastructure-allowlisted."""
    from clinify.saas.sso import _local_development_enabled, _tenant_domain

    tenant_site = _canonical_tenant_site(tenant_site)
    tenant = frappe.db.get_value(
        "Clinify Tenant",
        {"site_name": tenant_site},
        [
            "name",
            "site_name",
            "domain",
            "enabled",
            "clinic_status",
            "provisioning_status",
        ],
        as_dict=True,
    )
    if not tenant:
        raise ValueError("Tenant is not registered on the control site.")
    site_name = str(tenant.site_name or "").strip().lower()
    domain = _tenant_domain(tenant.domain)
    if (
        site_name != tenant_site
        or site_name != domain
        or not tenant.enabled
        or tenant.clinic_status != "Active"
        or tenant.provisioning_status != "Ready"
    ):
        raise ValueError("Tenant catalogue destination is not eligible.")

    raw_origins = os.environ.get("CLINIFY_TENANT_SYNC_ALLOWED_ORIGINS")
    if not raw_origins:
        raise ValueError("Tenant synchronization origins are not configured.")

    def unique_origin_entries(pairs):
        origins = {}
        for site, origin in pairs:
            if site in origins:
                raise ValueError("Tenant synchronization origin registry is ambiguous.")
            origins[site] = origin
        return origins

    try:
        allowed_origins = json.loads(raw_origins, object_pairs_hook=unique_origin_entries)
    except (TypeError, ValueError):
        raise ValueError("Tenant synchronization origin registry is malformed.") from None
    if not isinstance(allowed_origins, dict):
        raise ValueError("Tenant synchronization origin registry is malformed.")

    origin_value = allowed_origins.get(tenant_site)
    if not isinstance(origin_value, str):
        raise ValueError("Tenant has no infrastructure-approved synchronization origin.")
    parsed_origin = urlsplit(origin_value.strip())
    local_http = _local_development_enabled() and domain.endswith(".localhost")
    expected_scheme = "http" if local_http else "https"
    if (
        parsed_origin.scheme.lower() != expected_scheme
        or not parsed_origin.netloc
        or parsed_origin.username
        or parsed_origin.password
        or parsed_origin.path not in ("", "/")
        or parsed_origin.query
        or parsed_origin.fragment
        or (parsed_origin.hostname or "").lower() != domain
        or parsed_origin.port not in (None, 443 if expected_scheme == "https" else 80)
    ):
        raise ValueError("Tenant synchronization origin is invalid or does not match its registry record.")

    origin = f"{expected_scheme}://{domain}"
    endpoint = (
        origin
        + "/api/method/clinify.medicine_catalogue_sync.apply_tenant_projection_batch"
    )
    return tenant, endpoint


def normalize_product_record(record):
    """Validate and normalize one central product into a transport-safe mapping."""
    if hasattr(record, "as_dict"):
        record = record.as_dict()
    if not isinstance(record, Mapping):
        raise ValueError("Catalogue product must be an object.")

    product_id = str(record.get("central_product_id") or "").strip().upper()
    if not _PRODUCT_ID_PATTERN.fullmatch(product_id):
        raise ValueError("Catalogue product has an invalid Clinify product identifier.")

    ingredient = _required_text(record.get("ingredient_name"), "ingredient", product_id)
    strength_unit = _optional_text(record.get("strength_uom"))
    if len(strength_unit) > 140:
        raise ValueError(f"Catalogue product {product_id} has an invalid strength unit.")

    dosage_form = _required_text(record.get("dosage_form"), "dosage form", product_id)

    raw_strength = record.get("strength")
    if raw_strength in (None, ""):
        normalized_strength = ""
    else:
        try:
            strength = Decimal(str(raw_strength))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(f"Catalogue product {product_id} has an invalid strength.") from None
        if not strength.is_finite() or strength <= 0:
            raise ValueError(f"Catalogue product {product_id} has an invalid strength.")
        normalized_strength = format(strength.normalize(), "f")
        if len(normalized_strength) > 24:
            raise ValueError(f"Catalogue product {product_id} has an invalid strength.")

    raw_active = record.get("is_active", 1)
    if raw_active in (True, 1, "1"):
        is_active = 1
    elif raw_active in (False, 0, "0"):
        is_active = 0
    else:
        raise ValueError(f"Catalogue product {product_id} has an invalid active state.")

    composition = _optional_text(record.get("composition"))
    medicine_name = _optional_text(record.get("medicine_name"))
    manufacturer = _optional_text(record.get("manufacturer"))
    pack_label = _optional_text(record.get("pack_label"))
    prescription_required = _optional_text(record.get("prescription_required"))

    if len(composition) > 2000:
        raise ValueError(
            f"Catalogue product {product_id} has an invalid composition."
        )

    for fieldname, value in (
        ("medicine_name", medicine_name),
        ("manufacturer", manufacturer),
        ("pack_label", pack_label),
        ("prescription_required", prescription_required),
    ):
        if len(value) > 140:
            raise ValueError(f"Catalogue product {product_id} has an invalid {fieldname}.")

    source_mrp = _optional_nonnegative_decimal(
        record.get("source_mrp"), "source MRP", product_id
    )
    source_selling_price = _optional_nonnegative_decimal(
        record.get("source_selling_price"), "source selling price", product_id
    )

    source_provider = _optional_text(record.get("source_provider"))
    source_identifier = _optional_text(record.get("source_identifier"))
    source_revision = _optional_text(record.get("source_revision"))
    if source_identifier and not source_provider:
        raise ValueError(f"Catalogue product {product_id} has a source ID without a provider.")
    for fieldname, value in (
        ("source_provider", source_provider),
        ("source_identifier", source_identifier),
        ("source_revision", source_revision),
    ):
        if len(value) > 140:
            raise ValueError(f"Catalogue product {product_id} has an invalid {fieldname}.")

    product = {
        "central_product_id": product_id,
        "ingredient_name": ingredient,
        "composition": composition,
        "medicine_name": medicine_name,
        "strength": normalized_strength,
        "strength_uom": strength_unit,
        "dosage_form": dosage_form,
        "manufacturer": manufacturer,
        "pack_label": pack_label,
        "source_mrp": source_mrp,
        "source_selling_price": source_selling_price,
        "prescription_required": prescription_required,
        "source_provider": source_provider,
        "source_identifier": source_identifier,
        "source_revision": source_revision,
        "source_updated_at": _isoformat(record.get("source_updated_at")),
        "is_active": is_active,
    }

    product["clinical_identity_key"] = clinical_identity_key(product)
    product["identity_key"] = commercial_identity_key(product)
    product["clinical_identity_hash"] = product["clinical_identity_key"]
    product["identity_hash"] = product["identity_key"]

    return product


def _required_text(value, label, product_id):
    text = " ".join(str(value or "").split())
    if not text or len(text) > 140:
        raise ValueError(f"Catalogue product {product_id} has an invalid {label}.")
    return text


def _optional_text(value):
    if value in (None, ""):
        return ""
    return " ".join(str(value).split())


def _optional_nonnegative_decimal(value, label, product_id):
    if value in (None, ""):
        return ""

    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(
            f"Catalogue product {product_id} has an invalid {label}."
        ) from None

    if not number.is_finite() or number < 0:
        raise ValueError(
            f"Catalogue product {product_id} has an invalid {label}."
        )

    normalized = format(number.normalize(), "f")
    if len(normalized) > 24:
        raise ValueError(
            f"Catalogue product {product_id} has an invalid {label}."
        )

    return normalized


def _isoformat(value):
    if value in (None, ""):
        return ""
    if hasattr(value, "isoformat"):
        value = value.isoformat()
    text = str(value).strip()
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Catalogue product has an invalid source update timestamp.") from None
    return text


def _identity_strength(value):
    """Return a canonical strength component, preserving blank as blank."""
    if value in (None, ""):
        return ""
    try:
        return format(Decimal(str(value)).normalize(), "f")
    except (InvalidOperation, TypeError, ValueError):
        return " ".join(str(value).split()).casefold()


def clinical_identity_key(product):
    """Hash clinical composition, optional strength/unit, and dosage form."""
    identity = (
        " ".join(str(product["ingredient_name"]).split()).casefold(),
        _identity_strength(product.get("strength")),
        " ".join(str(product.get("strength_uom") or "").split()).casefold(),
        " ".join(str(product["dosage_form"]).split()).casefold(),
    )
    payload = "\x1f".join(identity).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def commercial_identity_key(product):
    """Hash the complete normalized commercial product identity."""
    identity = (
        " ".join(str(product["medicine_name"]).split()).casefold(),
        " ".join(str(product["ingredient_name"]).split()).casefold(),
        _identity_strength(product.get("strength")),
        " ".join(str(product.get("strength_uom") or "").split()).casefold(),
        " ".join(str(product["dosage_form"]).split()).casefold(),
        " ".join(str(product["manufacturer"]).split()).casefold(),
        " ".join(str(product["pack_label"]).split()).casefold(),
    )
    payload = "\x1f".join(identity).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def product_identity_key(product):
    """Backward-compatible alias for the commercial product identity."""
    return commercial_identity_key(product)


def validate_product_batch(records):
    """Validate a complete catalogue batch, allowing distinct strengths and forms."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("Catalogue batch must be a non-empty list.")

    products = []
    identifiers = set()
    identities = set()
    source_keys = set()
    for record in records:
        product = normalize_product_record(record)
        product_id = product["central_product_id"]
        if product_id in identifiers:
            raise ValueError(f"Catalogue batch repeats product {product_id}.")
        identifiers.add(product_id)

        if product["identity_key"] in identities:
            raise ValueError(
                f"Catalogue batch contains an ambiguous duplicate commercial identity for {product_id}."
            )
        identities.add(product["identity_key"])

        provider = product["source_provider"].casefold()
        source_id = product["source_identifier"].casefold()
        if provider and source_id:
            source_key = (provider, source_id)
            if source_key in source_keys:
                raise ValueError("Catalogue batch repeats a provider product identifier.")
            source_keys.add(source_key)

        products.append(product)

    return tuple(products)


def create_snapshot_manifest(records, revision):
    """Return canonical normalized products and their revision/count/digest manifest."""
    revision = validate_catalogue_revision(revision)
    products = validate_product_batch(records)
    digest_fields = (
        "central_product_id",
        "ingredient_name",
        "strength",
        "strength_uom",
        "dosage_form",
        "source_provider",
        "source_identifier",
        "source_revision",
        "source_updated_at",
        "is_active",
    )
    canonical_products = [
        {fieldname: product[fieldname] for fieldname in digest_fields}
        for product in sorted(products, key=lambda record: record["central_product_id"])
    ]
    canonical_payload = json.dumps(
        canonical_products,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    manifest = {
        "revision": revision,
        "product_count": len(canonical_products),
        "digest": hashlib.sha256(canonical_payload).hexdigest(),
    }
    return manifest, products


def validate_snapshot_manifest(manifest, records):
    """Reject manifests that do not describe the complete submitted normalized batch."""
    if isinstance(manifest, str):
        try:
            manifest = json.loads(manifest)
        except (TypeError, ValueError):
            raise ValueError("Snapshot manifest is malformed.") from None
    if not isinstance(manifest, Mapping) or set(manifest) != {
        "revision",
        "product_count",
        "digest",
    }:
        raise ValueError("Snapshot manifest is malformed.")

    expected, products = create_snapshot_manifest(records, manifest["revision"])
    product_count = manifest["product_count"]
    if isinstance(product_count, bool) or not isinstance(product_count, int):
        raise ValueError("Snapshot manifest product count is invalid.")
    digest = manifest["digest"]
    if (
        product_count != expected["product_count"]
        or not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
        or digest != expected["digest"]
    ):
        raise ValueError("Snapshot manifest does not match the complete product batch.")
    return expected, products


def build_central_medicine_item_catalogue():
    """Build the tenant payload from the control site's existing Drug Items."""
    source_items = frappe.get_all(
        "Item",
        filters={"item_group": "Drug"},
        fields=["name", *_MEDICINE_ITEM_FIELDS],
        order_by="name asc",
    )
    if not source_items:
        raise ValueError("The central Drug Item catalogue is empty.")

    item_codes = [item.name for item in source_items]
    source_links = frappe.get_all(
        "Medication Linked Item",
        filters={"item_code": ["in", item_codes]},
        fields=[
            "parent",
            "item_code",
            "item",
            "item_group",
            "stock_uom",
            "is_billable",
            "idx",
        ],
        order_by="parent asc, idx asc",
    )

    medication_names = {
        row.parent for row in source_links if row.get("parent")
    }
    medications = {}
    ingredients_by_parent = {}
    pending_names = set(medication_names)
    while pending_names:
        requested_names = sorted(pending_names - set(medications))
        if not requested_names:
            break
        rows = frappe.get_all(
            "Medication",
            filters={"name": ["in", requested_names]},
            fields=["name", *_MEDICATION_FIELDS],
            order_by="name asc",
        )
        if {row.name for row in rows} != set(requested_names):
            raise ValueError("A central linked Medication record is missing.")
        medications.update({row.name: row for row in rows})
        ingredients = frappe.get_all(
            "Medication Ingredient",
            filters={"parent": ["in", requested_names]},
            fields=["parent", "medication", "strength", "strength_uom", "idx"],
            order_by="parent asc, idx asc",
        )
        for ingredient in ingredients:
            ingredients_by_parent.setdefault(ingredient.parent, []).append(
                ingredient
            )
            if ingredient.medication:
                pending_names.add(ingredient.medication)

    linked_items_by_parent = {}
    for row in source_links:
        linked_items_by_parent.setdefault(row.parent, []).append(row)

    linked_uoms = {
        item.stock_uom for item in source_items if item.stock_uom
    }
    linked_uoms.update(
        row.stock_uom for row in source_links if row.stock_uom
    )
    linked_uoms.update(
        row.strength_uom
        for row in medications.values()
        if row.strength_uom
    )
    linked_uoms.update(
        row.strength_uom
        for rows in ingredients_by_parent.values()
        for row in rows
        if row.strength_uom
    )
    uoms = frappe.get_all(
        "UOM",
        filters={"name": ["in", sorted(linked_uoms)]},
        fields=["name", "uom_name", "must_be_whole_number", "enabled"],
        order_by="name asc",
    )
    if {row.name for row in uoms} != linked_uoms:
        raise ValueError("A central medicine UOM reference is missing.")

    class_names = {
        row.medication_class
        for row in medications.values()
        if row.medication_class
    }
    medication_classes = frappe.get_all(
        "Medication Class",
        filters={"name": ["in", sorted(class_names)]},
        fields=["name", "medication_class"],
        order_by="name asc",
    )
    if {row.name for row in medication_classes} != class_names:
        raise ValueError("A central Medication Class reference is missing.")

    dosage_form_names = {
        row.dosage_form
        for row in medications.values()
        if row.dosage_form
    }
    dosage_forms = frappe.get_all(
        "Dosage Form",
        filters={"name": ["in", sorted(dosage_form_names)]},
        fields=["name", "dosage_form"],
        order_by="name asc",
    )
    if {row.name for row in dosage_forms} != dosage_form_names:
        raise ValueError("A central Dosage Form reference is missing.")

    dosage_names = {
        row.default_prescription_dosage
        for row in medications.values()
        if row.default_prescription_dosage
    }
    dosages = frappe.get_all(
        "Prescription Dosage",
        filters={"name": ["in", sorted(dosage_names)]},
        fields=["name", "dosage"],
        order_by="name asc",
    )
    if {row.name for row in dosages} != dosage_names:
        raise ValueError("A central Prescription Dosage reference is missing.")

    duration_names = {
        row.default_prescription_duration
        for row in medications.values()
        if row.default_prescription_duration
    }
    durations = frappe.get_all(
        "Prescription Duration",
        filters={"name": ["in", sorted(duration_names)]},
        fields=["name", "number", "period"],
        order_by="name asc",
    )
    if {row.name for row in durations} != duration_names:
        raise ValueError("A central Prescription Duration reference is missing.")

    catalogue = {
        "catalogue_type": "drug_item_catalogue_v1",
        "items": [
            {
                "item_code": row.name,
                **{fieldname: row.get(fieldname) for fieldname in _MEDICINE_ITEM_FIELDS},
            }
            for row in source_items
        ],
        "medications": [
            {
                "name": name,
                **{
                    fieldname: row.get(fieldname)
                    for fieldname in _MEDICATION_FIELDS
                },
                "linked_items": [
                    {
                        "item_code": link.item_code,
                        "item": link.item,
                        "item_group": link.item_group,
                        "stock_uom": link.stock_uom,
                        "is_billable": link.is_billable,
                    }
                    for link in linked_items_by_parent.get(name, [])
                ],
                "combinations": [
                    {
                        "medication": ingredient.medication,
                        "strength": ingredient.strength,
                        "strength_uom": ingredient.strength_uom,
                    }
                    for ingredient in ingredients_by_parent.get(name, [])
                ],
            }
            for name, row in sorted(medications.items())
        ],
        "medication_classes": [
            {
                "name": row.name,
                "medication_class": row.medication_class,
            }
            for row in medication_classes
        ],
        "dosage_forms": [
            {"name": row.name, "dosage_form": row.dosage_form}
            for row in dosage_forms
        ],
        "uoms": [
            {
                "name": row.name,
                "uom_name": row.uom_name,
                "must_be_whole_number": row.must_be_whole_number,
                "enabled": row.enabled,
            }
            for row in uoms
        ],
        "prescription_dosages": [
            {"name": row.name, "dosage": row.dosage}
            for row in dosages
        ],
        "prescription_durations": [
            {
                "name": row.name,
                "number": row.number,
                "period": row.period,
            }
            for row in durations
        ],
    }
    return normalize_medicine_item_catalogue(catalogue)


def _catalogue_text(value, fieldname, required=False, maximum=2000):
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    else:
        raise ValueError(f"Medicine catalogue {fieldname} must be text.")
    if (required and not text.strip()) or len(text) > maximum:
        raise ValueError(f"Medicine catalogue {fieldname} is invalid.")
    return text


def _catalogue_flag(value, fieldname):
    if value in (True, 1, "1"):
        return 1
    if value in (False, 0, "0"):
        return 0
    raise ValueError(f"Medicine catalogue {fieldname} is invalid.")


def _catalogue_decimal(value, fieldname):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Medicine catalogue {fieldname} is invalid.") from None
    if not number.is_finite() or number < 0:
        raise ValueError(f"Medicine catalogue {fieldname} is invalid.")
    return format(number.normalize(), "f")


def normalize_medicine_item_catalogue(catalogue):
    """Validate and canonicalize a complete Item/Medication projection."""
    required_keys = {
        "catalogue_type",
        "items",
        "medications",
        "medication_classes",
        "dosage_forms",
        "uoms",
        "prescription_dosages",
        "prescription_durations",
    }
    if (
        not isinstance(catalogue, Mapping)
        or not required_keys.issubset(catalogue)
        or set(catalogue).difference(required_keys | {"source_item_codes"})
    ):
        raise ValueError("Medicine Item catalogue is malformed.")
    if catalogue["catalogue_type"] != "drug_item_catalogue_v1":
        raise ValueError("Medicine Item catalogue version is unsupported.")

    items = []
    item_codes = set()
    for record in catalogue["items"]:
        if not isinstance(record, Mapping):
            raise ValueError("Medicine Item catalogue contains an invalid Item.")
        item_code = _catalogue_text(
            record.get("item_code"), "Item code", required=True, maximum=140
        )
        if item_code in item_codes:
            raise ValueError("Medicine Item catalogue repeats an Item code.")
        item_codes.add(item_code)
        item_group = _catalogue_text(
            record.get("item_group"), "Item group", required=True, maximum=140
        )
        if item_group != "Drug":
            raise ValueError("Medicine Item catalogue contains a non-Drug Item.")
        items.append(
            {
                "item_code": item_code,
                "item_name": _catalogue_text(
                    record.get("item_name"), "Item name", required=True, maximum=140
                ),
                "item_group": item_group,
                "disabled": _catalogue_flag(record.get("disabled"), "Item disabled"),
                "is_stock_item": _catalogue_flag(
                    record.get("is_stock_item"), "Item stock state"
                ),
                "is_sales_item": _catalogue_flag(
                    record.get("is_sales_item"), "Item sales state"
                ),
                "stock_uom": _catalogue_text(
                    record.get("stock_uom"), "Item stock UOM", required=True, maximum=140
                ),
                "description": _catalogue_text(
                    record.get("description"), "Item description"
                ),
            }
        )
    if not items:
        raise ValueError("Medicine Item catalogue must not be empty.")
    source_item_codes = catalogue.get("source_item_codes", sorted(item_codes))
    if not isinstance(source_item_codes, (list, tuple)):
        raise ValueError("Medicine Item catalogue source Item codes are malformed.")
    normalized_source_item_codes = []
    for value in source_item_codes:
        item_code = _catalogue_text(
            value, "source Item code", required=True, maximum=140
        )
        if item_code in normalized_source_item_codes:
            raise ValueError("Medicine Item catalogue repeats a source Item code.")
        normalized_source_item_codes.append(item_code)
    if not item_codes.issubset(normalized_source_item_codes):
        raise ValueError("Medicine Item catalogue omits a batch Item code.")
    normalized_source_item_codes.sort()

    classes = _normalize_reference_rows(
        catalogue["medication_classes"], "medication_class"
    )
    dosage_forms = _normalize_reference_rows(
        catalogue["dosage_forms"], "dosage_form"
    )
    class_names = {row["name"] for row in classes}
    dosage_form_names = {row["name"] for row in dosage_forms}

    uoms = []
    uom_names = set()
    for row in catalogue["uoms"]:
        if not isinstance(row, Mapping):
            raise ValueError("Medicine Item catalogue contains an invalid UOM.")
        name = _catalogue_text(row.get("name"), "UOM name", required=True, maximum=140)
        if name in uom_names:
            raise ValueError("Medicine Item catalogue repeats a UOM.")
        uom_names.add(name)
        uoms.append(
            {
                "name": name,
                "uom_name": _catalogue_text(
                    row.get("uom_name"), "UOM name", required=True, maximum=140
                ),
                "must_be_whole_number": _catalogue_flag(
                    row.get("must_be_whole_number"), "UOM whole-number state"
                ),
                "enabled": _catalogue_flag(row.get("enabled"), "UOM enabled state"),
            }
        )

    dosages = _normalize_reference_rows(catalogue["prescription_dosages"], "dosage")
    durations = []
    duration_names = set()
    for row in catalogue["prescription_durations"]:
        if not isinstance(row, Mapping):
            raise ValueError("Medicine Item catalogue contains an invalid duration.")
        name = _catalogue_text(
            row.get("name"), "duration name", required=True, maximum=140
        )
        if name in duration_names:
            raise ValueError("Medicine Item catalogue repeats a duration.")
        duration_names.add(name)
        number = _catalogue_decimal(row.get("number"), "duration number")
        period = _catalogue_text(
            row.get("period"), "duration period", required=True, maximum=140
        )
        if name != f"{number} {period}":
            raise ValueError("Medicine Item catalogue duration name is inconsistent.")
        durations.append({"name": name, "number": number, "period": period})

    medication_names = set()
    medications = []
    for record in catalogue["medications"]:
        if not isinstance(record, Mapping):
            raise ValueError("Medicine Item catalogue contains an invalid Medication.")
        name = _catalogue_text(
            record.get("name"), "Medication name", required=True, maximum=140
        )
        generic_name = _catalogue_text(
            record.get("generic_name"),
            "Medication generic name",
            required=True,
            maximum=140,
        )
        if name != generic_name or name in medication_names:
            raise ValueError("Medicine Item catalogue has an inconsistent Medication name.")
        medication_names.add(name)
        medication_class = _catalogue_text(
            record.get("medication_class"),
            "Medication class",
            required=True,
            maximum=140,
        )
        strength_uom = _catalogue_text(
            record.get("strength_uom"), "Medication strength UOM", required=True, maximum=140
        )
        dosage_form = _catalogue_text(
            record.get("dosage_form"), "Medication dosage form", required=True, maximum=140
        )
        if medication_class not in class_names or dosage_form not in dosage_form_names:
            raise ValueError("Medicine Item catalogue has an unresolved Medication reference.")
        linked_items = []
        linked_codes = set()
        for linked in record["linked_items"]:
            if not isinstance(linked, Mapping):
                raise ValueError("Medicine Item catalogue contains an invalid Item link.")
            item_code = _catalogue_text(
                linked.get("item_code"), "linked Item code", required=True, maximum=140
            )
            if item_code not in item_codes or item_code in linked_codes:
                raise ValueError("Medicine Item catalogue has an invalid Item relationship.")
            linked_codes.add(item_code)
            if linked.get("item") != item_code:
                raise ValueError("Medicine Item catalogue has an inconsistent Item link.")
            linked_items.append(
                {
                    "item_code": item_code,
                    "item": item_code,
                    "item_group": _catalogue_text(
                        linked.get("item_group"),
                        "linked Item group",
                        required=True,
                        maximum=140,
                    ),
                    "stock_uom": _catalogue_text(
                        linked.get("stock_uom"),
                        "linked Item stock UOM",
                        required=True,
                        maximum=140,
                    ),
                    "is_billable": _catalogue_flag(
                        linked.get("is_billable"), "linked Item billable state"
                    ),
                }
            )
        combinations = []
        for ingredient in record["combinations"]:
            if not isinstance(ingredient, Mapping):
                raise ValueError("Medicine Item catalogue contains an invalid ingredient.")
            combinations.append(
                {
                    "medication": _catalogue_text(
                        ingredient.get("medication"),
                        "combination Medication",
                        required=True,
                        maximum=140,
                    ),
                    "strength": _catalogue_decimal(
                        ingredient.get("strength"), "ingredient strength"
                    ),
                    "strength_uom": _catalogue_text(
                        ingredient.get("strength_uom"),
                        "ingredient strength UOM",
                        required=True,
                        maximum=140,
                    ),
                }
            )
        medications.append(
            {
                "name": name,
                "generic_name": generic_name,
                "medication_class": medication_class,
                "strength": _catalogue_decimal(record.get("strength"), "Medication strength"),
                "strength_uom": strength_uom,
                "dosage_form": dosage_form,
                "disabled": _catalogue_flag(
                    record.get("disabled"), "Medication disabled state"
                ),
                "is_combination": _catalogue_flag(
                    record.get("is_combination"), "Medication combination state"
                ),
                "default_prescription_dosage": _catalogue_text(
                    record.get("default_prescription_dosage"),
                    "default prescription dosage",
                    maximum=140,
                ),
                "default_prescription_duration": _catalogue_text(
                    record.get("default_prescription_duration"),
                    "default prescription duration",
                    maximum=140,
                ),
                "price_list": _catalogue_text(
                    record.get("price_list"), "Medication price list", maximum=140
                ),
                "linked_items": linked_items,
                "combinations": combinations,
            }
        )
    if any(row["medication"] not in medication_names for record in medications for row in record["combinations"]):
        raise ValueError("Medicine Item catalogue has an unresolved combination ingredient.")

    for item in items:
        if item["stock_uom"] not in uom_names:
            raise ValueError("Medicine Item catalogue has an unresolved Item UOM.")
    for medication in medications:
        if medication["strength_uom"] not in uom_names:
            raise ValueError("Medicine Item catalogue has an unresolved Medication UOM.")
        if medication["default_prescription_dosage"] not in {
            row["name"] for row in dosages
        }:
            raise ValueError("Medicine Item catalogue has an unresolved prescription dosage.")
        if medication["default_prescription_duration"] not in duration_names:
            raise ValueError("Medicine Item catalogue has an unresolved prescription duration.")
        for link in medication["linked_items"]:
            if link["stock_uom"] not in uom_names:
                raise ValueError("Medicine Item catalogue has an unresolved linked Item UOM.")
        for ingredient in medication["combinations"]:
            if ingredient["strength_uom"] not in uom_names:
                raise ValueError("Medicine Item catalogue has an unresolved ingredient UOM.")

    return {
        "catalogue_type": "drug_item_catalogue_v1",
        "items": sorted(items, key=lambda row: row["item_code"]),
        "source_item_codes": normalized_source_item_codes,
        "medications": sorted(medications, key=lambda row: row["name"]),
        "medication_classes": sorted(classes, key=lambda row: row["name"]),
        "dosage_forms": sorted(dosage_forms, key=lambda row: row["name"]),
        "uoms": sorted(uoms, key=lambda row: row["name"]),
        "prescription_dosages": sorted(dosages, key=lambda row: row["name"]),
        "prescription_durations": sorted(durations, key=lambda row: row["name"]),
    }


def _normalize_reference_rows(records, fieldname):
    if not isinstance(records, (list, tuple)):
        raise ValueError("Medicine Item catalogue reference list is malformed.")
    rows = []
    seen = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("Medicine Item catalogue reference is malformed.")
        name = _catalogue_text(
            record.get("name"), "reference name", required=True, maximum=140
        )
        value = _catalogue_text(
            record.get(fieldname), fieldname, required=True, maximum=140
        )
        if name != value or name in seen:
            raise ValueError("Medicine Item catalogue reference is inconsistent.")
        seen.add(name)
        rows.append({"name": name, fieldname: value})
    return rows


def create_medicine_item_snapshot_manifest(catalogue, revision):
    """Create a deterministic digest for the complete Item/Medication payload."""
    revision = validate_catalogue_revision(revision)
    normalized = normalize_medicine_item_catalogue(catalogue)
    canonical_payload = json.dumps(
        normalized,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    manifest = {
        "revision": revision,
        "item_count": len(normalized["items"]),
        "digest": hashlib.sha256(canonical_payload).hexdigest(),
    }
    return manifest, normalized


def validate_medicine_item_snapshot(manifest, catalogue):
    if isinstance(manifest, str):
        try:
            manifest = json.loads(manifest)
        except (TypeError, ValueError):
            raise ValueError("Medicine Item snapshot manifest is malformed.") from None
    if not isinstance(manifest, Mapping) or set(manifest) != {
        "revision",
        "item_count",
        "digest",
    }:
        raise ValueError("Medicine Item snapshot manifest is malformed.")
    expected, normalized = create_medicine_item_snapshot_manifest(
        catalogue, manifest["revision"]
    )
    item_count = manifest["item_count"]
    digest = manifest["digest"]
    if (
        isinstance(item_count, bool)
        or not isinstance(item_count, int)
        or item_count != expected["item_count"]
        or not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
        or digest != expected["digest"]
    ):
        raise ValueError("Medicine Item manifest does not match the complete batch.")
    return expected, normalized


def _medicine_item_catalogue_batches(catalogue, batch_size):
    """Split a normalized Item catalogue while keeping each batch's Medication graph valid."""
    items = catalogue["items"]
    medications_by_name = {
        row["name"]: row for row in catalogue["medications"]
    }
    for offset in range(0, len(items), batch_size):
        batch_items = items[offset : offset + batch_size]
        batch_codes = {row["item_code"] for row in batch_items}
        medication_names = {
            medication["name"]
            for medication in catalogue["medications"]
            if any(
                link["item_code"] in batch_codes
                for link in medication["linked_items"]
            )
        }
        pending_names = list(medication_names)
        while pending_names:
            medication = medications_by_name[pending_names.pop()]
            for ingredient in medication["combinations"]:
                ingredient_name = ingredient["medication"]
                if ingredient_name not in medication_names:
                    medication_names.add(ingredient_name)
                    pending_names.append(ingredient_name)

        batch_medications = []
        for name in sorted(medication_names):
            medication = dict(medications_by_name[name])
            medication["linked_items"] = [
                link
                for link in medication["linked_items"]
                if link["item_code"] in batch_codes
            ]
            batch_medications.append(medication)

        class_names = {
            row["medication_class"] for row in batch_medications
        }
        dosage_form_names = {
            row["dosage_form"] for row in batch_medications
        }
        dosage_names = {
            row["default_prescription_dosage"]
            for row in batch_medications
        }
        duration_names = {
            row["default_prescription_duration"]
            for row in batch_medications
        }
        uom_names = {
            row["stock_uom"] for row in batch_items
        }
        for medication in batch_medications:
            uom_names.add(medication["strength_uom"])
            uom_names.update(
                link["stock_uom"] for link in medication["linked_items"]
            )
            uom_names.update(
                ingredient["strength_uom"]
                for ingredient in medication["combinations"]
            )

        yield {
            "catalogue_type": catalogue["catalogue_type"],
            "items": batch_items,
            "source_item_codes": catalogue["source_item_codes"],
            "medications": batch_medications,
            "medication_classes": [
                row
                for row in catalogue["medication_classes"]
                if row["name"] in class_names
            ],
            "dosage_forms": [
                row
                for row in catalogue["dosage_forms"]
                if row["name"] in dosage_form_names
            ],
            "uoms": [
                row for row in catalogue["uoms"] if row["name"] in uom_names
            ],
            "prescription_dosages": [
                row
                for row in catalogue["prescription_dosages"]
                if row["name"] in dosage_names
            ],
            "prescription_durations": [
                row
                for row in catalogue["prescription_durations"]
                if row["name"] in duration_names
            ],
        }


def _medicine_item_codes_for_conflicting_medications(
    catalogue, conflicting_medications
):
    if (
        not isinstance(conflicting_medications, (list, tuple))
        or not conflicting_medications
    ):
        raise ValueError("Conflicting Medication names are invalid.")

    medications_by_name = {
        row["name"]: row for row in catalogue["medications"]
    }
    affected_medications = set()
    for name in conflicting_medications:
        if (
            not isinstance(name, str)
            or not name
            or name != name.strip()
            or name not in medications_by_name
        ):
            raise ValueError("Conflicting Medication cannot be mapped safely.")
        affected_medications.add(name)

    changed = True
    while changed:
        changed = False
        for medication in catalogue["medications"]:
            if medication["name"] in affected_medications:
                continue
            if any(
                ingredient["medication"] in affected_medications
                for ingredient in medication["combinations"]
            ):
                affected_medications.add(medication["name"])
                changed = True

    affected_item_codes = {
        linked_item["item_code"]
        for name in affected_medications
        for linked_item in medications_by_name[name]["linked_items"]
    }
    batch_item_codes = {
        item["item_code"] for item in catalogue["items"]
    }
    if (
        not affected_item_codes
        or not affected_item_codes.issubset(batch_item_codes)
    ):
        raise ValueError("Conflicting Medication has no safely mapped Items.")
    return affected_item_codes


def _safe_sync_target(tenant_site, control_site):
    tenant_site = _canonical_tenant_site(tenant_site)
    if tenant_site == control_site:
        raise ValueError("The central catalogue cannot synchronize to its own control site.")
    return tenant_site


def validate_catalogue_revision(value):
    """Require sortable UTC YYYYMMDDHHMMSSffffff revisions for delivery fencing."""
    revision = str(value or "").strip()
    if not _CATALOGUE_REVISION_PATTERN.fullmatch(revision):
        raise ValueError("Catalogue revision must be a sortable UTC timestamp revision.")
    try:
        datetime.strptime(revision, "%Y%m%d%H%M%S%f")
    except ValueError:
        raise ValueError("Catalogue revision must be a valid UTC timestamp revision.") from None
    return revision


def _configured_sync_user():
    return str(
        os.environ.get("CLINIFY_CATALOGUE_SYNC_USER")
        or frappe.conf.get("CLINIFY_CATALOGUE_SYNC_USER")
        or ""
    ).strip()


def _require_tenant_sync_request(tenant_site, control_site):
    if getattr(frappe.request, "method", "").upper() != "POST":
        frappe.throw("Medicine catalogue synchronization requires POST.")
    if frappe.session.user == "Guest":
        frappe.throw("Authentication is required for medicine catalogue synchronization.")

    frappe.only_for(CLINIFY_CATALOGUE_SYNC_ROLE)
    expected_user = _configured_sync_user()
    if not expected_user or frappe.session.user != expected_user:
        frappe.throw("This account is not authorized for medicine catalogue synchronization.")

    configured_site = configured_control_site()
    current_site = str(frappe.local.site or "").strip().lower()
    if (
        current_site != tenant_site
        or str(control_site or "").strip().lower() != configured_site
        or current_site == configured_site
    ):
        frappe.throw("Medicine catalogue synchronization destination is invalid.")


@contextmanager
def _tenant_projection_write_lock(tenant_site):
    lock_suffix = hashlib.sha256(tenant_site.encode("utf-8")).hexdigest()[:32]
    lock_name = f"clinify_med_projection_{lock_suffix}"
    database = frappe.db
    result = database.sql("SELECT GET_LOCK(%s, %s)", (lock_name, 30))
    if not result or int(result[0][0] or 0) != 1:
        frappe.throw("Medicine catalogue synchronization is already in progress.")

    released = False

    def release_after_transaction():
        nonlocal released
        if released:
            return
        released = True
        database.sql("SELECT RELEASE_LOCK(%s)", (lock_name,))

    try:
        frappe.db.after_commit.add(release_after_transaction)
        frappe.db.after_rollback.add(release_after_transaction)
    except Exception:
        release_after_transaction()
        raise

    yield


@frappe.whitelist(methods=["POST"])
def apply_tenant_projection_batch(
    tenant_site=None,
    control_site=None,
    snapshot_manifest=None,
    products=None,
    catalogue=None,
):
    """Apply one authenticated medicine batch atomically on its tenant."""
    tenant_site = str(tenant_site or "").strip().lower()
    _require_tenant_sync_request(tenant_site, control_site)

    if isinstance(catalogue, str):
        try:
            catalogue = json.loads(catalogue)
        except (TypeError, ValueError):
            frappe.throw("Medicine Item catalogue batch is malformed.")
    if catalogue is not None:
        try:
            manifest, normalized = validate_medicine_item_snapshot(
                snapshot_manifest, catalogue
            )
        except ValueError:
            frappe.throw("Medicine Item snapshot failed validation.")
        with _tenant_projection_write_lock(tenant_site):
            return _apply_validated_tenant_medicine_item_batch(
                tenant_site, manifest, normalized
            )

    if isinstance(products, str):
        try:
            products = json.loads(products)
        except (TypeError, ValueError):
            frappe.throw("Medicine catalogue batch is malformed.")
    try:
        manifest, normalized = validate_snapshot_manifest(snapshot_manifest, products)
    except ValueError:
        frappe.throw("Medicine catalogue snapshot failed validation.")

    with _tenant_projection_write_lock(tenant_site):
        return _apply_validated_tenant_projection_batch(tenant_site, manifest, normalized)


def _ensure_medicine_reference(doctype, values):
    name = values["name"]
    if frappe.db.exists(doctype, name):
        return
    doc_values = {"doctype": doctype, **values}
    if doctype in ("Medication Class", "Dosage Form", "UOM", "Prescription Dosage"):
        doc_values.pop("name", None)
    frappe.get_doc(doc_values).insert(ignore_permissions=True)


def _apply_validated_tenant_medicine_item_batch(tenant_site, manifest, catalogue):
    revision = manifest["revision"]
    digest = manifest["digest"]
    state = _tenant_snapshot_state(tenant_site)
    last_revision = str(state.last_successful_revision or "")
    last_digest = str(state.last_successful_digest or "")
    item_codes = [item["item_code"] for item in catalogue["items"]]
    if last_revision > revision or (
        last_revision == revision and last_digest != digest
    ):
        return {
            "status": "conflict",
            "tenant_site": tenant_site,
            "snapshot_manifest": dict(manifest),
            "created_item_codes": [],
            "updated_item_codes": [],
            "skipped_item_codes": [],
            "missing_item_codes": [],
            "conflicting_item_codes": item_codes,
        }

    batch_item_codes = set(item_codes)
    source_item_codes = set(catalogue["source_item_codes"])
    source_medications = {row["name"] for row in catalogue["medications"]}
    conflicting_codes = []
    for item in catalogue["items"]:
        if not frappe.db.exists("Item", item["item_code"]):
            continue
        doc = frappe.get_doc("Item", item["item_code"])
        changed = any(
            str(getattr(doc, fieldname) or "")
            != str(item[fieldname] or "")
            for fieldname in _MEDICINE_ITEM_FIELDS
        )
        centrally_linked = source_medications and frappe.db.exists(
            "Medication Linked Item",
            {
                "item_code": item["item_code"],
                "parent": ["in", sorted(source_medications)],
            },
        )
        if changed and not centrally_linked:
            conflicting_codes.append(item["item_code"])

    conflicting_medications = []
    for medication in catalogue["medications"]:
        if not frappe.db.exists("Medication", medication["name"]):
            continue
        doc = frappe.get_doc("Medication", medication["name"])
        existing_links = list(doc.get("linked_items", []))
        centrally_linked = any(
            row.item_code in source_item_codes for row in existing_links
        )
        changed = any(
            str(getattr(doc, fieldname) or "")
            != str(medication[fieldname] or "")
            for fieldname in _MEDICATION_FIELDS
        )
        existing_combinations = sorted(
            (
                row.medication,
                _identity_strength(row.strength),
                str(row.strength_uom or ""),
            )
            for row in doc.get("combinations", [])
        )
        source_combinations = sorted(
            (
                row["medication"],
                _identity_strength(row["strength"]),
                row["strength_uom"],
            )
            for row in medication["combinations"]
        )
        changed = changed or existing_combinations != source_combinations
        has_source_links = bool(medication["linked_items"])
        if not centrally_linked and (changed or has_source_links):
            conflicting_medications.append(medication["name"])

    if conflicting_medications:
        return {
            "status": "conflict",
            "tenant_site": tenant_site,
            "snapshot_manifest": dict(manifest),
            "created_item_codes": [],
            "updated_item_codes": [],
            "skipped_item_codes": [],
            "missing_item_codes": [],
            "conflicting_item_codes": sorted(
                set(conflicting_codes) | set(item_codes)
                if conflicting_medications
                else set(conflicting_codes)
            ),
            "conflicting_medications": conflicting_medications,
        }

    savepoint = "clinify_medicine_item_catalogue_batch"
    frappe.db.savepoint(savepoint)
    created_codes = []
    updated_codes = []
    skipped_codes = []
    try:
        for row in catalogue["medication_classes"]:
            _ensure_medicine_reference(
                "Medication Class",
                {"name": row["name"], "medication_class": row["medication_class"]},
            )
        for row in catalogue["dosage_forms"]:
            _ensure_medicine_reference(
                "Dosage Form",
                {"name": row["name"], "dosage_form": row["dosage_form"]},
            )
        for row in catalogue["uoms"]:
            _ensure_medicine_reference(
                "UOM",
                {
                    "name": row["name"],
                    "uom_name": row["uom_name"],
                    "must_be_whole_number": row["must_be_whole_number"],
                    "enabled": row["enabled"],
                },
            )
        for row in catalogue["prescription_dosages"]:
            _ensure_medicine_reference(
                "Prescription Dosage",
                {"name": row["name"], "dosage": row["dosage"]},
            )
        for row in catalogue["prescription_durations"]:
            _ensure_medicine_reference(
                "Prescription Duration",
                {
                    "name": row["name"],
                    "number": row["number"],
                    "period": row["period"],
                },
            )

        for item in catalogue["items"]:
            values = {
                fieldname: item[fieldname]
                for fieldname in _MEDICINE_ITEM_FIELDS
            }
            if item["item_code"] in conflicting_codes:
                skipped_codes.append(item["item_code"])
                continue
            if frappe.db.exists("Item", item["item_code"]):
                doc = frappe.get_doc("Item", item["item_code"])
                changed = any(
                    str(getattr(doc, fieldname) or "")
                    != str(value or "")
                    for fieldname, value in values.items()
                )
                if changed:
                    for fieldname, value in values.items():
                        setattr(doc, fieldname, value)
                    doc.save(ignore_permissions=True)
                    updated_codes.append(item["item_code"])
                else:
                    skipped_codes.append(item["item_code"])
            else:
                frappe.get_doc(
                    {
                        "doctype": "Item",
                        "item_code": item["item_code"],
                        **values,
                    }
                ).insert(ignore_permissions=True)
                created_codes.append(item["item_code"])

        for medication in catalogue["medications"]:
            fields = {
                fieldname: medication[fieldname]
                for fieldname in _MEDICATION_FIELDS
            }
            if frappe.db.exists("Medication", medication["name"]):
                doc = frappe.get_doc("Medication", medication["name"])
                for fieldname, value in fields.items():
                    setattr(doc, fieldname, value)
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": "Medication",
                        **fields,
                    }
                )
                doc.insert(ignore_permissions=True)

            existing_links = {
                row.item_code: row
                for row in doc.get("linked_items", [])
                if row.item_code
            }
            source_links = {
                row["item_code"]: row for row in medication["linked_items"]
                if row["item_code"] not in conflicting_codes
            }
            merged_links = []
            for item_code, row in existing_links.items():
                if item_code not in batch_item_codes:
                    merged_links.append(
                        {
                            "item_code": row.item_code,
                            "item": row.item or row.item_code,
                            "item_group": row.item_group,
                            "stock_uom": row.stock_uom,
                            "is_billable": row.is_billable,
                            "change_in_item": 0,
                        }
                    )
            for item_code, row in source_links.items():
                merged_links.append(
                    {
                        "item_code": item_code,
                        "item": item_code,
                        "item_group": row["item_group"],
                        "stock_uom": row["stock_uom"],
                        "is_billable": row["is_billable"],
                        "change_in_item": 0,
                    }
                )
            doc.set("linked_items", merged_links)
            doc.set("combinations", medication["combinations"])
            doc.save(ignore_permissions=True)

        for item in catalogue["items"]:
            if item["item_code"] in conflicting_codes:
                continue
            doc = frappe.get_doc("Item", item["item_code"])
            changed = any(
                str(getattr(doc, fieldname) or "")
                != str(item[fieldname] or "")
                for fieldname in _MEDICINE_ITEM_FIELDS
            )
            if changed:
                for fieldname in _MEDICINE_ITEM_FIELDS:
                    setattr(doc, fieldname, item[fieldname])
                doc.save(ignore_permissions=True)

        state.last_attempted_at = now_datetime()
        state.last_attempted_revision = revision
        state.last_attempted_digest = digest
        state.last_attempt_status = "Succeeded"
        state.last_error_code = ""
        state.last_successful_at = now_datetime()
        state.last_successful_revision = revision
        state.last_successful_digest = digest
        state.last_created_count = len(created_codes)
        state.last_updated_count = len(updated_codes)
        state.last_skipped_count = len(skipped_codes)
        state.flags.clinify_catalogue_state_update = True
        if state.is_new():
            state.insert(ignore_permissions=True)
        else:
            state.save(ignore_permissions=True)
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise

    return {
        "status": "success",
        "tenant_site": tenant_site,
        "snapshot_manifest": dict(manifest),
        "created_item_codes": created_codes,
        "updated_item_codes": updated_codes,
        "skipped_item_codes": skipped_codes,
        "missing_item_codes": [],
        "conflicting_item_codes": sorted(conflicting_codes),
    }


def _tenant_snapshot_state(tenant_site):
    if frappe.db.exists("Clinify Medicine Sync State", tenant_site):
        return frappe.get_doc("Clinify Medicine Sync State", tenant_site)
    return frappe.get_doc(
        {
            "doctype": "Clinify Medicine Sync State",
            "tenant_site": tenant_site,
        }
    )


def _apply_validated_tenant_projection_batch(tenant_site, manifest, normalized):
    revision = manifest["revision"]
    digest = manifest["digest"]
    state = _tenant_snapshot_state(tenant_site)
    last_revision = str(state.last_successful_revision or "")
    last_digest = str(state.last_successful_digest or "")
    all_product_ids = [product["central_product_id"] for product in normalized]

    if last_revision > revision or (last_revision == revision and last_digest != digest):
        return {
            "status": "conflict",
            "tenant_site": tenant_site,
            "snapshot_manifest": dict(manifest),
            "created_product_ids": [],
            "updated_product_ids": [],
            "skipped_product_ids": [],
            "missing_product_ids": [],
            "conflicting_product_ids": all_product_ids,
        }

    existing_docs = {}
    conflicts = []
    for product in normalized:
        product_id = product["central_product_id"]
        if frappe.db.exists("Clinify Medicine Projection", product_id):
            doc = frappe.get_doc("Clinify Medicine Projection", product_id)
            if _projection_identity(doc) != _projection_identity(product):
                conflicts.append(product_id)
            else:
                existing_docs[product_id] = doc
                existing_revision = str(doc.catalogue_revision or "")
                existing_content_changed = any(
                    str(getattr(doc, fieldname) or "") != str(product[fieldname] or "")
                    for fieldname in _PROJECTION_FIELDS
                    if fieldname != "central_product_id"
                )
                if existing_revision > revision or (
                    existing_revision == revision and existing_content_changed
                ):
                    conflicts.append(product_id)

    if last_revision == revision and last_digest == digest:
        complete_projection = all(
            product["central_product_id"] in existing_docs
            and not any(
                str(getattr(existing_docs[product["central_product_id"]], fieldname) or "")
                != str(product[fieldname] or "")
                for fieldname in _PROJECTION_FIELDS
                if fieldname != "central_product_id"
            )
            for product in normalized
        )
        if complete_projection:
            return {
                "status": "success",
                "tenant_site": tenant_site,
                "snapshot_manifest": dict(manifest),
                "created_product_ids": [],
                "updated_product_ids": [],
                "skipped_product_ids": all_product_ids,
                "missing_product_ids": [],
                "conflicting_product_ids": [],
            }
        conflicts.extend(
            product_id for product_id in all_product_ids if product_id not in conflicts
        )

    if conflicts:
        return {
            "status": "conflict",
            "tenant_site": tenant_site,
            "snapshot_manifest": dict(manifest),
            "created_product_ids": [],
            "updated_product_ids": [],
            "skipped_product_ids": [],
            "missing_product_ids": [],
            "conflicting_product_ids": conflicts,
        }

    savepoint = "clinify_medicine_catalogue_batch"
    frappe.db.savepoint(savepoint)
    created_ids = []
    updated_ids = []
    skipped_ids = []
    try:
        for product in normalized:
            product_id = product["central_product_id"]
            existing = existing_docs.get(product_id)
            values = {
                fieldname: product[fieldname]
                for fieldname in _PROJECTION_FIELDS
            }
            if existing:
                content_changed = any(
                    str(getattr(existing, fieldname) or "") != str(values[fieldname] or "")
                    for fieldname in values
                    if fieldname != "central_product_id"
                )
                if not content_changed and existing.catalogue_revision == revision:
                    skipped_ids.append(product_id)
                    continue
                for fieldname, value in values.items():
                    setattr(existing, fieldname, value)
                existing.catalogue_revision = revision
                existing.flags.clinify_catalogue_sync = True
                existing.save(ignore_permissions=True)
                if content_changed:
                    updated_ids.append(product_id)
                else:
                    skipped_ids.append(product_id)
            else:
                values.update(
                    {
                        "doctype": "Clinify Medicine Projection",
                        "catalogue_revision": revision,
                    }
                )
                doc = frappe.get_doc(values)
                doc.flags.clinify_catalogue_sync = True
                doc.insert(ignore_permissions=True)
                created_ids.append(product_id)

        state.last_attempted_at = now_datetime()
        state.last_attempted_revision = revision
        state.last_attempted_digest = digest
        state.last_attempt_status = "Succeeded"
        state.last_error_code = ""
        state.last_successful_at = now_datetime()
        state.last_successful_revision = revision
        state.last_successful_digest = digest
        state.last_created_count = len(created_ids)
        state.last_updated_count = len(updated_ids)
        state.last_skipped_count = len(skipped_ids)
        state.flags.clinify_catalogue_state_update = True
        if state.is_new():
            state.insert(ignore_permissions=True)
        else:
            state.save(ignore_permissions=True)
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise

    return {
        "status": "success",
        "tenant_site": tenant_site,
        "snapshot_manifest": dict(manifest),
        "created_product_ids": created_ids,
        "updated_product_ids": updated_ids,
        "skipped_product_ids": skipped_ids,
        "missing_product_ids": [],
        "conflicting_product_ids": [],
    }


def _projection_identity(record):
    def value(fieldname):
        if isinstance(record, Mapping):
            return record.get(fieldname)
        return getattr(record, fieldname, None)

    return (
        " ".join(str(value("ingredient_name") or "").split()).casefold(),
        format(Decimal(str(value("strength"))).normalize(), "f"),
        " ".join(str(value("strength_uom") or "").split()).casefold(),
        " ".join(str(value("dosage_form") or "").split()).casefold(),
    )


def _record_failure(
    state_store,
    tenant_site,
    revision,
    error_code,
    snapshot_digest="",
    **details,
):
    state_store.record_failure(
        tenant_site,
        revision,
        error_code,
        snapshot_digest,
    )
    _LOGGER.warning(
        "Medicine catalogue synchronization failed: tenant=%s revision=%s code=%s",
        tenant_site,
        revision,
        error_code,
    )
    result = {
        "status": "failed",
        "tenant_site": tenant_site,
        "catalogue_revision": revision,
        "error_code": error_code,
    }
    result.update(details)
    return result


def _response_product_ids(response, fieldname, known_ids):
    values = response.get(fieldname, [])
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"Tenant synchronization returned invalid {fieldname}.")

    product_ids = []
    for value in values:
        product_id = str(value or "").strip().upper()
        if product_id not in known_ids or product_id in product_ids:
            raise ValueError(f"Tenant synchronization returned invalid {fieldname}.")
        product_ids.append(product_id)
    return product_ids


def _response_item_codes(response, fieldname, known_codes):
    values = response.get(fieldname, [])
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"Tenant synchronization returned invalid {fieldname}.")
    item_codes = []
    for value in values:
        item_code = str(value or "").strip()
        if item_code not in known_codes or item_code in item_codes:
            raise ValueError(f"Tenant synchronization returned invalid {fieldname}.")
        item_codes.append(item_code)
    return item_codes


def synchronize_tenant_catalogue(
    tenant_site,
    catalogue_revision,
    transport=None,
    state_store=None,
):
    """Synchronize, closing the internally created transport on return."""
    if transport is not None:
        return _synchronize_tenant_catalogue(
            tenant_site,
            catalogue_revision,
            transport,
            state_store,
        )

    with FrappeApiTokenTenantTransport() as transport:
        return _synchronize_tenant_catalogue(
            tenant_site,
            catalogue_revision,
            transport,
            state_store,
        )


def _synchronize_tenant_catalogue(
    tenant_site,
    catalogue_revision,
    transport,
    state_store=None,
):
    """Synchronize central Drug Items through the selected authenticated transport.

    The transport must authenticate the tenant, apply the complete batch in one
    tenant-local transaction, upsert by the source Item code, preserve omitted
    Items, and return only after that transaction succeeds. No direct
    cross-site database connection is used.
    """
    control_site = require_control_site_admin()
    tenant_site = _safe_sync_target(tenant_site, control_site)
    revision = validate_catalogue_revision(catalogue_revision)
    if state_store is None:
        state_store = FrappeCatalogueSyncStateStore()
    state_store.record_attempt(tenant_site, revision)
    try:
        catalogue = build_central_medicine_item_catalogue()
    except Exception:
        return _record_failure(state_store, tenant_site, revision, "central_catalogue_unavailable")

    try:
        manifest, catalogue = create_medicine_item_snapshot_manifest(
            catalogue, revision
        )
    except (TypeError, ValueError):
        return _record_failure(state_store, tenant_site, revision, "invalid_central_batch")

    state_store.record_attempt(tenant_site, revision, manifest["digest"])

    batch_metrics = None
    active_batch_attempt = 0
    active_batch_size = 0
    try:
        if catalogue.get("catalogue_type") == "drug_item_catalogue_v1":
            created_codes = []
            updated_codes = []
            skipped_codes = []
            conflicting_codes = []
            revision_time = datetime.strptime(revision, "%Y%m%d%H%M%S%f")
            batch_queue = list(
                _medicine_item_catalogue_batches(
                    catalogue, _MEDICINE_ITEM_SYNC_BATCH_SIZE
                )
            )
            batch_metrics = {
                "normal_batch_attempts": len(batch_queue),
                "batch_attempts": 0,
                "conflict_responses": 0,
                "reported_conflict_batches": 0,
                "split_operations": 0,
                "smallest_batch_size": None,
                "successful_batch_count": 0,
            }
            batch_index = 0
            batch_count = 0
            while batch_queue:
                batch = batch_queue.pop(0)
                batch_revision = (
                    revision_time + timedelta(microseconds=batch_index)
                ).strftime("%Y%m%d%H%M%S%f")
                batch_index += 1
                batch_manifest, batch = create_medicine_item_snapshot_manifest(
                    batch, batch_revision
                )
                active_batch_attempt = batch_metrics["batch_attempts"] + 1
                active_batch_size = len(batch["items"])
                batch_metrics["batch_attempts"] = active_batch_attempt
                previous_smallest = batch_metrics["smallest_batch_size"]
                batch_metrics["smallest_batch_size"] = (
                    active_batch_size
                    if previous_smallest is None
                    else min(previous_smallest, active_batch_size)
                )
                batch_response = transport.apply_projection_batch_atomically(
                    tenant_site,
                    batch_manifest,
                    batch,
                )
                if not isinstance(batch_response, Mapping):
                    return _record_failure(
                        state_store,
                        tenant_site,
                        revision,
                        "tenant_response_invalid",
                        manifest["digest"],
                    )
                if batch_response.get("status") == "conflict":
                    batch_metrics["conflict_responses"] += 1
                batch_codes = {item["item_code"] for item in batch["items"]}
                if (
                    str(batch_response.get("tenant_site") or "").strip().lower()
                    != tenant_site
                    or batch_response.get("snapshot_manifest") != batch_manifest
                ):
                    return _record_failure(
                        state_store,
                        tenant_site,
                        revision,
                        "tenant_response_invalid",
                        manifest["digest"],
                    )
                try:
                    batch_created = _response_item_codes(
                        batch_response, "created_item_codes", batch_codes
                    )
                    batch_updated = _response_item_codes(
                        batch_response, "updated_item_codes", batch_codes
                    )
                    batch_skipped = _response_item_codes(
                        batch_response, "skipped_item_codes", batch_codes
                    )
                    batch_missing = _response_item_codes(
                        batch_response, "missing_item_codes", batch_codes
                    )
                    batch_conflicts = _response_item_codes(
                        batch_response, "conflicting_item_codes", batch_codes
                    )
                    conflicting_medications = batch_response.get(
                        "conflicting_medications", []
                    )
                    if not isinstance(conflicting_medications, (list, tuple)):
                        return _record_failure(
                            state_store,
                            tenant_site,
                            revision,
                            "tenant_response_invalid",
                            manifest["digest"],
                        )
                    conflicting_medication_count = len(conflicting_medications)
                except ValueError:
                    return _record_failure(
                        state_store,
                        tenant_site,
                        revision,
                        "tenant_response_invalid",
                        manifest["digest"],
                    )
                if batch_conflicts:
                    batch_metrics["reported_conflict_batches"] += 1
                    _LOGGER.warning(
                        "Medicine catalogue batch conflict reported: "
                        "tenant=%s batch_attempt=%d batch_size=%d "
                        "category=%s conflicting_item_count=%d "
                        "conflicting_medication_count=%d",
                        tenant_site,
                        active_batch_attempt,
                        active_batch_size,
                        (
                            "medication_identity"
                            if conflicting_medication_count
                            else "item_or_snapshot"
                        ),
                        len(batch_conflicts),
                        conflicting_medication_count,
                    )
                if (
                    conflicting_medications
                    and batch_response.get("status") != "conflict"
                ):
                    return _record_failure(
                        state_store,
                        tenant_site,
                        revision,
                        "tenant_response_invalid",
                        manifest["digest"],
                    )
                if batch_response.get("status") == "conflict":
                    if not batch_conflicts:
                        return _record_failure(
                            state_store,
                            tenant_site,
                            revision,
                            "tenant_response_invalid",
                            manifest["digest"],
                        )
                    if conflicting_medications:
                        if any(
                            not isinstance(name, str)
                            or not name
                            or name != name.strip()
                            for name in conflicting_medications
                        ):
                            return _record_failure(
                                state_store,
                                tenant_site,
                                revision,
                                "tenant_response_invalid",
                                manifest["digest"],
                            )
                        try:
                            affected_item_codes = (
                                _medicine_item_codes_for_conflicting_medications(
                                    batch, conflicting_medications
                                )
                            )
                        except ValueError:
                            return _record_failure(
                                state_store,
                                tenant_site,
                                revision,
                                "tenant_response_invalid",
                                manifest["digest"],
                            )
                        protected_codes = sorted(affected_item_codes)
                        skipped_codes.extend(protected_codes)
                        conflicting_codes.extend(protected_codes)
                        unaffected_items = [
                            item
                            for item in batch["items"]
                            if item["item_code"] not in affected_item_codes
                        ]
                        if unaffected_items:
                            unaffected_catalogue = dict(batch)
                            unaffected_catalogue["items"] = unaffected_items
                            unaffected_batches = list(
                                _medicine_item_catalogue_batches(
                                    unaffected_catalogue,
                                    _MEDICINE_ITEM_SYNC_BATCH_SIZE,
                                )
                            )
                            batch_queue[0:0] = unaffected_batches
                        continue
                    if len(batch["items"]) > 1:
                        batch_metrics["split_operations"] += 1
                        sub_batches = list(
                            _medicine_item_catalogue_batches(
                                batch,
                                max(1, len(batch["items"]) // 2),
                            )
                        )
                        if len(sub_batches) < 2:
                            return _record_failure(
                                state_store,
                                tenant_site,
                                revision,
                                "tenant_response_invalid",
                                manifest["digest"],
                            )
                        batch_queue[0:0] = sub_batches
                        continue
                    if batch_conflicts != [batch["items"][0]["item_code"]]:
                        return _record_failure(
                            state_store,
                            tenant_site,
                            revision,
                            "tenant_identity_conflict",
                            manifest["digest"],
                            conflicting_item_codes=batch_conflicts,
                        )
                    skipped_codes.extend(batch_conflicts)
                    conflicting_codes.extend(batch_conflicts)
                    continue
                if batch_response.get("status") != "success":
                    error_code = (
                        "tenant_identity_conflict"
                        if batch_conflicts
                        else "tenant_sync_failed"
                    )
                    return _record_failure(
                        state_store,
                        tenant_site,
                        revision,
                        error_code,
                        manifest["digest"],
                        conflicting_item_codes=batch_conflicts,
                    )
                if batch_conflicts and not set(batch_conflicts).issubset(
                    batch_skipped
                ):
                    return _record_failure(
                        state_store,
                        tenant_site,
                        revision,
                        "tenant_identity_conflict",
                        manifest["digest"],
                        conflicting_item_codes=batch_conflicts,
                    )
                batch_outcomes = (
                    batch_created + batch_updated + batch_skipped
                )
                if (
                    any(
                        len(set(codes)) != len(codes)
                        for codes in (
                            batch_created,
                            batch_updated,
                            batch_skipped,
                            batch_missing,
                            batch_conflicts,
                        )
                    )
                    or
                    set(batch_created) & set(batch_updated)
                    or set(batch_created) & set(batch_skipped)
                    or set(batch_updated) & set(batch_skipped)
                    or set(batch_outcomes) & set(batch_missing)
                ):
                    return _record_failure(
                        state_store,
                        tenant_site,
                        revision,
                        "tenant_response_invalid",
                        manifest["digest"],
                    )
                batch_missing.extend(
                    sorted(
                        batch_codes.difference(
                            batch_outcomes, batch_missing, batch_conflicts
                        )
                    )
                )
                if batch_missing:
                    return _record_failure(
                        state_store,
                        tenant_site,
                        revision,
                        "tenant_projection_incomplete",
                        manifest["digest"],
                        missing_item_codes=batch_missing,
                    )
                batch_metrics["successful_batch_count"] += 1
                created_codes.extend(batch_created)
                updated_codes.extend(batch_updated)
                skipped_codes.extend(batch_skipped)
                conflicting_codes.extend(batch_conflicts)
                batch_count += 1
            response = {
                "status": "success",
                "tenant_site": tenant_site,
                "snapshot_manifest": manifest,
                "created_item_codes": created_codes,
                "updated_item_codes": updated_codes,
                "skipped_item_codes": skipped_codes,
                "missing_item_codes": [],
                "conflicting_item_codes": conflicting_codes,
                "batch_count": batch_count,
            }
        else:
            response = transport.apply_projection_batch_atomically(
                tenant_site,
                manifest,
                catalogue,
            )
    except Exception as exc:
        if batch_metrics is not None:
            active_batch_attempt = max(
                active_batch_attempt,
                batch_metrics["batch_attempts"],
            )
        _LOGGER.error(
            "Medicine catalogue synchronization processing failed: "
            "tenant=%s batch_attempt=%d batch_size=%d exception_type=%s",
            tenant_site,
            active_batch_attempt,
            active_batch_size,
            type(exc).__name__,
        )
        return _record_failure(
            state_store,
            tenant_site,
            revision,
            "tenant_sync_failed",
            manifest["digest"],
        )
    finally:
        if batch_metrics is not None:
            failed_batch_count = (
                batch_metrics["batch_attempts"]
                - batch_metrics["successful_batch_count"]
            )
            _LOGGER.info(
                "Medicine catalogue batch summary: tenant=%s "
                "normal_batch_attempts=%d batch_attempts=%d "
                "conflict_responses=%d reported_conflict_batches=%d "
                "split_operations=%d smallest_batch_size=%d "
                "successful_batch_count=%d failed_batch_count=%d",
                tenant_site,
                batch_metrics["normal_batch_attempts"],
                batch_metrics["batch_attempts"],
                batch_metrics["conflict_responses"],
                batch_metrics["reported_conflict_batches"],
                batch_metrics["split_operations"],
                batch_metrics["smallest_batch_size"] or 0,
                batch_metrics["successful_batch_count"],
                failed_batch_count,
            )

    if not isinstance(response, Mapping):
        return _record_failure(state_store, tenant_site, revision, "tenant_response_invalid")

    known_codes = {item["item_code"] for item in catalogue["items"]}
    try:
        created_codes = _response_item_codes(
            response, "created_item_codes", known_codes
        )
        updated_codes = _response_item_codes(
            response, "updated_item_codes", known_codes
        )
        skipped_codes = _response_item_codes(
            response, "skipped_item_codes", known_codes
        )
        missing_codes = _response_item_codes(
            response, "missing_item_codes", known_codes
        )
        conflicting_codes = _response_item_codes(
            response,
            "conflicting_item_codes",
            known_codes,
        )
    except ValueError:
        return _record_failure(state_store, tenant_site, revision, "tenant_response_invalid")

    if (
        str(response.get("tenant_site") or "").strip().lower() != tenant_site
        or response.get("snapshot_manifest") != manifest
    ):
        return _record_failure(state_store, tenant_site, revision, "tenant_response_invalid")
    if conflicting_codes and not set(conflicting_codes).issubset(skipped_codes):
        return _record_failure(
            state_store,
            tenant_site,
            revision,
            "tenant_identity_conflict",
            conflicting_item_codes=conflicting_codes,
            missing_item_codes=missing_codes,
        )
    if any(
        len(set(codes)) != len(codes)
        for codes in (
            created_codes,
            updated_codes,
            skipped_codes,
            missing_codes,
            conflicting_codes,
        )
    ):
        return _record_failure(state_store, tenant_site, revision, "tenant_response_invalid")
    outcome_codes = created_codes + updated_codes + skipped_codes
    if (
        set(created_codes) & set(updated_codes)
        or set(created_codes) & set(skipped_codes)
        or set(updated_codes) & set(skipped_codes)
        or set(outcome_codes) & set(missing_codes)
        or not set(conflicting_codes).issubset(skipped_codes)
    ):
        return _record_failure(state_store, tenant_site, revision, "tenant_response_invalid")
    unreported_codes = known_codes.difference(
        outcome_codes, missing_codes, conflicting_codes
    )
    if unreported_codes:
        missing_codes.extend(sorted(unreported_codes))
    if missing_codes:
        return _record_failure(
            state_store,
            tenant_site,
            revision,
            "tenant_projection_incomplete",
            missing_item_codes=missing_codes,
        )
    if response.get("status") != "success":
        return _record_failure(state_store, tenant_site, revision, "tenant_sync_failed")

    counts = {
        "created": len(created_codes),
        "updated": len(updated_codes),
        "skipped": len(skipped_codes),
    }
    state_store.record_success(tenant_site, revision, counts, manifest["digest"])
    return {
        "status": "success",
        "tenant_site": tenant_site,
        "snapshot_manifest": manifest,
        **counts,
        "created_item_codes": created_codes,
        "updated_item_codes": updated_codes,
        "skipped_item_codes": skipped_codes,
        "conflicting_item_codes": conflicting_codes,
    }
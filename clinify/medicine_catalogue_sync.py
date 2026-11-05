import hashlib
import json
import logging
import os
import re
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime
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
        self.http_session = http_session or requests
        self.timeout = timeout

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

        response = self.http_session.post(
            endpoint,
            headers={
                "Authorization": f"token {api_key}:{api_secret}",
                "Accept": "application/json",
            },
            json={
                "tenant_site": tenant.site_name,
                "control_site": configured_control_site(),
                "snapshot_manifest": dict(snapshot_manifest),
                "products": [dict(product) for product in products],
            },
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
):
    """Authenticated tenant endpoint applying one validated batch atomically."""
    tenant_site = str(tenant_site or "").strip().lower()
    _require_tenant_sync_request(tenant_site, control_site)

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


def synchronize_tenant_catalogue(
    tenant_site,
    catalogue_revision,
    transport=None,
    state_store=None,
):
    """Validate and request an atomic projection update through an injected transport.

    The transport must authenticate the tenant, apply the complete batch in one
    tenant-local transaction, upsert by central_product_id, preserve omitted
    products, and return only after that transaction succeeds. The default is
    FrappeApiTokenTenantTransport; transports are injectable for isolated tests.
    No direct cross-site database connection is used.
    """
    control_site = require_control_site_admin()
    tenant_site = _safe_sync_target(tenant_site, control_site)
    revision = validate_catalogue_revision(catalogue_revision)
    if state_store is None:
        state_store = FrappeCatalogueSyncStateStore()
    if transport is None:
        transport = FrappeApiTokenTenantTransport()
    state_store.record_attempt(tenant_site, revision)
    try:
        source_records = frappe.get_all(
            "Clinify Medicine Product",
            fields=list(_PRODUCT_FIELDS),
            order_by="central_product_id asc",
        )
    except Exception:
        return _record_failure(state_store, tenant_site, revision, "central_catalogue_unavailable")

    try:
        manifest, products = create_snapshot_manifest(source_records, revision)
    except (TypeError, ValueError):
        return _record_failure(state_store, tenant_site, revision, "invalid_central_batch")

    state_store.record_attempt(tenant_site, revision, manifest["digest"])

    try:
        response = transport.apply_projection_batch_atomically(
            tenant_site,
            manifest,
            products,
        )
    except Exception:
        return _record_failure(
            state_store,
            tenant_site,
            revision,
            "tenant_sync_failed",
            manifest["digest"],
        )

    if not isinstance(response, Mapping):
        return _record_failure(state_store, tenant_site, revision, "tenant_response_invalid")

    known_ids = {product["central_product_id"] for product in products}
    try:
        created_ids = _response_product_ids(response, "created_product_ids", known_ids)
        updated_ids = _response_product_ids(response, "updated_product_ids", known_ids)
        skipped_ids = _response_product_ids(response, "skipped_product_ids", known_ids)
        missing_ids = _response_product_ids(response, "missing_product_ids", known_ids)
        conflicting_ids = _response_product_ids(
            response,
            "conflicting_product_ids",
            known_ids,
        )
    except ValueError:
        return _record_failure(state_store, tenant_site, revision, "tenant_response_invalid")

    if (
        str(response.get("tenant_site") or "").strip().lower() != tenant_site
        or response.get("snapshot_manifest") != manifest
    ):
        return _record_failure(state_store, tenant_site, revision, "tenant_response_invalid")
    outcome_ids = created_ids + updated_ids + skipped_ids
    if len(set(outcome_ids + missing_ids + conflicting_ids)) != len(
        outcome_ids + missing_ids + conflicting_ids
    ):
        return _record_failure(state_store, tenant_site, revision, "tenant_response_invalid")
    unreported_ids = known_ids.difference(outcome_ids, missing_ids, conflicting_ids)
    if unreported_ids:
        missing_ids.extend(sorted(unreported_ids))
    if conflicting_ids:
        return _record_failure(
            state_store,
            tenant_site,
            revision,
            "tenant_identity_conflict",
            conflicting_product_ids=conflicting_ids,
            missing_product_ids=missing_ids,
        )
    if missing_ids:
        return _record_failure(
            state_store,
            tenant_site,
            revision,
            "tenant_projection_incomplete",
            missing_product_ids=missing_ids,
        )
    if response.get("status") != "success":
        return _record_failure(state_store, tenant_site, revision, "tenant_sync_failed")

    counts = {
        "created": len(created_ids),
        "updated": len(updated_ids),
        "skipped": len(skipped_ids),
    }
    state_store.record_success(tenant_site, revision, counts, manifest["digest"])
    return {
        "status": "success",
        "tenant_site": tenant_site,
        "snapshot_manifest": manifest,
        **counts,
        "created_product_ids": created_ids,
        "updated_product_ids": updated_ids,
        "skipped_product_ids": skipped_ids,
    }
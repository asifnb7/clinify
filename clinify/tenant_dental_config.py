# Copyright (c) 2026, Salniz Technologies and contributors
# For license information, please see license.txt

"""Tenant dental service configuration and pricing layer.

Clinify separates three layers:

A. Central standard catalogue (``Dental Service``) - shared identity/metadata.
B. Tenant service configuration (``Clinify Tenant Dental Service``) - which
   standard services a tenant offers plus any clinic-specific custom services.
C. Tenant pricing - a fixed selling price or a set of variable price options.

This module owns layer B/C logic shared between provisioning, reconciliation
and billing. The price resolver is intentionally pure (no database access) so
it can be unit-tested without a live site.
"""

import frappe
from frappe import _
from frappe.utils import flt


PRICING_TYPE_FIXED = "Fixed"
PRICING_TYPE_VARIABLE = "Variable"

# Central catalogue pricing basis that maps a NEW tenant configuration to
# Variable pricing (with predefined min/mid/max options). Every other central
# basis (Fixed, Per Tooth, Per Cap, Per Arch, ...) seeds a Fixed tenant price.
PRICING_BASIS_RANGE = "Range"

SERVICE_TYPE_STANDARD = "Standard"
SERVICE_TYPE_CUSTOM = "Custom"

CONFIG_DOCTYPE = "Clinify Tenant Dental Service"


class DentalPriceResolutionError(Exception):
	"""Raised when a billable dental service has no valid tenant price."""


def resolve_tenant_dental_price(config, selected_option=None, quantity=1):
	"""Resolve the selling rate for a tenant-configured dental service.

	``config`` is any object/dict exposing ``pricing_type``, ``fixed_price``,
	``price_options``, ``is_enabled`` and ``is_active``. Each price option
	exposes ``option_label``, ``name``, ``price`` and ``is_enabled``.

	Returns the resolved positive rate. Raises ``DentalPriceResolutionError``
	for any condition that would otherwise produce a silent zero rate or an
	unsafe fallback (central minimum/maximum price, another tenant's price).
	"""

	label = _config_label(config)

	if not config.get("is_active"):
		raise DentalPriceResolutionError(
			_("Dental service '{0}' is inactive.").format(label)
		)

	if not config.get("is_enabled"):
		raise DentalPriceResolutionError(
			_("Dental service '{0}' is disabled for this clinic.").format(label)
		)

	pricing_type = config.get("pricing_type")

	if pricing_type == PRICING_TYPE_FIXED:
		rate = flt(config.get("fixed_price"))
		if rate <= 0:
			raise DentalPriceResolutionError(
				_(
					"No tenant selling price is configured for dental service "
					"'{0}'."
				).format(label)
			)
		return rate

	if pricing_type == PRICING_TYPE_VARIABLE:
		if not selected_option:
			raise DentalPriceResolutionError(
				_(
					"A price option must be selected for variable dental "
					"service '{0}'."
				).format(label)
			)

		option = _find_enabled_option(config.get("price_options"), selected_option)
		if option is None:
			raise DentalPriceResolutionError(
				_(
					"The selected price option for dental service '{0}' is "
					"not valid or is disabled."
				).format(label)
			)

		rate = flt(option.get("price"))
		if rate <= 0:
			raise DentalPriceResolutionError(
				_(
					"The selected price option for dental service '{0}' has "
					"no price."
				).format(label)
			)
		return rate

	raise DentalPriceResolutionError(
		_("Dental service '{0}' has no pricing type configured.").format(label)
	)


def _find_enabled_option(options, selected_option):
	"""Return the enabled option selected by ``option_label`` or ``name``.

	The UI/API contract selects an option by its human-facing ``option_label``
	(e.g. "Minimum"), while the encounter Link field and legacy callers pass the
	child row's database ``name``. Match either identifier so both contracts
	resolve, but stay fail-closed: an unknown or disabled option never resolves.
	"""
	for option in options or []:
		if selected_option not in (
			option.get("option_label"),
			option.get("name"),
		):
			continue
		if not option.get("is_enabled"):
			return None
		return option
	return None


def _config_label(config):
	if config.get("service_type") == SERVICE_TYPE_CUSTOM:
		return config.get("custom_service_name") or config.get("name") or "Custom Service"
	return config.get("name") or config.get("dental_service") or "Dental Service"

# ---------------------------------------------------------------------------
# Database-backed helpers (run inside a tenant site)
# ---------------------------------------------------------------------------

def get_current_clinic_code():
	"""Return the current tenant's clinic code, or ``None`` on the control plane."""
	if not frappe.db.exists("DocType", "Clinic Configuration"):
		return None
	return frappe.db.get_single_value("Clinic Configuration", "clinic_code")


def tenant_config_for_standard_service(service_code):
	"""Return the tenant's configuration document for a standard service."""
	if not frappe.db.exists(CONFIG_DOCTYPE, service_code):
		return None
	return frappe.get_doc(CONFIG_DOCTYPE, service_code)


def ensure_tenant_dental_service_configs():
	"""Idempotently create tenant configurations from the standard catalogue.

	- A new standard service yields a new tenant configuration.
	- An existing tenant configuration is never overwritten: tenant selling
	  price, enabled/disabled state, pricing type, variable options and custom
	  services all survive reconciliation untouched.
	- Central reference metadata (ERPNext item, default qty, requires tooth,
	  pricing basis) is kept in sync because the tenant does not own it.

	Returns a small summary dict. Performs no writes when nothing changes.
	"""

	created = 0
	preserved = 0
	skipped = 0

	if not frappe.db.exists("DocType", CONFIG_DOCTYPE):
		return {"created": created, "preserved": preserved, "skipped": skipped}

	for service in frappe.get_all(
		"Dental Service",
		filters={"is_active": 1},
		fields=[
			"name",
			"service_code",
			"service_name",
			"erpnext_item",
			"default_qty",
			"requires_tooth",
			"pricing_basis",
			"minimum_price",
			"maximum_price",
		],
		order_by="service_name asc",
	):
		service_code = service.get("service_code") or service.get("name")

		if frappe.db.exists(CONFIG_DOCTYPE, service_code):
			preserved += 1
			_tenant_config_sync_reference_metadata(service, service_code)
			continue

		# NEW tenant configuration. pricing_type is derived from the central
		# pricing_basis, but ONLY Range maps to Variable pricing. Every other
		# basis (Fixed, Per Tooth, Per Cap, Per Arch, ...) keeps the existing
		# behaviour: a single Fixed selling price seeded from the central
		# reference minimum. That seed is a one-time, tenant-owned value that
		# reconciliation never rewrites.
		pricing_basis = service.get("pricing_basis")

		if pricing_basis == PRICING_BASIS_RANGE:
			price_options = _range_price_options(service)
			if price_options is None:
				# Invalid/missing Range bounds: refuse to create a Variable
				# configuration we cannot populate with valid, billable
				# prices. Skip it; a future reconciliation provisions it
				# correctly once the central bounds are valid.
				skipped += 1
				continue

			config = frappe.get_doc(
				{
					"doctype": CONFIG_DOCTYPE,
					"service_type": SERVICE_TYPE_STANDARD,
					"dental_service": service_code,
					"pricing_type": PRICING_TYPE_VARIABLE,
					"price_options": price_options,
					"is_enabled": 1,
					"is_active": 1,
				}
			)
		else:
			config = frappe.get_doc(
				{
					"doctype": CONFIG_DOCTYPE,
					"service_type": SERVICE_TYPE_STANDARD,
					"dental_service": service_code,
					"pricing_type": PRICING_TYPE_FIXED,
					# Seed a starting tenant price from the central reference so
					# a freshly provisioned tenant is immediately billable. This
					# is a one-time tenant-owned value; reconciliation never
					# rewrites it.
					"fixed_price": flt(service.get("minimum_price")) or 0,
					"is_enabled": 1,
					"is_active": 1,
				}
			)

		config.insert(ignore_permissions=True)
		created += 1

	if created:
		frappe.db.commit()

	return {
		"created": created,
		"preserved": preserved,
		"skipped": skipped,
	}


def _range_price_options(service):
	"""Return three deterministic, enabled price options for a Range service.

	Returns a list of ``{option_label, price, is_enabled}`` dicts for the
	central range's minimum, midpoint and maximum, or ``None`` when the central
	Range bounds are missing or invalid (non-positive, or minimum > maximum) so
	the caller never creates an unbillable Variable configuration.

	The midpoint is ``(minimum + maximum) / 2`` passed through ``flt`` with no
	precision argument, which performs no rounding and therefore preserves the
	full numeric precision of the calculated value.
	"""

	minimum = flt(service.get("minimum_price"))
	maximum = flt(service.get("maximum_price"))

	if minimum <= 0 or maximum <= 0 or minimum > maximum:
		return None

	midpoint = flt((minimum + maximum) / 2)

	return [
		{"option_label": "Minimum", "price": minimum, "is_enabled": 1},
		{"option_label": "Midpoint", "price": midpoint, "is_enabled": 1},
		{"option_label": "Maximum", "price": maximum, "is_enabled": 1},
	]


def _tenant_config_sync_reference_metadata(service, service_code):
	"""Keep central reference metadata aligned without touching tenant pricing."""
	config = frappe.get_doc(CONFIG_DOCTYPE, service_code)
	changed = False

	if config.erpnext_item != service.get("erpnext_item"):
		config.erpnext_item = service.get("erpnext_item")
		changed = True

	if config.default_qty != (service.get("default_qty") or 1):
		config.default_qty = service.get("default_qty") or 1
		changed = True

	if bool(config.requires_tooth) != bool(service.get("requires_tooth")):
		config.requires_tooth = service.get("requires_tooth")
		changed = True

	if config.pricing_basis != service.get("pricing_basis"):
		config.pricing_basis = service.get("pricing_basis")
		changed = True

	if changed:
		config.save(ignore_permissions=True)

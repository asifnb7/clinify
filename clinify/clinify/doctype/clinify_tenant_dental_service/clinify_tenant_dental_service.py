# Copyright (c) 2026, Salniz Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from clinify.tenant_dental_config import SERVICE_TYPE_CUSTOM


class ClinifyTenantDentalService(Document):
	"""Tenant-owned dental service configuration and pricing.

	This is the tenant layer. It never mutates the central ``Dental Service``
	standard catalogue and never stores tenant selling prices there. Each
	tenant runs on its own site/database, so records are already isolated to
	the tenant by the site boundary; ``clinic_code`` is an explicit audit tag
	used as an additional server-side guard.
	"""

	def autoname(self):
		if self.service_type == "Standard":
			if not self.dental_service:
				frappe.throw(
					_("Standard Dental Service is required for a Standard service.")
				)
			# The central Dental Service autoname is its service_code, so the
			# linked name is a stable, tenant-local key.
			self.name = self.dental_service
			return

		if not self.custom_service_name:
			frappe.throw(
				_("Custom Service Name is required for a Custom service.")
			)

		base = "CUSTOM-" + frappe.scrub(self.custom_service_name)[:60].upper()
		self.name = self._unique_name(base)

	def _unique_name(self, base):
		if not frappe.db.exists("Clinify Tenant Dental Service", base):
			return base
		return "{0}-{1}".format(base, frappe.generate_hash(length=6).upper())

	def validate(self):
		self._stamp_tenant_scope()
		self._sync_standard_reference_metadata()
		self._validate_identity()
		self._validate_pricing()

	def _stamp_tenant_scope(self):
		"""Record the owning tenant identity for audit and defense-in-depth."""
		if frappe.db.exists("DocType", "Clinic Configuration"):
			clinic_code = frappe.db.get_single_value(
				"Clinic Configuration",
				"clinic_code",
			)
			if clinic_code:
				self.clinic_code = clinic_code

	def _sync_standard_reference_metadata(self):
		"""Copy central reference metadata for Standard services.

		Only reference metadata is copied. Tenant selling prices, enabled state
		and variable options are never derived from the central catalogue here.
		"""
		if self.service_type != "Standard" or not self.dental_service:
			return

		reference = frappe.db.get_value(
			"Dental Service",
			self.dental_service,
			["erpnext_item", "default_qty", "requires_tooth", "pricing_basis"],
			as_dict=True,
		)

		if not reference:
			frappe.throw(
				_("Standard Dental Service '{0}' does not exist.").format(
					self.dental_service
				)
			)

		self.erpnext_item = reference.erpnext_item
		self.default_qty = reference.default_qty or 1
		self.requires_tooth = reference.requires_tooth
		self.pricing_basis = reference.pricing_basis

	def _validate_identity(self):
		if self.service_type == "Standard":
			if not self.dental_service:
				frappe.throw(
					_("Standard Dental Service is required for a Standard service.")
				)
			return

		if not self.custom_service_name:
			frappe.throw(
				_("Custom Service Name is required for a Custom service.")
			)

		if not self.erpnext_item:
			frappe.throw(
				_("ERPNext Item is required for a Custom service.")
			)

		if not frappe.db.exists("Item", self.erpnext_item):
			frappe.throw(
				_("ERPNext Item '{0}' does not exist.").format(self.erpnext_item)
			)

	def _validate_pricing(self):
		"""Prevent an enabled service from being saved in an unbillable state.

		Billing independently re-validates the price, so this is an early guard
		rather than the sole protection against a silent zero rate.
		"""
		if not self.is_enabled:
			return

		if self.pricing_type == "Fixed":
			if flt(self.fixed_price) <= 0:
				frappe.throw(
					_(
						"A positive Fixed Selling Price is required to enable "
						"service '{0}'."
					).format(self.service_display_name)
				)
			return

		if self.pricing_type == "Variable":
			has_valid_option = any(
				flt(option.price) > 0 and option.is_enabled
				for option in (self.price_options or [])
			)
			if not has_valid_option:
				frappe.throw(
					_(
						"At least one enabled Variable Price Option with a "
						"positive price is required to enable service '{0}'."
					).format(self.service_display_name)
				)

	@property
	def service_display_name(self):
		if self.service_type == "Custom":
			return self.custom_service_name or self.name
		standard_name = frappe.db.get_value(
			"Dental Service",
			self.dental_service,
			"service_name",
		)
		return standard_name or self.dental_service or self.name

	def on_trash(self):
		"""Protect historical references.

		A configuration that has already been used for billing (or is queued on
		an encounter) must not be physically deleted. Deactivate it instead so
		historical invoices and encounters keep resolving correctly.
		"""
		references = []

		if self.erpnext_item and frappe.db.exists(
			"Sales Invoice Item",
			{"item_code": self.erpnext_item},
		):
			references.append("Sales Invoice Item")

		if self.dental_service and frappe.db.exists(
			"Clinify Encounter Service",
			{"dental_service": self.dental_service},
		):
			references.append("Clinify Encounter Service")

		# Custom services are referenced on encounters through
		# tenant_dental_service rather than the central catalogue link.
		if self.service_type == SERVICE_TYPE_CUSTOM and frappe.db.exists(
			"Clinify Encounter Service",
			{"tenant_dental_service": self.name},
		):
			references.append("Clinify Encounter Service")

		if references:
			frappe.throw(
				_(
					"Service '{0}' has been used in {1}. It cannot be deleted. "
					"Deactivate it instead to preserve historical references."
				).format(
					self.service_display_name,
					" and ".join(references),
				)
			)

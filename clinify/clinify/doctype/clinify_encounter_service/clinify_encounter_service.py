# Copyright (c) 2026, Salniz Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ClinifyEncounterService(Document):
	def validate(self):
		self._validate_single_service_reference()

	def _validate_single_service_reference(self):
		"""A row must reference exactly one service.

		Standard services use the central ``dental_service`` link; custom
		tenant services use ``tenant_dental_service``. Reject both-empty and
		both-populated states so billing always resolves one unambiguous
		tenant configuration.
		"""

		has_standard = bool(self.dental_service)
		has_tenant = bool(self.tenant_dental_service)

		if has_standard and has_tenant:
			frappe.throw(
				_(
					"Row {0}: select either a standard Dental Service or a "
					"custom Tenant Dental Service, not both."
				).format(self.idx)
			)

		if not has_standard and not has_tenant:
			frappe.throw(
				_(
					"Row {0}: a Dental Service or Tenant Dental Service is "
					"required."
				).format(self.idx)
			)

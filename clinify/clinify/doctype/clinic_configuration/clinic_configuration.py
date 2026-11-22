# Copyright (c) 2026, Salniz Technologies and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


class ClinicConfiguration(Document):
	def validate(self):
		if self.brand_primary_color and not re.fullmatch(
			r"#[0-9A-Fa-f]{6}", self.brand_primary_color.strip()
		):
			frappe.throw("Primary Brand Colour must be a six-digit hex colour.")

		# Tenant administrators may edit the clinic profile, but these values
		# are owned by Clinify provisioning and subscription management.
		roles = frappe.get_roles()
		if (
			"Clinify Clinic Admin" in roles
			and "System Manager" not in roles
			and not self.is_new()
		):
			previous = frappe.get_single("Clinic Configuration")
			profile_fields = {
				"clinic_name", "clinic_email", "clinic_phone", "clinic_website",
				"clinic_logo", "brand_primary_color", "clinic_address",
				"city", "state", "country", "pincode",
			}
			for field in self.meta.fields:
				fieldname = field.fieldname
				if not fieldname or fieldname in profile_fields:
					continue
				if previous and self.get(fieldname) != previous.get(fieldname):
					frappe.throw("Clinic administrators cannot change {}.".format(field.label or fieldname))

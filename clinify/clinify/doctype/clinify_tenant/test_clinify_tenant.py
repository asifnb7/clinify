# Copyright (c) 2026, Salniz Technologies and Contributors
# See license.txt

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase


class TestClinifyTenant(FrappeTestCase):
	def test_print_footer_fields_are_available_with_safe_defaults(self):
		meta = frappe.get_meta("Clinify Tenant")
		self.assertEqual(meta.get_field("print_footer_mode").default, "Powered by Clinify")
		self.assertEqual(meta.get_field("print_footer_text").default, "Powered by Clinify")
		self.assertEqual(meta.get_field("print_footer_alignment").default, "Center")
		self.assertEqual(int(meta.get_field("print_footer_bold").default), 1)
		self.assertEqual(int(meta.get_field("show_footer_on_prescription").default), 1)
		self.assertEqual(int(meta.get_field("show_footer_on_invoice").default), 1)
		self.assertEqual(meta.get_field("print_footer_section").label, "Prescription Footer")
		self.assertEqual(meta.get_field("show_footer_on_prescription").label, "Enable Prescription Footer")
		self.assertEqual(meta.get_field("print_footer_mode").label, "Prescription Footer Type")
		self.assertEqual(meta.get_field("print_footer_mode").options.splitlines(), ["None", "Powered by Clinify", "Custom Message"])
		self.assertEqual(meta.get_field("print_footer_text").label, "Prescription Footer Message")
		self.assertEqual(meta.get_field("invoice_footer_section").label, "Invoice Footer")
		self.assertEqual(meta.get_field("invoice_footer_mode").label, "Invoice Footer Type")
		self.assertEqual(meta.get_field("invoice_footer_mode").options.splitlines(), ["None", "Powered by Clinify", "Custom Message"])
		self.assertEqual(meta.get_field("invoice_footer_text").label, "Invoice Footer Message")
		self.assertEqual(meta.get_field("invoice_footer_alignment").default, "Center")
		self.assertEqual(int(meta.get_field("invoice_footer_bold").default), 1)

	def test_control_plane_footer_fields_use_existing_admin_permission(self):
		meta = frappe.get_meta("Clinify Tenant")
		self.assertTrue(
			any(permission.role == "System Manager" and permission.write for permission in meta.permissions)
		)
		self.assertFalse(
			any(permission.role == "Clinify Clinic Admin" and permission.write for permission in meta.permissions)
		)

	def test_invalid_footer_mode_and_alignment_are_rejected(self):
		from clinify.clinify.doctype.clinify_tenant.clinify_tenant import ClinifyTenant

		doc = ClinifyTenant({"doctype": "Clinify Tenant", "print_footer_mode": "Injected"})
		with self.assertRaises(ValidationError):
			doc.validate()

		doc = ClinifyTenant({"doctype": "Clinify Tenant", "print_footer_alignment": "right; color:red"})
		with self.assertRaises(ValidationError):
			doc.validate()

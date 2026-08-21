# Copyright (c) 2026, Salniz Technologies and Contributors
# See license.txt

import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase


class TestClinicConfiguration(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta("Clinic Configuration")
		cls.form_script = Path(__file__).with_name("clinic_configuration.js").read_text()

	def test_required_identity_field(self):
		self.assertTrue(self.meta.get_field("clinic_name").reqd)

	def test_platform_status_options(self):
		self.assertEqual(
			self.meta.get_field("clinic_status").options.splitlines()[1:],
			["Active", "Inactive", "Suspended"],
		)
		self.assertEqual(
			self.meta.get_field("subscription_status").options.splitlines()[1:],
			["Trial", "Active", "Expired", "Suspended"],
		)

	def test_activation_date_field_and_active_rule(self):
		activation_date = self.meta.get_field("activation_date")

		self.assertEqual(activation_date.fieldtype, "Date")
		self.assertIn('frm.doc.clinic_status === "Active"', self.form_script)
		self.assertIn("!frm.doc.activation_date", self.form_script)

	def test_form_script_is_valid_json_free_javascript(self):
		self.assertNotIn("clinic_code", self.form_script.split("validate", 1)[1])

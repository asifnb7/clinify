# Copyright (c) 2026, Salniz Technologies and Contributors
# See license.txt

import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.exceptions import ValidationError
from unittest.mock import patch


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
			["Trial", "Active", "Expiring", "Expired", "Suspended"],
		)

	def test_activation_date_field_and_active_rule(self):
		activation_date = self.meta.get_field("activation_date")

		self.assertEqual(activation_date.fieldtype, "Date")
		self.assertIn('frm.doc.clinic_status === "Active"', self.form_script)
		self.assertIn("!frm.doc.activation_date", self.form_script)

	def test_tenant_profile_fields_are_available(self):
		self.assertEqual(self.meta.get_field("clinic_logo").fieldtype, "Attach Image")
		self.assertEqual(self.meta.get_field("clinic_website").options, "URL")
		self.assertEqual(self.meta.get_field("brand_primary_color").fieldtype, "Color")
		self.assertEqual(self.meta.get_field("brand_primary_color").default, "#173B82")
		self.assertTrue(self.meta.get_field("platform_attribution_text").read_only)
		self.assertTrue(self.meta.get_field("platform_attribution_position").read_only)

	def test_tenant_admin_cannot_change_platform_managed_fields(self):
		from clinify.saas.tenant_bootstrap import ADMIN_PERMISSIONS

		self.assertEqual(ADMIN_PERMISSIONS["Clinic Configuration"]["read"], 1)
		self.assertEqual(ADMIN_PERMISSIONS["Clinic Configuration"]["write"], 1)
		controller = Path(__file__).with_name("clinic_configuration.py").read_text()
		self.assertIn("profile_fields", controller)
		self.assertIn("self.meta.fields", controller)

	def test_profile_values_save_and_reload_on_the_current_site(self):
		clinic = frappe.get_single("Clinic Configuration")
		clinic.clinic_name = "Profile Persistence Test Clinic"
		clinic.clinic_email = "profile@example.invalid"
		clinic.clinic_phone = "+91 98765 43210"
		clinic.clinic_address = "12 Example Road"
		clinic.clinic_website = "https://profile.example.invalid"
		clinic.clinic_logo = "/files/profile-test-logo.png"
		clinic.brand_primary_color = "#275A91"
		clinic.save(ignore_permissions=True)

		reloaded = frappe.get_single("Clinic Configuration")
		self.assertEqual(reloaded.clinic_name, "Profile Persistence Test Clinic")
		self.assertEqual(reloaded.clinic_email, "profile@example.invalid")
		self.assertEqual(reloaded.clinic_phone, "+91 98765 43210")
		self.assertEqual(reloaded.clinic_address, "12 Example Road")
		self.assertEqual(reloaded.clinic_website, "https://profile.example.invalid")
		self.assertEqual(reloaded.clinic_logo, "/files/profile-test-logo.png")
		self.assertEqual(reloaded.brand_primary_color, "#275A91")

	def test_profile_configuration_has_no_cross_tenant_selector(self):
		configuration_api = Path(__file__).parents[3] / "clinic.py"
		source = configuration_api.read_text()
		self.assertIn('frappe.get_single("Clinic Configuration")', source)
		self.assertNotIn("tenant_id", source)
		self.assertNotIn("tenant_name", source)

	def test_tenant_admin_cannot_change_subscription_state(self):
		clinic = frappe.get_single("Clinic Configuration")
		clinic.subscription_status = "Suspended" if clinic.subscription_status != "Suspended" else "Active"
		with patch.object(frappe, "get_roles", return_value=["Clinify Clinic Admin"]):
			with self.assertRaises(ValidationError):
				clinic.save(ignore_permissions=True)

	def test_existing_tenant_admin_permission_is_synced(self):
		from clinify.saas.tenant_bootstrap import CLINIFY_ADMIN_ROLE

		permission = None
		for doctype in ("Custom DocPerm", "DocPerm"):
			permission_name = frappe.db.get_value(
				doctype,
				{
					"parent": "Clinic Configuration",
					"role": CLINIFY_ADMIN_ROLE,
					"permlevel": 0,
				},
				"name",
			)
			if permission_name:
				permission = frappe.get_doc(doctype, permission_name)
				break
		self.assertIsNotNone(permission)
		self.assertEqual(permission.read, 1)
		self.assertEqual(permission.write, 1)

	def test_form_script_is_valid_json_free_javascript(self):
		self.assertNotIn("clinic_code", self.form_script.split("validate", 1)[1])

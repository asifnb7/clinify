// Copyright (c) 2026, Salniz Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Clinic Configuration", {
	refresh(frm) {
		if (frappe.user.has_role("System Manager")) return;
		[
			"section_break_xley", "consultation_section", "free_followup_days",
			"allow_multiple_free_followups", "clinic_code", "contact_person",
			"department", "platform_section", "clinic_status",
			"subscription_status", "activation_date",
		].forEach((field) => frm.toggle_display(field, false));
	},
	validate(frm) {
		if (frm.doc.brand_primary_color && !/^#[0-9a-f]{6}$/i.test(frm.doc.brand_primary_color)) {
			frappe.throw(__("Primary Brand Colour must be a six-digit hex colour."));
		}
		const clinic_statuses = ["Active", "Inactive", "Suspended"];
		const subscription_statuses = ["Trial", "Active", "Expiring", "Expired", "Suspended"];

		if (!clinic_statuses.includes(frm.doc.clinic_status)) {
			frappe.throw(__("Please select a valid Clinic Status."));
		}

		if (!subscription_statuses.includes(frm.doc.subscription_status)) {
			frappe.throw(__("Please select a valid Subscription Status."));
		}

		if (frm.doc.clinic_status === "Active" && !frm.doc.activation_date) {
			frappe.throw(__("Activation Date is required for an active clinic."));
		}
	},
});

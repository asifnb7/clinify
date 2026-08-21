// Copyright (c) 2026, Salniz Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Clinic Configuration", {
	validate(frm) {
		const clinic_statuses = ["Active", "Inactive", "Suspended"];
		const subscription_statuses = ["Trial", "Active", "Expired", "Suspended"];

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

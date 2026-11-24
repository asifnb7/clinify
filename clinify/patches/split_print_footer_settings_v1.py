"""Copy the former shared footer values into each document footer setting."""

import frappe


def execute():
	from clinify.saas.sso import _is_control_site

	if not _is_control_site():
		return {"migrated": 0, "skipped": "not the control site"}

	from clinify.saas.orchestrator import _sync_tenant_print_footer_config

	fields = {
		"invoice_footer_mode": "print_footer_mode",
		"invoice_footer_text": "print_footer_text",
		"invoice_footer_alignment": "print_footer_alignment",
		"invoice_footer_bold": "print_footer_bold",
	}
	migrated = 0

	for row in frappe.get_all("Clinify Tenant", pluck="name"):
		tenant = frappe.get_doc("Clinify Tenant", row)
		changed = False
		for target, source in fields.items():
			value = tenant.get(source)
			if tenant.get(target) != value:
				tenant.set(target, value)
				changed = True

		if changed:
			tenant.save(ignore_permissions=True)
			migrated += 1
		elif tenant.provisioning_status == "Ready":
			_sync_tenant_print_footer_config(tenant)

	return {"migrated": migrated}

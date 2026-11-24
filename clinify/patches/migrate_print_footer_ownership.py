"""Move legacy tenant print footer settings into Clinify Tenant records."""

import json

import frappe

from clinify.saas.print_footer_config import tenant_fields_from_legacy_footer


def execute():
	from clinify.saas.sso import _is_control_site

	if not _is_control_site():
		return {"migrated": 0, "skipped": "not the control site"}

	from clinify.saas.orchestrator import (
		_run_bench,
		_site_exists,
		_sync_tenant_print_footer_config,
	)

	tenants = frappe.get_all(
		"Clinify Tenant",
		fields=["name", "site_name", "provisioning_status"],
	)
	migrated = 0

	for row in tenants:
		tenant = frappe.get_doc("Clinify Tenant", row.name)
		legacy = {}
		site_name = str(tenant.site_name or "").strip().lower()

		if site_name and _site_exists(site_name):
			try:
				output = _run_bench([
					"--site",
					site_name,
					"execute",
					"clinify.clinic.get_legacy_platform_footer_settings",
				])
				legacy = json.loads(output) if output else {}
			except Exception:
				frappe.log_error(
					title="Legacy print footer migration",
					message="Could not read legacy footer values for {}".format(
						site_name
					),
				)

		values = tenant_fields_from_legacy_footer(legacy)
		changed = any(
			tenant.get(fieldname) != value
			for fieldname, value in values.items()
		)
		for fieldname, value in values.items():
			tenant.set(fieldname, value)

		if changed:
			tenant.save(ignore_permissions=True)
		elif tenant.provisioning_status == "Ready":
			_sync_tenant_print_footer_config(tenant)

		migrated += 1

	return {"migrated": migrated}

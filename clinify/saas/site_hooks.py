import frappe

from clinify.saas.sso import _is_control_site


TENANT_HIDDEN_WORKSPACES = (
	"Administration",
	"Build",
	"ERPNext Settings",
	"Integrations",
	"Quality",
	"Reports",
	"Support",
	"Tools",
	"Users",
	"Website",
)


def _restrict_tenant_workspaces():
	"""Hide empty or system-only workspaces on tenant sites only."""
	if _is_control_site():
		return

	for workspace_name in TENANT_HIDDEN_WORKSPACES:
		if not frappe.db.exists("Workspace", workspace_name):
			continue

		workspace = frappe.get_doc("Workspace", workspace_name)
		roles = frappe.get_all(
			"Has Role",
			filters={
				"parent": workspace_name,
				"parenttype": "Workspace",
				"parentfield": "roles",
			},
			pluck="role",
		)
		if workspace.is_hidden and workspace.public and roles == ["System Manager"]:
			continue

		frappe.db.set_value(
			"Workspace",
			workspace_name,
			{"is_hidden": 1, "public": 1},
			update_modified=False,
		)
		frappe.db.delete(
			"Has Role",
			{
				"parent": workspace_name,
				"parenttype": "Workspace",
				"parentfield": "roles",
			},
		)
		frappe.get_doc({
			"doctype": "Has Role",
			"parent": workspace_name,
			"parenttype": "Workspace",
			"parentfield": "roles",
			"role": "System Manager",
		}).insert(ignore_permissions=True)

	frappe.clear_cache(doctype="Workspace")


def _protect_control_plane_ui():
    if _is_control_site():
        return

    # SaaS Workspace is control-plane UI and must not be public on tenants.
    if frappe.db.exists("Workspace", "SaaS"):
        meta = frappe.get_meta("Workspace")
        values = {"public": 0}

        if meta.has_field("is_hidden"):
            values["is_hidden"] = 1

        frappe.db.set_value(
            "Workspace",
            "SaaS",
            values,
            update_modified=False,
        )

    # The standalone SaaS Dashboard Page is also control-plane UI.
    # Restrict it to System Manager on tenant sites.
    if frappe.db.exists("Page", "saas-dashboard"):
        page = frappe.get_doc("Page", "saas-dashboard")

        if hasattr(page, "roles"):
            page.set("roles", [])
            page.append("roles", {"role": "System Manager"})
            page.save(ignore_permissions=True)

    frappe.db.commit()


def after_sync():
    _protect_control_plane_ui()
    _restrict_tenant_workspaces()


def _fix_drug_prescription_metadata():
    """Keep Drug Prescription metadata aligned after every site migration."""
    field_name = frappe.db.get_value(
        "DocField",
        {
            "parent": "Drug Prescription",
            "fieldname": "dosage_form",
        },
        "name",
    )

    if field_name:
        frappe.db.set_value(
            "DocField",
            field_name,
            "reqd",
            0,
            update_modified=False,
        )
        frappe.clear_cache(doctype="Drug Prescription")


def _ensure_clinic_profile_defaults():
    if not frappe.db.exists("DocType", "Clinic Configuration"):
        return
    if not frappe.db.get_single_value("Clinic Configuration", "brand_primary_color"):
        frappe.db.set_single_value(
            "Clinic Configuration",
            "brand_primary_color",
            "#173B82",
        )


def after_migrate():
    _protect_control_plane_ui()
    _fix_drug_prescription_metadata()
    if not _is_control_site():
        _restrict_tenant_workspaces()
        _ensure_clinic_profile_defaults()
        from clinify.saas.tenant_bootstrap import _ensure_clinic_profile_admin_permission

        _ensure_clinic_profile_admin_permission()
        from clinify.patches.install_clinify_prescription_print_format_v6 import execute as install_prescription
        from clinify.patches.install_clinify_invoice_print_format_v1 import execute as install_invoice

        install_prescription()
        install_invoice()
    frappe.db.commit()

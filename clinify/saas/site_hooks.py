import frappe

from clinify.saas.sso import _is_control_site


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
        _ensure_clinic_profile_defaults()
        from clinify.saas.tenant_bootstrap import _ensure_clinic_profile_admin_permission

        _ensure_clinic_profile_admin_permission()
    frappe.db.commit()

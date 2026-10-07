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


def after_migrate():
    _protect_control_plane_ui()

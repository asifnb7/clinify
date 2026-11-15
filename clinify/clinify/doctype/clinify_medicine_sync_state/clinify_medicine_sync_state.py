import frappe
from frappe.model.document import Document

from clinify.medicine_catalogue_sync import (
    CLINIFY_CATALOGUE_SYNC_ROLE,
    _configured_sync_user,
    configured_control_site,
    require_control_site_admin,
)


class ClinifyMedicineSyncState(Document):
    def validate(self):
        if not self.flags.get("clinify_catalogue_state_update"):
            frappe.throw("Synchronization state is managed by the catalogue service.")

        self.tenant_site = str(self.tenant_site or "").strip().lower()
        if not self.tenant_site:
            frappe.throw("Tenant site is required for synchronization state.")

        site = str(frappe.local.site or "").strip().lower()
        if site == configured_control_site():
            require_control_site_admin()
        else:
            if frappe.session.user == "Guest":
                frappe.throw("Authentication is required for synchronization state updates.")
            frappe.only_for(CLINIFY_CATALOGUE_SYNC_ROLE)
            if (
                frappe.session.user != _configured_sync_user()
                or self.tenant_site != site
            ):
                frappe.throw("Tenant synchronization state update is not authorized.")

    def on_trash(self):
        frappe.throw("Synchronization state cannot be deleted.")
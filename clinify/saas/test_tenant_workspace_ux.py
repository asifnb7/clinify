import frappe
from frappe.tests.utils import FrappeTestCase

from clinify.saas.site_hooks import TENANT_HIDDEN_WORKSPACES, _restrict_tenant_workspaces


class TestTenantWorkspaceUX(FrappeTestCase):
	user = "beta.final.e2e071026@example.com.invalid"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_restrict_tenant_workspaces()

	def test_empty_and_system_workspaces_are_hidden_from_tenant_sidebar(self):
		previous_user = frappe.session.user
		try:
			frappe.set_user(self.user)
			from frappe.desk.desktop import get_workspace_sidebar_items

			pages = get_workspace_sidebar_items().get("pages", [])
			visible = {page.name for page in pages}
			self.assertTrue(set(TENANT_HIDDEN_WORKSPACES).isdisjoint(visible))
		finally:
			frappe.set_user(previous_user)

	def test_intended_tenant_workspaces_resolve_to_usable_items(self):
		previous_user = frappe.session.user
		try:
			frappe.set_user(self.user)
			from frappe.desk.desktop import Workspace

			for name in ("Reception", "Doctor", "Billing", "Laboratory", "Pharmacy", "Settings"):
				doc = frappe.get_doc("Workspace", name)
				workspace = Workspace(doc.as_dict())
				workspace.build_workspace()
				self.assertTrue(
					workspace.shortcuts["items"],
					"{} has no permitted shortcut items".format(name),
				)
		finally:
			frappe.set_user(previous_user)

	def test_hidden_workspace_roles_block_direct_workspace_permission(self):
		previous_user = frappe.session.user
		try:
			frappe.set_user(self.user)
			from frappe.desk.desktop import Workspace

			for name in TENANT_HIDDEN_WORKSPACES:
				if not frappe.db.exists("Workspace", name):
					continue
				workspace = Workspace(frappe.get_doc("Workspace", name).as_dict(), minimal=True)
				self.assertFalse(workspace.is_permitted(), name)
		finally:
			frappe.set_user(previous_user)

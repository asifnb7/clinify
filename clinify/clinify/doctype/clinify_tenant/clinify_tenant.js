// Copyright (c) 2026, Salniz Technologies and contributors
// For license information, please see license.txt

const tenantSlug = (value) => (value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
const updateTenantIdentifiers = (frm) => { const slug = tenantSlug(frm.doc.tenant_name); if (!slug) return; frm.set_value("tenant_code", slug.toUpperCase().slice(0, 50)); frm.set_value("site_name", `${slug.slice(0, 90)}.localhost`); };
const updateSubscriptionEndDate = (frm) => { if (!frm.doc.plan) return; frappe.db.get_value("Clinify Plan", frm.doc.plan, "billing_cycle").then((r) => { const cycle = r.message && r.message.billing_cycle; if (!cycle) return; const d = frappe.datetime.str_to_obj(frappe.datetime.get_today()); if (cycle === "Monthly") d.setMonth(d.getMonth() + 1); else if (cycle === "Quarterly") d.setMonth(d.getMonth() + 3); else if (cycle === "Yearly") d.setFullYear(d.getFullYear() + 1); else return; d.setDate(d.getDate() - 1); frm.set_value("subscription_end_date", frappe.datetime.obj_to_str(d)); }); };
frappe.ui.form.on("Clinify Tenant", {
 tenant_name(frm) { if (frm.is_new()) updateTenantIdentifiers(frm); },
 plan(frm) { if (frm.is_new()) updateSubscriptionEndDate(frm); },
 refresh(frm) {
  frm.set_df_property("tenant_code", "read_only", 1); frm.set_df_property("site_name", "read_only", 1);
  if (frm.is_new() && frm.doc.tenant_name) updateTenantIdentifiers(frm);
  if (frm.is_new() && frm.doc.plan && !frm.doc.subscription_end_date) updateSubscriptionEndDate(frm);
  if (!frm.doc.__islocal && ["Pending", "Failed"].includes(frm.doc.provisioning_status) && frappe.user.has_role("System Manager")) {
   frm.add_custom_button(
    frm.doc.provisioning_status === "Failed" ? __("Retry Provisioning") : __("Provision Tenant"),
    () => {
    const required_fields = ["tenant_name", "administrator_email", "plan"];
    const missing = required_fields.filter((fieldname) => !frm.doc[fieldname]);
    if (missing.length) { frappe.msgprint({title: __("Missing Information"), message: __("Please complete all required tenant fields before provisioning."), indicator: "orange"}); return; }
    frappe.prompt([{fieldname: "administrator_password", fieldtype: "Password", label: __("Administrator Password"), reqd: 1}], (values) => {
     frappe.confirm(__("Create the tenant site and provision this clinic now?"), () => {
      frappe.call({method: "clinify.saas.provisioning.provision_tenant_from_ui", args: {tenant_name: frm.doc.tenant_name, tenant_code: frm.doc.tenant_code, site_name: frm.doc.site_name, administrator_email: frm.doc.administrator_email, administrator_password: values.administrator_password, administrator_name: frm.doc.administrator_name, plan: frm.doc.plan, subscription_end_date: frm.doc.subscription_end_date, domain: frm.doc.domain, contact_person: frm.doc.contact_person, registered_phone: frm.doc.registered_phone, registered_email: frm.doc.registered_email, address_line_1: frm.doc.address_line_1, address_line_2: frm.doc.address_line_2, registered_city: frm.doc.registered_city, registered_state: frm.doc.registered_state, postal_code: frm.doc.postal_code, registered_country: frm.doc.registered_country}, freeze: true, freeze_message: __("Provisioning tenant. Please wait..."), callback: (response) => {
       if (response.message && response.message.success) {
        if (response.message.queued) {
         frappe.show_alert({
          message: __("Tenant provisioning has been queued. The tenant will be available when provisioning completes."),
          indicator: "blue"
         });
        } else {
         frappe.show_alert({
          message: __("Tenant provisioned successfully."),
          indicator: "green"
         });
        }
        if (response.message.tenant) {
         frappe.set_route("Form", "Clinify Tenant", response.message.tenant);
        }
       }
      }});
     });
    }, __("Provision Tenant"), __("Provision"));
   });
  }
 }
});

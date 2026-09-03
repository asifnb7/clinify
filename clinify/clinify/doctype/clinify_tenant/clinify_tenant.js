// Copyright (c) 2026, Salniz Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Clinify Tenant", {
    refresh(frm) {
        if (!frm.doc.__islocal &&
            frm.doc.provisioning_status === "Pending" &&
            frappe.user.has_role("System Manager")) {

            frm.add_custom_button(__("Provision Tenant"), () => {
                const required_fields = [
                    "tenant_name",
                    "tenant_code",
                    "site_name",
                    "administrator_email",
                    "plan",
                ];

                const missing = required_fields.filter(
                    (fieldname) => !frm.doc[fieldname]
                );

                if (missing.length) {
                    frappe.msgprint({
                        title: __("Missing Information"),
                        message: __(
                            "Please complete all required tenant fields before provisioning."
                        ),
                        indicator: "orange",
                    });
                    return;
                }

                frappe.prompt(
                    [
                        {
                            fieldname: "administrator_password",
                            fieldtype: "Password",
                            label: __("Administrator Password"),
                            reqd: 1,
                        }
                    ],
                    (values) => {
                        frappe.confirm(
                            __(
                                "Create the tenant site and provision this clinic now?"
                            ),
                            () => {
                                frappe.call({
                                    method:
                                        "clinify.saas.provisioning.provision_tenant_from_ui",
                                    args: {
                                        tenant_name: frm.doc.tenant_name,
                                        tenant_code: frm.doc.tenant_code,
                                        site_name: frm.doc.site_name,
                                        administrator_email:
                                            frm.doc.administrator_email,
                                        administrator_password:
                                            values.administrator_password,
                                        administrator_name:
                                            frm.doc.administrator_name,
                                        plan: frm.doc.plan,
                                        domain: frm.doc.domain,
                                        contact_person: frm.doc.contact_person,
                                        registered_phone: frm.doc.registered_phone,
                                        registered_email: frm.doc.registered_email,
                                        address_line_1: frm.doc.address_line_1,
                                        address_line_2: frm.doc.address_line_2,
                                        registered_city: frm.doc.registered_city,
                                        registered_state: frm.doc.registered_state,
                                        postal_code: frm.doc.postal_code,
                                        registered_country: frm.doc.registered_country,
                                    },
                                    freeze: true,
                                    freeze_message: __(
                                        "Provisioning tenant. Please wait..."
                                    ),
                                    callback: (response) => {
                                        if (
                                            response.message &&
                                            response.message.success
                                        ) {
                                            frappe.show_alert({
                                                message: __(
                                                    "Tenant provisioned successfully."
                                                ),
                                                indicator: "green",
                                            });

                                            frappe.set_route(
                                                "Form",
                                                "Clinify Tenant",
                                                response.message.tenant
                                            );
                                        }
                                    },
                                });
                            }
                        );
                    },
                    __("Provision Tenant"),
                    __("Provision")
                );
            });
        }
    },
});

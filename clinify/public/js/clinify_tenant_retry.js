/*
 * Clinify Tenant - Failed Provisioning Retry
 *
 * Adds a controlled retry action for an existing tenant whose
 * provisioning status is Failed.
 *
 * The administrator password is collected only in the dialog and
 * submitted over the authenticated Frappe POST request. It is not
 * written to the Clinify Tenant document.
 */

frappe.ui.form.on("Clinify Tenant", {
    refresh(frm) {
        const retry_status = "Failed";
        const button_label = __("Retry Provisioning");

        frm.remove_custom_button(button_label);

        if (frm.is_new()) {
            return;
        }

        if (frm.doc.provisioning_status !== retry_status) {
            return;
        }

        frm.add_custom_button(button_label, () => {
            const dialog = new frappe.ui.Dialog({
                title: __("Retry Tenant Provisioning"),
                fields: [
                    {
                        fieldname: "administrator_password",
                        fieldtype: "Password",
                        label: __("Administrator Password"),
                        reqd: 1,
                        description: __(
                            "Enter the administrator password for this tenant. " +
                            "It will be used only for this provisioning attempt."
                        ),
                    },
                ],
                primary_action_label: __("Queue Provisioning"),
                primary_action(values) {
                    if (!values || !values.administrator_password) {
                        frappe.msgprint({
                            title: __("Password Required"),
                            message: __("Please enter the administrator password."),
                            indicator: "orange",
                        });
                        return;
                    }

                    dialog.hide();

                    frappe.call({
                        method: "clinify.saas.provisioning.provision_tenant_from_ui",
                        type: "POST",
                        freeze: true,
                        freeze_message: __("Queueing tenant provisioning..."),
                        args: {
                            tenant_name: frm.doc.tenant_name,
                            tenant_code: frm.doc.tenant_code,
                            site_name: frm.doc.site_name,
                            administrator_email: frm.doc.administrator_email,
                            administrator_password: values.administrator_password,
                            administrator_name: frm.doc.administrator_name,
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
                            subscription_end_date: frm.doc.subscription_end_date,
                        },
                        callback(r) {
                            if (r.exc) {
                                return;
                            }

                            const result = r.message || {};

                            frappe.show_alert({
                                message: result.message || __("Tenant provisioning has been queued."),
                                indicator: "green",
                            });

                            frm.reload_doc();
                        },
                    });
                },
            });

            dialog.show();
        });
    },
});

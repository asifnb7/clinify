console.log("Clinify Dental Palette V1 Loaded");

frappe.ui.form.on("Patient Encounter", {

refresh(frm) {

    // ------------------------------------------------
    // Hide legacy Dental workflow
    // ------------------------------------------------
    [
        "get_applicable_treatment_plans",
        "custom_dental_examination",
        "custom_procedure_type",
    ].forEach(function(field) {

        frm.set_df_property(field, "hidden", 1);

    });

    if (frm.__clinify_palette_loaded) {
        return;
    }

    frm.__clinify_palette_loaded = true;

    // Draft Encounter → Doctor
    // Allow doctors to select one or more Dental Services.
    if (frm.doc.docstatus === 0) {
        frm.add_custom_button(__("Select Dental Services"), function () {
            open_dental_palette(frm);
        });
    }

    // Submitted Encounter → Reception
    if (frm.doc.docstatus === 1) {

        frm.add_custom_button(__("🧾 Create Invoice"), function () {

            frappe.call({

                method: "clinify.encounter.create_invoice_from_encounter",

                args: {
                    encounter_name: frm.doc.name
                },

                freeze: true,
                freeze_message: __("Creating Invoice..."),

                callback: function(r) {

                    if (!r.exc && r.message) {

                        frappe.show_alert({
                            message: __("Invoice Created"),
                            indicator: "green"
                        });

                        frappe.set_route(
                            "Form",
                            "Sales Invoice",
                            r.message
                        );

                    }

                }

            });

        });

    }

}
});


function open_dental_palette(frm) {

    frappe.call({

        method: "clinify.clinify.api.dental_service.get_active_dental_services",

        freeze: true,
        freeze_message: __("Loading Dental Services..."),

        callback: function (r) {

            if (r.exc) {
                return;
            }

            const services = r.message || [];

            if (!services.length) {

                frappe.msgprint({
                    title: __("No Dental Services"),
                    message: __(
                        "No active Dental Services are configured."
                    ),
                    indicator: "orange"
                });

                return;
            }

            let html = `
                <div style="padding:20px">

                    <h3 style="margin-bottom:20px">
                        Clinify Dental Services
                    </h3>

                    <div id="clinify-service-list">
            `;

            services.forEach(service => {

                html += `

                    <button
                        class="btn btn-default clinify-service"
                        data-service="${frappe.utils.escape_html(service.name)}"
                        style="
                            margin:8px;
                            min-width:180px;
                        ">

                        🦷 ${frappe.utils.escape_html(
                            service.service_name
                        )}

                    </button>

                `;

            });

            html += `
                    </div>
                </div>
            `;

            let dialog = new frappe.ui.Dialog({

                title: __("Select Dental Service"),

                size: "large",

                fields: [
                    {
                        fieldtype: "HTML",
                        fieldname: "body"
                    }
                ]

            });

            dialog.fields_dict.body.$wrapper.html(html);

            dialog.show();

            dialog.$wrapper.on(
                "click",
                ".clinify-service",
                function () {

                    const service_name = $(this).attr(
                        "data-service"
                    );

                    console.log(
                        "Selected Dental Service:",
                        service_name
                    );

                    add_service(
                        frm,
                        service_name,
                        services
                    );

                    dialog.hide();

                }
            );

        }

    });

}


function add_service(
    frm,
    service_name,
    services
) {

    console.log(
        "Adding Dental Service:",
        service_name
    );

    const service = services.find(
        item => item.name === service_name
    );

    if (!service) {

        frappe.msgprint({
            title: __("Dental Service Error"),
            message: __(
                "The selected Dental Service could not be found."
            ),
            indicator: "red"
        });

        return;
    }

    const row = frm.add_child(
        "custom_dental_services"
    );

    row.dental_service = service.name;

    row.qty = service.default_qty || 1;

    frm.refresh_field(
        "custom_dental_services"
    );

    frappe.show_alert({

        message: __(
            "{0} added",
            [service.service_name]
        ),

        indicator: "green"

    });

}



function add_service(frm, service_code) {

    console.log("Adding Service:", service_code);

    const row = frm.add_child("custom_dental_services");

    row.dental_service = service_code;

    row.qty = 1;

    frm.refresh_field("custom_dental_services");

    frappe.show_alert({

        message: __("Service Added"),

        indicator: "green"

    });

}
console.log("CLINIFY DENTAL SERVICE PALETTE V3 LOADED");

frappe.ui.form.on("Patient Encounter", {

    refresh(frm) {

        [
            "get_applicable_treatment_plans",
            "custom_dental_examination",
            "custom_procedure_type",
        ].forEach(function(fieldname) {

            if (frm.fields_dict[fieldname]) {
                frm.set_df_property(
                    fieldname,
                    "hidden",
                    1
                );
            }

        });

        if (frm.doc.docstatus !== 0) {
            return;
        }

        if (frm.__clinify_dental_palette_added) {
            return;
        }

        frm.__clinify_dental_palette_added = true;

        frm.add_custom_button(
            __("Select Dental Services"),
            function() {
                open_dental_palette(frm);
            }
        );
    }

});


function open_dental_palette(frm) {

    frappe.call({

        method:
            "clinify.api.dental_service.get_active_dental_services",

        freeze: true,

        freeze_message:
            __("Loading Dental Services..."),

        callback: function(r) {

            if (r.exc) {

                frappe.msgprint({
                    title: __("Dental Service Error"),
                    message: __(
                        "Unable to load Dental Services."
                    ),
                    indicator: "red"
                });

                return;
            }

            const services =
                r.message || [];

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

                    <div
                        id="clinify-service-list"
                        style="
                            display:flex;
                            flex-wrap:wrap;
                            gap:10px;
                        "
                    >
            `;

            services.forEach(function(service) {

                html += `
                    <button
                        type="button"
                        class="btn btn-default clinify-service"
                        data-service="${frappe.utils.escape_html(service.name)}"
                        style="
                            margin:4px;
                            min-width:180px;
                        "
                    >
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

            const dialog =
                new frappe.ui.Dialog({

                    title:
                        __("Select Dental Service"),

                    size:
                        "large",

                    fields: [
                        {
                            fieldtype:
                                "HTML",

                            fieldname:
                                "body"
                        }
                    ]
                });

            dialog.fields_dict.body.$wrapper.html(
                html
            );

            dialog.show();

            dialog.$wrapper.on(
                "click",
                ".clinify-service",
                function() {

                    const service_name =
                        $(this).attr(
                            "data-service"
                        );

                    dialog.hide();

                    add_service(
                        frm,
                        service_name,
                        services
                    );
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

    const service =
        services.find(function(item) {
            return item.name === service_name;
        });

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

    /*
     * Dental Service is the authoritative catalogue.
     *
     * requires_tooth = 1
     *     Ask for Tooth / Area.
     *
     * requires_tooth = 0
     *     Add directly.
     */

    if (Number(service.requires_tooth) === 1) {

        const tooth_dialog =
            new frappe.ui.Dialog({

                title:
                    __("Tooth / Area Required"),

                fields: [
                    {
                        fieldname:
                            "tooth_area",

                        fieldtype:
                            "Data",

                        label:
                            __("Tooth / Area"),

                        reqd:
                            1,

                        description:
                            __(
                                "Enter the tooth number or treatment area."
                            )
                    }
                ],

                primary_action_label:
                    __("Add Service"),

                primary_action:
                    function(values) {

                        const tooth_area =
                            (
                                values.tooth_area ||
                                ""
                            ).trim();

                        if (!tooth_area) {

                            frappe.msgprint({
                                title:
                                    __("Tooth / Area Required"),

                                message:
                                    __(
                                        "Please enter the Tooth / Area."
                                    ),

                                indicator:
                                    "red"
                            });

                            return;
                        }

                        tooth_dialog.hide();

                        add_dental_service_row(
                            frm,
                            service,
                            tooth_area
                        );
                    }
            });

        tooth_dialog.show();

        return;
    }

    add_dental_service_row(
        frm,
        service,
        ""
    );
}


function add_dental_service_row(
    frm,
    service,
    tooth_area
) {

    const row =
        frm.add_child(
            "custom_dental_services"
        );

    row.dental_service =
        service.name;

    row.qty =
        service.default_qty || 1;

    row.tooth_area =
        tooth_area || "";

    frm.refresh_field(
        "custom_dental_services"
    );

    frappe.show_alert({

        message:
            __(
                "{0} added",
                [
                    service.service_name
                ]
            ),

        indicator:
            "green"
    });
}

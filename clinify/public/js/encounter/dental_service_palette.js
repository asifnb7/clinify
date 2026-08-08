console.log("Clinify Dental Palette V1 Loaded");

frappe.ui.form.on("Patient Encounter", {

refresh(frm) {

    if (frm.__clinify_palette_loaded) {
        return;
    }

    frm.__clinify_palette_loaded = true;

    // Draft Encounter → Doctor
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

    const services = [
        { code: "DS001", label: "🦷 Scaling" },
        { code: "DS002", label: "🦷 Filling" },
        { code: "DS003", label: "🦷 RCT" },
        { code: "DS004", label: "🦷 Extraction" },
        { code: "DS005", label: "🦷 Crown" }
    ];

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
                data-code="${service.code}"
                style="
                    margin:8px;
                    min-width:150px;
                ">

                ${service.label}

            </button>

        `;

    });

    html += `
            </div>
        </div>
    `;

    let dialog = new frappe.ui.Dialog({

        title: "Select Dental Service",

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

    dialog.$wrapper.on("click", ".clinify-service", function () {

        const service_code = $(this).data("code");

        console.log("Selected:", service_code);

        add_service(frm, service_code);

        dialog.hide();

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
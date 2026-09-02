console.log("CLINIFY ENCOUNTER JS LOADED - RUNTIME GRID FIX");

frappe.ui.form.on("Patient Encounter", {

    setup(frm) {
        setup_clinify_prescription_grid(frm);
    },

    refresh(frm) {
        setup_clinify_prescription_grid(frm);
    },

});


function setup_clinify_prescription_grid(frm) {

    const field = frm.fields_dict.drug_prescription;

    if (!field || !field.grid) {
        return;
    }

    const grid = field.grid;


    /*
     * Clinify prescription grid configuration.
     *
     * Only these fields should appear in the
     * compact doctor-facing prescription table.
     */

    const visible_fields = [
        "drug_code",
        "drug_name",
        "dosage",
        "period",
        "custom_instruction",
    ];


    const column_config = {
        drug_code: 2,
        drug_name: 3,
        dosage: 2,
        period: 1,
        custom_instruction: 2,
    };


    /*
     * Apply configuration to BOTH collections used
     * by the Frappe Grid implementation.
     */

    const configure_fields = (fields) => {

        if (!fields) {
            return;
        }

        fields.forEach((df) => {

            if (!df || !df.fieldname) {
                return;
            }


            if (visible_fields.includes(df.fieldname)) {

                df.hidden = 0;
                df.in_list_view = 1;
                df.columns = column_config[df.fieldname];

            } else {

                df.in_list_view = 0;
                df.columns = 0;

            }

        });

    };


    /*
     * Configure the grid's actual runtime fields.
     */

    configure_fields(grid.docfields);

    configure_fields(grid.editable_fields);

    configure_fields(grid.meta && grid.meta.fields);


    /*
     * Explicitly rebuild editable_fields.
     *
     * This prevents an old editable field list from
     * overriding the Clinify configuration.
     */

    if (grid.docfields) {

        grid.editable_fields = grid.docfields.filter((df) =>
            visible_fields.includes(df.fieldname)
        );

    }


    /*
     * Clear Frappe's calculated visible columns so
     * they are rebuilt from the new configuration.
     */

    grid.visible_columns = [];


    /*
     * Diagnostic output.
     *
     * This does not change application behavior.
     */

    console.log(
        "CLINIFY PRESCRIPTION GRID:",
        grid.editable_fields.map((df) => ({
            fieldname: df.fieldname,
            in_list_view: df.in_list_view,
            columns: df.columns,
        }))
    );


    grid.setup_visible_columns();

    frm.refresh_field("drug_prescription");

}


frappe.ui.form.on("Drug Prescription", {

    drug_code(frm, cdt, cdn) {

        const row = locals[cdt][cdn];

        if (!row.drug_code) {
            return;
        }


        frappe.call({

            method:
                "clinify.api.drug_search.get_drug_prescription_defaults",

            args: {
                drug_code: row.drug_code,
            },

            callback(r) {

                if (!r.message) {
                    return;
                }

                const data = r.message;


                frappe.model.set_value(
                    cdt,
                    cdn,
                    "drug_name",
                    data.drug_name || ""
                );


                frappe.model.set_value(
                    cdt,
                    cdn,
                    "strength",
                    data.strength || 0
                );


                frappe.model.set_value(
                    cdt,
                    cdn,
                    "strength_uom",
                    data.strength_uom || ""
                );


                frappe.model.set_value(
                    cdt,
                    cdn,
                    "dosage_form",
                    data.dosage_form || ""
                );


                frappe.model.set_value(
                    cdt,
                    cdn,
                    "dosage",
                    data.dosage || ""
                );


                frappe.model.set_value(
                    cdt,
                    cdn,
                    "period",
                    data.period || ""
                );


                if (
                    data.interval !== null &&
                    data.interval !== undefined
                ) {

                    frappe.model.set_value(
                        cdt,
                        cdn,
                        "interval",
                        data.interval
                    );

                }


                frappe.model.set_value(
                    cdt,
                    cdn,
                    "interval_uom",
                    data.interval_uom || ""
                );


                frm.refresh_field(
                    "drug_prescription"
                );

            },

        });

    },

});

// ============================================================
// CLINIFY PRESCRIPTION PRINT BUTTON
// ============================================================

frappe.ui.form.on("Patient Encounter", {

    refresh(frm) {

        if (frm.is_new()) {
            return;
        }

        frm.add_custom_button(
            __("Print Prescription"),
            function () {

                const url =
                    "/printview" +
                    "?doctype=" +
                    encodeURIComponent("Patient Encounter") +
                    "&name=" +
                    encodeURIComponent(frm.doc.name) +
                    "&format=" +
                    encodeURIComponent("Clinify Prescription") +
                    "&trigger_print=1";

                window.open(
                    url,
                    "_blank"
                );

            }
        );

    }

});

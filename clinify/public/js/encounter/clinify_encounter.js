console.log(
    "CLINIFY ENCOUNTER JS LOADED - VITALS + PRESCRIPTION + INVOICE"
);


// ============================================================
// PATIENT ENCOUNTER
// ============================================================

frappe.ui.form.on(
    "Patient Encounter",
    {

        setup(frm) {

            setup_clinify_prescription_grid(
                frm
            );

        },


        refresh(frm) {

            // ------------------------------------------------
            // Prescription Grid
            // ------------------------------------------------

            setup_clinify_prescription_grid(
                frm
            );


            // ------------------------------------------------
            // Vital Signs
            // ------------------------------------------------

            load_clinify_vitals(
                frm
            );


            // ------------------------------------------------
            // Custom Buttons
            // ------------------------------------------------

            if (
                !frm.is_new()
            ) {

                add_clinify_print_button(
                    frm
                );

                add_clinify_invoice_button(
                    frm
                );

            }

        },


        // ----------------------------------------------------
        // Reload vitals when appointment changes
        // ----------------------------------------------------

        appointment(frm) {

            load_clinify_vitals(
                frm
            );

        },


        // ----------------------------------------------------
        // Reload vitals when patient changes
        // ----------------------------------------------------

        patient(frm) {

            load_clinify_vitals(
                frm
            );

        },


        // ----------------------------------------------------
        // Reload vitals when encounter date changes
        // ----------------------------------------------------

        encounter_date(frm) {

            load_clinify_vitals(
                frm
            );

        },

    }
);


// ============================================================
// LOAD CLINIFY VITAL SIGNS
// ============================================================

function load_clinify_vitals(frm) {

    // Remove any existing display first

    remove_clinify_vitals(
        frm
    );


    // --------------------------------------------------------
    // CASE 1
    // SAVED ENCOUNTER
    // --------------------------------------------------------

    if (
        !frm.is_new() &&
        frm.doc.name
    ) {

        frappe.call({

            method:
                "clinify.encounter.get_matching_vitals",


            args: {

                encounter_name:
                    frm.doc.name,

            },


            callback(r) {

                if (
                    !r.message
                ) {

                    return;

                }


                render_clinify_vitals(
                    frm,
                    r.message
                );

            },

        });

        return;

    }


    // --------------------------------------------------------
    // CASE 2
    // NEW / UNSAVED ENCOUNTER
    //
    // Match vitals using:
    //
    // Patient
    // Appointment
    // Encounter Date
    // --------------------------------------------------------

    if (
        !frm.doc.patient ||
        !frm.doc.encounter_date
    ) {

        remove_clinify_vitals(
            frm
        );

        return;

    }


    frappe.call({

        method:
            "clinify.encounter.get_matching_vitals_for_context",


        args: {

            patient:
                frm.doc.patient,


            appointment:
                frm.doc.appointment ||
                null,


            encounter_date:
                frm.doc.encounter_date,

        },


        callback(r) {

            if (
                !r.message
            ) {

                remove_clinify_vitals(
                    frm
                );

                return;

            }


            render_clinify_vitals(
                frm,
                r.message
            );

        },

    });

}


// ============================================================
// RENDER CLINIFY VITAL SIGNS
// ============================================================

function render_clinify_vitals(
    frm,
    vital
) {

    if (
        !vital
    ) {

        return;

    }


    // Remove previous instance

    remove_clinify_vitals(
        frm
    );


    // --------------------------------------------------------
    // FORMAT VALUES
    // --------------------------------------------------------

    const recorded_date =
        format_clinify_date(
            vital.signs_date
        );


    const bp =
        vital.bp ||
        build_clinify_bp(
            vital.bp_systolic,
            vital.bp_diastolic
        ) ||
        "-";


    const pulse =
        format_clinify_value(
            vital.pulse
        );


    const temperature =
        format_clinify_value(
            vital.temperature
        );


    const respiratory_rate =
        format_clinify_value(
            vital.respiratory_rate
        );


    const weight =
        format_clinify_number(
            vital.weight,
            " kg"
        );


    const bmi =
        format_clinify_value(
            vital.bmi
        );


    const height =
        format_clinify_number(
            vital.height,
            " m"
        );


    // ========================================================
    // LOCKED CLINIFY VITAL SIGNS DESIGN
    // ========================================================

    const html = `

        <div
            id="clinify-vital-signs-card"
            style="
                margin: 12px 0 16px 0;
                border: 1px solid #d7dee8;
                border-radius: 14px;
                background: #ffffff;
                box-shadow:
                    0 2px 8px rgba(0, 0, 0, 0.04);
                overflow: hidden;
            "
        >


            <!-- HEADER -->

            <div
                style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 16px 18px;
                    border-bottom:
                        1px solid #e5e9ef;
                "
            >

                <div
                    style="
                        font-size: 18px;
                        font-weight: 700;
                        letter-spacing: 0.4px;
                        color: #2f3b4a;
                    "
                >
                    VITAL SIGNS
                </div>


                <div
                    style="
                        font-size: 13px;
                        font-weight: 600;
                        color: #64748b;
                    "
                >
                    Recorded: ${recorded_date}
                </div>

            </div>


            <!-- VITAL TABLE -->

            <div
                id="clinify-vital-grid"
                style="
                    display: grid;
                    grid-template-columns:
                        repeat(7, minmax(0, 1fr));
                    padding:
                        6px 10px 10px 10px;
                "
            >


                <!-- BP -->

                <div
                    class="clinify-vital-item"
                >

                    <div
                        class="clinify-vital-label"
                    >

                        <span
                            style="
                                color: #e05a47;
                                font-size: 16px;
                            "
                        >
                            💧
                        </span>

                        BP

                    </div>


                    <div
                        class="clinify-vital-value"
                    >
                        ${bp}
                    </div>

                </div>


                <!-- PULSE -->

                <div
                    class="clinify-vital-item"
                >

                    <div
                        class="clinify-vital-label"
                    >

                        <span
                            style="
                                color: #e64b7c;
                                font-size: 16px;
                            "
                        >
                            ♥
                        </span>

                        Pulse

                    </div>


                    <div
                        class="clinify-vital-value"
                    >
                        ${pulse}
                    </div>

                </div>


                <!-- TEMPERATURE -->

                <div
                    class="clinify-vital-item"
                >

                    <div
                        class="clinify-vital-label"
                    >

                        <span
                            style="
                                color: #e5a13d;
                                font-size: 16px;
                            "
                        >
                            ♨
                        </span>

                        Temperature

                    </div>


                    <div
                        class="clinify-vital-value"
                    >
                        ${temperature}
                    </div>

                </div>


                <!-- RESPIRATORY RATE -->

                <div
                    class="clinify-vital-item"
                >

                    <div
                        class="clinify-vital-label"
                    >

                        <span
                            style="
                                color: #4389b8;
                                font-size: 16px;
                            "
                        >
                            ♥
                        </span>

                        Resp. Rate

                    </div>


                    <div
                        class="clinify-vital-value"
                    >
                        ${respiratory_rate}
                    </div>

                </div>


                <!-- WEIGHT -->

                <div
                    class="clinify-vital-item"
                >

                    <div
                        class="clinify-vital-label"
                    >

                        <span
                            style="
                                color: #8b5ba5;
                                font-size: 16px;
                            "
                        >
                            ⚖
                        </span>

                        Weight

                    </div>


                    <div
                        class="clinify-vital-value"
                    >
                        ${weight}
                    </div>

                </div>


                <!-- BMI -->

                <div
                    class="clinify-vital-item"
                >

                    <div
                        class="clinify-vital-label"
                    >

                        <span
                            style="
                                color: #3b9b87;
                                font-size: 16px;
                            "
                        >
                            ↗
                        </span>

                        BMI

                    </div>


                    <div
                        class="clinify-vital-value"
                    >
                        ${bmi}
                    </div>

                </div>


                <!-- HEIGHT -->

                <div
                    class="clinify-vital-item"
                    style="
                        border-right: none;
                    "
                >

                    <div
                        class="clinify-vital-label"
                    >

                        <span
                            style="
                                color: #477d9c;
                                font-size: 16px;
                            "
                        >
                            ↕
                        </span>

                        Height

                    </div>


                    <div
                        class="clinify-vital-value"
                    >
                        ${height}
                    </div>

                </div>


            </div>

        </div>


        <style>

            .clinify-vital-item {

                min-width: 0;

                padding:
                    12px
                    14px
                    10px
                    14px;

                text-align: center;

                border-right:
                    1px
                    solid
                    #e1e6ed;

            }


            .clinify-vital-label {

                display: flex;

                align-items: center;

                justify-content: center;

                gap: 6px;

                font-size: 14px;

                font-weight: 700;

                color: #526170;

                white-space: nowrap;

            }


            .clinify-vital-value {

                margin-top: 8px;

                font-size: 15px;

                font-weight: 500;

                color: #344252;

                white-space: nowrap;

            }


            @media (max-width: 1000px) {

                #clinify-vital-grid {

                    grid-template-columns:
                        repeat(
                            4,
                            minmax(0, 1fr)
                        )
                        !important;

                }

            }


            @media (max-width: 700px) {

                #clinify-vital-grid {

                    grid-template-columns:
                        repeat(
                            2,
                            minmax(0, 1fr)
                        )
                        !important;

                }


                .clinify-vital-item {

                    border-bottom:
                        1px
                        solid
                        #e1e6ed;

                }

            }

        </style>

    `;


    // --------------------------------------------------------
    // INSERT AT THE TOP OF THE ENCOUNTER FORM
    //
    // frm.layout.wrapper is deliberately used here because it
    // works for both:
    //
    // 1. New Patient Encounter
    // 2. Saved Patient Encounter
    // --------------------------------------------------------

    const $form_wrapper =
        $(frm.layout.wrapper);


    if (
        $form_wrapper.length
    ) {

        $form_wrapper.prepend(
            html
        );

    }

}


// ============================================================
// REMOVE PREVIOUS VITAL DISPLAY
// ============================================================

function remove_clinify_vitals(
    frm
) {

    if (
        frm &&
        frm.layout &&
        frm.layout.wrapper
    ) {

        $(frm.layout.wrapper)
            .find(
                "#clinify-vital-signs-card"
            )
            .remove();

    }

}


// ============================================================
// FORMAT DATE
// ============================================================

function format_clinify_date(
    value
) {

    if (
        !value
    ) {

        return "-";

    }


    try {

        return frappe.datetime.str_to_user(
            value
        );

    }

    catch (error) {

        return value;

    }

}


// ============================================================
// FORMAT GENERIC VITAL VALUE
// ============================================================

function format_clinify_value(
    value
) {

    if (
        value === null ||
        value === undefined ||
        value === "" ||
        value === 0 ||
        value === "0"
    ) {

        return "-";

    }


    return value;

}


// ============================================================
// FORMAT NUMBER WITH UNIT
// ============================================================

function format_clinify_number(
    value,
    suffix
) {

    if (
        value === null ||
        value === undefined ||
        value === "" ||
        Number(value) === 0
    ) {

        return "-";

    }


    return `${value}${suffix}`;

}


// ============================================================
// BUILD BLOOD PRESSURE
// ============================================================

function build_clinify_bp(
    systolic,
    diastolic
) {

    if (
        systolic &&
        diastolic
    ) {

        return `${systolic}/${diastolic} mmHg`;

    }


    return "";

}


// ============================================================
// CLINIFY PRESCRIPTION GRID
// ============================================================

function setup_clinify_prescription_grid(
    frm
) {

    const field =
        frm.fields_dict.drug_prescription;


    if (
        !field ||
        !field.grid
    ) {

        return;

    }


    const grid =
        field.grid;


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


    const configure_fields =
        function(fields) {

            if (
                !fields
            ) {

                return;

            }


            fields.forEach(
                function(df) {

                    if (
                        !df ||
                        !df.fieldname
                    ) {

                        return;

                    }


                    if (
                        visible_fields.includes(
                            df.fieldname
                        )
                    ) {

                        df.hidden = 0;

                        df.in_list_view = 1;

                        df.columns =
                            column_config[
                                df.fieldname
                            ];

                    }

                    else {

                        df.in_list_view = 0;

                        df.columns = 0;

                    }

                }
            );

        };


    configure_fields(
        grid.docfields
    );


    configure_fields(
        grid.editable_fields
    );


    configure_fields(
        grid.meta &&
        grid.meta.fields
    );


    if (
        grid.docfields
    ) {

        grid.editable_fields =
            grid.docfields.filter(
                function(df) {

                    return visible_fields.includes(
                        df.fieldname
                    );

                }
            );

    }


    grid.visible_columns = [];


    grid.setup_visible_columns();


    frm.refresh_field(
        "drug_prescription"
    );

}


// ============================================================
// DRUG PRESCRIPTION AUTO-FILL
// ============================================================

frappe.ui.form.on(
    "Drug Prescription",
    {

        drug_code(
            frm,
            cdt,
            cdn
        ) {

            const row =
                locals[cdt][cdn];


            if (
                !row.drug_code
            ) {

                return;

            }


            frappe.call({

                method:
                    "clinify.api.drug_search.get_drug_prescription_defaults",


                args: {

                    drug_code:
                        row.drug_code,

                },


                callback(r) {

                    if (
                        !r.message
                    ) {

                        return;

                    }


                    const data =
                        r.message;


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

    }
);


// ============================================================
// PRINT PRESCRIPTION BUTTON
// ============================================================

function add_clinify_print_button(
    frm
) {

    frm.add_custom_button(

        __(
            "Print Prescription"
        ),

        function() {

            const url =

                "/printview" +

                "?doctype=" +

                encodeURIComponent(
                    "Patient Encounter"
                ) +

                "&name=" +

                encodeURIComponent(
                    frm.doc.name
                ) +

                "&format=" +

                encodeURIComponent(
                    "Clinify Prescription"
                ) +

                "&trigger_print=1";


            window.open(

                url,

                "_blank"

            );

        }

    );

}


// ============================================================
// CREATE INVOICE BUTTON
// ============================================================

function add_clinify_invoice_button(
    frm
) {

    frm.add_custom_button(

        __(
            "Create Invoice"
        ),

        function() {

            frappe.call({

                method:
                    "clinify.encounter.create_invoice_from_encounter",


                args: {

                    encounter_name:
                        frm.doc.name,

                },


                freeze: true,


                freeze_message:
                    __(
                        "Creating Invoice..."
                    ),


                callback(r) {

                    if (
                        !r.message
                    ) {

                        return;

                    }


                    frappe.show_alert({

                        message:
                            __(
                                "Invoice Created Successfully"
                            ),

                        indicator:
                            "green",

                    });


                    frappe.set_route(

                        "Form",

                        "Sales Invoice",

                        r.message

                    );

                },

            });

        },


        __(
            "Create"
        )

    );

}

// ============================================================

// ============================================================
// ============================================================


// ============================================================
// CLINIFY DENTAL SERVICES — INLINE GRID FINAL
// ============================================================
//
// Final doctor workflow:
//
//   + Add Dental Service
//          |
//          v
//   Dental Service cell becomes a selector
//          |
//          v
//   Select service
//          |
//          +--> requires_tooth = 0
//          |       Tooth Number = —
//          |
//          +--> requires_tooth = 1
//                  Tooth Number = FDI selector
//
// Doctor-facing columns:
//
//   Dental Service | Tooth Number | Remarks
//
// Quantity remains stored internally as qty=default_qty.
// ============================================================

console.log("CLINIFY DENTAL SERVICES INLINE GRID FINAL LOADED");

const CLINIFY_FDI_TEETH = [
    "11", "12", "13", "14", "15", "16", "17", "18",
    "21", "22", "23", "24", "25", "26", "27", "28",
    "31", "32", "33", "34", "35", "36", "37", "38",
    "41", "42", "43", "44", "45", "46", "47", "48"
];

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

        setup_clinify_dental_services_grid(frm);
    }

});


function setup_clinify_dental_services_grid(frm) {

    const field =
        frm.fields_dict.custom_dental_services;

    if (!field || !field.grid) {
        return;
    }

    const grid = field.grid;

    // ------------------------------------------------------------
    // Native Frappe Add Row is disabled.
    // ------------------------------------------------------------

    grid.cannot_add_rows = true;

    // Prevent the Frappe row editor/pencil workflow.
    grid.cannot_edit_rows = true;

    grid.wrapper
        .find(".grid-add-row")
        .hide();

    // ------------------------------------------------------------
    // Keep only the three clinical columns visible.
    // ------------------------------------------------------------

    try {

        frm.set_df_property(
            "custom_dental_services",
            "fields",
            [
                "dental_service",
                "tooth_area",
                "remarks"
            ]
        );

    } catch (e) {
        // DocType in_list_view remains authoritative.
    }

    // ------------------------------------------------------------
    // Create the single Add Dental Service control.
    // ------------------------------------------------------------

    // ------------------------------------------------------------
    // Re-render the custom Tooth / Area selector whenever Frappe
    // re-renders a Dental Services grid row.
    //
    // Frappe can rebuild grid-row DOM when the doctor moves between
    // sections or re-enters a row. The row data remains intact, but
    // custom DOM injected into field_area is otherwise destroyed.
    // ------------------------------------------------------------

    if (!grid.__clinify_tooth_render_handler_bound) {

        grid.wrapper.on(
            "grid-row-render.clinifyDentalTooth",
            function(event, grid_row) {

                if (
                    !grid_row ||
                    !grid_row.doc ||
                    !grid_row.doc.dental_service
                ) {
                    return;
                }

                update_clinify_tooth_cell(
                    frm,
                    grid_row
                );

            }
        );

        grid.__clinify_tooth_render_handler_bound = true;
    }

    if (!grid.__clinify_inline_add_button) {

        const button = $(
            '<button type="button" ' +
            'class="btn btn-xs btn-default clinify-inline-add-dental">' +
            '+ ' + __("Add Dental Service") +
            '</button>'
        );

        button.css({
            "margin-top": "8px",
            "margin-bottom": "8px"
        });

        button.on("click", function() {
            add_clinify_inline_dental_row(frm);
        });

        grid.wrapper.append(button);

        grid.__clinify_inline_add_button = button;
    }

    render_clinify_dental_rows(frm);
}


function add_clinify_inline_dental_row(frm) {

    const row =
        frm.add_child("custom_dental_services");

    row.dental_service = "";
    row.tooth_area = "";
    row.qty = 1;
    row.remarks = "";

    // One controlled refresh so Frappe creates the
    // native child-table Link field for this row.
    frm.refresh_field("custom_dental_services");

    // Activate the native Dental Service Link field.
    setTimeout(function() {

        const field =
            frm.fields_dict.custom_dental_services;

        if (!field || !field.grid) {
            return;
        }

        const grid_row =
            field.grid.grid_rows.find(function(item) {
                return item.doc.name === row.name;
            });

        if (!grid_row) {
            return;
        }

        const column =
            grid_row.columns &&
            grid_row.columns.dental_service;

        if (!column || !column.field_area) {
            return;
        }

        const input =
            $(column.field_area).find("input").first();

        if (!input.length) {
            return;
        }

        input.trigger("focus");

    }, 0);
}


function render_clinify_dental_rows(frm) {

    const field =
        frm.fields_dict.custom_dental_services;

    if (!field || !field.grid) {
        return;
    }

    const grid =
        field.grid;

    grid.wrapper
        .find(".grid-add-row")
        .hide();

    (grid.grid_rows || []).forEach(function(grid_row) {

        if (!grid_row || !grid_row.doc) {
            return;
        }

        if (!grid_row.doc.dental_service) {
            return;
        }

        update_clinify_tooth_cell(
            frm,
            grid_row
        );

    });
}


function update_clinify_tooth_cell(
    frm,
    grid_row
) {

    const row =
        grid_row.doc;

    const column =
        grid_row.columns &&
        grid_row.columns.tooth_area;

    if (!column || !column.field_area) {
        return;
    }

    const wrapper =
        $(column.field_area);

    // Keep Tooth / Area content visually centered in the grid cell.
    wrapper.css({
        "text-align": "center"
    });

    const requires_tooth =
        Number(
            row.__clinify_requires_tooth || 0
        ) === 1;

    wrapper
        .find(".clinify-tooth-select")
        .remove();

    wrapper
        .find(".clinify-tooth-display")
        .remove();

    wrapper
        .find("input")
        .hide();

    if (!requires_tooth) {

        wrapper.append(
            $("<span>")
                .addClass(
                    "clinify-tooth-display"
                )
                .css({
                    "color": "#999",
                    "padding": "6px 8px"
                })
                .text("—")
        );

        return;
    }

    const select =
        $('<select class="form-control input-sm ' +
          'clinify-tooth-select"></select>');

    select.css({
        "text-align": "center",
        "text-align-last": "center"
    });

    select.append(
        $("<option>")
            .val("")
            .text(__("Select Tooth Number"))
    );

    CLINIFY_FDI_TEETH.forEach(function(tooth) {

        select.append(
            $("<option>")
                .val(tooth)
                .text(tooth)
        );

    });

    select.val(
        row.tooth_area || ""
    );

    wrapper.append(select);

    // ------------------------------------------------------------
    // Critical: this event only changes the row data.
    // It does NOT refresh the grid.
    // ------------------------------------------------------------

    select.on("change", function() {

        row.tooth_area =
            $(this).val() || "";

        // Keep the control alive and visible.
        select.val(
            row.tooth_area
        );

    });

}


frappe.ui.form.on(
    "Clinify Encounter Service",
    {

        dental_service(frm, cdt, cdn) {

            const row =
                locals[cdt][cdn];

            if (!row || !row.dental_service) {
                return;
            }

            frappe.db.get_value(
                "Dental Service",
                row.dental_service,
                [
                    "requires_tooth",
                    "default_qty"
                ]
            ).then(function(r) {

                const values =
                    r.message || {};

                row.qty =
                    Number(
                        values.default_qty || 1
                    );

                row.__clinify_requires_tooth =
                    Number(
                        values.requires_tooth || 0
                    ) === 1 ? 1 : 0;

                if (
                    !row.__clinify_requires_tooth
                ) {
                    row.tooth_area = "";
                }

                const field =
                    frm.fields_dict.custom_dental_services;

                if (
                    field &&
                    field.grid
                ) {

                    const grid_row =
                        field.grid.grid_rows.find(
                            function(item) {
                                return (
                                    item.doc &&
                                    item.doc.name === cdn
                                );
                            }
                        );

                    if (grid_row) {
                        update_clinify_tooth_cell(
                            frm,
                            grid_row
                        );
                    }
                }

            });

        }

    }
);


// ------------------------------------------------------------
// Clinical validation.
// This remains a safety net even though the UI requires the
// tooth selection for tooth-specific services.
// ------------------------------------------------------------

frappe.ui.form.on(
    "Patient Encounter",
    {

        validate(frm) {

            const rows =
                frm.doc.custom_dental_services || [];

            for (const row of rows) {

                if (!row.dental_service) {
                    frappe.throw(
                        __("Please select a Dental Service for row {0}.", [
                            row.idx
                        ])
                    );
                }

                const requires_tooth =
                    Number(
                        row.__clinify_requires_tooth || 0
                    ) === 1;

                if (
                    requires_tooth &&
                    !row.tooth_area
                ) {

                    frappe.throw(
                        __("Row {0}: Please select a Tooth Number for {1}.", [
                            row.idx,
                            row.dental_service
                        ])
                    );

                }

            }

        }

    }
);

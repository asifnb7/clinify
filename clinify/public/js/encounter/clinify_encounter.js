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
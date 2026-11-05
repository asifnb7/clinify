
const CLINIFY_LINK_MASTERS = {
    dosage: {
        doctype: "Prescription Dosage",
        fields: ["name", "dosage"],
    },
    period: {
        doctype: "Prescription Duration",
        fields: ["name"],
    },
};

const clinifyOptionCache = {};

function clinify_get_options(fieldname) {
    if (!clinifyOptionCache[fieldname]) {
        const config = CLINIFY_LINK_MASTERS[fieldname];

        clinifyOptionCache[fieldname] = frappe
            .call({
                method: "frappe.client.get_list",
                args: {
                    doctype: config.doctype,
                    fields: config.fields,
                    limit_page_length: 200,
                },
            })
            .then(function (r) {
                let options = (r.message || []).map(function (row) {
                    return {
                        label:
                            fieldname === "dosage" && row.dosage
                                ? row.dosage
                                : row.name,
                        value: row.name,
                    };
                });

                if (fieldname === "period") {
                    options = options
                        .filter(function (option) {
                            return /^\d+\s+Day$/i.test(option.value);
                        })
                        .sort(function (a, b) {
                            const aDays = parseInt(
                                a.value,
                                10
                            );
                            const bDays = parseInt(
                                b.value,
                                10
                            );

                            return aDays - bDays;
                        });
                }

                return options;
            })
            .catch(function (error) {
                delete clinifyOptionCache[fieldname];
                throw error;
            });
    }

    return clinifyOptionCache[fieldname];
}



function clinify_format_medicine_name(name) {
    let value = String(name || "").trim();

    if (!value) {
        return "";
    }

    value = value.replace(/\s+(Tablet|Tablets|Tab)$/i, "");

    if (/\s+Syrup$/i.test(value)) {
        value = value.replace(/\s+Syrup$/i, "");
        return value.trim() + " (Syrup)";
    }

    return value;
}



function clinify_format_medicine_name(name) {
    let value = String(name || "").trim();

    if (!value) {
        return "";
    }

    // Tablet is the default dosage form in the medicine catalogue.
    // Hide only the display suffix; do not change the stored Item.
    value = value.replace(/\s+(Tablet|Tablets|Tab)$/i, "");

    // Keep Syrup distinguishable.
    if (/\s+Syrup$/i.test(value)) {
        value = value.replace(/\s+Syrup$/i, "");
        return value.trim() + " (Syrup)";
    }

    return value;
}



function clinify_format_medicine_name(name) {
    let value = String(name || "").trim();

    if (!value) {
        return "";
    }

    value = value.replace(/\s+(Tablet|Tablets|Tab)$/i, "");

    if (/\s+Syrup$/i.test(value)) {
        value = value.replace(/\s+Syrup$/i, "");
        return value.trim() + " (Syrup)";
    }

    return value;
}


function clinify_render_medicine_dropdown(field) {
    if (!field || !field.awesomplete) {
        return;
    }

    const awesomplete = field.awesomplete;

    if (awesomplete.__clinifyNativeMedicineRendererBound) {
        return;
    }

    awesomplete.__clinifyNativeMedicineRendererBound = true;

    /*
     * Frappe's native Link control uses Awesomplete to render
     * each dropdown entry. Wrap that renderer instead of modifying
     * the DOM after rendering.
     *
     * This preserves:
     * - native Frappe Link control
     * - native search/autocomplete
     * - native keyboard navigation
     * - native grid structure
     * - stored Item code
     */
    const originalItemRenderer = awesomplete.item;

    if (typeof originalItemRenderer !== "function") {
        return;
    }

    awesomplete.item = function (item, input) {
        const html = originalItemRenderer.call(
            awesomplete,
            item,
            input
        );

        const container = document.createElement("div");
        container.innerHTML = html;

        const strong = container.querySelector("strong");

        if (strong) {
            strong.textContent =
                clinify_format_medicine_name(
                    strong.textContent
                );
        }

        container
            .querySelectorAll(".small")
            .forEach(function (element) {
                element.remove();
            });

        return container.innerHTML;
    };
}



function clinify_find_grid_control(gridRow, input) {
    if (!gridRow) {
        return null;
    }

    const controls = (gridRow.on_grid_fields || []).concat(
        gridRow.grid_form
            ? Object.values(gridRow.grid_form.fields_dict || {})
            : []
    );

    return (
        controls.find(function (control) {
            return (
                control &&
                control.$input &&
                control.$input[0] === input
            );
        }) || null
    );
}

function clinify_open_full_list(field, fieldname) {
    if (!field || !field.$input || !field.awesomplete) {
        return;
    }

    clinify_get_options(fieldname).then(function (options) {
        if (
            !field.$input ||
            !field.awesomplete ||
            document.activeElement !== field.$input[0]
        ) {
            return;
        }

        const awesomplete = field.awesomplete;

        if (!awesomplete.__clinifyOriginalFilter) {
            awesomplete.__clinifyOriginalFilter =
                awesomplete.filter;
        }

        awesomplete.list = options;
        awesomplete.filter = function () {
            return true;
        };

        awesomplete.open();
    });
}

function clinify_bind_grid_dropdowns(frm) {
    const field = frm.fields_dict.drug_prescription;

    if (!field || !field.grid || !field.grid.wrapper) {
        return;
    }

    const grid = field.grid;

    grid.wrapper
        .off(".clinifyDropdown")
        .on(
            "focusin.clinifyDropdown click.clinifyDropdown",
            'input[data-fieldname="dosage"], input[data-fieldname="period"], input[data-fieldname="drug_code"]',
            function () {
                const input = this;
                const fieldname =
                    input.getAttribute("data-fieldname");

                const rowName = $(input)
                    .closest(".grid-row")
                    .attr("data-name");

                const gridRow =
                    grid.grid_rows_by_docname &&
                    grid.grid_rows_by_docname[rowName];

                const control = clinify_find_grid_control(
                    gridRow,
                    input
                );

                if (!control || !control.awesomplete) {
                    return;
                }

                if (fieldname === "drug_code") {
                    return;
                }

                if (control.awesomplete.isOpened) {
                    return;
                }

                setTimeout(function () {
                    clinify_open_full_list(
                        control,
                        fieldname
                    );
                }, 0);
            }
        );
}


/*
 * Clinify Medicine Link display
 *
 * The prescription grid uses Frappe's native Link control.
 * Frappe's search_link response contains a description which
 * is rendered as the second line of the autocomplete.
 *
 * For the Clinify medicine field only, remove that description
 * from the native Awesomplete result after the server response
 * has been received.
 *
 * This does NOT replace the Link control or the grid.
 */
function clinify_strip_medicine_link_description(field) {
    if (!field || field.df.fieldname !== "drug_code") {
        return;
    }

    if (
        !field.awesomplete ||
        field.__clinifyMedicineDescriptionBound
    ) {
        return;
    }

    field.__clinifyMedicineDescriptionBound = true;

    const awesomplete = field.awesomplete;

    const originalEvaluate = awesomplete.evaluate;

    if (typeof originalEvaluate !== "function") {
        return;
    }

    awesomplete.evaluate = function () {
        originalEvaluate.apply(awesomplete, arguments);

        if (!Array.isArray(awesomplete.list)) {
            return;
        }

        awesomplete.list.forEach(function (item) {
            if (item && typeof item === "object") {
                delete item.description;
            }
        });
    };
}


function clinify_bind_inline_medicine_links(frm) {
    const tableField =
        frm.fields_dict &&
        frm.fields_dict.drug_prescription;

    if (
        !tableField ||
        !tableField.grid ||
        !tableField.grid.grid_rows
    ) {
        return;
    }

    tableField.grid.grid_rows.forEach(function (gridRow) {
        if (!gridRow || !gridRow.columns) {
            return;
        }

        const column = gridRow.columns.drug_code;

        if (!column || !column.field) {
            return;
        }

        clinify_strip_medicine_link_description(column.field);
    });
}



function clinify_format_medicine_name(name) {
    let value = String(name || "").trim();

    if (!value) {
        return "";
    }

    value = value.replace(/\s+(Tablet|Tablets|Tab)$/i, "");

    if (/\s+Syrup$/i.test(value)) {
        value = value.replace(/\s+Syrup$/i, "");
        return value.trim() + " (Syrup)";
    }

    return value;
}


function clinify_bind_actual_medicine_link(frm) {
    const tableField =
        frm.fields_dict &&
        frm.fields_dict.drug_prescription;

    if (
        !tableField ||
        !tableField.grid ||
        !tableField.grid.wrapper
    ) {
        return;
    }

    const grid = tableField.grid;

    const selector =
        '.grid-row input[data-fieldname="drug_code"]';

    grid.wrapper
        .off("focusin.clinifyMedicineLink", selector)
        .on(
            "focusin.clinifyMedicineLink",
            selector,
            function () {
                const input = this;
                const rowWrapper = $(input).closest(".grid-row");
                const gridRow = rowWrapper.data("grid_row");

                if (!gridRow) {
                    return;
                }

                const field =
                    gridRow.on_grid_fields_dict &&
                    gridRow.on_grid_fields_dict.drug_code;

                if (
                    !field ||
                    !field.awesomplete ||
                    field.__clinifyActualMedicineLinkBound
                ) {
                    return;
                }

                field.__clinifyActualMedicineLinkBound = true;

                const awesomplete = field.awesomplete;
                const originalItem = awesomplete.item;

                /*
                 * Frappe's native Link renderer adds the description
                 * below the label. Replace ONLY the renderer for this
                 * specific medicine Link control.
                 */
                awesomplete.item = function (item, value, index) {
                    const element =
                        originalItem.call(
                            awesomplete,
                            item,
                            value,
                            index
                        );

                    const strong =
                        element.querySelector("strong");

                    if (strong) {
                        strong.textContent =
                            clinify_format_medicine_name(
                                strong.textContent
                            );
                    }

                    element
                        .querySelectorAll(".small")
                        .forEach(function (node) {
                            node.remove();
                        });

                    return element;
                };

                /*
                 * Capture the selection event BEFORE Frappe's own
                 * ControlLink handler. This changes only the displayed
                 * label; the actual Item value remains unchanged.
                 */
                input.addEventListener(
                    "awesomplete-select",
                    function (event) {
                        if (!event.text) {
                            return;
                        }

                        event.text.label =
                            clinify_format_medicine_name(
                                event.text.label ||
                                event.text.value
                            );

                        event.text.description = "";
                    },
                    true
                );

                /*
                 * The list may already have been loaded before our
                 * renderer was attached. Re-evaluate if necessary.
                 */
                if (awesomplete.opened) {
                    awesomplete.evaluate();
                }
            }
        );
}



function clinify_medicine_wrap_css() {
    if (document.getElementById("clinify-medicine-wrap-css")) {
        return;
    }

    const style = document.createElement("style");
    style.id = "clinify-medicine-wrap-css";
    style.textContent = `
        .form-grid .grid-row .grid-static-col[data-fieldname="drug_code"] {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            height: auto !important;
            min-height: 36px;
            overflow-wrap: anywhere !important;
            word-break: normal !important;
        }

        .form-grid .grid-row .grid-static-col[data-fieldname="drug_code"] .ellipsis {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            height: auto !important;
            overflow-wrap: anywhere !important;
            word-break: normal !important;
        }

        .form-grid .grid-row {
            height: auto !important;
            min-height: 36px;
        }
    `;

    document.head.appendChild(style);
}

frappe.ui.form.on("Patient Encounter", {
    refresh(frm) {
        clinify_medicine_wrap_css();
        clinify_bind_actual_medicine_link(frm);
        const tableField =
            frm.fields_dict &&
            frm.fields_dict.drug_prescription;

        if (
            tableField &&
            tableField.grid &&
            Array.isArray(tableField.grid.docfields)
        ) {
            const medicineField =
                tableField.grid.docfields.find(function (df) {
                    return df.fieldname === "drug_code";
                });

            if (medicineField) {
                medicineField.label = __("Medicine Name");
            }
        }

        clinify_bind_grid_dropdowns(frm);
        clinify_bind_inline_medicine_links(frm);
    },
});

frappe.ui.form.on("Drug Prescription", {
    form_render(frm, cdt, cdn) {
        const gridRow = frm.cur_grid;

        if (!gridRow) {
            return;
        }

        let drugCodeField = null;

        if (Array.isArray(gridRow.on_grid_fields)) {
            drugCodeField =
                gridRow.on_grid_fields.find(function (control) {
                    return (
                        control &&
                        control.df &&
                        control.df.fieldname === "drug_code"
                    );
                }) || null;
        }

        if (
            !drugCodeField &&
            gridRow.grid_form &&
            gridRow.grid_form.fields_dict
        ) {
            drugCodeField =
                gridRow.grid_form.fields_dict.drug_code || null;
        }


          if (drugCodeField) {
              clinify_render_medicine_dropdown(drugCodeField);
          }


        ["dosage", "period"].forEach((fieldname) => {
            let field = null;

            // The live controls in this prescription grid are exposed
            // through on_grid_fields.
            if (Array.isArray(gridRow.on_grid_fields)) {
                field =
                    gridRow.on_grid_fields.find(function (control) {
                        return (
                            control &&
                            control.df &&
                            control.df.fieldname === fieldname
                        );
                    }) || null;
            }

            // Fallback for other Frappe grid rendering paths.
            if (!field && gridRow.grid_form && gridRow.grid_form.fields_dict) {
                field = gridRow.grid_form.fields_dict[fieldname] || null;
            }

            if (!field) {
                return;
            }

            // These are catalogue selections, not master-data creation points.
            field.df.only_select = 1;

});
    },

    setup(frm) {
        frm.set_query("drug_code", "drug_prescription", function () {
            return {
                query: "clinify.api.drug_search.get_medication_item_query",
            };
        });

        frm.set_query("dosage", "drug_prescription", function () {
            return {
                page_length: 100,
            };
        });

        frm.set_query("period", "drug_prescription", function () {
            return {
                query:
                    "clinify.api.drug_search.get_prescription_duration_query",
            };
        });
    },

    dosage(frm, cdt, cdn) {
        frm.refresh_field("drug_prescription");
    },

    period(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (row.period !== "Custom" && row.custom_prescription_duration_days) {
            frappe.model.set_value(
                cdt,
                cdn,
                "custom_prescription_duration_days",
                null
            );
        }

        frm.refresh_field("drug_prescription");
    },

    custom_prescription_duration_days(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (!row.custom_prescription_duration_days) {
            return;
        }

        if (row.period !== "Custom") {
            frappe.model.set_value(
                cdt,
                cdn,
                "period",
                "Custom"
            );
        }

        const days = parseInt(
            row.custom_prescription_duration_days,
            10
        );

        if (!Number.isInteger(days) || days < 1) {
            frappe.msgprint(
                __("Custom duration must be a positive whole number of days.")
            );
            frappe.model.set_value(
                cdt,
                cdn,
                "custom_prescription_duration_days",
                null
            );
        }

        frm.refresh_field("drug_prescription");
    },

    drug_code(frm, cdt, cdn) {
console.log("CLINIFY DRUG CODE HANDLER FIRED", cdt, cdn);
const row = locals[cdt][cdn];
        const requestId = (row.__clinifyDrugDefaultsRequest || 0) + 1;
        row.__clinifyDrugDefaultsRequest = requestId;

        const fieldsToClear = [
            "drug_name",
            "medication",
            "strength",
            "strength_uom",
            "dosage_form",
            "dosage",
            "period",
            "custom_prescription_duration_days",
            "interval",
            "interval_uom",
        ];

        fieldsToClear.forEach((field) => {
            frappe.model.set_value(
                cdt,
                cdn,
                field,
                field === "strength" || field === "interval" ? 0 : ""
            );
        });

        const selectedDrugCode = row.drug_code;

        if (!selectedDrugCode) {
            return;
        }

        // CASE 1:
        // The selected Item is the medicine catalogue record.
        // No Medication / Medication Linked Item resolution is required.
        // Dosage and period remain doctor-controlled.
        frappe.model.set_value(
            cdt,
            cdn,
            "drug_name",
            row.drug_name || row.item_name || selectedDrugCode
        );

        frappe.model.set_value(
            cdt,
            cdn,
            "dosage",
            "0-0-0"
        );

        frappe.model.set_value(
            cdt,
            cdn,
            "period",
            "0 Day"
        );

        frm.refresh_field("drug_prescription");
    },
});

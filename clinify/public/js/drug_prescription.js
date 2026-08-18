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

            callback: function (r) {
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
                    "medication",
                    data.medication || ""
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

                if (data.interval !== null && data.interval !== undefined) {
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

                frm.refresh_field("drug_prescription");
            },
        });
    },
});
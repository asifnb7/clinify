const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function createHarness(row) {
    let handlers;
    const callbacks = [];
    const messages = [];
    const locals = { "Drug Prescription": { row } };
    const frappe = {
        ui: {
            form: {
                on(_doctype, registeredHandlers) {
                    handlers = registeredHandlers;
                },
            },
        },
        model: {
            set_value(doctype, rowName, field, value) {
                locals[doctype][rowName][field] = value;
                return Promise.resolve();
            },
        },
        call(options) {
            callbacks.push(options.callback);
        },
        msgprint(message) {
            messages.push(message);
        },
    };
    const source = fs.readFileSync(
        path.join(__dirname, "..", "drug_prescription.js"),
        "utf8"
    );
    vm.runInNewContext(source, { frappe, locals });

    return {
        callbacks,
        handlers,
        messages,
        locals,
        row,
        frm: { refresh_field() {} },
    };
}

test("failed defaults lookup leaves no values from the previous medicine", () => {
    const harness = createHarness({
        drug_code: "ITEM-NEW",
        drug_name: "Old drug",
        medication: "Old medication",
        strength: 500,
        strength_uom: "mg",
        dosage_form: "Tablet",
        dosage: "1-0-1",
        period: "5 Day",
        interval: 8,
        interval_uom: "Hour",
    });

    harness.handlers.drug_code(harness.frm, "Drug Prescription", "row");

    for (const field of [
        "medication",
        "strength_uom",
        "dosage_form",
        "dosage",
        "period",
        "interval_uom",
    ]) {
        assert.equal(harness.row[field], "");
    }
    assert.equal(harness.row.strength, 0);
    assert.equal(harness.row.interval, 0);

    harness.callbacks[0]({ message: null });

    assert.equal(harness.row.medication, "");
    assert.equal(harness.row.dosage, "");
    assert.equal(harness.row.period, "");
});

test("a slower response for the previous selection is ignored", () => {
    const harness = createHarness({ drug_code: "ITEM-OLD", medication: "Previous" });

    harness.handlers.drug_code(harness.frm, "Drug Prescription", "row");
    harness.row.drug_code = "ITEM-NEW";
    harness.handlers.drug_code(harness.frm, "Drug Prescription", "row");

    harness.callbacks[0]({
        message: {
            mapping_valid: true,
            medication: "Previous",
            strength: 500,
            dosage: "old",
        },
    });
    assert.equal(harness.row.medication, "");

    harness.callbacks[1]({
        message: {
            mapping_valid: true,
            medication: "Current",
            strength: 10,
            dosage: "1-0-1",
            period: "5 Day",
        },
    });
    assert.equal(harness.row.medication, "Current");
    assert.equal(harness.row.strength, 10);
});
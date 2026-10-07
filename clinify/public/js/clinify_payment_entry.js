/*
 * Clinify Payment Entry UI
 *
 * Provides direct access to the Sales Invoice associated with
 * this Payment Entry.
 *
 * Accounting and payment processing remain standard ERPNext.
 * This file only controls Clinify navigation/print actions.
 */

frappe.ui.form.on("Payment Entry", {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        add_clinify_payment_actions(frm);
    },
});


function get_referenced_sales_invoice(frm) {

    const references = frm.doc.references || [];

    const reference = references.find(function (row) {
        return (
            row.reference_doctype === "Sales Invoice" &&
            row.reference_name
        );
    });

    return reference ? reference.reference_name : null;
}


function add_clinify_payment_actions(frm) {

    if (frm.__clinify_payment_actions_added) {
        return;
    }

    frm.__clinify_payment_actions_added = true;

    frm.add_custom_button(
        __("View Invoice"),
        function () {

            const invoice = get_referenced_sales_invoice(frm);

            if (!invoice) {
                frappe.msgprint(
                    __("No Sales Invoice is linked to this Payment Entry.")
                );
                return;
            }

            frappe.set_route(
                "Form",
                "Sales Invoice",
                invoice
            );
        },
        __("Clinify")
    );


    frm.add_custom_button(
        __("Print Clinify Invoice"),
        function () {

            const invoice = get_referenced_sales_invoice(frm);

            if (!invoice) {
                frappe.msgprint(
                    __("No Sales Invoice is linked to this Payment Entry.")
                );
                return;
            }

            frappe.utils.print(
                "Sales Invoice",
                invoice,
                "Clinify Invoice",
                null,
                frappe.boot.lang
            );
        },
        __("Clinify")
    );


    frm.add_custom_button(
        __("Download Clinify Invoice"),
        function () {

            const invoice = get_referenced_sales_invoice(frm);

            if (!invoice) {
                frappe.msgprint(
                    __("No Sales Invoice is linked to this Payment Entry.")
                );
                return;
            }

            const url =
                `/api/method/frappe.utils.print_format.download_pdf` +
                `?doctype=${encodeURIComponent("Sales Invoice")}` +
                `&name=${encodeURIComponent(invoice)}` +
                `&format=${encodeURIComponent("Clinify Invoice")}` +
                `&no_letterhead=1`;

            window.open(
                url,
                "_blank"
            );
        },
        __("Clinify")
    );
}

/*
 * Clinify Sales Invoice UI
 *
 * Patient-facing invoice actions.
 *
 * Billing and Sales Invoice data remain unchanged.
 * This file only controls the Clinify print/download experience.
 */

frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        add_clinify_invoice_actions(frm);
    },

    onload_post_render(frm) {
        if (frm.is_new()) {
            return;
        }

        add_clinify_invoice_actions(frm);
    },
});


function add_clinify_invoice_actions(frm) {

    if (frm.__clinify_invoice_actions_added) {
        return;
    }

    frm.__clinify_invoice_actions_added = true;

    frm.add_custom_button(
        __("Print Clinify Invoice"),
        function () {

            frappe.utils.print(
                "Sales Invoice",
                frm.doc.name,
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

            const url =
                `/api/method/frappe.utils.print_format.download_pdf` +
                `?doctype=${encodeURIComponent("Sales Invoice")}` +
                `&name=${encodeURIComponent(frm.doc.name)}` +
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

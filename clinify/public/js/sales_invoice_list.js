frappe.listview_settings["Sales Invoice"] = {

    add_fields: [
        "customer_name",
        "custom_primary_doctor",
        "grand_total",
        "outstanding_amount",
        "posting_date",
        "status"
    ],

    formatters: {

        grand_total(value) {
            return format_currency(value);
        },

        outstanding_amount(value) {
            return format_currency(value);
        }

    },

    get_indicator(doc) {

        if (doc.status === "Paid") {
            return [__("Paid"), "green", "status,=,Paid"];
        }

        if (doc.status === "Overdue") {
            return [__("Overdue"), "orange", "status,=,Overdue"];
        }

        if (doc.status === "Unpaid") {
            return [__("Unpaid"), "red", "status,=,Unpaid"];
        }

        if (doc.status === "Cancelled") {
            return [__("Cancelled"), "darkgrey", "status,=,Cancelled"];
        }

        if (doc.status === "Draft") {
            return [__("Draft"), "blue", "docstatus,=,0"];
        }

    }

};

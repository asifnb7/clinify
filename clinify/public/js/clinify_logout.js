(function () {
    "use strict";

    if (
        !window.frappe ||
        !frappe.Application ||
        !frappe.boot ||
        frappe.boot.clinify_is_control_site !== false
    ) {
        return;
    }

    frappe.Application.prototype.logout = function () {
        const me = this;
        me.logged_out = true;

        frappe.confirm(__("Are you sure you want to log out?"), function () {
            return frappe.call({
                method: "clinify.saas.sso.logout_to_control",
                callback: function (response) {
                    if (response.exc) {
                        return;
                    }

                    if (typeof response.message !== "string" || !response.message) {
                        frappe.msgprint(__("Could not determine the Clinify sign-out destination."));
                        return;
                    }

                    window.location.assign(response.message);
                },
            });
        });
    };
})();

/*
 * ==========================================================
 * Clinify UI Framework
 * Version : 1.0
 * ==========================================================
 */

frappe.ready(function () {

    // Current Desk Route
    const route = frappe.get_route();

    if (!route || !route.length) {
        return;
    }

    console.log("Clinify UI Framework Loaded");

});

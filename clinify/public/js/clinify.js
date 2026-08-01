console.log("Clinify JS Loaded");

frappe.router.on("change", () => {

    const route = frappe.get_route();

    if (!route || !route.length) return;

    console.log("Route:", route);

    if (route[0] === "reception") {

        console.log("Redirecting to Reception Dashboard");

        frappe.set_route("reception-dashboard");
    }
});
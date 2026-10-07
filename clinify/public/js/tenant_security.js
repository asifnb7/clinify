(function () {
    "use strict";

    const hostname = (window.location.hostname || "").toLowerCase();
    const controlSites = new Set([
        "clinify.localhost",
        "clinify.salniz.com"
    ]);

    if (controlSites.has(hostname)) {
        return;
    }

    function hardenTenantUI() {
        // Tenant users must never receive the Frappe "Change User"
        // selector. This is deliberately tenant-only.
        document.querySelectorAll("button, a, [role='button']").forEach(function (el) {
            const text = (el.textContent || "")
                .replace(/\s+/g, " ")
                .trim()
                .toLowerCase();

            if (text === "change user") {
                el.remove();
            }
        });

        document.querySelectorAll(
            '[data-label="Change User"], [data-doctype="Change User"]'
        ).forEach(function (el) {
            el.remove();
        });

        // Control-plane SaaS routes must never be exposed on tenant sites.
        if (window.frappe && frappe.get_route) {
            const route = frappe.get_route() || [];
            const first = String(route[0] || "").toLowerCase();

            if (first === "saas" || first === "saas-dashboard") {
                frappe.set_route("home");
            }
        }
    }

    function start() {
        hardenTenantUI();

        if (document.documentElement) {
            const observer = new MutationObserver(function () {
                hardenTenantUI();
            });

            observer.observe(document.documentElement, {
                childList: true,
                subtree: true
            });
        }

        if (window.frappe && frappe.router && frappe.router.on) {
            frappe.router.on("change", function () {
                setTimeout(hardenTenantUI, 50);
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();

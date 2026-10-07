frappe.pages["saas-dashboard"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __("SaaS Dashboard"),
        single_column: true,
    });

    page.main.html(`
        <style>
            .clinify-saas-dashboard {
                padding: 8px 4px 32px;
            }

            .clinify-saas-header {
                margin-bottom: 22px;
            }

            .clinify-saas-header h2 {
                margin: 0 0 6px;
                font-size: 24px;
                font-weight: 600;
            }

            .clinify-saas-header p {
                margin: 0;
                color: var(--text-muted);
                font-size: 14px;
            }

            .clinify-saas-metrics {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 16px;
                margin-bottom: 24px;
            }

            .clinify-saas-card {
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 18px 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,.05);
            }

            .clinify-saas-card-label {
                color: var(--text-muted);
                font-size: 13px;
                margin-bottom: 8px;
            }

            .clinify-saas-card-value {
                font-size: 30px;
                line-height: 1.1;
                font-weight: 600;
                color: var(--text-color);
            }

            .clinify-saas-card-sub {
                margin-top: 8px;
                font-size: 12px;
                color: var(--text-muted);
            }

            .clinify-saas-section {
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                margin-bottom: 20px;
                overflow: hidden;
            }

            .clinify-saas-section-head {
                padding: 16px 20px;
                border-bottom: 1px solid var(--border-color);
            }

            .clinify-saas-section-head h3 {
                margin: 0;
                font-size: 17px;
                font-weight: 600;
            }

            .clinify-saas-actions {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 14px;
                padding: 18px 20px;
            }

            .clinify-saas-action {
                border: 1px solid var(--border-color);
                border-radius: 10px;
                padding: 16px;
                background: var(--card-bg);
                cursor: pointer;
                text-align: left;
                transition: border-color .15s ease,
                            box-shadow .15s ease;
            }

            .clinify-saas-action:hover {
                border-color: var(--primary);
                box-shadow: 0 2px 8px rgba(0,0,0,.06);
            }

            .clinify-saas-action-title {
                font-weight: 600;
                margin-bottom: 5px;
            }

            .clinify-saas-action-text {
                color: var(--text-muted);
                font-size: 12px;
            }

            .clinify-saas-table-wrap {
                overflow-x: auto;
            }

            .clinify-saas-table {
                width: 100%;
                border-collapse: collapse;
            }

            .clinify-saas-table th {
                text-align: left;
                padding: 12px 16px;
                font-size: 12px;
                color: var(--text-muted);
                font-weight: 600;
                border-bottom: 1px solid var(--border-color);
                white-space: nowrap;
            }

            .clinify-saas-table td {
                padding: 14px 16px;
                border-bottom: 1px solid var(--border-color);
                vertical-align: middle;
                font-size: 13px;
            }

            .clinify-saas-table tr:last-child td {
                border-bottom: 0;
            }

            .clinify-saas-link {
                color: var(--text-color);
                font-weight: 600;
                cursor: pointer;
            }

            .clinify-saas-link:hover {
                color: var(--primary);
            }

            .clinify-saas-pill {
                display: inline-flex;
                align-items: center;
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 12px;
                background: var(--bg-light-gray);
                white-space: nowrap;
            }

            .clinify-saas-empty {
                padding: 28px 20px;
                color: var(--text-muted);
                text-align: center;
            }

            @media (max-width: 1100px) {
                .clinify-saas-metrics {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                .clinify-saas-actions {
                    grid-template-columns: 1fr;
                }
            }

            @media (max-width: 650px) {
                .clinify-saas-metrics {
                    grid-template-columns: 1fr;
                }
            }
        </style>

        <div class="clinify-saas-dashboard">
            <div class="clinify-saas-header">
                <h2>Clinify SaaS Dashboard</h2>
                <p>
                    Platform overview for clinics, subscriptions,
                    provisioning and tenant accounts.
                </p>
            </div>

            <div class="clinify-saas-metrics">
                <div class="clinify-saas-card">
                    <div class="clinify-saas-card-label">
                        Total Clinics
                    </div>
                    <div class="clinify-saas-card-value"
                         id="saas-total-clinics">—</div>
                    <div class="clinify-saas-card-sub">
                        Registered tenant accounts
                    </div>
                </div>

                <div class="clinify-saas-card">
                    <div class="clinify-saas-card-label">
                        Active Clinics
                    </div>
                    <div class="clinify-saas-card-value"
                         id="saas-active-clinics">—</div>
                    <div class="clinify-saas-card-sub">
                        Enabled and active
                    </div>
                </div>

                <div class="clinify-saas-card">
                    <div class="clinify-saas-card-label">
                        Active Subscriptions
                    </div>
                    <div class="clinify-saas-card-value"
                         id="saas-active-subscriptions">—</div>
                    <div class="clinify-saas-card-sub">
                        Current subscription periods
                    </div>
                </div>

                <div class="clinify-saas-card">
                    <div class="clinify-saas-card-label">
                        Trial Subscriptions
                    </div>
                    <div class="clinify-saas-card-value"
                         id="saas-trial-subscriptions">—</div>
                    <div class="clinify-saas-card-sub">
                        Clinics currently on Trial
                    </div>
                </div>
            </div>

            <div class="clinify-saas-section">
                <div class="clinify-saas-section-head">
                    <h3>Tenant Management</h3>
                </div>

                <div class="clinify-saas-actions">
                    <div class="clinify-saas-action"
                         id="saas-open-tenants">
                        <div class="clinify-saas-action-title">
                            Tenant Accounts
                        </div>
                        <div class="clinify-saas-action-text">
                            View and manage all Clinify clinics.
                        </div>
                    </div>

                    <div class="clinify-saas-action"
                         id="saas-new-tenant">
                        <div class="clinify-saas-action-title">
                            Create Tenant
                        </div>
                        <div class="clinify-saas-action-text">
                            Register a new clinic tenant.
                        </div>
                    </div>

                    <div class="clinify-saas-action"
                         id="saas-subscriptions">
                        <div class="clinify-saas-action-title">
                            Subscriptions & Plans
                        </div>
                        <div class="clinify-saas-action-text">
                            Manage subscription contracts and plans.
                        </div>
                    </div>
                </div>
            </div>

            <div class="clinify-saas-section">
                <div class="clinify-saas-section-head">
                    <h3>Tenant Overview</h3>
                </div>

                <div class="clinify-saas-table-wrap">
                    <table class="clinify-saas-table">
                        <thead>
                            <tr>
                                <th>Clinic</th>
                                <th>Tenant ID</th>
                                <th>Plan</th>
                                <th>Status</th>
                                <th>Subscription</th>
                                <th>Valid Until</th>
                            </tr>
                        </thead>
                        <tbody id="saas-tenant-table">
                            <tr>
                                <td colspan="6"
                                    class="clinify-saas-empty">
                                    Loading tenant accounts...
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="clinify-saas-metrics">
                <div class="clinify-saas-card">
                    <div class="clinify-saas-card-label">
                        Expiring Within 30 Days
                    </div>
                    <div class="clinify-saas-card-value"
                         id="saas-expiring">—</div>
                </div>

                <div class="clinify-saas-card">
                    <div class="clinify-saas-card-label">
                        Provisioning Pending
                    </div>
                    <div class="clinify-saas-card-value"
                         id="saas-pending">—</div>
                </div>

                <div class="clinify-saas-card">
                    <div class="clinify-saas-card-label">
                        Provisioning Failed
                    </div>
                    <div class="clinify-saas-card-value"
                         id="saas-failed">—</div>
                </div>

                <div class="clinify-saas-card">
                    <div class="clinify-saas-card-label">
                        Platform
                    </div>
                    <div class="clinify-saas-card-value">
                        Clinify
                    </div>
                    <div class="clinify-saas-card-sub">
                        Control Plane
                    </div>
                </div>
            </div>
        </div>
    `);

    const root = $(page.main);

    root.on("click", "#saas-open-tenants", function () {
        frappe.set_route("List", "Clinify Tenant");
    });

    root.on("click", "#saas-new-tenant", function () {
        frappe.new_doc("Clinify Tenant");
    });

    root.on("click", "#saas-subscriptions", function () {
        frappe.set_route("List", "Clinify Subscription");
    });

    root.on("click", ".clinify-saas-link", function () {
        const name = $(this).attr("data-name");

        if (name) {
            frappe.set_route("Form", "Clinify Tenant", name);
        }
    });

    frappe.call({
        method: "clinify.clinify.page.saas_dashboard.saas_dashboard.get_dashboard",
    }).then((r) => {
        const data = r.message || {};
        const metrics = data.metrics || {};
        const tenants = data.recent_tenants || [];

        $("#saas-total-clinics").text(metrics.total_clinics ?? 0);
        $("#saas-active-clinics").text(metrics.active_clinics ?? 0);
        $("#saas-active-subscriptions").text(
            metrics.active_subscriptions ?? 0
        );
        $("#saas-trial-subscriptions").text(
            metrics.trial_subscriptions ?? 0
        );
        $("#saas-expiring").text(
            metrics.expiring_30_days ?? 0
        );
        $("#saas-pending").text(
            metrics.provisioning_pending ?? 0
        );
        $("#saas-failed").text(
            metrics.provisioning_failed ?? 0
        );

        const tbody = $("#saas-tenant-table");

        if (!tenants.length) {
            tbody.html(`
                <tr>
                    <td colspan="6"
                        class="clinify-saas-empty">
                        No tenant accounts found.
                    </td>
                </tr>
            `);
            return;
        }

        tbody.html(
            tenants.map((tenant) => `
                <tr>
                    <td>
                        <span
                            class="clinify-saas-link"
                            data-name="${frappe.utils.escape_html(
                                tenant.name
                            )}">
                            ${frappe.utils.escape_html(
                                tenant.tenant_name || "—"
                            )}
                        </span>
                    </td>

                    <td>
                        ${frappe.utils.escape_html(
                            tenant.tenant_id || "—"
                        )}
                    </td>

                    <td>
                        ${frappe.utils.escape_html(
                            tenant.plan || "—"
                        )}
                    </td>

                    <td>
                        <span class="clinify-saas-pill">
                            ${frappe.utils.escape_html(
                                tenant.clinic_status || "—"
                            )}
                        </span>
                    </td>

                    <td>
                        ${frappe.utils.escape_html(
                            tenant.subscription_status || "—"
                        )}
                    </td>

                    <td>
                        ${frappe.utils.escape_html(
                            tenant.subscription_end_date || "—"
                        )}
                    </td>
                </tr>
            `).join("")
        );
    });
};

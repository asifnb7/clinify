frappe.listview_settings["Clinify Tenant"] = {
    hide_name_column: true,

    /*
     * Only the seven approved business columns are displayed.
     * Provisioning remains a DocType field but is intentionally
     * not part of this registry view.
     */
    add_fields: [
        "tenant_id",
        "tenant_name",
        "site_name",
        "plan",
        "subscription_end_date",
        "days_remaining",
        "clinic_status",
    ],

    get_indicator(doc) {
        if (doc.clinic_status === "Active") {
            return [
                __("Active"),
                "green",
                "clinic_status,=,Active",
            ];
        }

        if (doc.clinic_status === "Suspended") {
            return [
                __("Suspended"),
                "orange",
                "clinic_status,=,Suspended",
            ];
        }

        if (doc.clinic_status === "Closed") {
            return [
                __("Closed"),
                "red",
                "clinic_status,=,Closed",
            ];
        }

        if (doc.clinic_status) {
            return [
                __(doc.clinic_status),
                "gray",
                `clinic_status,=,${doc.clinic_status}`,
            ];
        }

        return null;
    },

    onload(listview) {
        /*
         * ------------------------------------------------------------
         * Explicit seven-column registry.
         *
         * Frappe's row checkbox/action controls remain outside
         * .level-left. Therefore this grid contains ONLY the actual
         * tenant data columns.
         * ------------------------------------------------------------
         */
        const original_setup_columns =
            listview.setup_columns.bind(listview);

        listview.setup_columns = function () {
            original_setup_columns();

            const get_df = (fieldname) =>
                this.meta.fields.find(
                    (df) => df.fieldname === fieldname
                );

            const tenant_id = get_df("tenant_id");
            const tenant_name = get_df("tenant_name");
            const site_name = get_df("site_name");
            const plan = get_df("plan");
            const subscription_end_date =
                get_df("subscription_end_date");
            const days_remaining =
                get_df("days_remaining");
            const clinic_status =
                get_df("clinic_status");

            this.columns = [
                {
                    type: "Subject",
                    df: tenant_id,
                },
                {
                    type: "Field",
                    df: tenant_name,
                },
                {
                    type: "Field",
                    df: site_name,
                },
                {
                    type: "Field",
                    df: plan,
                },
                {
                    type: "Field",
                    df: subscription_end_date,
                },
                {
                    type: "Field",
                    df: days_remaining,
                },
                {
                    type: "Field",
                    df: clinic_status,
                },
            ];
        };

        listview.setup_columns();
        listview.render_header(true);


        /*
         * ------------------------------------------------------------
         * FINAL VISUAL LAYOUT
         * ------------------------------------------------------------
         */
        const style_id =
            "clinify-tenant-final-registry-layout";

        const old_style =
            document.getElementById(style_id);

        if (old_style) {
            old_style.remove();
        }

        const style = document.createElement("style");

        style.id = style_id;

        style.textContent = `
            /*
             * ========================================================
             * TENANT REGISTRY — MAIN GRID
             * ========================================================
             *
             * EXACTLY seven tenant data columns:
             *
             * Tenant ID
             * Clinic Name
             * Tenant Site
             * Plan
             * Valid Until
             * Days Left
             * Status
             *
             * The Frappe checkbox and row action controls are NOT
             * part of .level-left and therefore do not consume
             * these seven grid columns.
             */

            .list-row-head .level-left,
            .list-row .level-left {
                display: grid !important;

                grid-template-columns:
                    125px
                    minmax(170px, 1.25fr)
                    minmax(180px, 1.35fr)
                    125px
                    120px
                    90px
                    105px !important;

                align-items: center !important;

                width: 100% !important;
                min-width: 0 !important;

                flex: 1 1 auto !important;

                column-gap: 0 !important;
                row-gap: 0 !important;

                overflow: visible !important;
            }


            /*
             * Every tenant cell is one grid item.
             */

            .list-row-head .list-row-col,
            .list-row .level-left > .list-row-col {
                display: flex !important;

                box-sizing: border-box !important;

                flex: none !important;

                width: auto !important;
                min-width: 0 !important;
                max-width: none !important;

                margin: 0 !important;

                padding-left: 0 !important;
                padding-right: 14px !important;

                align-items: center !important;

                overflow: hidden !important;

                text-overflow: clip !important;
            }


            /*
             * ========================================================
             * HEADER
             * ========================================================
             */

            .list-row-head {
                min-height: 54px !important;
                height: auto !important;

                box-sizing: border-box !important;
            }

            .list-row-head .list-row-col {
                min-height: 44px !important;
                height: auto !important;

                font-weight: 600 !important;

                color: var(--text-color) !important;

                line-height: 1.25 !important;

                white-space: normal !important;

                word-break: normal !important;
                overflow-wrap: normal !important;

                overflow: visible !important;
                text-overflow: clip !important;
            }


            /*
             * ========================================================
             * DATA ROWS
             * ========================================================
             */

            .list-row-container {
                min-height: 62px !important;
                height: auto !important;
            }

            .list-row-container .list-row {
                min-height: 62px !important;
                height: auto !important;

                align-items: center !important;

                box-sizing: border-box !important;
            }

            .list-row .list-row-col {
                min-height: 50px !important;
                height: auto !important;

                line-height: 1.35 !important;

                white-space: normal !important;

                word-break: normal !important;
                overflow-wrap: anywhere !important;

                overflow: hidden !important;

                text-overflow: clip !important;
            }


            /*
             * ========================================================
             * FORCE WRAP INSIDE FRAPPE INTERNAL CONTENT
             * ========================================================
             */

            .list-row .list-row-col .ellipsis,
            .list-row .list-row-col a.ellipsis,
            .list-row .list-row-col span.ellipsis {
                display: block !important;

                box-sizing: border-box !important;

                width: 100% !important;
                max-width: 100% !important;

                margin: 0 !important;

                white-space: normal !important;

                overflow: visible !important;

                text-overflow: clip !important;

                word-break: normal !important;

                overflow-wrap: anywhere !important;

                line-height: 1.35 !important;
            }


            /*
             * ========================================================
             * TENANT ID
             * ========================================================
             */

            .list-row .level-left
                > .list-row-col:nth-child(1) {
                justify-content: flex-start !important;
                align-items: center !important;

                white-space: normal !important;

                overflow: hidden !important;

                word-break: normal !important;
                overflow-wrap: anywhere !important;
            }

            .list-row .level-left
                > .list-row-col:nth-child(1) > *,
            .list-row .level-left
                > .list-row-col:nth-child(1) a {
                display: block !important;

                width: 100% !important;
                max-width: 100% !important;

                margin: 0 !important;

                white-space: normal !important;

                overflow: visible !important;

                text-overflow: clip !important;

                word-break: normal !important;

                overflow-wrap: anywhere !important;

                line-height: 1.35 !important;

                font-weight: 600 !important;
            }


            /*
             * ========================================================
             * CLINIC NAME
             * ========================================================
             */

            .list-row .level-left
                > .list-row-col:nth-child(2) {
                justify-content: flex-start !important;
                align-items: center !important;

                white-space: normal !important;

                overflow: hidden !important;

                word-break: normal !important;
                overflow-wrap: anywhere !important;
            }

            .list-row .level-left
                > .list-row-col:nth-child(2) > *,
            .list-row .level-left
                > .list-row-col:nth-child(2) a,
            .list-row .level-left
                > .list-row-col:nth-child(2) span {
                display: block !important;

                width: 100% !important;
                max-width: 100% !important;

                margin: 0 !important;

                white-space: normal !important;

                overflow: visible !important;

                text-overflow: clip !important;

                word-break: normal !important;

                overflow-wrap: anywhere !important;

                line-height: 1.35 !important;

                font-weight: 600 !important;
            }


            /*
             * ========================================================
             * SITE / PLAN / VALID UNTIL
             * ========================================================
             */

            .list-row .level-left
                > .list-row-col:nth-child(3),
            .list-row .level-left
                > .list-row-col:nth-child(4),
            .list-row .level-left
                > .list-row-col:nth-child(5) {
                justify-content: flex-start !important;
                align-items: center !important;

                white-space: normal !important;

                overflow: hidden !important;

                text-overflow: clip !important;

                word-break: normal !important;
                overflow-wrap: anywhere !important;
            }


            /*
             * ========================================================
             * DAYS LEFT
             * ========================================================
             */

            .list-row-head .list-row-col:nth-child(6),
            .list-row .level-left
                > .list-row-col:nth-child(6) {
                justify-content: center !important;

                text-align: center !important;

                white-space: nowrap !important;

                word-break: normal !important;
                overflow-wrap: normal !important;

                overflow: visible !important;
            }


            /*
             * ========================================================
             * STATUS
             * ========================================================
             */

            .list-row-head .list-row-col:nth-child(7),
            .list-row .level-left
                > .list-row-col:nth-child(7) {
                justify-content: center !important;

                text-align: center !important;

                white-space: nowrap !important;

                word-break: normal !important;
                overflow-wrap: normal !important;

                overflow: visible !important;
            }

            .list-row .level-left
                > .list-row-col:nth-child(7)
                .indicator-pill {
                display: inline-flex !important;

                align-items: center !important;
                justify-content: center !important;

                flex: 0 0 auto !important;

                white-space: nowrap !important;

                max-width: 100% !important;
            }


            /*
             * ========================================================
             * LEFT FILTER SIDEBAR
             * ========================================================
             */

            .list-sidebar {
                box-sizing: border-box !important;

                width: 250px !important;
                min-width: 250px !important;
                max-width: 250px !important;

                padding: 0 14px 18px 14px !important;

                overflow: visible !important;
            }

            .list-sidebar .list-sidebar-section {
                box-sizing: border-box !important;

                width: 100% !important;

                margin: 0 0 22px 0 !important;

                padding: 0 !important;
            }

            .list-sidebar .section-head,
            .list-sidebar .section-title,
            .list-sidebar
                .list-sidebar-section > label {
                display: block !important;

                box-sizing: border-box !important;

                width: 100% !important;

                margin: 0 0 10px 0 !important;

                padding: 0 4px !important;

                text-align: left !important;

                line-height: 1.25 !important;
            }

            .list-sidebar .form-group,
            .list-sidebar .frappe-control,
            .list-sidebar .input-group,
            .list-sidebar .control-input,
            .list-sidebar .control-value,
            .list-sidebar .awesomplete,
            .list-sidebar .input-with-feedback {
                box-sizing: border-box !important;

                width: 100% !important;
                max-width: 100% !important;

                margin-left: 0 !important;
                margin-right: 0 !important;
            }

            .list-sidebar .form-control {
                box-sizing: border-box !important;

                width: 100% !important;

                min-width: 0 !important;

                height: 46px !important;
                min-height: 46px !important;

                margin: 0 !important;

                padding: 0 12px !important;

                border-radius: 10px !important;
            }

            .list-sidebar .form-group
                + .form-group,
            .list-sidebar .frappe-control
                + .frappe-control {
                margin-top: 12px !important;
            }

            .list-sidebar a,
            .list-sidebar .btn-link {
                display: block !important;

                box-sizing: border-box !important;

                width: 100% !important;

                margin: 0 !important;

                padding: 7px 4px !important;

                text-align: left !important;

                line-height: 1.35 !important;
            }

            .list-sidebar input[type="text"],
            .list-sidebar input.form-control {
                box-sizing: border-box !important;

                width: 100% !important;

                max-width: 100% !important;

                height: 46px !important;

                border-radius: 10px !important;
            }


            /*
             * ========================================================
             * INTERNAL NAME FIELD
             * ========================================================
             */

            .list-row-col[data-fieldname="name"] {
                display: none !important;
            }


            /*
             * ========================================================
             * RESPONSIVE
             * ========================================================
             */

            @media (max-width: 1250px) {
                .list-sidebar {
                    width: 225px !important;
                    min-width: 225px !important;
                    max-width: 225px !important;
                }

                .list-row-head .level-left,
                .list-row .level-left {
                    grid-template-columns:
                        115px
                        minmax(145px, 1.2fr)
                        minmax(155px, 1.3fr)
                        115px
                        110px
                        80px
                        100px !important;
                }
            }
        `;

        document.head.appendChild(style);
    },

    formatters: {
        days_remaining(value, df, doc) {
            const end_date = doc.subscription_end_date;

            if (!end_date) {
                return "";
            }

            const today = frappe.datetime.str_to_obj(
                frappe.datetime.get_today()
            );

            const expiry = frappe.datetime.str_to_obj(
                end_date
            );

            const milliseconds_per_day =
                24 * 60 * 60 * 1000;

            return Math.ceil(
                (expiry - today) /
                milliseconds_per_day
            );
        },
    },
};

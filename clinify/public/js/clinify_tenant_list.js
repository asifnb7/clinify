frappe.listview_settings["Clinify Tenant"] = {
    hide_name_column: true,
    total_fields: 8,

    add_fields: [
        "subscription_end_date",
        "days_remaining",
    ],

    get_indicator(doc) {
        if (doc.clinic_status === "Active") {
            return [__("Active"), "green", "clinic_status,=,Active"];
        }

        if (doc.clinic_status === "Suspended") {
            return [__("Suspended"), "orange", "clinic_status,=,Suspended"];
        }

        if (doc.clinic_status === "Closed") {
            return [__("Closed"), "red", "clinic_status,=,Closed"];
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
        const original_setup_columns = listview.setup_columns.bind(listview);

        listview.setup_columns = function () {
            original_setup_columns();

            const get_df = (fieldname) =>
                this.meta.fields.find(
                    (df) => df.fieldname === fieldname
                );

            /*
             * Explicit Clinify Tenant columns.
             *
             * We deliberately construct these from this.meta.fields
             * instead of relying on Frappe's already-sliced columns.
             *
             * Final order:
             * 1. Tenant ID
             * 2. Clinic
             * 3. Site
             * 4. Plan
             * 5. Subscription Valid Until
             * 6. Days Remaining
             * 7. Status
             * 8. Provisioning
             */

            const subject = {
                type: "Subject",
                df: get_df("tenant_id"),
            };

            const fieldnames = [
                "tenant_name",
                "site_name",
                "plan",
                "subscription_end_date",
                "days_remaining",
                "clinic_status",
                "provisioning_status",
            ];

            const fields = fieldnames
                .map((fieldname) => get_df(fieldname))
                .filter(Boolean)
                .map((df) => ({
                    type: "Field",
                    df,
                }));

            this.columns = [
                subject,
                ...fields,
            ];
        };

        listview.setup_columns();
        listview.render_header(true);

        const style_id = "clinify-tenant-list-readable";

        if (!document.getElementById(style_id)) {
            const style = document.createElement("style");

            style.id = style_id;

            style.textContent = `
                .list-row-container {
                    min-height: 52px;
                }

                .list-row {
                    align-items: flex-start;
                }

                .list-row .level-left {
                    display: flex !important;
                    flex: 1 1 auto !important;
                    min-width: 0 !important;
                    width: 100% !important;
                    overflow: visible !important;
                    white-space: normal !important;
                }

                /*
                 * Frappe sets .list-row, .list-row-head to height: 40px.
                 * Allow Clinify rows to grow when cell content wraps.
                 */
                .list-row-container .list-row {
                    height: auto !important;
                    min-height: 52px !important;
                }

                .list-row .list-row-col {
                    box-sizing: border-box !important;
                    min-width: 0 !important;
                    height: auto !important;
                    min-height: 42px !important;
                    padding-right: 10px !important;

                    white-space: normal !important;
                    overflow: visible !important;
                    text-overflow: clip !important;

                    word-break: break-word !important;
                    overflow-wrap: anywhere !important;

                    line-height: 1.35 !important;
                    flex-shrink: 0 !important;
                }

                /*
                 * Clinify Tenant columns.
                 *
                 * Final order:
                 * 1. Tenant ID
                 * 2. Clinic
                 * 3. Site
                 * 4. Plan
                 * 5. Subscription Valid Until
                 * 6. Days Remaining
                 * 7. Status
                 * 8. Provisioning
                 *
                 * The same widths are applied to both header and data
                 * rows. Explicit flex-basis prevents Frappe's default
                 * flex: 1 1 0% rules from redistributing the columns.
                 */

                .list-row-head .list-row-col:nth-child(1),
                .list-row .level-left > .list-row-col:nth-child(1) {
                    flex: 0 0 13% !important;
                    width: 13% !important;
                }

                .list-row-head .list-row-col:nth-child(2),
                .list-row .level-left > .list-row-col:nth-child(2) {
                    flex: 0 0 18% !important;
                    width: 18% !important;
                }

                .list-row-head .list-row-col:nth-child(3),
                .list-row .level-left > .list-row-col:nth-child(3) {
                    flex: 0 0 14% !important;
                    width: 14% !important;
                }

                .list-row-head .list-row-col:nth-child(4),
                .list-row .level-left > .list-row-col:nth-child(4) {
                    flex: 0 0 11% !important;
                    width: 11% !important;
                }

                .list-row-head .list-row-col:nth-child(5),
                .list-row .level-left > .list-row-col:nth-child(5) {
                    flex: 0 0 15% !important;
                    width: 15% !important;
                }

                .list-row-head .list-row-col:nth-child(6),
                .list-row .level-left > .list-row-col:nth-child(6) {
                    flex: 0 0 10% !important;
                    width: 10% !important;
                }

                .list-row-head .list-row-col:nth-child(7),
                .list-row .level-left > .list-row-col:nth-child(7) {
                    flex: 0 0 10% !important;
                    width: 10% !important;
                }

                .list-row-head .list-row-col:nth-child(8),
                .list-row .level-left > .list-row-col:nth-child(8) {
                    flex: 0 0 9% !important;
                    width: 9% !important;
                }

                /*
                 * Disable Frappe ellipsis behavior so complete values
                 * can wrap onto multiple lines.
                 */

                .list-row .list-row-col.ellipsis,
                .list-row .list-row-col .ellipsis,
                .list-row .list-row-col a.ellipsis,
                .list-row .list-row-col span.ellipsis,
                .list-row .list-row-col .indicator-pill,
                .list-row .list-row-col .indicator-pill .ellipsis {
                    white-space: normal !important;
                    overflow: visible !important;
                    text-overflow: clip !important;

                    word-break: break-word !important;
                    overflow-wrap: anywhere !important;

                    max-width: 100% !important;
                }

                /*
                 * Keep headers compact and readable.
                 */

                .list-row-head .list-row-col,
                .list-row .level-left > .list-row-col {
                    box-sizing: border-box !important;
                    min-width: 0 !important;
                    padding-left: 0 !important;
                    padding-right: 8px !important;
                }

                .list-row-head .list-row-col {
                    min-height: 0 !important;
                    height: auto !important;

                    white-space: normal !important;
                    overflow: visible !important;
                    text-overflow: clip !important;

                    word-break: normal !important;
                    overflow-wrap: normal !important;

                    line-height: 1.25 !important;
                }

                /*
                 * Keep header words intact. Long headings may wrap
                 * between words, but should never split inside a word.
                 */
                .list-row-head .list-row-col:nth-child(1),
                .list-row-head .list-row-col:nth-child(2),
                .list-row-head .list-row-col:nth-child(3),
                .list-row-head .list-row-col:nth-child(4),
                .list-row-head .list-row-col:nth-child(6),
                .list-row-head .list-row-col:nth-child(7),
                .list-row-head .list-row-col:nth-child(8) {
                    white-space: nowrap !important;
                }

                .list-row-head .list-row-col:nth-child(5) {
                    white-space: normal !important;
                }

                /*
                 * Keep Tenant ID and Clinic visually prominent so the
                 * primary tenant information is easy to scan.
                 */
                .list-row .level-left > .list-row-col:nth-child(1),
                .list-row .level-left > .list-row-col:nth-child(1) *,
                .list-row .level-left > .list-row-col:nth-child(2),
                .list-row .level-left > .list-row-col:nth-child(2) * {
                    font-weight: 600 !important;
                }

                /*
                 * Keep the Days Remaining heading and values readable
                 * without splitting individual words.
                 */
                .list-row-head .list-row-col:nth-child(6),
                .list-row .level-left > .list-row-col:nth-child(6) {
                    word-break: normal !important;
                    overflow-wrap: normal !important;
                }

                /*
                 * Status and Provisioning indicators stay intact rather
                 * than splitting their labels across multiple lines.
                 */
                .list-row .list-row-col:nth-child(7),
                .list-row .list-row-col:nth-child(8),
                .list-row .list-row-col:nth-child(7) *,
                .list-row .list-row-col:nth-child(8) * {
                    word-break: normal !important;
                    overflow-wrap: normal !important;
                }

                .list-row .list-row-col:nth-child(7) .indicator-pill,
                .list-row .list-row-col:nth-child(8) .indicator-pill {
                    display: inline-flex !important;
                    align-items: center !important;
                    white-space: nowrap !important;
                    max-width: 100% !important;
                }

                /*
                 * Final Clinify Tenant presentation layer.
                 *
                 * This matches the approved Tenant List design:
                 * - bold Tenant ID and Clinic
                 * - strong, aligned headers
                 * - separated Days Remaining / Status / Provisioning
                 * - centered operational indicators
                 * - controlled wrapping for long business values
                 */

                .list-row-head .list-row-col {
                    display: flex !important;
                    align-items: center !important;
                    min-width: 0 !important;
                    box-sizing: border-box !important;
                    font-weight: 600 !important;
                    color: var(--text-color) !important;
                    padding-left: 0 !important;
                    padding-right: 10px !important;
                }

                .list-row .level-left > .list-row-col {
                    display: flex !important;
                    align-items: center !important;
                    min-width: 0 !important;
                    box-sizing: border-box !important;
                    padding-left: 0 !important;
                    padding-right: 10px !important;
                }

                /*
                 * Primary tenant identity.
                 */
                .list-row .level-left > .list-row-col:nth-child(1),
                .list-row .level-left > .list-row-col:nth-child(1) *,
                .list-row .level-left > .list-row-col:nth-child(2),
                .list-row .level-left > .list-row-col:nth-child(2) * {
                    font-weight: 600 !important;
                }

                /*
                 * Keep business text readable and naturally wrapped.
                 */
                .list-row .level-left > .list-row-col:nth-child(2),
                .list-row .level-left > .list-row-col:nth-child(3),
                .list-row .level-left > .list-row-col:nth-child(4),
                .list-row .level-left > .list-row-col:nth-child(5) {
                    white-space: normal !important;
                    word-break: normal !important;
                    overflow-wrap: anywhere !important;
                    overflow: visible !important;
                    text-overflow: clip !important;
                    line-height: 1.4 !important;
                }

                /*
                 * Days Remaining is isolated from Status and centered.
                 */
                .list-row-head .list-row-col:nth-child(6),
                .list-row .level-left > .list-row-col:nth-child(6) {
                    justify-content: center !important;
                    text-align: center !important;
                    white-space: nowrap !important;
                    word-break: normal !important;
                    overflow-wrap: normal !important;
                    overflow: visible !important;
                }

                /*
                 * Status and Provisioning each get their own centered
                 * visual area so their pills can never collide.
                 */
                .list-row-head .list-row-col:nth-child(7),
                .list-row .level-left > .list-row-col:nth-child(7),
                .list-row-head .list-row-col:nth-child(8),
                .list-row .level-left > .list-row-col:nth-child(8) {
                    justify-content: center !important;
                    text-align: center !important;
                    white-space: nowrap !important;
                    word-break: normal !important;
                    overflow-wrap: normal !important;
                    overflow: visible !important;
                }

                .list-row .level-left > .list-row-col:nth-child(7) .indicator-pill,
                .list-row .level-left > .list-row-col:nth-child(8) .indicator-pill {
                    flex: 0 0 auto !important;
                    display: inline-flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                    white-space: nowrap !important;
                    word-break: normal !important;
                    overflow-wrap: normal !important;
                    max-width: 100% !important;
                }

                /*
                 * Keep header labels intact and aligned with their cells.
                 */
                .list-row-head .list-row-col:nth-child(1),
                .list-row-head .list-row-col:nth-child(2),
                .list-row-head .list-row-col:nth-child(3),
                .list-row-head .list-row-col:nth-child(4),
                .list-row-head .list-row-col:nth-child(6),
                .list-row-head .list-row-col:nth-child(7),
                .list-row-head .list-row-col:nth-child(8) {
                    white-space: nowrap !important;
                    word-break: normal !important;
                    overflow-wrap: normal !important;
                }

                .list-row-head .list-row-col:nth-child(5) {
                    white-space: normal !important;
                    word-break: normal !important;
                    overflow-wrap: normal !important;
                    line-height: 1.2 !important;
                }

                /*
                 * Give the header a little more breathing room, matching
                 * the approved design's visual hierarchy.
                 */
                .list-row-head {
                    min-height: 52px !important;
                    height: auto !important;
                    align-items: center !important;
                }

                .list-row-head .list-row-col {
                    min-height: 44px !important;
                }

                /*
                 * Internal Frappe document name remains hidden.
                 */
                .list-row-col[data-fieldname="name"] {
                    display: none !important;
                }
            `;

            document.head.appendChild(style);
        }
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

            const expiry = frappe.datetime.str_to_obj(end_date);

            const milliseconds_per_day = 24 * 60 * 60 * 1000;

            return Math.ceil(
                (expiry - today) / milliseconds_per_day
            );
        },
    },
};

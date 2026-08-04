frappe.pages["reception-dashboard"].on_page_load = function (wrapper) {

    let page = frappe.ui.make_app_page({
        parent: wrapper,
        single_column: true
    });

    page.set_title(__("Reception Dashboard"));

    const quickActions = [
        {
            label: "Book Appointment",
            icon: "fa-calendar",
            theme: "appointment",
            buttonClass: "quick-action-book-appointment-btn"
        },
        {
            label: "Patient",
            icon: "fa-user",
            theme: "patient",
            buttonClass: "quick-action-patient-btn"
        },
        {
            label: "Yesterday",
            icon: "fa-history",
            theme: "yesterday",
            buttonClass: "quick-action-yesterday-btn"
        },
        {
            label: "Tomorrow",
            icon: "fa-calendar",
            theme: "tomorrow",
            buttonClass: "quick-action-tomorrow-btn"
        },
        {
            label: "Doctor",
            icon: "fa-user-md",
            theme: "doctor",
            buttonClass: "quick-action-doctor-btn"
        },
        {
            label: "Accounts",
            icon: "fa-money",
            theme: "accounts",
            buttonClass: "quick-action-accounts-btn"
        }
    ];

    $(page.body).html(`

<div class="container-fluid reception-dashboard">

<style>

.reception-dashboard{
    margin-top:-0.75rem;
}

.reception-dashboard .quick-actions-container{
    display:flex;
    flex-wrap:nowrap;
    gap:1.25rem;
}

.reception-dashboard .quick-action-item{
    flex:1 1 0;
    min-width:0;
}

.reception-dashboard .quick-action-card{

    align-items:center;
    background:#fff;
    border:1px solid #edf0f3;
    box-shadow:0 2px 8px rgba(16,24,40,.06);

    color:inherit;
    cursor:pointer;

    display:flex;
    justify-content:center;

    min-height:112px;

    padding:.5rem 1rem;

    text-align:center;

    transition:
        background-color .2s,
        border-color .2s,
        box-shadow .2s,
        transform .2s;

    width:100%;
}

.reception-dashboard .quick-action-card:hover{

    background:#fcfdff;

    border-color:rgba(13,110,253,.25);

    box-shadow:0 .75rem 1.5rem rgba(16,24,40,.10);

    transform:translateY(-3px);
}

.reception-dashboard .quick-action-icon-circle{

    display:flex;
    justify-content:center;
    align-items:center;

    width:72px;
    height:72px;

    border-radius:50%;

    margin-bottom:.25rem;
}

.reception-dashboard .quick-action-icon{

    font-size:36px;

}

.reception-dashboard .quick-action-label{

    font-size:.9rem;
    font-weight:700;

}

.quick-action-card--appointment .quick-action-icon-circle{

    background:#fff3cd;

}

.quick-action-card--appointment .quick-action-icon{

    color:#856404;

}

.quick-action-card--patient .quick-action-icon-circle,
.quick-action-card--yesterday .quick-action-icon-circle,
.quick-action-card--tomorrow .quick-action-icon-circle{

    background:rgba(13,110,253,.1);

}

.quick-action-card--patient .quick-action-icon,
.quick-action-card--yesterday .quick-action-icon,
.quick-action-card--tomorrow .quick-action-icon{

    color:#0d6efd;

}
.quick-action-card--doctor .quick-action-icon-circle{

    background:rgba(25,135,84,.10);

}

.quick-action-card--doctor .quick-action-icon{

    color:#198754;

}

.quick-action-card--accounts .quick-action-icon-circle{

    background:rgba(253,126,20,.12);

}

.quick-action-card--accounts .quick-action-icon{

    color:#fd7e14;

}

@media (max-width:991.98px){

    .reception-dashboard .quick-actions-container{

        flex-wrap:wrap;

    }

    .reception-dashboard .quick-action-item{

        flex:1 1 30%;
        min-width:150px;

    }

}

.reception-dashboard .reception-dashboard-header{

    background:#007be0;
    color:#fff;

    display:flex;
    align-items:center;

    margin-bottom:1.5rem;

    min-height:84px;

    padding:1.5rem;

}

.reception-dashboard .reception-dashboard-header h3{

    color:#fff;
    margin:0;

}

.reception-dashboard .reception-summary-card .card-body{

    padding:.875rem 1.25rem;

}

.reception-dashboard .summary-card-content{

    gap:1.25rem;

}

.reception-dashboard .summary-icon-circle{

    display:flex;
    justify-content:center;
    align-items:center;

    width:76px;
    height:76px;

    flex:0 0 76px;

    border-radius:50%;

    background:#f8f9fa;

}

.reception-dashboard .summary-icon{

    font-size:2.75rem;

}

.reception-dashboard .summary-metric{

    font-size:36px;

}

</style>

<div class="reception-dashboard-header">

    <h3 class="fw-bold">

        Reception Dashboard

    </h3>

</div>

<div class="row mb-3">

    <div class="col-md-12 text-md-end">

        <span
            id="dashboard-timestamp"
            class="d-inline-flex align-items-center rounded-3"
            style="background:#fff3cd;padding:10px 18px;font-weight:700;">

            <span class="fw-bold text-primary me-2">📅</span>

            <span
                class="fw-bold text-primary me-2"
                id="dashboard-day">
                Wednesday
            </span>

            <span class="fw-bold text-dark me-2">|</span>

            <span
                class="fw-bold text-dark me-2"
                id="dashboard-date">
                13 Jul 2026
            </span>

            <span class="fw-bold text-dark me-2">|</span>

            <span
                class="fw-bold text-dark"
                id="dashboard-time">
                10:42 AM
            </span>

            <span class="fw-bold text-primary ms-2">🕒</span>

        </span>

    </div>

</div>

<div class="row mb-3">

    <div class="col-md-3">

        <div class="card mb-3 shadow-sm rounded-3 h-100 reception-summary-card">

            <div class="card-body d-flex align-items-center summary-card-content">

                <div class="summary-icon-circle">

                    <span class="summary-icon">👥</span>

                </div>

                <div>

                    <div class="text-uppercase fw-bold mb-2">

                        Today's Patients

                    </div>

                    <div
                        id="summary-today-count"
                        class="fw-bold summary-metric">

                        0

                    </div>

                </div>

            </div>

        </div>

    </div>
    <div class="col-md-3">

        <div class="card mb-3 shadow-sm rounded-3 h-100 reception-summary-card">

            <div class="card-body d-flex align-items-center summary-card-content">

                <div class="summary-icon-circle">
                    <span class="summary-icon">⏳</span>
                </div>

                <div>

                    <div class="text-uppercase fw-bold mb-2">
                        Waiting
                    </div>

                    <div
                        id="summary-waiting-count"
                        class="fw-bold summary-metric">

                        0

                    </div>

                </div>

            </div>

        </div>

    </div>

    <div class="col-md-3">

        <div class="card mb-3 shadow-sm rounded-3 h-100 reception-summary-card">

            <div class="card-body d-flex align-items-center summary-card-content">

                <div class="summary-icon-circle">
                    <span class="summary-icon">✅</span>
                </div>

                <div>

                    <div class="text-uppercase fw-bold mb-2">
                        Checked In
                    </div>

                    <div
                        id="summary-checked-in-count"
                        class="fw-bold summary-metric">

                        0

                    </div>

                </div>

            </div>

        </div>

    </div>

    <div class="col-md-3">

        <div class="card mb-3 shadow-sm rounded-3 h-100 reception-summary-card">

            <div class="card-body d-flex align-items-center summary-card-content">

                <div class="summary-icon-circle">
                    <span class="summary-icon">💚</span>
                </div>

                <div>

                    <div class="text-uppercase fw-bold mb-2">
                        Ready for Billing
                    </div>

                    <div
                        id="summary-ready-count"
                        class="fw-bold summary-metric">

                        0

                    </div>

                </div>

            </div>

        </div>

    </div>

</div>

<div class="row mb-3">

    <div class="col-md-12">

        <div class="card mb-3 shadow-sm">

            <div class="card-body">

                <div class="quick-actions-container">

                    ${quickActions.map(function(action){

                        return `

                        <div class="quick-action-item">

                            <button
                                type="button"
                                class="quick-action-card quick-action-card--${action.theme} shadow-sm rounded-3 ${action.buttonClass}">

                                <div>

                                    <div class="quick-action-icon-circle">

                                        <i class="fa ${action.icon} quick-action-icon"></i>

                                    </div>

                                    <div class="quick-action-label">

                                        ${action.label}

                                    </div>

                                </div>

                            </button>

                        </div>

                        `;

                    }).join("")}

                </div>

            </div>

        </div>

    </div>

</div>

<div class="row">

    <div class="col-md-6">

        <div class="card mb-3">

            <div class="card-body">

                <h4>Today's Appointments</h4>

                <div id="appointments-list">

                    Loading...

                </div>

            </div>

        </div>

    </div>
    <div class="col-md-6">

        <div class="card mb-3">

            <div class="card-body">

                <h4>
                    Billing Queue
                    <span
                        id="billing-count"
                        class="badge bg-primary ms-2">
                        0
                    </span>
                </h4>

                <div id="billing-list">
                    Loading...
                </div>

            </div>

        </div>

    </div>

</div>

<div class="row">

    <div class="col-md-12">

        <div class="card mb-3">

            <div class="card-body">

                <h4>Ready for Billing</h4>

                <div id="ready-for-billing-list">

                    <div class="table-responsive">

                        <table class="table table-borderless table-sm table-hover align-middle mb-0">

                            <thead class="text-uppercase">

                                <tr>

                                    <th class="fw-bold">👤 Patient</th>

                                    <th class="fw-bold">🩺 Doctor</th>

                                    <th class="fw-bold">🕒 Time</th>

                                    <th class="fw-bold">Status</th>

                                    <th class="fw-bold">Action</th>

                                </tr>

                            </thead>

                            <tbody>

                                <tr>

                                    <td colspan="5">

                                        Loading...

                                    </td>

                                </tr>

                            </tbody>

                        </table>

                    </div>

                </div>

            </div>

        </div>

    </div>

</div>

</div>

`);

function updateDashboardTime() {

    const now = new Date();

    const day = now.toLocaleDateString(
        "en-US",
        { weekday: "long" }
    );

    const date = now.toLocaleDateString(
        "en-GB",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );

    const time = now.toLocaleTimeString(
        "en-US",
        {
            hour: "2-digit",
            minute: "2-digit",
            hour12: true
        }
    );

    $("#dashboard-timestamp").html(

        '<span class="fw-bold text-primary">📅</span> ' +

        '<span class="fw-bold text-primary">' +

        day +

        '</span> ' +

        '<span class="mx-3 fw-bold text-dark">|</span>' +

        '<span class="fw-bold text-dark">' +

        date +

        '</span> ' +

        '<span class="mx-3 fw-bold text-dark">|</span>' +

        '<span class="fw-bold text-dark">' +

        time +

        '</span> ' +

        '<span class="fw-bold text-primary">🕒</span>'

    );

}

updateDashboardTime();

setInterval(updateDashboardTime, 1000);

function setSummaryCounts(
    todayCount,
    waitingCount,
    checkedInCount,
    readyCount
) {

    if (todayCount !== undefined) {
        $("#summary-today-count").text(todayCount);
    }

    if (waitingCount !== undefined) {
        $("#summary-waiting-count").text(waitingCount);
    }

    if (checkedInCount !== undefined) {
        $("#summary-checked-in-count").text(checkedInCount);
    }

    if (readyCount !== undefined) {
        $("#summary-ready-count").text(readyCount);
    }

}

function loadDashboardSummary() {

    frappe.call({

        method: "clinify.reception.get_dashboard_summary",

        callback: function (r) {

            if (!r.message) {
                return;
            }

            setSummaryCounts(
                r.message.today,
                r.message.waiting,
                r.message.checked_in,
                r.message.ready_for_billing
            );

        }

    });

}

loadDashboardSummary();
frappe.call({

    method: "clinify.reception.get_todays_appointments",

    callback: function (r) {

        let html = "";

        if (!r.message || r.message.length === 0) {

            html = "<p>No appointments today.</p>";

        } else {

            r.message.forEach(function (appt) {

                const status =
                    appt.custom_reception_status || "Waiting";

                html += `

<div class="border-bottom py-3">

    <div class="d-flex justify-content-between align-items-start gap-3">

        <div class="flex-grow-1">

            <div class="mb-1">

                <strong>${appt.patient_name}</strong>

            </div>

            <div class="text-secondary mb-2">

                🩺 Dr. ${appt.doctor_name || "-"}

            </div>

            <div class="fw-bold mb-2">

                🕒 ${appt.appointment_time}

            </div>

            <span
                class="badge"
                style="
                    background:${appt.journey_color};
                    color:white;
                    font-size:.95rem;
                    padding:.65em .9em;
                ">

                ${appt.journey_label}

            </span>

        </div>

        <div class="text-end">

            ${
                status === "Checked In"

                ?

                `
                <button
                    class="btn btn-sm btn-success"
                    disabled>

                    ✓ Checked In

                </button>
                `

                :

                `
                <button
                    class="btn btn-sm btn-primary check-in-btn"
                    data-appointment="${appt.name}">

                    Check In

                </button>
                `
            }

        </div>

    </div>

</div>

`;

            });

        }

        $("#appointments-list").html(html);

    }

});

frappe.call({

    method: "clinify.reception.get_billing_queue",

    callback: function (r) {

        let html = "";

        $("#billing-count").text(

            (r.message || []).length

        );

        if (!r.message || r.message.length === 0) {

            html = "<p>No pending bills.</p>";

        } else {

            r.message.forEach(function (bill, index) {

                let badgeColor = "#0d6efd";

                if (bill.workflow_stage === "Draft") {

                    badgeColor = "#ffc107";

                }

                else if (
                    bill.workflow_stage === "Pending Payment"
                ) {

                    badgeColor = "#fd7e14";

                }

                else if (
                    bill.workflow_stage === "Completed"
                ) {

                    badgeColor = "#198754";

                }

                html += `
<div class="border rounded p-3 mb-3">

    <div class="d-flex justify-content-between">

        <div>

            <div class="fw-bold fs-6">

                ${index + 1}.
                &nbsp;&nbsp;
                👤 ${bill.patient}

            </div>

            <div class="fw-bold mt-1">

                ${bill.customer_name}

            </div>

            <div class="text-secondary">

                🩺 Dr. ${bill.doctor_name || "-"}

            </div>

            <div class="mt-2">

                💰 Total : ₹${bill.grand_total}

            </div>

            <div class="fw-bold text-danger mt-1">

                💵 Due : ₹${bill.outstanding_amount}

            </div>

        </div>

        <div class="text-end">

            <span
                class="badge"
                style="background:${badgeColor};padding:8px 12px;">

                ${bill.workflow_stage}

            </span>

            <br><br>

            <button
                class="btn btn-sm btn-primary view-invoice-btn"
                data-invoice="${bill.name}">

                View Invoice

            </button>

        </div>

    </div>

</div>

`;

            });

        }

        $("#billing-list").html(html);

    }

});

frappe.call({

    method: "clinify.reception.get_ready_for_billing",

    callback: function (r) {

        let html = "";

        if (!r.message || r.message.length === 0) {

            html = "<p>No appointments ready for billing.</p>";

        } else {

            html += `

<div class="table-responsive">

<table class="table table-borderless table-sm table-hover align-middle mb-0">

<tbody>

`;

            r.message.forEach(function (appt) {

                html += `

<tr>

    <td class="align-middle py-3 fs-6">

        <strong>${appt.patient_name}</strong>

    </td>

    <td class="align-middle py-3 text-secondary fs-6">

        Dr. ${appt.doctor_name || "-"}

    </td>

    <td class="align-middle py-3 fw-bold fs-6">

        ${appt.appointment_time}

    </td>

    <td class="align-middle py-3">

        <span
            class="badge badge-success rounded-pill"
            style="font-size:.92rem;padding:.55em .85em;">

            Ready

        </span>

    </td>

    <td class="align-middle py-3">

        <button
            class="btn btn-sm btn-outline-primary create-invoice-btn"
            data-appointment="${appt.name}"
            style="min-width:120px;">

            🧾 Create Invoice

        </button>

    </td>

</tr>

`;

            });

            html += `

</tbody>

</table>

</div>

`;

        }

        $("#ready-for-billing-list").html(html);

    }

});

};
function refreshReceptionDashboard() {

    window.location.reload();

}

$(document).on("click", ".check-in-btn", function () {

    const appointment = $(this).data("appointment");

    frappe.call({

        method: "clinify.reception.check_in_patient",

        args: {
            appointment: appointment
        },

        callback: function () {

            refreshReceptionDashboard();

        }

    });

});

$(document).on("click", ".quick-action-book-appointment-btn", function () {

    frappe.new_doc("Patient Appointment");

});

$(document).on("click", ".quick-action-patient-btn", function () {

    frappe.set_route("reception-patient-workspace");

});

$(document).on("click", ".quick-action-yesterday-btn", function () {

    frappe.route_options = {
        appointment_date: frappe.datetime.add_days(
            frappe.datetime.get_today(),
            -1
        )
    };

    frappe.set_route(
        "List",
        "Patient Appointment"
    );

});

$(document).on("click", ".quick-action-tomorrow-btn", function () {

    frappe.route_options = {
        appointment_date: frappe.datetime.add_days(
            frappe.datetime.get_today(),
            1
        )
    };

    frappe.set_route(
        "List",
        "Patient Appointment"
    );

});

$(document).on("click", ".quick-action-doctor-btn", function () {

    frappe.set_route(
        "List",
        "Healthcare Practitioner"
    );

});

$(document).on("click", ".quick-action-accounts-btn", function () {

    frappe.set_route(
        "Workspaces",
        "Accounting"
    );

});

$(document).on("click", ".patient-btn", function () {

    frappe.set_route(
        "Form",
        "Patient",
        $(this).data("patient")
    );

});

$(document).on("click", ".view-invoice-btn", function () {

    frappe.set_route(
        "Form",
        "Sales Invoice",
        $(this).data("invoice")
    );

});

$(document).on("click", ".create-invoice-btn", function () {

    const appointment = $(this).data("appointment");

    const button = $(this);

    button
        .prop("disabled", true)
        .text("Creating...");

    frappe.call({

        method: "clinify.reception.create_invoice_from_ready_appointment",

        args: {
            appointment: appointment
        },

        callback: function (r) {

            if (r.message && r.message.success) {

                frappe.show_alert({

                    message: __("Invoice Created Successfully"),

                    indicator: "green"

                });

                frappe.set_route(

                    "Form",

                    "Sales Invoice",

                    r.message.invoice

                );

            } else {

                button
                    .prop("disabled", false)
                    .text("🧾 Create Invoice");

                frappe.msgprint(

                    __("Failed to create invoice.")

                );

            }

        },

        error: function () {

            button
                .prop("disabled", false)
                .text("🧾 Create Invoice");

        }

    });

});

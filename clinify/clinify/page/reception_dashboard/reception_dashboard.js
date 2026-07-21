frappe.pages["reception-dashboard"].on_page_load = function(wrapper) {



    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Reception Dashboard",
        single_column: true
    });

    $(page.body).html(`
        <div class="container-fluid">

            <div class="row mb-3">

                <div class="col-md-12 text-md-end">
                    <span id="dashboard-timestamp" class="d-inline-flex align-items-center rounded-3" style="background:#fff3cd;padding:10px 18px;font-weight:700;">
                        <span class="fw-bold text-primary me-2">📅</span>
                        <span class="fw-bold text-primary me-2" id="dashboard-day">Wednesday</span>
                        <span class="fw-bold text-dark me-2">|</span>
                        <span class="fw-bold text-dark me-2" id="dashboard-date">13 Jul 2026</span>
                        <span class="fw-bold text-dark me-2">|</span>
                        <span class="fw-bold text-dark" id="dashboard-time">10:42 AM</span>
                        <span class="fw-bold text-primary ms-2">🕒</span>
                    </span>
                </div>

            </div>

            <div class="row mb-3">

                <div class="col-md-3">
                    <div class="card mb-3 shadow-sm rounded-3 h-100">
                        <div class="card-body d-flex align-items-center gap-3">
                            <div class="rounded-circle bg-light d-flex align-items-center justify-content-center" style="width:60px;height:60px;">
                                <span class="fs-2">👥</span>
                            </div>
                            <div>
                                <div class="text-uppercase fw-bold mb-2">Today's Patients</div>
                                <div id="summary-today-count" class="fw-bold" style="font-size:36px;">0</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="card mb-3 shadow-sm rounded-3 h-100">
                        <div class="card-body d-flex align-items-center gap-3">
                            <div class="rounded-circle bg-light d-flex align-items-center justify-content-center" style="width:60px;height:60px;">
                                <span class="fs-2">⏳</span>
                            </div>
                            <div>
                                <div class="text-uppercase fw-bold mb-2">Waiting</div>
                                <div id="summary-waiting-count" class="fw-bold" style="font-size:36px;">0</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="card mb-3 shadow-sm rounded-3 h-100">
                        <div class="card-body d-flex align-items-center gap-3">
                            <div class="rounded-circle bg-light d-flex align-items-center justify-content-center" style="width:60px;height:60px;">
                                <span class="fs-2">✅</span>
                            </div>
                            <div>
                                <div class="text-uppercase fw-bold mb-2">Checked In</div>
                                <div id="summary-checked-in-count" class="fw-bold" style="font-size:36px;">0</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="card mb-3 shadow-sm rounded-3 h-100">
                        <div class="card-body d-flex align-items-center gap-3">
                            <div class="rounded-circle bg-light d-flex align-items-center justify-content-center" style="width:60px;height:60px;">
                                <span class="fs-2">💚</span>
                            </div>
                            <div>
                                <div class="text-uppercase fw-bold mb-2">Ready for Billing</div>
                                <div id="summary-ready-count" class="fw-bold" style="font-size:36px;">0</div>
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

                            <h4>Billing Queue</h4>

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
                                                <td colspan="5">Loading...</td>
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
        const day = now.toLocaleDateString("en-US", { weekday: "long" });
        const date = now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
        const time = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true });

        $("#dashboard-timestamp").html(
            '<span class="fw-bold text-primary">📅</span> ' +
            '<span class="fw-bold text-primary">' + day + '</span> ' +
            '<span class="fw-bold text-dark">|</span> ' +
            '<span class="fw-bold text-dark">' + date + '</span> ' +
            '<span class="fw-bold text-dark">|</span> ' +
            '<span class="fw-bold text-dark">' + time + '</span> ' +
            '<span class="fw-bold text-primary">🕒</span>'
        );
    }

    updateDashboardTime();
    setInterval(updateDashboardTime, 1000);

    function setSummaryCounts(todayCount, waitingCount, checkedInCount, readyCount) {
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

frappe.call({
    method: "clinify.reception.get_todays_appointments",
    callback: function (r) {

        let html = "";
        let totalAppointments = 0;
        let checkedInCount = 0;
        let waitingCount = 0;

        if (!r.message || r.message.length === 0) {
            html = "<p>No appointments today.</p>";
        } else {

            totalAppointments = r.message.length;

            r.message.forEach(function (appt) {

                const status = appt.custom_reception_status || "Waiting";

                if (status === "Checked In") {
                    checkedInCount += 1;
                } else if (status !== "Ready for Billing") {
                    waitingCount += 1;
                }


  html += `
    <div class="border-bottom py-3">

        <div class="d-flex justify-content-between align-items-start gap-3">

            <div class="flex-grow-1">
                <div class="mb-1"><strong>${appt.patient_name}</strong></div>
                <div class="text-secondary mb-2">🩺 Dr. ${appt.doctor_name || "-"}</div>
                <div class="fw-bold mb-2">🕒 ${appt.appointment_time}</div>
                <span class="badge" style="background:${appt.journey_color}; color:white; font-size:0.95rem; padding:0.65em 0.9em;">
                    ${appt.journey_label}
                </span>
            </div>

            <div class="text-end">
                ${
                    status === "Checked In"
                    ?
                    `<button class="btn btn-sm btn-success" disabled>
                        ✓ Checked In
                    </button>`
                    :
                    `<button
                        class="btn btn-sm btn-primary check-in-btn"
                        data-appointment="${appt.name}">
                        Check In
                    </button>`
                }
            </div>

        </div>

    </div>
`;

           });

        }

        $("#appointments-list").html(html);
        setSummaryCounts(totalAppointments, waitingCount, checkedInCount);
    }
});

frappe.call({
    method: "clinify.reception.get_billing_queue",
    callback: function (r) {

        let html = "";

        if (!r.message || r.message.length === 0) {

            html = "<p>No pending bills.</p>";

        } else {

            r.message.forEach(function (bill) {

html += `
    <div class="border-bottom py-3 d-flex align-items-center justify-content-between gap-3">

        <div>
            <div class="mb-1"><span class="me-1">👤</span><strong>${bill.customer_name}</strong></div>
            <div class="text-secondary mb-1">🩺 Dr. ${bill.doctor_name || "-"}</div>
            <div class="fw-bold">₹${bill.outstanding_amount}</div>
        </div>

        <div class="text-end">
            <span class="badge badge-warning mb-2" style="font-size:0.95rem; padding:0.55em 0.85em;">${bill.status}</span>
            <br>
            <button
                class="btn btn-sm btn-primary view-invoice-btn"
                data-invoice="${bill.name}">
                View Invoice
            </button>
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
                                    <span class="badge badge-success rounded-pill" style="font-size:0.92rem; padding:0.55em 0.85em;">Ready</span>
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
        setSummaryCounts(undefined, undefined, undefined, (r.message || []).length);

    }
});

};
function refreshReceptionDashboard() {
    frappe.set_route("reception-dashboard");

    setTimeout(function () {
        window.location.reload();
    }, 100);
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

$(document).on("click", ".patient-btn", function () {

    const patient = $(this).data("patient");

    frappe.set_route(
        "Form",
        "Patient",
        patient
    );

});

$(document).on("click", ".view-invoice-btn", function () {

    const invoice = $(this).data("invoice");

    frappe.set_route(
        "Form",
        "Sales Invoice",
        invoice
    );

});

$(document).on("click", ".create-invoice-btn", function () {

    const appointment = $(this).data("appointment");

    const button = $(this);
    button.prop("disabled", true).text("Creating...");

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

        button.prop("disabled", false).text("🧾 Create Invoice");

        frappe.msgprint(
            "Failed to create invoice. Please check the appointment mapping."
        );
    }
},
        error: function () {
            button.prop("disabled", false).text("🧾 Create Invoice");
        }
    });

});

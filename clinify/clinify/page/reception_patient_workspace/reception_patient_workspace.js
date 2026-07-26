frappe.pages["reception-patient-workspace"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Reception Patient Workspace",
        single_column: true
    });

const state = {
    patient: null,
    appointments: [],
    encounters: [],
    billing: [],
    outstanding: 0,
    payments: [],
    prescriptions: [],
    documents: [],
    searchResults: [],
    searchRequestId: 0
};

    const placeholderSections = [
    "Payments",
    "Prescriptions",
    "Documents"
];

    function escapeHtml(value) {
        return frappe.utils.escape_html(String(value || "-"));
    }
    function calculateAge(dob) {
    if (!dob) return "-";

    const birthDate = new Date(dob);
    const today = new Date();

    let age = today.getFullYear() - birthDate.getFullYear();

    const monthDifference = today.getMonth() - birthDate.getMonth();

    if (
        monthDifference < 0 ||
        (monthDifference === 0 &&
            today.getDate() < birthDate.getDate())
    ) {
        age--;
    }

    return age >= 0 ? `${age} Years` : "-";
}

function formatDate(value) {

    if (!value) {
        return "-";
    }

    const date = new Date(value);

    if (isNaN(date)) {
        return value;
    }

    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const year = date.getFullYear();

    return `${day}-${month}-${year}`;
}

function formatTime(value) {

    if (!value) {
        return "-";
    }

    const time = String(value).split(".")[0];

    const parts = time.split(":");

    if (parts.length < 2) {
        return value;
    }

    let hour = parseInt(parts[0], 10);
    const minute = parts[1];

    const suffix = hour >= 12 ? "PM" : "AM";

    hour = hour % 12;

    if (hour === 0) {
        hour = 12;
    }

    return `${hour}:${minute} ${suffix}`;
}

function appointmentStatusBadge(status) {

    const colors = {
        "Scheduled": "warning",
        "Open": "info",
        "Closed": "success",
        "Cancelled": "danger"
    };

    const color = colors[status] || "secondary";

    return `
        <span class="badge badge-${color}">
            ${escapeHtml(status || "-")}
        </span>
    `;
}

function receptionStatusBadge(status) {

    const colors = {
        "Waiting": "secondary",
        "Checked In": "info",
        "Ready for Billing": "warning",
        "Billing": "primary",
        "Completed": "success"
    };

    const color = colors[status] || "secondary";

    return `
        <span class="badge badge-${color}">
            ${escapeHtml(status || "-")}
        </span>
    `;
}

function accountBalanceHtml(balance) {

    balance = Number(balance || 0);

    let color = "#000000";

    if (balance > 0) {
        color = "#dc3545";
    } else if (balance < 0) {
        color = "#198754";
    }

    return `
        <span style="
            color:${color};
            font-size:20px;
            font-weight:700;
        ">
            ₹${Math.round(Math.abs(balance)).toLocaleString("en-IN")}
        </span>
    `;
}

function formatCurrency(amount) {
    return `₹${Math.round(Math.abs(amount)).toLocaleString("en-IN")}`;
}

function appointmentAccountHtml(row) {

    if (row.billing_status === "Pending") {
        return `<span class="indicator orange">Pending</span>`;
    }

    return `
        <span style="
            color:${row.account_balance > 0 ? "#d9534f" : "#28a745"};
            font-weight:600;
        ">
            ${formatCurrency(row.account_balance)}
        </span>
    `;
}

function renderPatientSummary(patient) {

    return `
        <div class="reception-patient-summary-details">

            <div>
    <span>Patient Name</span>

    <strong style="
        color:#0d6efd;
        font-size:20px;
        font-weight:700;
    ">
        ${escapeHtml(patient.patient_name)}
    </strong>

</div>

            <div>
                <span>Clinify ID</span>
                <strong>${escapeHtml(
                    patient.custom_clinify_patient_id || "Not Assigned"
                )}</strong>
            </div>

            <div>
                <span>ERP Patient ID</span>
                <strong>${escapeHtml(patient.name)}</strong>
            </div>

               <div class="patient-account-summary">

    <span>

        Outstanding Account

    </span>

    ${accountBalanceHtml(patient.account_balance)}

</div>
    

            <div>
                <span>Mobile</span>
                <strong>${escapeHtml(
                    patient.mobile || patient.phone || "-"
                )}</strong>
            </div>

            <div>
                <span>Gender</span>
                <strong>${escapeHtml(patient.sex || "-")}</strong>
            </div>

            <div>
                <span>DOB</span>
                <strong>${escapeHtml(formatDate(patient.dob))}</strong>
            </div>

            <div>
                <span>Age</span>
                <strong>${escapeHtml(calculateAge(patient.dob))}</strong>
            </div>

        </div>
    `;
}

function renderAppointments(appointments) {

    if (!appointments || !appointments.length) {
        return `
    <section class="reception-workspace-card">

        <h5>Appointment History</h5>

        <div class="text-muted text-center p-4">
            No appointment history found.
        </div>

    </section>
`;
    }

    let html = `

    <section class="reception-workspace-card">

        <h5>Appointment History</h5>

        <table class="table table-bordered table-hover">

            <thead>

                <tr>
                    <th>Appointment</th>
                    <th>Date</th>
                    <th>Doctor</th>
                    <th>Status</th>
                    <th>Reception</th>
                    <th>Account</th>
                </tr>

            </thead>

            <tbody>
`;

    appointments.forEach(row => {

        html += `
            <tr>

                <td>
                    <a href="/app/patient-appointment/${row.name}"
   target="_blank"
   class="reception-document-link">
                        ${row.name}
                    </a>
                </td>

                <td>
                    ${frappe.datetime.str_to_user(row.appointment_date)}
                </td>

                <td>
                    ${row.doctor_name || ""}
                </td>

                <td>
    ${appointmentStatusBadge(row.status)}
</td>

                <td>
                    ${receptionStatusBadge(row.custom_reception_status)}
                </td>

                <td>
                    ${appointmentAccountHtml(row)}
                </td>

            </tr>
        `;
    });

    html += `
            </tbody>

        </table>

    </section>
`;

    return html;
}

function renderEncounterHistory() {

    if (!state.encounters.length) {
        return `
            <section class="reception-workspace-card">
                <h5>Encounter History</h5>
                <p class="text-muted mb-0">
                    No encounter history available.
                </p>
            </section>
        `;
    }

    const rows = state.encounters.map(function (encounter) {

        return `
            <tr>

                <td>
                    <a href="/app/patient-encounter/${encounter.name}"
                       target="_blank">
                        ${escapeHtml(encounter.name)}
                    </a>
                </td>

                <td>
                    ${escapeHtml(formatDate(encounter.encounter_date))}
                </td>

                <td>
    ${escapeHtml(encounter.practitioner_name || "-")}
</td>

<td>
    ${escapeHtml(encounter.medical_department || "-")}
</td>

<td>
    ${escapeHtml(encounter.encounter_comment || "-")}
</td>
            </tr>
        `;

    }).join("");

    return `
        <section class="reception-workspace-card">

            <h5>Encounter History</h5>

            <table class="table table-sm table-hover mb-0">

                <thead>

                        <tr>
    <th>Encounter</th>
    <th>Date</th>
    <th>Doctor</th>
    <th>Department</th>
    <th>Chief Complaint</th>
</tr>
                    </thead>

                <tbody>

                    ${rows}

                </tbody>

            </table>

        </section>
    `;
}


function renderBilling() {

    if (!state.billing.length) {

        return `
            <section class="reception-workspace-card">

                <h5>Billing</h5>

                <p class="text-muted mb-0">
                    No invoices found.
                </p>

            </section>
        `;
    }

    const rows = state.billing.map(function (invoice) {

        return `
            <tr>

                <td>
                    <a href="/app/sales-invoice/${invoice.name}"
                       target="_blank">
                        ${escapeHtml(invoice.name)}
                    </a>
                </td>

                <td>
                    ${escapeHtml(formatDate(invoice.posting_date))}
                </td>

                <td>
                    ${escapeHtml(invoice.status)}
                </td>

                <td style="text-align:right;">
                    ${formatCurrency(invoice.grand_total)}
                </td>

                <td style="text-align:right;">
                    ${formatCurrency(invoice.paid_amount)}
                </td>

                <td style="text-align:right;color:#d9534f;font-weight:600;">
                    ${formatCurrency(invoice.outstanding_amount)}
                </td>

            </tr>
        `;

    }).join("");

    return `
        <section class="reception-workspace-card">

            <h5>Billing</h5>

            <table class="table table-sm table-hover">

                <thead>

                    <tr>
                        <th>Invoice</th>
                        <th>Date</th>
                        <th>Status</th>
                        <th>Total</th>
                        <th>Paid</th>
                        <th>Due</th>
                    </tr>

                </thead>

                <tbody>

                    ${rows}

                </tbody>

            </table>

            <hr>

            <div style="
                display:flex;
                justify-content:space-between;
                align-items:center;
            ">

                <strong>Outstanding Balance</strong>

                ${accountBalanceHtml(state.outstanding)}

            </div>

        </section>
    `;
}

function renderSidebar() {

    const sidebar = $(page.body).find("#reception-workspace-sidebar");

    if (!sidebar.length) {
        return;
    }

    if (!state.patient) {

        sidebar.html(`
            <h5>Workspace Sidebar</h5>

            <div class="text-muted">
                Search a patient to enable workspace actions.
            </div>
        `);

        return;
    }

    sidebar.html(`

        <h5>Workspace Sidebar</h5>

        <div id="workspace-sidebar-content">

            <div>

                <div style="
                    font-size:12px;
                    color:#777;
                    font-weight:600;
                ">
                    CURRENT PATIENT
                </div>

                <div style="
                    color:#0d6efd;
                    font-size:18px;
                    font-weight:700;
                    margin-top:6px;
                ">
                    ${escapeHtml(state.patient.patient_name)}
                </div>

                <div style="
                    color:#777;
                    font-size:13px;
                ">
                    ${escapeHtml(state.patient.name)}
                </div>

            </div>

            <hr>

            <div>

                <strong>Quick Actions</strong>

                <div style="
                    display:grid;
                    gap:10px;
                    margin-top:12px;
                ">

                    <button
                        class="btn btn-primary btn-sm"
                        id="btn-new-appointment">

                        New Appointment

                    </button>

                    <button
                        class="btn btn-default btn-sm"
                        id="btn-open-patient">

                        Open Patient Record

                    </button>

                </div>

            </div>

            <hr>

            <div>

                <strong>Recent Activity</strong>

                <div class="text-muted mt-2">

                    Coming Soon

                </div>

            </div>

        </div>

    `);

}

function renderWorkspace() {

    const patient = state.patient;

    const patientSummary = patient
        ? renderPatientSummary(patient)
        : `
            <p class="text-muted mb-0">
                Search and select a patient to open the reception workspace.
            </p>
        `;

    const appointmentSection = patient
        ? renderAppointments(state.appointments)
        : "";

    const encounterSection = patient
        ? renderEncounterHistory()
        : "";

    const billingSection = patient
        ? renderBilling()
        : "";

    const placeholderCards = patient
        ? placeholderSections.map(function(section){

            return `
                <section class="reception-workspace-card">

                    <h5>${section}</h5>

                    <p class="text-muted mb-0">

                        ${section} details will appear here.

                    </p>

                </section>
            `;

        }).join("")
        : "";

    $(page.body)

        .find("#reception-patient-workspace-content")

        .html(`

            <section class="reception-workspace-card reception-patient-summary-card">

                <h5>Patient Summary</h5>

                ${patientSummary}

            </section>

            ${appointmentSection}

            ${encounterSection}

            ${billingSection}

            ${placeholderCards}

        `);

    renderSidebar();

}

    function renderSearchResults() {
        const resultsWrapper = $(page.body).find("#reception-patient-search-results");

        if (!state.searchResults.length) {
            resultsWrapper.empty();
            return;
        }

        resultsWrapper.html(state.searchResults.map(function (patient, index) {
            return `
                <button type="button" class="reception-patient-result" data-result-index="${index}">
                    <strong>${escapeHtml(patient.patient_name)}</strong>
                    <span>${escapeHtml(patient.custom_clinify_patient_id || patient.name)}</span>
                    <small>${escapeHtml(patient.mobile || "No mobile number")}</small>
                </button>
            `;
        }).join(""));
    }

    function searchPatients(searchText) {
        const requestId = ++state.searchRequestId;

        if (searchText.length < 2) {
            state.searchResults = [];
            renderSearchResults();
            return;
        }

        frappe.call({
            method: "clinify.reception.search_patients",
            args: {
                search_text: searchText
            },
            callback: function (response) {
                if (requestId !== state.searchRequestId) {
                    return;
                }

                state.searchResults = response.message || [];
                renderSearchResults();
            }
        });
    }

    function loadPatient(patientName) {

    frappe.call({
        method: "clinify.reception.get_reception_patient",
        args: {
            patient: patientName
        },
        freeze: true,
        freeze_message: __("Loading patient workspace..."),
        callback: function (patientResponse) {

            state.patient = patientResponse.message || {};

            frappe.call({
                method: "clinify.reception.get_patient_appointments",
                args: {
                    patient: patientName
                },
                callback: function (appointmentResponse) {

                    state.appointments = appointmentResponse.message || [];

frappe.call({
    method: "clinify.reception.get_patient_encounters",
    args: {
        patient: patientName
    },
    callback: function (encounterResponse) {

        state.encounters = encounterResponse.message || [];

frappe.call({
    method: "clinify.reception.get_patient_billing",
    args: {
        patient: patientName
    },
    callback: function (billingResponse) {

        const billingData = billingResponse.message || {};

state.billing = billingData.invoices || [];
state.outstanding = billingData.total_outstanding || 0;

        state.searchResults = [];

        $(page.body)
            .find("#reception-patient-search")
            .val(state.patient.patient_name);

        renderSearchResults();
        renderWorkspace();
    }
});
    }
});
                }
            });
        }
    });
}

    $(page.body).html(`
        <div class="container-fluid reception-patient-workspace">
            <style>
                .reception-patient-workspace {
                    padding-top: 1rem;
                }

                .reception-patient-workspace-header {
                    align-items: center;
                    background: var(--blue-600, #007be0);
                    color: #fff;
                    display: flex;
                    margin-bottom: 1.25rem;
                    min-height: 76px;
                    padding: 1.25rem 1.5rem;
                }

                .reception-patient-workspace-header h3 {
                    color: inherit;
                    margin: 0;
                }

                .reception-patient-search-card,
                .reception-workspace-card,
                .reception-workspace-sidebar {
                    background: #fff;
                    border: 1px solid var(--border-color, #e2e2e2);
                    border-radius: 0.5rem;
                    box-shadow: 0 2px 8px rgba(16, 24, 40, 0.06);
                }

                .reception-patient-search-card {
                    margin-bottom: 1.25rem;
                    padding: 1.25rem;
                    position: relative;
                }

                .reception-patient-search-card label {
                    display: block;
                    font-weight: 700;
                    margin-bottom: 0.5rem;
                }

                .reception-patient-search-results {
                    background: #fff;
                    border: 1px solid var(--border-color, #e2e2e2);
                    border-radius: 0.5rem;
                    box-shadow: 0 0.75rem 1.5rem rgba(16, 24, 40, 0.12);
                    left: 1.25rem;
                    max-height: 320px;
                    overflow-y: auto;
                    position: absolute;
                    right: 1.25rem;
                    top: calc(100% - 1.25rem);
                    z-index: 10;
                }

                .reception-patient-result {
                    background: transparent;
                    border: 0;
                    border-bottom: 1px solid var(--border-color, #e2e2e2);
                    cursor: pointer;
                    display: grid;
                    gap: 0.15rem;
                    padding: 0.875rem 1rem;
                    text-align: left;
                    width: 100%;
                }

                .reception-patient-result:last-child {
                    border-bottom: 0;
                }

                .reception-patient-result:hover,
.reception-patient-result:focus {
    background: var(--blue-50, #f7fbfd);
    outline: none;
}

.reception-document-link,
.reception-workspace-card table a {

    color: #0d6efd;
    font-weight: 700;
    text-decoration: none;
}

.reception-document-link:hover,
.reception-workspace-card table a:hover {

    color: #084298;
    text-decoration: underline;
}

                .reception-patient-result span,
                .reception-patient-result small,
                .reception-patient-summary-details span {
                    color: var(--text-muted, #7c7c7c);
                }

                .reception-patient-workspace-layout {
    display: grid;
    gap: 1.25rem;
    grid-template-columns: minmax(0, 1fr) 220px;
}

                .reception-patient-workspace-content {
                    display: grid;
                    gap: 1.25rem;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                .reception-workspace-card,
                .reception-workspace-sidebar {
                    min-height: 132px;
                    padding: 1.25rem;
                }

                .reception-workspace-card h5,
.reception-workspace-sidebar h5 {

    background: #f5f5f5;
    border-bottom: 1px solid #ddd;

    border-radius: 8px 8px 0 0;

    margin: -1.25rem -1.25rem 1rem -1.25rem;

    padding: 12px 16px;

    font-weight: 700;
}

                .reception-patient-summary-card {
                    grid-column: 1 / -1;
                }

                .reception-patient-summary-details {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

                .reception-patient-summary-details div {
                    display: grid;
                    gap: 0.25rem;
                }
.patient-account-summary {
    display: grid;
    gap: 0.25rem;
}

.patient-account-summary span {

    color:#666;

    font-size:13px;

    font-weight:700;

    letter-spacing:.4px;

    text-transform:uppercase;

}
    #workspace-sidebar-content {

    display:flex;

    flex-direction:column;

    gap:18px;

}
    

                @media (max-width: 991.98px) {
                    .reception-patient-workspace-layout {
                        grid-template-columns: 1fr;
                    }
                }

                @media (max-width: 575.98px) {
                    .reception-patient-workspace-content,
                    .reception-patient-summary-details {
                        grid-template-columns: 1fr;
                    }
                }
            </style>

            <header class="reception-patient-workspace-header">
                <h3 class="fw-bold">Reception Patient Workspace</h3>
            </header>

            <section class="reception-patient-search-card">
                <label for="reception-patient-search">Find Patient</label>
                <input
                    id="reception-patient-search"
                    class="form-control"
                    type="search"
                    autocomplete="off"
                    placeholder="Search by Patient ID, name, or mobile number">
                <div id="reception-patient-search-results" class="reception-patient-search-results"></div>
            </section>

            <div class="reception-patient-workspace-layout">
                <main id="reception-patient-workspace-content" class="reception-patient-workspace-content"></main>
<aside
    id="reception-workspace-sidebar"
    class="reception-workspace-sidebar">
</aside>
            </div>
        </div>
    `);

    let searchTimeout;

    $(page.body).on("input", "#reception-patient-search", function () {
        const searchText = $(this).val().trim();

        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function () {
            searchPatients(searchText);
        }, 250);
    });

    $(page.body).on("click", ".reception-patient-result", function () {
        const resultIndex = $(this).data("result-index");
        const patient = state.searchResults[resultIndex];

        if (patient) {
            loadPatient(patient.name);
        }
    });

    renderWorkspace();
$(page.body).on("click", "#btn-open-patient", function () {

    if (!state.patient) return;

    frappe.set_route(
        "Form",
        "Patient",
        state.patient.name
    );

});

$(page.body).on("click", "#btn-new-appointment", function () {

    if (!state.patient) return;

    frappe.new_doc("Patient Appointment", {

        patient: state.patient.name

    });

});
};

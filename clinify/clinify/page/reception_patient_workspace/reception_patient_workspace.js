frappe.pages["reception-patient-workspace"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Reception Patient Workspace",
        single_column: true
    });

    const state = {
    patient: null,
    appointments: [],
    searchResults: [],
    searchRequestId: 0
};

    const placeholderSections = [
    "Encounters",
    "Billing",
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

function renderPatientSummary(patient) {
    return `
        <div class="reception-patient-summary-details">

            <div>
                <span>Patient Name</span>
                <strong>${escapeHtml(patient.patient_name)}</strong>
            </div>

            <div>
                <span>Clinify ID</span>
                <strong>${escapeHtml(
                    patient.custom_clinify_patient_id || "Not Assigned"
                )}</strong>
            </div>

            <div>
                <span>ERPNext Patient ID</span>
                <strong>${escapeHtml(patient.name)}</strong>
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
                <span>Date of Birth</span>
                <strong>${escapeHtml(patient.dob || "-")}</strong>
            </div>

            <div>
                <span>Age</span>
                <strong>${escapeHtml(calculateAge(patient.dob))}</strong>
            </div>

        </div>
    `;
}
function renderAppointments() {

    if (!state.appointments.length) {
        return `
            <section class="reception-workspace-card">
                <h5>Appointment History</h5>
                <p class="text-muted mb-0">
                    No appointment history found.
                </p>
            </section>
        `;
    }

    const rows = state.appointments.map(function (appointment) {

        return `
            <tr>
                <td>${escapeHtml(appointment.appointment_date)}</td>
                <td>${escapeHtml(appointment.appointment_time || "-")}</td>
                <td>${escapeHtml(
                    appointment.doctor_name ||
                    appointment.practitioner_name ||
                    "-"
                )}</td>
                <td>${escapeHtml(appointment.status || "-")}</td>
                <td>${escapeHtml(
                    appointment.custom_reception_status || "-"
                )}</td>
            </tr>
        `;

    }).join("");

    return `
        <section class="reception-workspace-card">
            <h5>Appointment History</h5>

            <table class="table table-sm table-hover mb-0">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Time</th>
                        <th>Doctor</th>
                        <th>Status</th>
                        <th>Reception</th>
                    </tr>
                </thead>

                <tbody>
                    ${rows}
                </tbody>
            </table>
        </section>
    `;
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
        ? renderAppointments()
        : "";

    const placeholderCards = patient
        ? placeholderSections.map(function (section) {
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

    $(page.body).find("#reception-patient-workspace-content").html(`
        <section class="reception-workspace-card reception-patient-summary-card">
            <h5>Patient Summary</h5>
            ${patientSummary}
        </section>

        ${appointmentSection}

        ${placeholderCards}
    `);
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

                .reception-patient-result span,
                .reception-patient-result small,
                .reception-patient-summary-details span {
                    color: var(--text-muted, #7c7c7c);
                }

                .reception-patient-workspace-layout {
                    display: grid;
                    gap: 1.25rem;
                    grid-template-columns: minmax(0, 1fr) 280px;
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
                    font-weight: 700;
                    margin-bottom: 0.875rem;
                }

                .reception-patient-summary-card {
                    grid-column: 1 / -1;
                }

                .reception-patient-summary-details {
                    display: grid;
                    gap: 1rem;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                }

                .reception-patient-summary-details div {
                    display: grid;
                    gap: 0.25rem;
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
                <aside class="reception-workspace-sidebar">
                    <h5>Workspace Sidebar</h5>
                    <p class="text-muted mb-0">Reserved for upcoming reception actions.</p>
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
};

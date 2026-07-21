frappe.pages["doctor-dashboard"].on_page_load = function (wrapper) {

    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Doctor Dashboard",
        single_column: true
    });

    $(page.body).html(`
        <div class="container-fluid">

            <div class="card">
                <div class="card-body">

                    <h3>Today's Patients</h3>

                    <div id="doctor-patient-list">
                        Loading...
                    </div>

                </div>
            </div>

        </div>
    `);

    frappe.call({
        method: "clinify.doctor.get_todays_patients",
        callback: function (r) {

            let html = "";

            if (!r.message || r.message.length === 0) {

                html = "<p>No patients scheduled today.</p>";

            } else {

                r.message.forEach(function (patient) {

                    html += `
                        <div class="border-bottom py-3">

                            <strong>${patient.patient_name}</strong>

                            <br>

                            <small class="text-muted">
                                Dr. ${patient.doctor_name || "-"}
                            </small>

                            <br>

                            ${patient.appointment_time}

                            <br>

                            <small class="text-muted">
                                ${patient.custom_reception_status || "Waiting"}
                            </small>

                            <br><br>

                            <button
                                class="btn btn-primary btn-sm open-consultation-btn"
                                data-appointment="${patient.name}">

                                Open Consultation

                            </button>

                        </div>
                    `;

                });

            }

            $("#doctor-patient-list").html(html);

        }
    });

};


$(document).on("click", ".open-consultation-btn", function () {
console.log("Open Consultation button clicked");
    const appointment = $(this).data("appointment");

    frappe.call({

        method: "clinify.doctor.launch_consultation",

        args: {
            appointment: appointment
        },

        callback: function (r) {

            if (!r.message) {
                frappe.msgprint("Unable to launch consultation.");
                return;
            }

            if (r.message.exists) {

                frappe.set_route(
                    "Form",
                    "Patient Encounter",
                    r.message.encounter
                );

            } else {

                frappe.model.open_mapped_doc({
                    method: "healthcare.healthcare.doctype.patient_appointment.patient_appointment.make_encounter",
                    frm: {
                        doc: {
                            doctype: "Patient Appointment",
                            name: appointment
                        }
                    }
                });

            }

        }

    });

});

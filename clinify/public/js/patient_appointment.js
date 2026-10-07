console.log("[CLINIFY] patient_appointment.js LOADED");

frappe.ui.form.on("Patient Appointment", {
    setup(frm) {
        console.log("[CLINIFY] Patient Appointment setup fired");

        frm.set_query("appointment_type", function () {
            console.log("[CLINIFY] appointment_type query fired");

            return {
                filters: {
                    name: "OPD",
                },
            };
        });
    },

    onload(frm) {
        console.log("[CLINIFY] Patient Appointment onload fired");

        if (frm.is_new() && !frm.doc.appointment_type) {
            frm.set_value("appointment_type", "OPD");
        }
    },
});

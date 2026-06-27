frappe.pages["reception-dashboard"].on_page_load = function(wrapper) {



    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Reception Dashboard",
        single_column: true
    });

    $(page.body).html(`
        <div class="container-fluid">

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

        </div>
    `);

frappe.call({
    method: "clinify.reception.get_todays_appointments",
    callback: function (r) {

        let html = "";

        if (!r.message || r.message.length === 0) {
            html = "<p>No appointments today.</p>";
        } else {

            r.message.forEach(function (appt) {

                html += `
                    <div class="border-bottom py-2">
                        <strong>${appt.patient_name}</strong><br>
${appt.appointment_time} • ${appt.status}

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

        if (!r.message || r.message.length === 0) {

            html = "<p>No pending bills.</p>";

        } else {

            r.message.forEach(function (bill) {

                html += `
                    <div class="border-bottom py-2">
                        <strong>${bill.customer_name}</strong><br>
                        ₹${bill.outstanding_amount} • ${bill.status}
                    </div>
                `;

            });

        }

        $("#billing-list").html(html);

    }
});

};

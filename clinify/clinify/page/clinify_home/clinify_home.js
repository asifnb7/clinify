frappe.pages["clinify-home"].on_page_load = function (wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Clinify",
        single_column: true
    });

    const body = $(`
        <div class="container mt-4">

            <div class="row">

                <div class="col-md-4 mb-3">
                    <button class="btn btn-primary w-100" id="reception">
                        🏥 Reception
                    </button>
                </div>

                <div class="col-md-4 mb-3">
                    <button class="btn btn-primary w-100" id="doctor">
                        👨‍⚕ Doctor
                    </button>
                </div>

                <div class="col-md-4 mb-3">
                    <button class="btn btn-secondary w-100">
                        🧪 Laboratory
                    </button>
                </div>

                <div class="col-md-4 mb-3">
                    <button class="btn btn-secondary w-100">
                        💊 Pharmacy
                    </button>
                </div>

                <div class="col-md-4 mb-3">
                    <button class="btn btn-secondary w-100">
                        💰 Billing
                    </button>
                </div>

                <div class="col-md-4 mb-3">
                    <button class="btn btn-secondary w-100">
                        📊 Reports
                    </button>
                </div>

            </div>

        </div>
    `);

    $(page.body).append(body);

    body.find("#reception").click(() => {
        frappe.set_route("reception-dashboard");
    });

    body.find("#doctor").click(() => {
        frappe.set_route("doctor-dashboard");
    });

};
app_name = "clinify"
app_title = "Clinify"
app_publisher = "Salniz Technologies"
app_description = "Healthcare, Simplified"
app_email = "salniz.info@gmail.com"
app_license = "mit"

# Includes in <head>
# ------------------
# app_include_css = "/assets/clinify/css/clinify.css"
# app_include_js = "/assets/clinify/js/clinify.js"

# Home Pages
# ----------
# home_page = "login"

# Generators
# ----------
# website_generators = ["Web Page"]

# Installation
# ------------
# before_install = "clinify.install.before_install"
after_install = "clinify.install.after_install"

# Uninstallation
# --------------
# before_uninstall = "clinify.uninstall.before_uninstall"
# after_uninstall = "clinify.uninstall.after_uninstall"

# Permissions
# -----------
# permission_query_conditions = {}
# has_permission = {}

# Doctype Class Overrides
# -----------------------
# override_doctype_class = {}

# Document Events
# ---------------
# doc_events = {}

# Scheduled Tasks
# ----------------
# scheduler_events = {}

# Testing
# -------
before_tests = "clinify.tests.before_tests"

# Override Methods
# ----------------
# No unsafe overrides here
override_whitelisted_methods = {}

app_include_css = [
    "/assets/clinify/theme/css/clinify-theme.css",
    "/assets/clinify/css/clinify_subscription_list.css",
]

app_include_js = [
    "/assets/clinify/js/reception_route.js",
    "/assets/clinify/js/tenant_security.js",
]


doctype_list_js = {
    "Clinify Subscription": "public/js/clinify_subscription_list.js",
    "Clinify Tenant": "public/js/clinify_tenant_list.js",
}

doctype_js = {
    "Patient Encounter": "public/js/encounter/clinify_encounter.js",
    "Drug Prescription": "public/js/drug_prescription.js",
    "Sales Invoice": "public/js/clinify_sales_invoice.js",
    "Payment Entry": "public/js/clinify_payment_entry.js",
    "Patient Appointment": "public/js/patient_appointment.js",
}
web_include_css = "/assets/clinify/css/clinify-login.css"

doc_events = {
    "Patient": {
        "before_insert": "clinify.patient.assign_clinify_patient_id"
    },

   "Patient Encounter": {
    "before_insert": "clinify.encounter.before_insert",
    "on_update": "clinify.encounter.after_save",
}
}

on_session_creation = [
    "clinify.saas.sso.on_session_creation",
]

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

fixtures = [
    "Workspace",
    "Custom Field",
    "Property Setter",
    "Client Script",
    "Server Script",
    "Custom HTML Block",
    {
        "doctype": "Custom DocPerm",
        "filters": [
            ["parent", "=", "Lab Test Template"]
        ]
    },
]


after_sync = "clinify.saas.site_hooks.after_sync"
after_migrate = "clinify.saas.site_hooks.after_migrate"

# Clinify Tenant failed-provisioning retry UI
if isinstance(app_include_js, list):
    if "/assets/clinify/js/clinify_tenant_retry.js" not in app_include_js:
        app_include_js.append("/assets/clinify/js/clinify_tenant_retry.js")
else:
    if app_include_js != "/assets/clinify/js/clinify_tenant_retry.js":
        app_include_js = [app_include_js, "/assets/clinify/js/clinify_tenant_retry.js"]
# CLINIFY_NATIVE_DOCTOR_SCHEDULE_HOOK
# Extends native Healthcare Practitioner creation with Clinify's
# tenant OPD scheduling foundation. Healthcare core is untouched.

doc_events = globals().get("doc_events", {})

_clinify_practitioner_events = doc_events.setdefault(
    "Healthcare Practitioner",
    {},
)

_clinify_schedule_handler = (
    "clinify.doctor_schedule.ensure_default_schedule"
)

_clinify_existing_handler = _clinify_practitioner_events.get(
    "after_insert"
)

if _clinify_existing_handler is None:
    _clinify_practitioner_events["after_insert"] = (
        _clinify_schedule_handler
    )
elif isinstance(_clinify_existing_handler, list):
    if _clinify_schedule_handler not in _clinify_existing_handler:
        _clinify_existing_handler.append(
            _clinify_schedule_handler
        )
else:
    if _clinify_existing_handler != _clinify_schedule_handler:
        _clinify_practitioner_events["after_insert"] = [
            _clinify_existing_handler,
            _clinify_schedule_handler,
        ]

del _clinify_practitioner_events
del _clinify_schedule_handler
del _clinify_existing_handler

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
# after_install = "clinify.install.after_install"

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
# before_tests = "clinify.tests.before_tests"

# Override Methods
# ----------------
# No unsafe overrides here
override_whitelisted_methods = {}

app_include_css = "/assets/clinify/theme/css/clinify-theme.css"

app_include_js = "/assets/clinify/js/clinify.js"
doctype_js = {
    "Patient Encounter": "public/js/encounter/dental_service_palette.js"
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

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

fixtures = [
    "Workspace",
    "Custom Field",
    "Property Setter",
    "Server Script",
]
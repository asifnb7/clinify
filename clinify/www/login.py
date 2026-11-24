from clinify.saas.sso import _is_control_site


def get_context(context):
    context.favicon = "/assets/clinify/images/clinify-logo.png"
    context.clinify_is_control_site = _is_control_site()

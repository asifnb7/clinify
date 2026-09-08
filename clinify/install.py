import frappe


def after_install():
    """Ensure Clinify custom schema exists after a fresh app installation."""
    from clinify.patches.install_core_custom_fields import execute

    execute()

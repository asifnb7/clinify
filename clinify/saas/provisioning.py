import re

import frappe


RESERVED_SITE_NAMES = {
    "assets",
    "common_site_config",
    "localhost",
    "site1",
    "site2",
    "test",
}


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _validate_site_name(site_name):
    site_name = _clean(site_name)

    if not site_name:
        frappe.throw("Site Name is required.")

    if len(site_name) > 100:
        frappe.throw("Site Name must not exceed 100 characters.")

    if site_name.lower() in RESERVED_SITE_NAMES:
        frappe.throw("The requested Site Name is reserved.")

    if not re.match(r"^[a-z0-9][a-z0-9._-]*$", site_name):
        frappe.throw(
            "Site Name may contain only lowercase letters, numbers, "
            "periods, underscores, and hyphens."
        )

    return site_name


def _validate_tenant_code(tenant_code):
    tenant_code = _clean(tenant_code).upper()

    if not tenant_code:
        frappe.throw("Tenant Code is required.")

    if len(tenant_code) > 50:
        frappe.throw("Tenant Code must not exceed 50 characters.")

    if not re.match(r"^[A-Z0-9][A-Z0-9_-]*$", tenant_code):
        frappe.throw(
            "Tenant Code may contain only uppercase letters, "
            "numbers, underscores, and hyphens."
        )

    return tenant_code


def _validate_email(email):
    email = _clean(email)

    if not email:
        frappe.throw("Administrator Email is required.")

    if not frappe.utils.validate_email_address(email, throw=False):
        frappe.throw("Administrator Email is not valid.")

    return email


def validate_provision_request(
    tenant_name,
    tenant_code,
    site_name,
    administrator_email,
    plan,
    domain=None,
):
    """
    Validate a Clinify tenant provisioning request.

    This function is intentionally read-only.

    It does NOT:
    - create a site
    - create a tenant
    - install an app
    - run migration
    - create a user
    - create a subscription
    """

    tenant_name = _clean(tenant_name)
    domain = _clean(domain)

    if not tenant_name:
        frappe.throw("Tenant Name is required.")

    if len(tenant_name) > 140:
        frappe.throw("Tenant Name must not exceed 140 characters.")

    tenant_code = _validate_tenant_code(tenant_code)
    site_name = _validate_site_name(site_name)
    administrator_email = _validate_email(administrator_email)

    if not plan:
        frappe.throw("Plan is required.")

    if not frappe.db.exists("Clinify Plan", plan):
        frappe.throw("Clinify Plan does not exist: {}".format(plan))

    existing_tenant = frappe.db.get_value(
        "Clinify Tenant",
        {"tenant_code": tenant_code},
        "name",
    )

    if existing_tenant:
        frappe.throw(
            "Tenant Code already exists: {}".format(tenant_code)
        )

    existing_site = frappe.db.get_value(
        "Clinify Tenant",
        {"site_name": site_name},
        "name",
    )

    if existing_site:
        frappe.throw(
            "Site Name is already registered: {}".format(site_name)
        )

    if domain:
        existing_domain = frappe.db.get_value(
            "Clinify Tenant",
            {"domain": domain},
            "name",
        )

        if existing_domain:
            frappe.throw(
                "Domain is already registered: {}".format(domain)
            )

    return {
        "valid": True,
        "tenant_name": tenant_name,
        "tenant_code": tenant_code,
        "site_name": site_name,
        "domain": domain,
        "administrator_email": administrator_email,
        "plan": plan,
    }


@frappe.whitelist()
def validate_provisioning_request(
    tenant_name,
    tenant_code,
    site_name,
    administrator_email,
    plan,
    domain=None,
):
    """
    Public validation endpoint.

    No database records are created or modified.
    """

    return validate_provision_request(
        tenant_name=tenant_name,
        tenant_code=tenant_code,
        site_name=site_name,
        administrator_email=administrator_email,
        plan=plan,
        domain=domain,
    )

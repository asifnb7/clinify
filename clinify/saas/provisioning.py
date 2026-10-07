import re
import uuid

import frappe
from frappe.utils.password import decrypt, encrypt


RESERVED_SITE_NAMES = {
    "assets",
    "common_site_config",
    "localhost",
    "site1",
    "site2",
    "test",
}


PROVISIONING_CREDENTIAL_TTL = 900
PROVISIONING_JOB_PREFIX = "clinify:tenant-provisioning:"


def _credential_key(token):
    return "{}credential:{}".format(PROVISIONING_JOB_PREFIX, token)


def _store_provisioning_password(password):
    token = uuid.uuid4().hex
    frappe.cache().set_value(_credential_key(token), encrypt(password), expires_in_sec=PROVISIONING_CREDENTIAL_TTL)
    return token


def _consume_provisioning_password(token):
    encrypted = frappe.cache().get_value(_credential_key(token))
    if not encrypted:
        frappe.throw("Provisioning credentials have expired. Please retry provisioning.")
    frappe.cache().delete_value(_credential_key(token))
    return decrypt(encrypted)


def _provisioning_job_name(tenant_name):
    return "{}{}".format(PROVISIONING_JOB_PREFIX, tenant_name)


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
    contact_person=None,
    registered_phone=None,
    registered_email=None,
    address_line_1=None,
    address_line_2=None,
    registered_city=None,
    registered_state=None,
    postal_code=None,
    registered_country=None,
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
    contact_person = _clean(contact_person)
    registered_phone = _clean(registered_phone)
    registered_email = _clean(registered_email)
    address_line_1 = _clean(address_line_1)
    address_line_2 = _clean(address_line_2)
    registered_city = _clean(registered_city)
    registered_state = _clean(registered_state)
    postal_code = _clean(postal_code)
    registered_country = _clean(registered_country)

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

    existing_administrator = frappe.db.exists(
        "Clinify Tenant",
        {"administrator_email": administrator_email},
    )

    if existing_administrator:
        frappe.throw(
            "Administrator Email is already registered to another Tenant."
        )

    return {
        "valid": True,
        "tenant_name": tenant_name,
        "tenant_code": tenant_code,
        "site_name": site_name,
        "domain": domain,
        "administrator_email": administrator_email,
        "plan": plan,
        "contact_person": contact_person,
        "registered_phone": registered_phone,
        "registered_email": registered_email,
        "address_line_1": address_line_1,
        "address_line_2": address_line_2,
        "registered_city": registered_city,
        "registered_state": registered_state,
        "postal_code": postal_code,
        "registered_country": registered_country,
    }


def _require_provisioning_access():
    """
    Restrict tenant provisioning to the Clinify control plane.

    For the current beta/dev environment the control plane is
    clinify.localhost. Production should replace this with an explicit
    control-plane site configuration.
    """

    if frappe.session.user == "Guest":
        frappe.throw(
            "Authentication is required for tenant provisioning."
        )

    frappe.only_for("System Manager")

    control_site = frappe.conf.get("clinify_control_site") or "clinify.localhost"

    if frappe.local.site != control_site:
        frappe.throw(
            "Tenant provisioning is only available from the Clinify control plane."
        )


@frappe.whitelist()
def provision_tenant_from_ui(
    tenant_name,
    tenant_code,
    site_name,
    administrator_email,
    administrator_password,
    administrator_name=None,
    plan=None,
    domain=None,
    contact_person=None,
    registered_phone=None,
    registered_email=None,
    address_line_1=None,
    address_line_2=None,
    registered_city=None,
    registered_state=None,
    postal_code=None,
    registered_country=None,
    subscription_end_date=None,
):
    """
    Provision a new Clinify tenant from the control-plane UI.

    The administrator password is accepted only for the duration of this
    request and is never written to Clinify Tenant or any control-plane
    document.
    """

    if frappe.request.method != "POST":
        frappe.throw(
            "Tenant provisioning must use POST."
        )

    _require_provisioning_access()

    administrator_password = _clean(administrator_password)
    if not tenant_code or not site_name:
        slug = re.sub(r"[^a-z0-9]+", "-", _clean(tenant_name).lower()).strip("-")
        if not slug:
            frappe.throw("A valid Clinic Name is required to generate Tenant Code and Tenant Site.")
        tenant_code = slug.upper()[:50]
        site_name = slug[:90] + ".localhost"
        base_code, base_site = tenant_code, site_name
        n = 2
        while frappe.db.exists("Clinify Tenant", {"tenant_code": tenant_code}) or frappe.db.exists("Clinify Tenant", {"site_name": site_name}):
            suffix = "-" + str(n)
            tenant_code = base_code[:50-len(suffix)] + suffix
            site_name = base_site[:100-len(suffix)-len(".localhost")] + suffix + ".localhost"
            n += 1


    if not administrator_password:
        frappe.throw(
            "Administrator Password is required."
        )

    existing_tenant = frappe.db.get_value(
        "Clinify Tenant",
        {"tenant_code": _clean(tenant_code)},
        [
            "name",
            "tenant_name",
            "tenant_code",
            "site_name",
            "administrator_email",
            "administrator_name",
            "plan",
            "domain",
            "contact_person",
            "registered_phone",
            "registered_email",
            "address_line_1",
            "address_line_2",
            "registered_city",
            "registered_state",
            "postal_code",
            "registered_country",
            "provisioning_status",
        ],
        as_dict=True,
    )

    if existing_tenant:
        retryable_statuses = {
            "Pending",
            "Creating Site",
            "Installing Apps",
            "Configuring Clinic",
            "Creating Subscription",
            "Creating Administrator",
            "Verifying",
            "Failed",
        }

        if existing_tenant.provisioning_status not in retryable_statuses:
            frappe.throw(
                "Tenant cannot be provisioned from the UI in its current status: {}".format(
                    existing_tenant.provisioning_status
                )
            )

        validation = {
            "valid": True,
            "tenant_name": existing_tenant.tenant_name,
            "tenant_code": existing_tenant.tenant_code,
            "site_name": existing_tenant.site_name,
            "administrator_email": existing_tenant.administrator_email,
            "plan": existing_tenant.plan,
            "domain": existing_tenant.domain,
            "contact_person": existing_tenant.contact_person,
            "registered_phone": existing_tenant.registered_phone,
            "registered_email": existing_tenant.registered_email,
            "address_line_1": existing_tenant.address_line_1,
            "address_line_2": existing_tenant.address_line_2,
            "registered_city": existing_tenant.registered_city,
            "registered_state": existing_tenant.registered_state,
            "postal_code": existing_tenant.postal_code,
            "registered_country": existing_tenant.registered_country,
        }

    else:
        validation = validate_provision_request(
            tenant_name=tenant_name,
            tenant_code=tenant_code,
            site_name=site_name,
            administrator_email=administrator_email,
            plan=plan,
            domain=domain,
            contact_person=contact_person,
            registered_phone=registered_phone,
            registered_email=registered_email,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            registered_city=registered_city,
            registered_state=registered_state,
            postal_code=postal_code,
            registered_country=registered_country,
        )

    password_token = _store_provisioning_password(administrator_password)

    job_id = "{}{}".format(
        PROVISIONING_JOB_PREFIX,
        validation["tenant_code"],
    )

    frappe.enqueue(
        "clinify.saas.provisioning.run_queued_provisioning",
        queue="long",
        job_id=job_id,
        deduplicate=True,
        enqueue_after_commit=True,
        tenant_name=validation["tenant_name"],
        tenant_code=validation["tenant_code"],
        site_name=validation["site_name"],
        administrator_email=validation["administrator_email"],
        plan=validation["plan"],
        administrator_password_token=password_token,
        administrator_name=(
            _clean(administrator_name)
            or validation["tenant_name"]
        ),
        domain=validation["domain"],
        contact_person=validation["contact_person"],
        registered_phone=validation["registered_phone"],
        registered_email=validation["registered_email"],
        address_line_1=validation["address_line_1"],
        address_line_2=validation["address_line_2"],
        registered_city=validation["registered_city"],
        registered_state=validation["registered_state"],
        postal_code=validation["postal_code"],
        registered_country=validation["registered_country"],
        subscription_end_date=subscription_end_date,
    )

    return {
        "success": True,
        "queued": True,
        "tenant": existing_tenant.name if existing_tenant else validation["tenant_name"],
        "tenant_name": validation["tenant_name"],
        "tenant_code": validation["tenant_code"],
        "site_name": validation["site_name"],
        "provisioning_status": "Queued",
        "message": "Tenant provisioning has been queued.",
    }


def run_queued_provisioning(
    tenant_name,
    tenant_code,
    site_name,
    administrator_email,
    plan,
    administrator_password_token,
    administrator_name=None,
    domain=None,
    contact_person=None,
    registered_phone=None,
    registered_email=None,
    address_line_1=None,
    address_line_2=None,
    registered_city=None,
    registered_state=None,
    postal_code=None,
    registered_country=None,
    subscription_end_date=None,
):
    password = None
    try:
        password = _consume_provisioning_password(administrator_password_token)

        from clinify.saas.orchestrator import provision_tenant

        return provision_tenant(
            tenant_name=tenant_name,
            tenant_code=tenant_code,
            site_name=site_name,
            administrator_email=administrator_email,
            plan=plan,
            admin_password=password,
            subscription_end_date=subscription_end_date,
            administrator_name=administrator_name,
            domain=domain,
            contact_person=contact_person,
            registered_phone=registered_phone,
            registered_email=registered_email,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            registered_city=registered_city,
            registered_state=registered_state,
            postal_code=postal_code,
            registered_country=registered_country,
        )
    finally:
        password = None


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

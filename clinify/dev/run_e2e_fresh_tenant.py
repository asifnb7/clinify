"""End-to-end acceptance run for ONE fresh disposable tenant.

This is the only acceptance path for the tenant-provisioning work: a brand-new
local tenant provisioned from the control site, with every value the bootstrap
and the SSO handoff need supplied as *test input before provisioning*.

Nothing here repairs, updates, or reuses an existing tenant record.  The tenant
it creates is disposable and is deliberately left in place afterwards.

Supplied up front, so no post-provisioning record edits are required:
  * `registered_country` + address -> ERPNext Company/Fiscal Year foundation
  * `domain` -> the SSO audience, which must equal `site_name`

Run:
    CLINIFY_E2E_ADMIN_PASSWORD=... env/bin/python /tmp/fresh_drive.py
"""

import os

import frappe

from clinify.saas.orchestrator import provision_tenant

TENANT_NAME = "SSO Fresh E2E 02"
TENANT_CODE = "SSO-FRESH-E2E-02"
SITE_NAME = "sso-fresh-e2e-02.localhost"
# The SSO audience check requires domain == site_name, so a provisioned tenant is
# only login-capable if the domain arrives with it.
DOMAIN = SITE_NAME
ADMINISTRATOR_EMAIL = "sso.fresh.e2e02@example.com.invalid"
PLAN = "STARTER-MONTHLY"

TENANT_FIELDS = [
    "name",
    "tenant_code",
    "site_name",
    "domain",
    "administrator_email",
    "registered_country",
    "registered_city",
    "registered_state",
    "postal_code",
    "contact_person",
    "provisioning_status",
    "provisioning_error",
    "subscription_status",
    "subscription_end_date",
]


def run():
    result = provision_tenant(
        tenant_name=TENANT_NAME,
        tenant_code=TENANT_CODE,
        site_name=SITE_NAME,
        administrator_email=ADMINISTRATOR_EMAIL,
        plan=PLAN,
        admin_password=os.environ["CLINIFY_E2E_ADMIN_PASSWORD"],
        administrator_name="SSO Fresh E2E Administrator 02",
        domain=DOMAIN,
        contact_person="SSO Fresh E2E Contact 02",
        registered_phone="+91 80 0000 0002",
        registered_email=ADMINISTRATOR_EMAIL,
        address_line_1="1 Church Street",
        registered_city="Bengaluru",
        registered_state="Karnataka",
        postal_code="560001",
        registered_country="India",
    )

    print("PROVISION RESULT:", result)

    print(
        "TENANT STATE AFTER RUN:",
        frappe.db.get_value(
            "Clinify Tenant",
            {"tenant_code": TENANT_CODE},
            TENANT_FIELDS,
            as_dict=True,
        ),
    )

    return result

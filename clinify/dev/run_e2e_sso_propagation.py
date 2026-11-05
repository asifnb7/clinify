"""End-to-end check for tenant control-plane config propagation.

Exercises the real provisioning path (`provision_tenant`) against a throwaway
site so the crash-era behaviour of `after_sync` and the propagation of the
Clinify control-plane keys can be observed on a genuine new tenant.

Run:
    CLINIFY_E2E_ADMIN_PASSWORD=... bench --site clinify.localhost \
        execute clinify.dev.run_e2e_sso_propagation.run

It intentionally does not delete anything; the tenant is a throwaway.
"""

import os

import frappe

from clinify.saas.orchestrator import provision_tenant

TENANT_NAME = "SSO Propagation E2E 01"
TENANT_CODE = "SSO-PROP-E2E-01"
SITE_NAME = "sso-prop-e2e-01.localhost"
ADMINISTRATOR_EMAIL = "sso.prop.e2e01@example.com.invalid"
PLAN = "STARTER-MONTHLY"


def run():
    result = provision_tenant(
        tenant_name=TENANT_NAME,
        tenant_code=TENANT_CODE,
        site_name=SITE_NAME,
        administrator_email=ADMINISTRATOR_EMAIL,
        plan=PLAN,
        admin_password=os.environ["CLINIFY_E2E_ADMIN_PASSWORD"],
        administrator_name="SSO Propagation Administrator 01",
        domain=None,
        # `registered_country` is not `reqd` on Clinify Tenant, but the tenant
        # bootstrap needs it to build the ERPNext Company/Fiscal Year
        # foundation, and the plan currency is INR.
        contact_person="SSO Propagation Contact 01",
        registered_phone="+91 80 0000 0000",
        registered_email=ADMINISTRATOR_EMAIL,
        address_line_1="1 Church Street",
        registered_city="Bengaluru",
        registered_state="Karnataka",
        postal_code="560001",
        registered_country="India",
    )

    print(result)

    tenant = frappe.db.get_value(
        "Clinify Tenant",
        {"tenant_code": TENANT_CODE},
        ["name", "provisioning_status", "provisioning_error"],
        as_dict=True,
    )

    print("TENANT STATE AFTER RUN:", tenant)

    return result

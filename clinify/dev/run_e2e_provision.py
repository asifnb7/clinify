import os

import frappe

from clinify.saas.orchestrator import provision_tenant


def run():
    result = provision_tenant(
        tenant_name="Frontend E2E Starter Test 01",
        tenant_code="FRONTEND_E2E_STARTER_01",
        site_name="frontend-e2e-starter-01.localhost",
        administrator_email="frontend.e2e01@example.com.invalid",
        plan="STARTER-MONTHLY",
        admin_password=os.environ["CLINIFY_E2E_ADMIN_PASSWORD"],
        administrator_name="Frontend E2E Administrator 01",
        domain=None,
    )

    print(result)

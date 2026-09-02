import os

import frappe

from clinify.saas.orchestrator import provision_tenant


def run():
    result = provision_tenant(
        tenant_name="E2E Starter Test 04",
        tenant_code="E2E_STARTER_TEST_04",
        site_name="e2e-starter-test-04.localhost",
        administrator_email="e2e.starter04@example.com.invalid",
        plan="STARTER-MONTHLY",
        admin_password=os.environ["CLINIFY_E2E_ADMIN_PASSWORD"],
        administrator_name="E2E Starter Administrator 04",
        domain=None,
    )

    print(result)

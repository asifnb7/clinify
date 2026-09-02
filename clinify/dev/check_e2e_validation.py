import frappe

from clinify.saas.provisioning import validate_provision_request


def run():
    result = validate_provision_request(
        tenant_name="E2E Starter Test",
        tenant_code="E2E_STARTER_TEST",
        site_name="e2e-starter-test.localhost",
        administrator_email="e2e.starter@example.com.invalid",
        plan="STARTER-MONTHLY",
        domain=None,
    )

    print(result)

import frappe


def run():
    rows = frappe.get_all(
        "Clinify Tenant",
        filters={"tenant_code": "E2E_STARTER_TEST"},
        fields=[
            "name",
            "tenant_code",
            "site_name",
            "provisioning_status",
        ],
    )

    print(rows if rows else "NO EXISTING E2E_STARTER_TEST TENANT")

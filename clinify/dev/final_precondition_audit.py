import frappe
from pathlib import Path


def run():
    print("=" * 70)
    print("CLINIFY — CONTROL SITE FINAL PRECONDITION CHECK")
    print("=" * 70)

    print("\n--- AVAILABLE PLANS ---")
    plans = frappe.get_all(
        "Clinify Plan",
        fields=[
            "name",
            "plan_name",
            "plan_code",
            "plan_type",
            "billing_cycle",
            "price",
            "currency",
            "is_active",
        ],
        order_by="creation asc",
    )

    for plan in plans:
        print(plan)

    if not plans:
        print("NO CLINIFY PLANS FOUND")

    print("\n--- TENANT COUNT ---")
    print(frappe.db.count("Clinify Tenant"))

    print("\n--- EXISTING TEST SITE DIRECTORIES ---")
    sites_path = Path(frappe.get_site_path(".."))
    # Use the bench sites directory directly.
    bench_sites = Path(frappe.get_site_path()).parent

    for item in sorted(bench_sites.iterdir()):
        if item.is_dir():
            print(item.name)

    print("\n--- EXISTING CLINIFY TENANTS ---")
    tenants = frappe.get_all(
        "Clinify Tenant",
        fields=[
            "name",
            "tenant_name",
            "tenant_code",
            "site_name",
            "provisioning_status",
        ],
        order_by="creation asc",
    )

    for tenant in tenants:
        print(tenant)

    if not tenants:
        print("NO CLINIFY TENANTS")

    print("\n" + "=" * 70)
    print("FINAL PRECONDITION AUDIT COMPLETE")
    print("=" * 70)

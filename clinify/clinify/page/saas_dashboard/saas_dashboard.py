import frappe
from frappe.utils import add_days, getdate, today


@frappe.whitelist()
def get_dashboard():
    """
    Platform-level Clinify SaaS dashboard.

    The dashboard reads only the control-plane Clinify Tenant
    records. Tenant clinical databases are not queried.
    """

    if frappe.session.user == "Guest":
        frappe.throw(
            "SaaS Dashboard access requires authentication.",
            frappe.PermissionError,
        )

    if not frappe.db.exists(
        "Has Role",
        {
            "parent": frappe.session.user,
            "role": "System Manager",
            "parenttype": "User",
        },
    ):
        frappe.throw(
            "SaaS Dashboard is restricted to System Managers.",
            frappe.PermissionError,
        )

    today_date = getdate(today())
    expiry_limit = add_days(today_date, 30)

    total_clinics = frappe.db.count("Clinify Tenant")

    active_clinics = frappe.db.count(
        "Clinify Tenant",
        {
            "enabled": 1,
            "clinic_status": "Active",
        },
    )

    active_subscriptions = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabClinify Tenant`
        WHERE subscription_status IS NOT NULL
          AND subscription_status != ''
          AND subscription_end_date IS NOT NULL
          AND subscription_end_date >= %s
        """,
        (today_date,),
    )[0][0]

    trial_subscriptions = frappe.db.count(
        "Clinify Tenant",
        {
            "subscription_status": "Trial",
        },
    )

    expiring_30_days = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabClinify Tenant`
        WHERE enabled = 1
          AND subscription_end_date IS NOT NULL
          AND subscription_end_date >= %s
          AND subscription_end_date <= %s
        """,
        (today_date, expiry_limit),
    )[0][0]

    provisioning_pending = frappe.db.count(
        "Clinify Tenant",
        {
            "provisioning_status": "Pending",
        },
    )

    provisioning_failed = frappe.db.count(
        "Clinify Tenant",
        {
            "provisioning_status": "Failed",
        },
    )

    recent_tenants = frappe.get_all(
        "Clinify Tenant",
        fields=[
            "name",
            "tenant_id",
            "tenant_name",
            "site_name",
            "plan",
            "subscription_status",
            "subscription_end_date",
            "clinic_status",
            "provisioning_status",
        ],
        order_by="modified desc",
        limit_page_length=5,
    )

    return {
        "metrics": {
            "total_clinics": total_clinics,
            "active_clinics": active_clinics,
            "active_subscriptions": active_subscriptions,
            "trial_subscriptions": trial_subscriptions,
            "expiring_30_days": expiring_30_days,
            "provisioning_pending": provisioning_pending,
            "provisioning_failed": provisioning_failed,
        },
        "recent_tenants": recent_tenants,
    }

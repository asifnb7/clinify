import frappe
from frappe.utils import today

from clinify.saas.provisioning import (
    _clean,
    _validate_email,
    _validate_tenant_code,
)


CLINIFY_ADMIN_ROLE = "Clinify Clinic Admin"


ADMIN_PERMISSIONS = {
    "Clinic Configuration": {
        "read": 1,
        "write": 1,
        "create": 0,
        "delete": 0,
        "submit": 0,
        "cancel": 0,
        "amend": 0,
    },
    "Clinify Subscription": {
        "read": 1,
        "write": 1,
        "create": 0,
        "delete": 0,
        "submit": 0,
        "cancel": 0,
        "amend": 0,
    },
    "Dental Service": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "submit": 0,
        "cancel": 0,
        "amend": 0,
    },
    "Treatment Plan Template": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "submit": 0,
        "cancel": 0,
        "amend": 0,
    },
}


def _ensure_admin_role():
    if frappe.db.exists("Role", CLINIFY_ADMIN_ROLE):
        return CLINIFY_ADMIN_ROLE

    role = frappe.get_doc({
        "doctype": "Role",
        "role_name": CLINIFY_ADMIN_ROLE,
        "desk_access": 1,
        "is_custom": 1,
    })

    role.insert(ignore_permissions=True)
    frappe.db.commit()

    return role.name


def _ensure_admin_permissions():
    if not frappe.db.exists("Role", CLINIFY_ADMIN_ROLE):
        frappe.throw(
            "Required role does not exist: {}".format(
                CLINIFY_ADMIN_ROLE
            )
        )

    for doctype, permissions in ADMIN_PERMISSIONS.items():

        if not frappe.db.exists("DocType", doctype):
            continue

        existing = frappe.db.exists(
            "DocPerm",
            {
                "parent": doctype,
                "role": CLINIFY_ADMIN_ROLE,
                "permlevel": 0,
            },
        )

        if existing:
            docperm = frappe.get_doc("DocPerm", existing)

            for field, value in permissions.items():
                setattr(docperm, field, value)

            docperm.save(ignore_permissions=True)
            continue

        docperm = frappe.get_doc({
            "doctype": "DocPerm",
            "parent": doctype,
            "parenttype": "DocType",
            "parentfield": "permissions",
            "role": CLINIFY_ADMIN_ROLE,
            "permlevel": 0,
            **permissions,
        })

        docperm.insert(ignore_permissions=True)

    frappe.db.commit()


def _ensure_clinic_configuration(
    tenant_name,
    tenant_code,
    administrator_email,
    subscription_status,
):
    clinic = frappe.get_single("Clinic Configuration")

    clinic.clinic_name = tenant_name
    clinic.clinic_code = tenant_code
    clinic.clinic_email = administrator_email
    clinic.activation_date = clinic.activation_date or today()
    clinic.clinic_status = "Active"
    clinic.subscription_status = subscription_status

    clinic.save(ignore_permissions=True)
    frappe.db.commit()

    return clinic


def _ensure_plan(plan_definition):
    if not plan_definition:
        frappe.throw("Plan definition is required.")

    plan_code = _clean(plan_definition.get("plan_code")).upper()

    if not plan_code:
        frappe.throw("Plan code is required.")

    existing = frappe.db.exists(
        "Clinify Plan",
        {"plan_code": plan_code},
    )

    plan_data = {
        "plan_name": _clean(plan_definition.get("plan_name")),
        "plan_code": plan_code,
        "description": plan_definition.get("description"),
        "plan_type": plan_definition.get("plan_type"),
        "billing_cycle": plan_definition.get("billing_cycle"),
        "price": plan_definition.get("price"),
        "currency": plan_definition.get("currency"),
        "max_users": plan_definition.get("max_users"),
        "max_practitioners": plan_definition.get("max_practitioners"),
        "max_patients": plan_definition.get("max_patients"),
        "is_active": plan_definition.get("is_active"),
    }

    if not plan_data["plan_name"]:
        frappe.throw("Plan name is required.")

    if existing:
        plan = frappe.get_doc(
            "Clinify Plan",
            existing,
        )

        for field, value in plan_data.items():
            setattr(plan, field, value)

        plan.save(ignore_permissions=True)
    else:
        plan = frappe.get_doc({
            "doctype": "Clinify Plan",
            **plan_data,
        })

        plan.insert(ignore_permissions=True)

    frappe.db.commit()

    return plan


def _ensure_subscription(clinic, plan_code):
    plan_code = _clean(plan_code).upper()

    if not plan_code:
        frappe.throw("Plan is required.")

    existing = frappe.db.exists(
        "Clinify Subscription",
        {
            "clinic": clinic.name,
            "is_active": 1,
        },
    )

    if existing:
        subscription = frappe.get_doc(
            "Clinify Subscription",
            existing,
        )

        if subscription.plan != frappe.db.get_value(
            "Clinify Plan",
            {"plan_code": plan_code},
            "name",
        ):
            frappe.throw(
                "Active subscription already exists with a different plan."
            )

        return subscription

    plan = frappe.db.get_value(
        "Clinify Plan",
        {
            "plan_code": plan_code,
            "is_active": 1,
        },
        [
            "name",
            "plan_code",
            "plan_type",
            "billing_cycle",
            "price",
            "currency",
        ],
        as_dict=True,
    )

    if not plan:
        frappe.throw(
            "Active Clinify Plan was not found: {}".format(plan_code)
        )

    subscription_status = (
        "Trial"
        if plan.plan_type == "Trial"
        else "Active"
    )

    subscription = frappe.get_doc({
        "doctype": "Clinify Subscription",
        "clinic": clinic.name,
        "plan": plan.name,
        "subscription_status": subscription_status,
        "start_date": clinic.activation_date,
        "billing_cycle": plan.billing_cycle,
        "price": plan.price,
        "currency": plan.currency,
        "is_active": 1,
    })

    subscription.insert(ignore_permissions=True)
    frappe.db.commit()

    return subscription


def _ensure_admin_user(
    administrator_email,
    administrator_name=None,
):
    existing = frappe.db.exists(
        "User",
        administrator_email,
    )

    if existing:
        user = frappe.get_doc("User", existing)

        if not user.enabled:
            user.enabled = 1
            user.save(ignore_permissions=True)

        if not any(
            row.role == CLINIFY_ADMIN_ROLE
            for row in user.roles
        ):
            user.append(
                "roles",
                {
                    "doctype": "Has Role",
                    "role": CLINIFY_ADMIN_ROLE,
                },
            )
            user.save(ignore_permissions=True)

        frappe.db.commit()
        return user

    name_parts = (administrator_name or "Clinify Administrator").split(
        None,
        1,
    )

    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    user = frappe.get_doc({
        "doctype": "User",
        "email": administrator_email,
        "first_name": first_name,
        "last_name": last_name,
        "enabled": 1,
        "user_type": "System User",
        "send_welcome_email": 0,
        "roles": [
            {
                "doctype": "Has Role",
                "role": CLINIFY_ADMIN_ROLE,
            }
        ],
    })

    user.insert(ignore_permissions=True)
    frappe.db.commit()

    return user


def bootstrap_tenant(
    tenant_name,
    tenant_code,
    administrator_email,
    administrator_name=None,
    plan=None,
    plan_definition=None,
):
    """
    Bootstrap a newly-created Clinify tenant site.

    This function runs INSIDE the tenant site.

    Validation is performed before any provisioning mutation.
    """

    tenant_name = _clean(tenant_name)

    if not tenant_name:
        frappe.throw("Tenant Name is required.")

    if len(tenant_name) > 140:
        frappe.throw("Tenant Name must not exceed 140 characters.")

    tenant_code = _validate_tenant_code(tenant_code)
    administrator_email = _validate_email(administrator_email)

    _ensure_admin_role()
    _ensure_admin_permissions()

    plan_code = _clean(plan).upper()

    if not plan_code:
        frappe.throw("Plan is required.")

    if not plan_definition:
        frappe.throw("Plan definition is required.")

    plan_type = _clean(plan_definition.get("plan_type"))

    subscription_status = (
        "Trial"
        if plan_type == "Trial"
        else "Active"
    )

    clinic = _ensure_clinic_configuration(
        tenant_name=tenant_name,
        tenant_code=tenant_code,
        administrator_email=administrator_email,
        subscription_status=subscription_status,
    )

    local_plan = _ensure_plan(plan_definition)

    if local_plan.plan_code != plan_code:
        frappe.throw(
            "Plan definition does not match requested plan: {}".format(
                plan_code
            )
        )

    subscription = _ensure_subscription(
        clinic=clinic,
        plan_code=plan_code,
    )

    administrator = _ensure_admin_user(
        administrator_email=administrator_email,
        administrator_name=administrator_name,
    )

    verification = verify_tenant(
        tenant_code=tenant_code,
        administrator_email=administrator_email,
    )

    frappe.db.commit()

    return {
        "success": True,
        "clinic": clinic.name,
        "subscription": subscription.name,
        "administrator": administrator.name,
        "verification": verification,
    }


def verify_tenant(
    tenant_code,
    administrator_email,
):
    """
    Verify the complete Clinify tenant bootstrap state.

    This function runs inside the tenant site and is read-only.
    """

    tenant_code = _validate_tenant_code(tenant_code)
    administrator_email = _validate_email(administrator_email)

    clinic = frappe.get_single("Clinic Configuration")

    if clinic.clinic_code != tenant_code:
        frappe.throw(
            "Clinic Code mismatch: expected {}, found {}".format(
                tenant_code,
                clinic.clinic_code,
            )
        )

    subscription = frappe.db.get_value(
        "Clinify Subscription",
        {
            "clinic": "Clinic Configuration",
            "is_active": 1,
        },
        [
            "name",
            "plan",
            "subscription_status",
            "start_date",
            "billing_cycle",
            "price",
            "currency",
            "is_active",
        ],
        as_dict=True,
    )

    if not subscription:
        frappe.throw("No active Clinify Subscription found.")

    administrator = frappe.db.get_value(
        "User",
        administrator_email,
        [
            "name",
            "email",
            "enabled",
            "user_type",
        ],
        as_dict=True,
    )

    if not administrator:
        frappe.throw(
            "Administrator does not exist: {}".format(
                administrator_email
            )
        )

    admin_role = frappe.db.exists(
        "Has Role",
        {
            "parent": administrator_email,
            "role": CLINIFY_ADMIN_ROLE,
        },
    )

    if not admin_role:
        frappe.throw(
            "Administrator is missing role: {}".format(
                CLINIFY_ADMIN_ROLE
            )
        )

    checks = {
        "clinic_configuration": True,
        "clinic_code": clinic.clinic_code == tenant_code,
        "clinic_active": clinic.clinic_status == "Active",
        "subscription": True,
        "subscription_active": bool(subscription.is_active),
        "administrator": True,
        "administrator_enabled": bool(administrator.enabled),
        "administrator_system_user": (
            administrator.user_type == "System User"
        ),
        "admin_role": True,
    }

    if not all(checks.values()):
        frappe.throw(
            "Tenant verification failed: {}".format(checks)
        )

    return {
        "verified": True,
        "checks": checks,
        "clinic": clinic.name,
        "clinic_code": clinic.clinic_code,
        "subscription": subscription,
        "administrator": administrator.name,
        "admin_role": CLINIFY_ADMIN_ROLE,
    }

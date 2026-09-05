"""Control-site identities required by Clinify's tenant SSO handoff."""

import frappe

from clinify.saas.provisioning import _validate_email


CLINIFY_CONTROL_USER_ROLE = "Clinify Control User"


def _ensure_control_user_role():
    """Provide the minimal desk-access role required for a System User."""

    existing = frappe.db.exists("Role", CLINIFY_CONTROL_USER_ROLE)

    if existing:
        role = frappe.get_doc("Role", existing)
        changed = False

        if not role.desk_access:
            role.desk_access = 1
            changed = True

        if not role.is_custom:
            role.is_custom = 1
            changed = True

        if changed:
            role.save(ignore_permissions=True)
            frappe.db.commit()

        return role

    role = frappe.get_doc(
        {
            "doctype": "Role",
            "role_name": CLINIFY_CONTROL_USER_ROLE,
            "desk_access": 1,
            "is_custom": 1,
        }
    )
    role.insert(ignore_permissions=True)
    frappe.db.commit()
    return role


def _tenant_names_for_email(administrator_email):
    tenants = frappe.get_all(
        "Clinify Tenant",
        filters={"administrator_email": administrator_email},
        fields=["name"],
    )
    return [
        tenant["name"]
        if isinstance(tenant, dict)
        else tenant.name
        for tenant in tenants
    ]


def _ensure_exact_tenant_mapping(tenant, administrator_email):
    """Reject an email that could send a control user to another tenant."""

    tenant_names = _tenant_names_for_email(administrator_email)

    if len(tenant_names) != 1 or tenant_names[0] != tenant.name:
        raise RuntimeError(
            "Administrator email must map to exactly this Clinify Tenant."
        )


def _control_user_for_email(administrator_email):
    users = frappe.get_all(
        "User",
        filters={"email": administrator_email},
        fields=["name", "email", "enabled", "user_type"],
    )

    if len(users) > 1:
        raise RuntimeError(
            "Administrator email belongs to multiple control-site users."
        )

    if not users:
        return None

    user = users[0]
    user_name = user["name"] if isinstance(user, dict) else user.name

    # User names are login identities in Frappe.  Do not take over a User
    # whose email happens to match this provisioning request.
    if user_name != administrator_email:
        raise RuntimeError(
            "Administrator email belongs to a different control-site user."
        )

    return frappe.get_doc("User", user_name)


def _name_parts(administrator_name):
    parts = (administrator_name or "Clinify Administrator").split(None, 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def validate_control_site_administrator(tenant, administrator_email):
    """Validate the tenant-to-control-user identity binding without mutation."""

    administrator_email = _validate_email(administrator_email)
    _ensure_exact_tenant_mapping(tenant, administrator_email)
    user = _control_user_for_email(administrator_email)

    if user and user.user_type != "System User":
        raise RuntimeError(
            "Administrator email belongs to a non-System control-site user."
        )

    return user


def ensure_control_site_administrator(
    tenant,
    administrator_email,
    administrator_name,
    admin_password,
):
    """Ensure the SSO login identity for one already-created tenant.

    ``admin_password`` is consumed only when creating a new Frappe User.
    It is deliberately not copied to a Clinify control-plane document.
    Existing users retain their password on provisioning retries.
    """

    if not admin_password:
        raise RuntimeError("Administrator password is required.")

    administrator_email = _validate_email(administrator_email)
    user = validate_control_site_administrator(
        tenant,
        administrator_email,
    )

    if user:
        if not user.enabled:
            user.enabled = 1
            user.save(ignore_permissions=True)
            frappe.db.commit()

        return user

    _ensure_control_user_role()
    first_name, last_name = _name_parts(administrator_name)
    user = frappe.get_doc(
        {
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
                    "role": CLINIFY_CONTROL_USER_ROLE,
                }
            ],
            # Frappe stores only its password hash in __Auth.  This transient
            # field is not a Clinify Tenant or other control-plane field.
            "new_password": admin_password,
        }
    )
    user.insert(ignore_permissions=True)
    frappe.db.commit()
    return user

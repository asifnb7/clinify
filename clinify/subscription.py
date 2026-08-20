import frappe

from clinify.clinic import get_current_clinic


ALLOWED_SUBSCRIPTION_STATUSES = {
    "Trial",
    "Active",
}


def get_current_subscription():
    """
    Return the current active Clinify Subscription
    for the current clinic.

    The subscription is selected using:

    1. Current Clinic Configuration
    2. is_active = 1

    If multiple active subscriptions exist,
    the most recently created subscription is returned.
    """

    clinic = get_current_clinic()

    subscription_name = frappe.db.get_value(
        "Clinify Subscription",
        {
            "clinic": clinic.name,
            "is_active": 1,
        },
        "name",
        order_by="creation desc",
    )

    if not subscription_name:
        return None

    return frappe.get_doc(
        "Clinify Subscription",
        subscription_name,
    )


def get_current_subscription_doc():
    """
    Return the current Clinify Subscription document.

    This is an explicit alias intended for lifecycle
    operations and future service code.
    """

    return get_current_subscription()


def get_subscription_state():
    """
    Return the current subscription state.

    Clinify Subscription is the subscription
    source of truth.
    """

    subscription = get_current_subscription()

    if not subscription:
        return {
            "subscription_exists": False,
            "subscription_status": None,
            "start_date": None,
            "end_date": None,
            "is_active": False,
        }

    return {
        "subscription_exists": True,
        "subscription_status": subscription.subscription_status,
        "start_date": subscription.start_date,
        "end_date": subscription.end_date,
        "is_active": bool(subscription.is_active),
    }


def is_subscription_active():
    """
    Return True when the current subscription
    permits Clinify access.

    Allowed statuses:

    - Trial
    - Active
    """

    subscription = get_current_subscription()

    if not subscription:
        return False

    if not subscription.is_active:
        return False

    return (
        subscription.subscription_status
        in ALLOWED_SUBSCRIPTION_STATUSES
    )


def can_access_clinify():
    """
    Return True only when:

    1. The clinic itself is Active.
    2. A current subscription exists.
    3. The subscription record is active.
    4. The subscription status permits access.
    """

    clinic = get_current_clinic()

    if clinic.clinic_status != "Active":
        return False

    return is_subscription_active()


def get_subscription_summary():
    """
    Return the complete current subscription summary.

    Intended for future SaaS dashboards,
    APIs, administration screens, and billing logic.
    """

    subscription = get_current_subscription()

    if not subscription:
        return {
            "subscription_exists": False,
            "subscription": None,
            "plan": None,
            "plan_name": None,
            "subscription_status": None,
            "start_date": None,
            "end_date": None,
            "billing_cycle": None,
            "price": None,
            "currency": None,
            "is_active": False,
        }

    plan_name = frappe.db.get_value(
        "Clinify Plan",
        subscription.plan,
        "plan_name",
    )

    return {
        "subscription_exists": True,
        "subscription": subscription.name,
        "plan": subscription.plan,
        "plan_name": plan_name,
        "subscription_status": subscription.subscription_status,
        "start_date": subscription.start_date,
        "end_date": subscription.end_date,
        "billing_cycle": subscription.billing_cycle,
        "price": subscription.price,
        "currency": subscription.currency,
        "is_active": bool(subscription.is_active),
    }


def get_access_status():
    """
    Return the complete Clinify access decision.

    This preserves compatibility with the existing
    clinify.access service.
    """

    clinic = get_current_clinic()

    subscription_active = is_subscription_active()

    clinic_active = (
        clinic.clinic_status == "Active"
    )

    access_allowed = (
        clinic_active
        and subscription_active
    )

    subscription_summary = get_subscription_summary()

    return {
        "clinic_active": clinic_active,
        "subscription_active": subscription_active,
        "access_allowed": access_allowed,
        "clinic_status": clinic.clinic_status,
        "subscription_status": (
            subscription_summary["subscription_status"]
        ),
        "activation_date": clinic.activation_date,
        "subscription": subscription_summary,
    }


def _require_current_subscription():
    """
    Return the current subscription.

    Raises a validation error when no active
    subscription record exists for the clinic.
    """

    subscription = get_current_subscription()

    if not subscription:
        frappe.throw(
            "No active Clinify Subscription exists "
            "for the current clinic."
        )

    return subscription


def activate_subscription():
    """
    Activate the current subscription.

    This changes the subscription status to Active
    and ensures the subscription record is active.
    """

    subscription = _require_current_subscription()

    subscription.subscription_status = "Active"
    subscription.is_active = 1

    subscription.save(
        ignore_permissions=True
    )

    frappe.db.commit()

    return get_subscription_summary()


def expire_subscription():
    """
    Mark the current subscription as Expired.

    The record remains active so that the current
    subscription state remains discoverable, but
    Clinify access is denied because Expired does
    not permit access.
    """

    subscription = _require_current_subscription()

    subscription.subscription_status = "Expired"
    subscription.is_active = 1

    subscription.save(
        ignore_permissions=True
    )

    frappe.db.commit()

    return get_subscription_summary()


def suspend_subscription():
    """
    Suspend the current subscription.

    The subscription record remains the current
    record, but Clinify access is denied.
    """

    subscription = _require_current_subscription()

    subscription.subscription_status = "Suspended"
    subscription.is_active = 1

    subscription.save(
        ignore_permissions=True
    )

    frappe.db.commit()

    return get_subscription_summary()


def cancel_subscription():
    """
    Cancel the current subscription.

    A cancelled subscription is no longer considered
    the current active subscription.

    The record is preserved for subscription history.
    """

    subscription = _require_current_subscription()

    subscription.subscription_status = "Cancelled"
    subscription.is_active = 0

    subscription.save(
        ignore_permissions=True
    )

    frappe.db.commit()

    return {
        "subscription": subscription.name,
        "subscription_status": subscription.subscription_status,
        "is_active": bool(subscription.is_active),
    }


def change_subscription_plan(plan_name):
    """
    Change the plan of the current subscription.

    The supplied plan must:

    1. Exist.
    2. Be active.

    The billing cycle, price, and currency are copied
    from the selected Clinify Plan.
    """

    subscription = _require_current_subscription()

    plan = frappe.get_doc(
        "Clinify Plan",
        plan_name,
    )

    if not plan.is_active:
        frappe.throw(
            f"Clinify Plan '{plan.name}' is inactive."
        )

    subscription.plan = plan.name
    subscription.billing_cycle = plan.billing_cycle
    subscription.price = plan.price
    subscription.currency = plan.currency

    subscription.save(
        ignore_permissions=True
    )

    frappe.db.commit()

    return get_subscription_summary()

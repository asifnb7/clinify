import frappe
from frappe import _
from frappe.model.document import Document


class ClinifySubscription(Document):
    def validate(self):
        self.validate_clinic()
        self.validate_plan()
        self.validate_dates()
        self.populate_plan_snapshot()
        self.validate_single_active_subscription()

    def validate_clinic(self):
        if not self.clinic:
            frappe.throw(
                _("Clinic is required.")
            )

    def validate_plan(self):
        if not self.plan:
            frappe.throw(
                _("Clinify Plan is required.")
            )

        if not frappe.db.exists(
            "Clinify Plan",
            self.plan
        ):
            frappe.throw(
                _("Selected Clinify Plan does not exist.")
            )

        plan_is_active = frappe.db.get_value(
            "Clinify Plan",
            self.plan,
            "is_active",
        )

        if not plan_is_active:
            frappe.throw(
                _("Selected Clinify Plan is inactive.")
            )

    def validate_dates(self):
        if (
            self.start_date
            and self.end_date
            and self.end_date < self.start_date
        ):
            frappe.throw(
                _("End Date cannot be before Start Date.")
            )

    def has_plan_changed(self):
        """
        Return True when this is a new subscription or
        when the selected plan has changed.
        """

        if self.is_new():
            return True

        previous_plan = frappe.db.get_value(
            "Clinify Subscription",
            self.name,
            "plan",
        )

        return previous_plan != self.plan

    def populate_plan_snapshot(self):
        """
        Snapshot commercial values from the selected plan.

        Values are copied when:

        1. A new subscription is created.
        2. The subscription is changed to another plan.

        If the plan remains unchanged, the stored values are
        preserved so historical subscription pricing is retained.
        """

        if not self.has_plan_changed():
            return

        plan = frappe.get_doc(
            "Clinify Plan",
            self.plan,
        )

        self.billing_cycle = plan.billing_cycle
        self.price = plan.price
        self.currency = plan.currency

    def validate_single_active_subscription(self):
        """
        Ensure that only one active subscription exists
        for a clinic.

        The current document is excluded when updating
        an existing subscription.
        """

        if not self.is_active:
            return

        existing_subscription = frappe.db.get_value(
            "Clinify Subscription",
            {
                "clinic": self.clinic,
                "is_active": 1,
                "name": ["!=", self.name or ""],
            },
            "name",
        )

        if existing_subscription:
            frappe.throw(
                _(
                    "Clinic already has an active "
                    "Clinify Subscription: {0}"
                ).format(existing_subscription)
            )

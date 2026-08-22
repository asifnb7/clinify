import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class ClinifySubscription(Document):
    def autoname(self):
        """
        Generate a readable subscription ID.

        Format:

        {CLINIC-CODE}-SUB-0001

        Examples:

        CLINIFY-DEMO-SUB-0001
        ABC-CLINIC-SUB-0002

        This allows multiple historical subscriptions
        for the same clinic without naming conflicts.
        """

        if not self.clinic:
            frappe.throw(
                _("Clinic is required before naming the subscription.")
            )

        clinic = frappe.get_single(
            "Clinic Configuration"
        )

        clinic_code = clinic.clinic_code

        if not clinic_code:
            frappe.throw(
                _(
                    "Clinic Code is required to create "
                    "a Clinify Subscription."
                )
            )

        clinic_code = frappe.scrub(
            clinic_code
        ).upper().replace("_", "-")

        self.name = make_autoname(
            f"{clinic_code}-SUB-.####"
        )

    def validate(self):
        self.validate_clinic()
        self.validate_plan()
        self.validate_dates()
        self.populate_plan_snapshot()
        self.validate_single_active_subscription()

    def on_update(self):
        """
        Synchronize the mirrored clinic lifecycle state
        after a Clinify Subscription is saved.

        Clinify Subscription remains the lifecycle
        source of truth. The synchronization rules live
        centrally in clinify.subscription.
        """

        from clinify.subscription import _sync_clinic_lifecycle

        _sync_clinic_lifecycle(self)

    def validate_clinic(self):
        """
        Clinify currently operates with one clinic per site.

        Clinic Configuration is a Single DocType, so the
        subscription stores its fixed identity rather than
        using a database Link.
        """

        if not self.clinic:
            self.clinic = "Clinic Configuration"

        if self.clinic != "Clinic Configuration":
            frappe.throw(
                _("Invalid clinic identity.")
            )

    def validate_plan(self):
        if not self.plan:
            frappe.throw(
                _("Clinify Plan is required.")
            )

        if not frappe.db.exists(
            "Clinify Plan",
            self.plan,
        ):
            frappe.throw(
                _("Selected Clinify Plan does not exist.")
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

    def populate_plan_snapshot(self):
        """
        Copy commercial values from the selected plan
        into the subscription.

        The subscription stores its own snapshot so that
        future changes to a Clinify Plan do not alter
        historical subscriptions.
        """

        if not self.plan:
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
        Ensure that a clinic can have only one
        active subscription record at a time.

        Historical subscriptions may remain in the system
        with is_active = 0.
        """

        if not self.clinic:
            return

        if not self.is_active:
            return

        existing_subscription = frappe.db.get_value(
            "Clinify Subscription",
            {
                "clinic": self.clinic,
                "is_active": 1,
                "name": ["!=", self.name],
            },
            "name",
        )

        if existing_subscription:
            frappe.throw(
                _(
                    "Clinic already has an active "
                    "Clinify Subscription: {0}"
                ).format(
                    existing_subscription
                )
            )

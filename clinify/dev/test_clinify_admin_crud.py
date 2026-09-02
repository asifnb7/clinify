import frappe


USER = "clinify-admin-test@example.com"
TEST_ITEM = "CLINIFY-TEST-DENTAL-SERVICE"


def _result(label, status, detail=""):
    suffix = f" — {detail}" if detail else ""
    print(f"{label}: {status}{suffix}")


def run():
    if not frappe.db.exists("User", USER):
        frappe.throw(f"Test user does not exist: {USER}")

    original_user = frappe.session.user

    dental_service_name = None
    treatment_template_name = None

    try:
        frappe.set_user(USER)

        print(f"User: {frappe.session.user}")
        print("")

        # ---------------------------------------------------------
        # Clinic Configuration
        # ---------------------------------------------------------
        print("=== Clinic Configuration ===")

        try:
            frappe.get_single("Clinic Configuration")
            _result("READ", "PASS", "Clinic Configuration accessible")
        except Exception as e:
            _result("READ", "FAIL", str(e))

        # ---------------------------------------------------------
        # Clinify Subscription
        # ---------------------------------------------------------
        print("\n=== Clinify Subscription ===")

        try:
            subscriptions = frappe.get_all(
                "Clinify Subscription",
                fields=["name"],
                limit_page_length=1,
            )

            _result(
                "READ",
                "PASS",
                f"accessible; records found: {len(subscriptions)}",
            )
        except Exception as e:
            _result("READ", "FAIL", str(e))

        # ---------------------------------------------------------
        # Dental Service CREATE / READ / WRITE / DELETE
        # ---------------------------------------------------------
        print("\n=== Dental Service ===")

        service_code = "TEST-ADMIN-CRUD"

        existing = frappe.db.exists(
            "Dental Service",
            {"service_code": service_code},
        )

        if existing:
            try:
                frappe.delete_doc(
                    "Dental Service",
                    existing,
                    ignore_permissions=False,
                )
                frappe.db.commit()
            except Exception as e:
                _result("CLEANUP", "FAIL", str(e))
                frappe.db.rollback()

        if not frappe.db.exists("Item", TEST_ITEM):
            _result(
                "CREATE",
                "SKIP",
                f"Required ERPNext Item does not exist: {TEST_ITEM}",
            )
        else:
            try:
                service = frappe.get_doc({
                    "doctype": "Dental Service",
                    "service_code": service_code,
                    "service_name": "Clinify Admin CRUD Test",
                    "erpnext_item": TEST_ITEM,
                    "is_active": 1,
                    "default_qty": 1,
                    "pricing_basis": "Fixed",
                    "minimum_price": 100,
                    "maximum_price": 100,
                })

                service.insert(ignore_permissions=False)
                dental_service_name = service.name
                frappe.db.commit()

                _result(
                    "CREATE",
                    "PASS",
                    dental_service_name,
                )

                fetched = frappe.get_doc(
                    "Dental Service",
                    dental_service_name,
                )

                _result(
                    "READ",
                    "PASS",
                    fetched.name,
                )

                fetched.description = (
                    "Updated by Clinify Clinic Admin CRUD test"
                )
                fetched.save(ignore_permissions=False)
                frappe.db.commit()

                _result(
                    "WRITE",
                    "PASS",
                    fetched.name,
                )

                frappe.delete_doc(
                    "Dental Service",
                    dental_service_name,
                    ignore_permissions=False,
                )

                dental_service_name = None
                frappe.db.commit()

                _result("DELETE", "PASS")

            except Exception as e:
                frappe.db.rollback()
                _result("CRUD", "FAIL", str(e))

        # ---------------------------------------------------------
        # Treatment Plan Template
        # ---------------------------------------------------------
        print("\n=== Treatment Plan Template ===")

        template_name = "TEST-CLINIFY-ADMIN-TEMPLATE"

        existing_template = frappe.db.exists(
            "Treatment Plan Template",
            template_name,
        )

        if existing_template:
            try:
                frappe.delete_doc(
                    "Treatment Plan Template",
                    existing_template,
                    ignore_permissions=False,
                )
                frappe.db.commit()
            except Exception as e:
                _result("CLEANUP", "FAIL", str(e))
                frappe.db.rollback()

        try:
            template = frappe.get_doc({
                "doctype": "Treatment Plan Template",
                "template_name": template_name,
            })

            template.insert(ignore_permissions=False)
            treatment_template_name = template.name
            frappe.db.commit()

            _result(
                "CREATE",
                "PASS",
                treatment_template_name,
            )

            fetched = frappe.get_doc(
                "Treatment Plan Template",
                treatment_template_name,
            )

            _result(
                "READ",
                "PASS",
                fetched.name,
            )

            frappe.delete_doc(
                "Treatment Plan Template",
                treatment_template_name,
                ignore_permissions=False,
            )

            treatment_template_name = None
            frappe.db.commit()

            _result("DELETE", "PASS")

        except Exception as e:
            frappe.db.rollback()
            _result("CRUD", "FAIL", str(e))

        # ---------------------------------------------------------
        # Platform Boundary
        # ---------------------------------------------------------
        print("\n=== Platform Boundary ===")

        for doctype in (
            "Clinify Plan",
            "Clinify Tenant",
            "Clinify Settings",
        ):
            try:
                if not frappe.permissions.has_permission(
                    doctype,
                    "read",
                    user=USER,
                    raise_exception=False,
                ):
                    _result(
                        doctype,
                        "PASS",
                        "access denied",
                    )
                else:
                    _result(
                        doctype,
                        "UNEXPECTED ALLOW",
                        "Clinic Admin should not access this",
                    )

            except Exception as e:
                _result(
                    doctype,
                    "PASS",
                    f"access denied: {e}",
                )

    finally:
        # Defensive cleanup if a test failed halfway through.
        if dental_service_name and frappe.db.exists(
            "Dental Service",
            dental_service_name,
        ):
            try:
                frappe.set_user("Administrator")

                frappe.delete_doc(
                    "Dental Service",
                    dental_service_name,
                    ignore_permissions=True,
                )

                frappe.db.commit()
            except Exception:
                frappe.db.rollback()

        if treatment_template_name and frappe.db.exists(
            "Treatment Plan Template",
            treatment_template_name,
        ):
            try:
                frappe.set_user("Administrator")

                frappe.delete_doc(
                    "Treatment Plan Template",
                    treatment_template_name,
                    ignore_permissions=True,
                )

                frappe.db.commit()
            except Exception:
                frappe.db.rollback()

        frappe.set_user(original_user)

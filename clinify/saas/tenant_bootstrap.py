import frappe
from frappe.utils import add_to_date, now_datetime, today

from erpnext.setup.setup_wizard.operations import install_fixtures as erpnext_fixtures
from frappe.utils.fixtures import sync_fixtures

from clinify.saas.provisioning import (
    _clean,
    _validate_email,
    _validate_tenant_code,
)


CLINIFY_ADMIN_ROLE = "Clinify Clinic Admin"


ADMIN_PERMISSIONS = {
    "Patient": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Appointment": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Patient Appointment": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Page": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
    },
    "Healthcare Practitioner": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Patient Encounter": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 1, "cancel": 1, "amend": 1,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Vital Signs": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 1, "cancel": 1, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Clinical Procedure Template": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Lab Test Template": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Observation Template": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Medication": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Dosage Form": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Prescription Dosage": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Prescription Duration": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "UOM": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Patient Care Type": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Therapy Plan": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Therapy Type": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Complaint": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Diagnosis": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Code System": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Code Value": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Inpatient Record": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Clinical Procedure": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 1, "cancel": 1, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Lab Test": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 1, "cancel": 1, "amend": 1,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Medication Request": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Sales Invoice": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 1, "cancel": 1, "amend": 1,
        "report": 1, "export": 0, "print": 1,
        "email": 1, "share": 1,
    },
    "Payment Entry": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 1, "cancel": 1, "amend": 1,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Item": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Company": {
        "read": 1, "write": 1, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1,
        "email": 1, "share": 1,
    },
    "Clinic Configuration": {
        "read": 1, "write": 1, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
    },
    "Clinify Subscription": {
        "read": 0, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
    },
    "Dental Service": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
    },
    "Treatment Plan Template": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
    },
    "Appointment Type": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
    },
    "Medical Department": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
    },
    "Healthcare Settings": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
    },
    "Practitioner Schedule": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
    },
    "Healthcare Service Unit": {
        "read": 1, "write": 0, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
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

        # If a DocType has any Custom DocPerm records, Frappe uses
        # those records instead of the standard DocType permissions.
        # Preserve that permission model and add/update Clinic Admin
        # as a Custom DocPerm without modifying other roles.
        has_custom_permissions = frappe.db.exists(
            "Custom DocPerm",
            {
                "parent": doctype,
            },
        )

        permission_doctype = (
            "Custom DocPerm"
            if has_custom_permissions
            else "DocPerm"
        )

        existing = frappe.db.exists(
            permission_doctype,
            {
                "parent": doctype,
                "role": CLINIFY_ADMIN_ROLE,
                "permlevel": 0,
            },
        )

        if existing:
            docperm = frappe.get_doc(permission_doctype, existing)
            changed = False

            for field, value in permissions.items():
                if getattr(docperm, field) != value:
                    setattr(docperm, field, value)
                    changed = True

            if changed:
                docperm.save(ignore_permissions=True)
            continue

        docperm_data = {
            "doctype": permission_doctype,
            "parent": doctype,
            "role": CLINIFY_ADMIN_ROLE,
            "permlevel": 0,
            **permissions,
        }

        if permission_doctype == "DocPerm":
            docperm_data.update({
                "parenttype": "DocType",
                "parentfield": "permissions",
            })

        docperm = frappe.get_doc(docperm_data)
        docperm.insert(ignore_permissions=True)

    frappe.db.commit()

def _ensure_gender_master_data():
    """Ensure the standard gender masters required by Healthcare are available."""
    if not frappe.db.exists("DocType", "Gender"):
        return

    for gender in ("MALE", "FEMALE"):
        if not frappe.db.exists("Gender", gender):
            frappe.get_doc({
                "doctype": "Gender",
                "gender": gender,
            }).insert(ignore_permissions=True)

    frappe.db.commit()


def _ensure_clinic_configuration(
    tenant_name,
    tenant_code,
    administrator_email,
    subscription_status,
    contact_person=None,
    registered_phone=None,
    registered_email=None,
    address_line_1=None,
    address_line_2=None,
    registered_city=None,
    registered_state=None,
    postal_code=None,
    registered_country=None,
    subscription_end_date=None,
):
    clinic = frappe.get_single("Clinic Configuration")

    clinic.clinic_name = tenant_name
    clinic.clinic_code = tenant_code

    # Registered clinic contact information is authoritative
    # from the control-plane Clinify Tenant during provisioning.
    clinic.contact_person = _clean(contact_person)
    clinic.clinic_phone = _clean(registered_phone)
    clinic.clinic_email = _clean(registered_email) or administrator_email

    address_lines = [
        _clean(address_line_1),
        _clean(address_line_2),
    ]
    clinic.clinic_address = "\n".join(
        line for line in address_lines if line
    )

    clinic.city = _clean(registered_city)
    clinic.state = _clean(registered_state)
    clinic.pincode = _clean(postal_code)
    clinic.country = _clean(registered_country)

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


def _ensure_subscription(clinic, plan_code, subscription_end_date=None):
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

    start_date = clinic.activation_date
    billing_cycle = _clean(plan.billing_cycle)

    if billing_cycle == "Monthly":
        calculated_end_date = add_to_date(start_date, months=1, days=-1)
    elif billing_cycle == "Quarterly":
        calculated_end_date = add_to_date(start_date, months=3, days=-1)
    elif billing_cycle == "Yearly":
        calculated_end_date = add_to_date(start_date, years=1, days=-1)
    else:
        frappe.throw(
            "Unsupported billing cycle: {}".format(
                billing_cycle
            )
        )

    if subscription_end_date:
        subscription_end_date = frappe.utils.getdate(subscription_end_date)
    end_date = subscription_end_date or calculated_end_date
    if end_date < start_date:
        frappe.throw("Subscription end date cannot be before the subscription start date.")

    subscription = frappe.get_doc({
        "doctype": "Clinify Subscription",
        "clinic": clinic.name,
        "plan": plan.name,
        "subscription_status": subscription_status,
        "start_date": start_date,
        "end_date": end_date,
        "billing_cycle": billing_cycle,
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



def _ensure_erpnext_foundation_fixtures():
    """Ensure the minimal ERPNext foundation records required by Company/Healthcare."""
    from frappe.desk.page.setup_wizard.setup_wizard import make_records
    from erpnext.setup.setup_wizard.operations.install_fixtures import add_sale_stages

    foundation_records = [
        {
            "doctype": "Item Group",
            "item_group_name": "Products",
            "is_group": 0,
            "parent_item_group": "All Item Groups",
        },
        {
            "doctype": "Item Group",
            "item_group_name": "Services",
            "is_group": 0,
            "parent_item_group": "All Item Groups",
        },
        {
            "doctype": "Warehouse Type",
            "name": "Transit",
        },
        {
            "doctype": "Supplier Group",
            "supplier_group_name": "All Supplier Groups",
            "is_group": 1,
        },
        {
            "doctype": "Customer Group",
            "customer_group_name": "All Customer Groups",
            "is_group": 1,
        },
        {
            "doctype": "Sales Person",
            "sales_person_name": "Sales Team",
            "is_group": 1,
            "parent_sales_person": "",
        },
        {
            "doctype": "Territory",
            "name": "All Territories",
            "territory_name": "All Territories",
            "is_group": 1,
            "parent_territory": "",
        },
    ]

    for record in foundation_records:
        doctype = record["doctype"]

        if doctype == "Warehouse Type":
            exists = frappe.db.exists(doctype, record["name"])
        elif doctype == "Item Group":
            exists = frappe.db.exists(doctype, record["item_group_name"])
        elif doctype == "Supplier Group":
            exists = frappe.db.exists(doctype, record["supplier_group_name"])
        elif doctype == "Customer Group":
            exists = frappe.db.exists(doctype, record["customer_group_name"])
        elif doctype == "Sales Person":
            exists = frappe.db.exists(doctype, record["sales_person_name"])
        elif doctype == "Territory":
            exists = frappe.db.exists(doctype, record["name"])
        else:
            exists = False

        if not exists:
            make_records([record])

    # ERPNext's standard setup wizard also supplies the standard Stock Entry
    # Types. Fresh tenant provisioning does not run the broad ERPNext fixture
    # installer, so create only these required standard masters here.
    stock_entry_types = [
        ("Material Issue", "Material Issue"),
        ("Material Receipt", "Material Receipt"),
        ("Material Transfer", "Material Transfer"),
        ("Manufacture", "Manufacture"),
        ("Repack", "Repack"),
        ("Disassemble", "Disassemble"),
        ("Send to Subcontractor", "Send to Subcontractor"),
        ("Material Transfer for Manufacture", "Material Transfer for Manufacture"),
        ("Material Consumption for Manufacture", "Material Consumption for Manufacture"),
    ]

    for name, purpose in stock_entry_types:
        if not frappe.db.exists("Stock Entry Type", name):
            frappe.get_doc(
                {
                    "doctype": "Stock Entry Type",
                    "name": name,
                    "purpose": purpose,
                    "is_standard": 1,
                }
            ).insert(ignore_permissions=True)

    # ERPNext's standard setup wizard also supplies the standard Party Type
    # account mappings. Fresh tenant provisioning intentionally avoids the
    # broad ERPNext fixture installer, so create only these required masters.
    party_types = [
        ("Customer", "Receivable"),
        ("Supplier", "Payable"),
        ("Employee", "Payable"),
        ("Shareholder", "Payable"),
    ]

    for party_type, account_type in party_types:
        if not frappe.db.exists("Party Type", party_type):
            frappe.get_doc(
                {
                    "doctype": "Party Type",
                    "party_type": party_type,
                    "account_type": account_type,
                }
            ).insert(ignore_permissions=True)

    # ERPNext's standard UOM data is normally installed by add_uom_data().
    # Fresh-tenant provisioning intentionally avoids the broad fixture
    # installer, so guarantee the specific standard UOM required by
    # Healthcare medication tests.
    if not frappe.db.exists("UOM", "Nos"):
        frappe.get_doc(
            {
                "doctype": "UOM",
                "uom_name": "Nos",
                "name": "Nos",
                "enabled": 1,
                "must_be_whole_number": 1,
            }
        ).db_insert()

    # ERPNext's standard setup wizard also supplies the Cash Mode of Payment.
    # Fresh-tenant provisioning intentionally avoids the broad fixture
    # installer, so guarantee this standard dependency explicitly.
    if not frappe.db.exists("Mode of Payment", "Cash"):
        frappe.get_doc(
            {
                "doctype": "Mode of Payment",
                "mode_of_payment": "Cash",
                "type": "Cash",
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)

    # ERPNext's standard setup wizard supplies the CRM Sales Stage masters.
    # Only install them when the foundation is missing; do not run the
    # broad ERPNext fixture installer.
    if not frappe.db.exists("Sales Stage", "Prospecting"):
        add_sale_stages()


def _ensure_erpnext_foundation(
    tenant_name,
    plan_definition,
    registered_country=None,
):
    """
    Initialize the minimum ERPNext tenant foundation required by Clinify.

    This intentionally reuses ERPNext's supported setup operations while
    avoiding the broad ERPNext fixture installer. The latter is designed for
    the interactive setup wizard and can modify a large set of nested-set
    master data.

    This function runs inside a newly-created tenant site.
    """

    if not frappe.db.exists("DocType", "Company"):
        frappe.throw("ERPNext Company DocType is not available.")

    if not frappe.db.exists("DocType", "Fiscal Year"):
        frappe.throw("ERPNext Fiscal Year DocType is not available.")

    country = str(registered_country or "").strip()
    if not country:
        frappe.throw("Registered Country is required for ERPNext foundation setup.")

    currency = str(
        (plan_definition or {}).get("currency") or ""
    ).strip().upper()

    if not currency:
        frappe.throw("Plan currency is required for ERPNext foundation setup.")

    company_count = frappe.db.count("Company")
    tenant_company_exists = frappe.db.exists(
        "Company",
        {"company_name": tenant_name},
    )

    # Standard UOM/UOM conversion data is intentionally installed first.
    # add_uom_data() is idempotent and inserts only missing records.
    erpnext_fixtures.add_uom_data()

    # ERPNext Company.on_update() creates a default "Goods In Transit"
    # warehouse with warehouse_type="Transit". Healthcare also relies on
    # the standard "Services" Item Group. These are the minimal setup
    # records required by the tenant foundation; avoid the broad ERPNext
    # setup-wizard fixture installer.
    _ensure_erpnext_foundation_fixtures()

    if not tenant_company_exists:
        current_year = now_datetime().year

        setup_args = frappe._dict(
            {
                "currency": currency,
                "company_name": tenant_name,
                "company_abbr": None,
                "country": country,
                "domain": None,
                "chart_of_accounts": "Standard",
                "fy_start_date": f"{current_year}-01-01",
                "fy_end_date": f"{current_year}-12-31",
            }
        )

        erpnext_fixtures.install_company(setup_args)

    # Synchronize Clinify's registered fixtures into the new tenant.
    # This applies Clinify Custom Fields, Property Setters, Client Scripts,
    # Server Scripts, Workspace records, and other registered fixtures.
    sync_fixtures("clinify")

    # install_defaults() requires Company to exist because it establishes
    # Global Defaults.default_company.
    if not frappe.db.exists("Company", {"company_name": tenant_name}):
        frappe.throw(
            "ERPNext foundation initialization failed: Company was not created."
        )

    default_args = frappe._dict(
        {
            "currency": currency,
            "company_name": tenant_name,
            "country": country,
            "domain": None,
            "chart_of_accounts": "Standard",
            "bank_account": None,
        }
    )

    erpnext_fixtures.install_defaults(default_args)

    company = frappe.db.get_value(
        "Company",
        {"company_name": tenant_name},
        ["name", "abbr", "default_currency", "country"],
        as_dict=True,
    )

    fiscal_year_count = frappe.db.count("Fiscal Year")

    stock_uom = frappe.db.get_single_value(
        "Stock Settings",
        "stock_uom",
    )

    standard_buying = frappe.db.exists(
        "Price List",
        {"name": "Standard Buying"},
    )

    standard_selling = frappe.db.exists(
        "Price List",
        {"name": "Standard Selling"},
    )

    transit_type = frappe.db.exists("Warehouse Type", "Transit")

    warehouse_count = frappe.db.count(
        "Warehouse",
        {"company": tenant_name},
    )

    expected_warehouses = (
        frappe.db.count(
            "Warehouse",
            {"company": tenant_name, "warehouse_name": "All Warehouses"},
        )
        and frappe.db.count(
            "Warehouse",
            {"company": tenant_name, "warehouse_name": "Stores"},
        )
        and frappe.db.count(
            "Warehouse",
            {"company": tenant_name, "warehouse_name": "Work In Progress"},
        )
        and frappe.db.count(
            "Warehouse",
            {"company": tenant_name, "warehouse_name": "Finished Goods"},
        )
        and frappe.db.count(
            "Warehouse",
            {
                "company": tenant_name,
                "warehouse_name": "Goods In Transit",
                "warehouse_type": "Transit",
            },
        )
    )

    services_item_group = frappe.db.exists("Item Group", "Services")

    if not company:
        frappe.throw("ERPNext foundation verification failed: Company is missing.")

    if fiscal_year_count == 0:
        frappe.throw("ERPNext foundation verification failed: Fiscal Year is missing.")

    if not stock_uom:
        frappe.throw("ERPNext foundation verification failed: Stock UOM is missing.")

    if not standard_buying:
        frappe.throw(
            "ERPNext foundation verification failed: Standard Buying Price List is missing."
        )

    if not standard_selling:
        frappe.throw(
            "ERPNext foundation verification failed: Standard Selling Price List is missing."
        )

    if not transit_type:
        frappe.throw(
            "ERPNext foundation verification failed: Warehouse Type Transit is missing."
        )

    if not expected_warehouses:
        frappe.throw(
            "ERPNext foundation verification failed: Default warehouse tree is incomplete."
        )

    if not services_item_group:
        frappe.throw(
            "ERPNext foundation verification failed: Services Item Group is missing."
        )

    return {
        "company": company.name,
        "company_abbr": company.abbr,
        "currency": company.default_currency,
        "country": company.country,
        "fiscal_year_count": fiscal_year_count,
        "stock_uom": stock_uom,
        "standard_buying": bool(standard_buying),
        "standard_selling": bool(standard_selling),
        "warehouse_type_transit": bool(transit_type),
        "warehouse_count": warehouse_count,
        "default_warehouses_complete": bool(expected_warehouses),
        "services_item_group": bool(services_item_group),
    }


def _finalize_frappe_setup():
    """
    Finalize the tenant site's Frappe setup state.

    Tenant provisioning does not run the interactive Frappe setup wizard,
    so reproduce only the setup-completion state transition required by
    Frappe after the required application stack has been installed.
    """
    frappe.get_single("Installed Applications").update_versions()

    for app_name in ("frappe", "erpnext"):
        if not frappe.db.exists("Installed Application", {"app_name": app_name}):
            frappe.throw(f"Required application is missing from Installed Applications: {app_name}")

        frappe.db.set_value(
            "Installed Application",
            {"app_name": app_name},
            "is_setup_complete",
            1,
        )

    frappe.clear_cache(doctype="System Settings")

    frappe.db.set_single_value(
        "System Settings",
        "enable_onboarding",
        1,
    )

    frappe.db.set_single_value(
        "System Settings",
        "setup_complete",
        1,
    )

    frappe.db.commit()
    frappe.clear_cache()



def _ensure_healthcare_dental_foundation():
    """Ensure the minimum Clinify dental scheduling foundation exists."""

    # -------------------------------------------------
    # Medical Department
    # -------------------------------------------------
    if frappe.db.exists("DocType", "Medical Department"):
        if not frappe.db.exists("Medical Department", "Dental"):
            frappe.get_doc({
                "doctype": "Medical Department",
                "department": "Dental",
            }).insert(ignore_permissions=True)

    # -------------------------------------------------
    # Appointment Type
    # -------------------------------------------------
    if frappe.db.exists("DocType", "Appointment Type"):
        if not frappe.db.exists("Appointment Type", "OPD"):
            appointment_type = frappe.get_doc({
                "doctype": "Appointment Type",
                "appointment_type": "OPD",
                "allow_booking_for": "Practitioner",
                "default_duration": 20,
            })

            price_list = frappe.db.get_value(
                "Price List",
                {"selling": 1},
                "name",
            )
            if price_list:
                appointment_type.price_list = price_list

            appointment_type.insert(ignore_permissions=True)

    # -------------------------------------------------
    # Healthcare Service Unit Type
    # -------------------------------------------------
    service_unit_type = None

    if frappe.db.exists("DocType", "Healthcare Service Unit Type"):
        service_unit_type = frappe.db.exists(
            "Healthcare Service Unit Type",
            "OPD",
        )

        if not service_unit_type:
            service_unit_type_doc = frappe.get_doc({
                "doctype": "Healthcare Service Unit Type",
                "service_unit_type": "OPD",
                "allow_appointments": 1,
                "overlap_appointments": 0,
            })
            service_unit_type_doc.insert(ignore_permissions=True)
            service_unit_type = service_unit_type_doc.name
        else:
            service_unit_type_doc = frappe.get_doc(
                "Healthcare Service Unit Type",
                service_unit_type,
            )
            if not service_unit_type_doc.allow_appointments:
                service_unit_type_doc.allow_appointments = 1
                service_unit_type_doc.save(ignore_permissions=True)

    # -------------------------------------------------
    # Healthcare Service Unit
    # -------------------------------------------------
    if (
        service_unit_type
        and frappe.db.exists("DocType", "Healthcare Service Unit")
    ):
        company = frappe.defaults.get_user_default("Company")
        if not company:
            company = frappe.db.get_value(
                "Company",
                {"is_group": 0},
                "name",
            )

        existing_service_unit = frappe.db.exists(
            "Healthcare Service Unit",
            {
                "healthcare_service_unit_name": "OPD",
                "company": company,
            },
        )

        if not existing_service_unit:
            service_unit = frappe.get_doc({
                "doctype": "Healthcare Service Unit",
                "healthcare_service_unit_name": "OPD",
                "is_group": 0,
                "service_unit_type": service_unit_type,
                "service_unit_capacity": 1,
                "allow_appointments": 1,
                "overlap_appointments": 0,
            })
            if not company:
                company = frappe.db.get_value(
                    "Company",
                    {"is_group": 0},
                    "name",
                )

            if company:
                service_unit.company = company

            service_unit.insert(ignore_permissions=True)

    frappe.db.commit()


def reconcile_tenant_foundation():
    """Repair only Clinify-owned administrator and Healthcare foundation state.

    Invoke explicitly with ``bench --site <tenant> execute``. This is not a
    substitute for full provisioning and deliberately does not touch tenant
    users, subscriptions, catalogue data, or clinical/financial documents.
    """
    frappe.only_for("System Manager")

    site_name = (frappe.local.site or "").strip().lower()
    control_site = (
        frappe.conf.get("clinify_control_site") or "clinify.localhost"
    ).strip().lower()

    from clinify.saas.sso import _is_control_site

    if site_name == control_site or _is_control_site():
        frappe.throw("Tenant foundation reconciliation cannot run on the control site.")

    _ensure_admin_role()
    _ensure_admin_permissions()
    _ensure_gender_master_data()
    _ensure_healthcare_dental_foundation()

    frappe.clear_cache()

    return {
        "success": True,
        "site": site_name,
        "reconciled": [
            "Clinify Clinic Admin role",
            "Clinify Clinic Admin permissions",
            "Gender master data",
            "Healthcare and Dental foundation",
        ],
    }


def _ensure_clinify_catalogue():
    """
    Ensure the minimum Clinify clinical catalogue exists in a tenant.

    This is intentionally idempotent and reuses Clinify's existing
    catalogue importers/installers rather than duplicating catalogue data.
    """

    # -------------------------------------------------
    # Required ERPNext Item Groups
    # -------------------------------------------------

    if frappe.db.exists("DocType", "Item Group"):

        if not frappe.db.exists("Item Group", "Services"):
            frappe.get_doc(
                {
                    "doctype": "Item Group",
                    "item_group_name": "Services",
                    "parent_item_group": "All Item Groups",
                    "is_group": 0,
                }
            ).insert(ignore_permissions=True)

        if not frappe.db.exists("Item Group", "Dental"):
            frappe.get_doc(
                {
                    "doctype": "Item Group",
                    "item_group_name": "Dental",
                    "parent_item_group": "All Item Groups",
                    "is_group": 0,
                }
            ).insert(ignore_permissions=True)

    # -------------------------------------------------
    # Consultation Item
    # -------------------------------------------------

    if not frappe.db.exists("Item", "CONSULTATION"):
        item = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": "CONSULTATION",
                "item_name": "Doctor Consultation",
                "item_group": "Services",
                "is_stock_item": 0,
                "is_sales_item": 1,
                "disabled": 0,
            }
        )
        item.insert(ignore_permissions=True)

    # -------------------------------------------------
    # Common Medicines
    # -------------------------------------------------

    from clinify.importers.drug_importer import (
        import_common_medicines,
    )

    import_common_medicines()

    # -------------------------------------------------
    # Lab Test Templates
    # -------------------------------------------------

    from clinify.patches.create_lab_test_template_dev import (
        execute as install_lab_test_templates,
    )

    install_lab_test_templates()

    # -------------------------------------------------
    # Dental Catalogue
    # -------------------------------------------------

    from clinify.dev.dental_catalogue import (
        install as install_dental_catalogue,
    )

    install_dental_catalogue()

    frappe.db.commit()

def bootstrap_tenant(
    tenant_name,
    tenant_code,
    administrator_email,
    administrator_name=None,
    plan=None,
    plan_definition=None,
    contact_person=None,
    registered_phone=None,
    registered_email=None,
    address_line_1=None,
    address_line_2=None,
    registered_city=None,
    registered_state=None,
    postal_code=None,
    registered_country=None,
    subscription_end_date=None,
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

    contact_person = _clean(contact_person)
    registered_phone = _clean(registered_phone)
    registered_email = _clean(registered_email)
    address_line_1 = _clean(address_line_1)
    address_line_2 = _clean(address_line_2)
    registered_city = _clean(registered_city)
    registered_state = _clean(registered_state)
    postal_code = _clean(postal_code)
    registered_country = _clean(registered_country)

    plan_code = _clean(plan).upper()

    if not plan_code:
        frappe.throw("Plan is required.")

    if not plan_definition:
        frappe.throw("Plan definition is required.")

    _ensure_admin_role()
    _ensure_admin_permissions()
    _ensure_gender_master_data()

    erpnext_foundation = _ensure_erpnext_foundation(
        tenant_name=tenant_name,
        plan_definition=plan_definition,
        registered_country=registered_country,
    )

    _ensure_healthcare_dental_foundation()
    _ensure_clinify_catalogue()

    # Install Clinify's authoritative print formats for every new tenant.
    # The installers are idempotent and own the approved print templates.
    from clinify.patches.install_clinify_prescription_print_format_v6 import (
        execute as install_clinify_prescription_print_format,
    )
    from clinify.patches.install_clinify_invoice_print_format_v1 import (
        execute as install_clinify_invoice_print_format,
    )

    install_clinify_prescription_print_format()
    install_clinify_invoice_print_format()

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
        contact_person=contact_person,
        registered_phone=registered_phone,
        registered_email=registered_email,
        address_line_1=address_line_1,
        address_line_2=address_line_2,
        registered_city=registered_city,
        registered_state=registered_state,
        postal_code=postal_code,
        registered_country=registered_country,
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

    _finalize_frappe_setup()

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
            "end_date",
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

import os
import subprocess
from pathlib import Path

import frappe
from frappe.utils import now_datetime

from clinify.saas.provisioning import validate_provision_request
from clinify.clinify.doctype.clinify_tenant.clinify_tenant import generate_tenant_id


BENCH_PATH = Path(frappe.get_app_path("clinify")).parents[2]
SITES_PATH = BENCH_PATH / "sites"

CLINIFY_APP = "clinify"


def _set_status(tenant, status, error=None):
    tenant.provisioning_status = status
    tenant.provisioning_error = error
    tenant.save(ignore_permissions=True)
    frappe.db.commit()


def _site_exists(site_name):
    return (SITES_PATH / site_name).is_dir()


def _run_bench(args):
    command = ["bench"] + args

    result = subprocess.run(
        command,
        cwd=str(BENCH_PATH),
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        output = "\n".join(
            part
            for part in [
                result.stdout.strip(),
                result.stderr.strip(),
            ]
            if part
        )

        raise RuntimeError(
            "Bench command failed (exit code {}):\n{}".format(
                result.returncode,
                output[-12000:],
            )
        )

    return result.stdout.strip()


def _create_site(site_name, admin_password):
    if _site_exists(site_name):
        raise RuntimeError(
            "Site directory already exists: {}".format(site_name)
        )

    db_admin_user = os.environ.get("CLINIFY_DB_ADMIN_USER")
    db_admin_password = os.environ.get("CLINIFY_DB_ADMIN_PASSWORD")

    if not db_admin_user or not db_admin_password:
        raise RuntimeError(
            "MariaDB provisioning credentials are not configured. "
            "Set CLINIFY_DB_ADMIN_USER and CLINIFY_DB_ADMIN_PASSWORD."
        )

    _run_bench(
        [
            "new-site",
            site_name,
            "--admin-password",
            admin_password,
            "--db-root-username",
            db_admin_user,
            "--db-root-password",
            db_admin_password,
            "--install-app",
            CLINIFY_APP,
        ]
    )


def _get_plan_definition(plan_code):
    plan_code = str(plan_code or "").strip().upper()

    if not plan_code:
        raise RuntimeError("Plan is required.")

    plan = frappe.db.get_value(
        "Clinify Plan",
        {"plan_code": plan_code, "is_active": 1},
        [
            "name",
            "plan_name",
            "plan_code",
            "plan_type",
            "billing_cycle",
            "price",
            "currency",
            "max_users",
            "max_practitioners",
            "max_patients",
            "is_active",
        ],
        as_dict=True,
    )

    if not plan:
        raise RuntimeError(
            "Active Clinify Plan was not found: {}".format(plan_code)
        )

    return dict(plan)


def _bootstrap_site(
    site_name,
    tenant_name,
    tenant_code,
    administrator_email,
    administrator_name,
    plan,
    plan_definition,
    contact_person=None,
    registered_phone=None,
    registered_email=None,
    address_line_1=None,
    address_line_2=None,
    registered_city=None,
    registered_state=None,
    postal_code=None,
    registered_country=None,
):
    method = (
        "clinify.saas.tenant_bootstrap.bootstrap_tenant"
    )

    import json

    args = json.dumps(
        [
            tenant_name,
            tenant_code,
            administrator_email,
            administrator_name,
            plan,
            plan_definition,
            contact_person,
            registered_phone,
            registered_email,
            address_line_1,
            address_line_2,
            registered_city,
            registered_state,
            postal_code,
            registered_country,
        ]
    )

    _run_bench(
        [
            "--site",
            site_name,
            "execute",
            method,
            "--args",
            args,
        ]
    )


def _verify_site(
    site_name,
    tenant_code,
    administrator_email,
):
    import json

    method = "clinify.saas.tenant_bootstrap.verify_tenant"

    args = json.dumps(
        [
            tenant_code,
            administrator_email,
        ]
    )

    output = _run_bench(
        [
            "--site",
            site_name,
            "execute",
            method,
            "--args",
            args,
        ]
    )

    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Tenant verification returned invalid JSON: {}".format(
                output[-12000:]
            )
        ) from exc

def provision_tenant(
    tenant_name,
    tenant_code,
    site_name,
    administrator_email,
    plan,
    admin_password,
    administrator_name=None,
    domain=None,
    contact_person=None,
    registered_phone=None,
    registered_email=None,
    address_line_1=None,
    address_line_2=None,
    registered_city=None,
    registered_state=None,
    postal_code=None,
    registered_country=None,
):
    """
    Provision a new Clinify tenant from the control site.

    This function creates the control-site Clinify Tenant
    record first, then provisions the tenant site and
    bootstraps it.

    It intentionally does not delete failed tenant records.
    """

    if not admin_password:
        frappe.throw("Administrator password is required.")

    tenant = frappe.db.get_value(
        "Clinify Tenant",
        {"tenant_code": tenant_code},
        [
            "name",
            "tenant_name",
            "tenant_code",
            "site_name",
            "domain",
            "administrator_name",
            "administrator_email",
            "plan",
            "contact_person",
            "registered_phone",
            "registered_email",
            "address_line_1",
            "address_line_2",
            "registered_city",
            "registered_state",
            "postal_code",
            "registered_country",
            "provisioning_status",
            "tenant_id",
        ],
        as_dict=True,
    )

    if tenant:
        tenant = frappe.get_doc("Clinify Tenant", tenant.name)

        if tenant.provisioning_status not in ("Pending", "Verifying"):
            frappe.throw(
                "Only a Pending or Verifying Tenant can be provisioned. "
                "Current status: {}".format(
                    tenant.provisioning_status
                )
            )

        if tenant.tenant_name != tenant_name:
            frappe.throw("Tenant Name does not match the saved Tenant.")

        if tenant.site_name != site_name:
            frappe.throw("Site Name does not match the saved Tenant.")

        if tenant.administrator_email != administrator_email:
            frappe.throw(
                "Administrator Email does not match the saved Tenant."
            )

        if tenant.plan != plan:
            frappe.throw("Plan does not match the saved Tenant.")

        validation = {
            "tenant_name": tenant.tenant_name,
            "tenant_code": tenant.tenant_code,
            "site_name": tenant.site_name,
            "domain": tenant.domain,
            "administrator_email": tenant.administrator_email,
            "plan": tenant.plan,
            "contact_person": tenant.contact_person,
            "registered_phone": tenant.registered_phone,
            "registered_email": tenant.registered_email,
            "address_line_1": tenant.address_line_1,
            "address_line_2": tenant.address_line_2,
            "registered_city": tenant.registered_city,
            "registered_state": tenant.registered_state,
            "postal_code": tenant.postal_code,
            "registered_country": tenant.registered_country,
        }

    else:
        validation = validate_provision_request(
            tenant_name=tenant_name,
            tenant_code=tenant_code,
            site_name=site_name,
            administrator_email=administrator_email,
            plan=plan,
            domain=domain,
        )

        if _site_exists(validation["site_name"]):
            frappe.throw(
                "Site directory already exists: {}".format(
                    validation["site_name"]
                )
            )

        tenant = frappe.get_doc(
            {
                "doctype": "Clinify Tenant",
                "tenant_name": validation["tenant_name"],
                "tenant_code": validation["tenant_code"],
                "site_name": validation["site_name"],
                "domain": validation["domain"],
                "administrator_name": administrator_name
                or validation["tenant_name"],
                "administrator_email": validation[
                    "administrator_email"
                ],
                "plan": validation["plan"],
                "contact_person": validation["contact_person"],
                "registered_phone": validation["registered_phone"],
                "registered_email": validation["registered_email"],
                "address_line_1": validation["address_line_1"],
                "address_line_2": validation["address_line_2"],
                "registered_city": validation["registered_city"],
                "registered_state": validation["registered_state"],
                "postal_code": validation["postal_code"],
                "registered_country": validation["registered_country"],
                "provisioning_status": "Pending",
                "enabled": 1,
                "clinic_status": "Active",
            }
        )

        tenant.insert(ignore_permissions=True)
        frappe.db.commit()

    if (
        tenant.provisioning_status != "Verifying"
        and _site_exists(validation["site_name"])
    ):
        frappe.throw(
            "Site directory already exists: {}".format(
                validation["site_name"]
            )
        )

    try:
        if tenant.provisioning_status == "Verifying":
            verification = _verify_site(
                site_name=validation["site_name"],
                tenant_code=validation["tenant_code"],
                administrator_email=validation[
                    "administrator_email"
                ],
            )

            tenant.subscription = verification["subscription"]["name"]
            tenant.subscription_status = verification["subscription"]["subscription_status"]
            tenant.subscription_end_date = verification["subscription"]["end_date"]

            if not tenant.tenant_id:
                tenant.tenant_id = generate_tenant_id(
                    tenant_name=tenant.tenant_name,
                    subscription_start_date=verification["subscription"]["start_date"],
                )

            tenant.provisioning_status = "Ready"
            tenant.provisioning_error = None
            tenant.provisioned_on = now_datetime()
            tenant.last_verified_on = now_datetime()
            tenant.save(ignore_permissions=True)

            frappe.db.commit()

            return {
                "success": True,
                "tenant": tenant.name,
                "site": tenant.site_name,
                "status": tenant.provisioning_status,
                "verification": verification,
            }

        _set_status(tenant, "Creating Site")

        _create_site(
            site_name=validation["site_name"],
            admin_password=admin_password,
        )

        _set_status(tenant, "Installing Apps")

        # new-site already installed Clinify through
        # --install-app. This status exists so the state
        # machine remains explicit.
        installed_apps = _run_bench(
            [
                "--site",
                validation["site_name"],
                "list-apps",
            ]
        )

        if CLINIFY_APP not in installed_apps:
            _run_bench(
                [
                    "--site",
                    validation["site_name"],
                    "install-app",
                    CLINIFY_APP,
                ]
            )

        _set_status(tenant, "Configuring Clinic")

        plan_definition = _get_plan_definition(
            validation["plan"]
        )

        _set_status(tenant, "Creating Subscription")

        _set_status(tenant, "Creating Administrator")

        _bootstrap_site(
            site_name=validation["site_name"],
            tenant_name=validation["tenant_name"],
            tenant_code=validation["tenant_code"],
            administrator_email=validation[
                "administrator_email"
            ],
            administrator_name=administrator_name
            or validation["tenant_name"],
            plan=validation["plan"],
            plan_definition=plan_definition,
            contact_person=validation["contact_person"],
            registered_phone=validation["registered_phone"],
            registered_email=validation["registered_email"],
            address_line_1=validation["address_line_1"],
            address_line_2=validation["address_line_2"],
            registered_city=validation["registered_city"],
            registered_state=validation["registered_state"],
            postal_code=validation["postal_code"],
            registered_country=validation["registered_country"],
        )

        _set_status(tenant, "Verifying")

        verification = _verify_site(
            site_name=validation["site_name"],
            tenant_code=validation["tenant_code"],
            administrator_email=validation[
                "administrator_email"
            ],
        )

        tenant.subscription = verification["subscription"]["name"]
        tenant.subscription_status = verification["subscription"]["subscription_status"]
        tenant.subscription_end_date = verification["subscription"]["end_date"]

        if not tenant.tenant_id:
            tenant.tenant_id = generate_tenant_id(
                tenant_name=tenant.tenant_name,
                subscription_start_date=verification["subscription"]["start_date"],
            )

        tenant.provisioning_status = "Ready"
        tenant.provisioning_error = None
        tenant.provisioned_on = now_datetime()
        tenant.last_verified_on = now_datetime()
        tenant.save(ignore_permissions=True)

        frappe.db.commit()

        return {
            "success": True,
            "tenant": tenant.name,
            "site": tenant.site_name,
            "status": tenant.provisioning_status,
            "verification": verification,
        }

    except Exception as exc:
        error = str(exc)

        try:
            tenant.reload()
        except Exception:
            pass

        tenant.provisioning_status = "Failed"
        tenant.provisioning_error = error[:2000]
        tenant.save(ignore_permissions=True)
        frappe.db.commit()

        raise

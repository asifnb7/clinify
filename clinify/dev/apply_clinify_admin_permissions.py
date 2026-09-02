import json
from pathlib import Path
import frappe
from frappe.utils import now_datetime


ROLE = "Clinify Clinic Admin"


PERMISSIONS = {
    "Patient": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1,
    },
    "Appointment": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1,
    },
    "Healthcare Practitioner": {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1,
    },
    "Patient Encounter": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 1, "cancel": 1, "amend": 1,
        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1,
    },
    "Clinical Procedure": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 1, "cancel": 1, "amend": 0,
        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1,
    },
    "Lab Test": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 1, "cancel": 1, "amend": 1,
        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1,
    },
    "Medication Request": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1,
    },
    "Sales Invoice": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 1, "cancel": 1, "amend": 1,
        "report": 1, "export": 0, "print": 1, "email": 1, "share": 1,
    },
    "Payment Entry": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 1, "cancel": 1, "amend": 1,
        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1,
    },
    "Item": {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1,
    },
    "Company": {
        "read": 1, "write": 1, "create": 0, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1,
    },
}


def run():
    print("=" * 70)
    print("CLINIFY BETA — APPLY TENANT ADMIN PERMISSIONS")
    print("=" * 70)

    print("\nROLE:")
    print(ROLE)

    if not frappe.db.exists("Role", ROLE):
        frappe.throw(f"Role does not exist: {ROLE}")

    # ------------------------------------------------------------
    # BACKUP CURRENT PERMISSIONS
    # ------------------------------------------------------------

    existing = frappe.get_all(
        "DocPerm",
        filters={"role": ROLE},
        fields=[
            "name",
            "parent",
            "permlevel",
            "read",
            "write",
            "create",
            "delete",
            "submit",
            "cancel",
            "amend",
            "report",
            "export",
            "print",
            "email",
            "share",
        ],
        order_by="parent asc, permlevel asc",
    )

    backup = {
        "timestamp": str(now_datetime()),
        "role": ROLE,
        "docperms": existing,
    }

    backup_path = (
        str(
            Path(frappe.get_app_path("clinify")).parent
            / "clinify"
            / "dev"
            / (
                "clinify_admin_docperm_backup_"
                + now_datetime().strftime("%Y%m%d_%H%M%S")
                + ".json"
            )
        )
    )

    with open(backup_path, "w") as f:
        json.dump(backup, f, indent=2, default=str)

    print("\nBACKUP:")
    print(backup_path)

    # ------------------------------------------------------------
    # APPLY PERMISSIONS
    # ------------------------------------------------------------

    permission_fields = [
        "read",
        "write",
        "create",
        "delete",
        "submit",
        "cancel",
        "amend",
        "report",
        "export",
        "print",
        "email",
        "share",
    ]

    for doctype, values in PERMISSIONS.items():

        print(f"\n--- {doctype} ---")

        if not frappe.db.exists("DocType", doctype):
            print("SKIPPED: DocType does not exist")
            continue

        existing_perm = frappe.db.exists(
            "DocPerm",
            {
                "parent": doctype,
                "role": ROLE,
                "permlevel": 0,
            },
        )

        if existing_perm:
            docperm = frappe.get_doc("DocPerm", existing_perm)
            action = "UPDATED"
        else:
            docperm = frappe.new_doc("DocPerm")
            docperm.parent = doctype
            docperm.parenttype = "DocType"
            docperm.parentfield = "permissions"
            docperm.role = ROLE
            docperm.permlevel = 0
            action = "CREATED"

        for fieldname in permission_fields:
            setattr(docperm, fieldname, values.get(fieldname, 0))

        docperm.save(ignore_permissions=True)

        print(action)

        print({
            "read": docperm.read,
            "write": docperm.write,
            "create": docperm.create,
            "delete": docperm.delete,
            "submit": docperm.submit,
            "cancel": docperm.cancel,
            "amend": docperm.amend,
        })

    frappe.db.commit()

    print("\n" + "=" * 70)
    print("TENANT ADMIN PERMISSIONS APPLIED")
    print("=" * 70)


if __name__ == "__main__":
    run()

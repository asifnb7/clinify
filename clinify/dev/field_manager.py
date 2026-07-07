"""
Clinify Development Toolkit
Field Manager

Reusable helpers for creating and managing Custom Fields
programmatically.

Author: Clinify Development Team
"""

import frappe


def field_exists(doctype: str, fieldname: str) -> bool:
    """
    Check whether a Custom Field already exists.
    """

    return bool(
        frappe.db.exists(
            "Custom Field",
            {
                "dt": doctype,
                "fieldname": fieldname,
            },
        )
    )


def create_field(
    *,
    doctype,
    fieldname,
    label,
    fieldtype,
    insert_after,
    **kwargs,
):
    """
    Create a Custom Field only if it does not already exist.

    Example:

    create_field(
        doctype="Patient Appointment",
        fieldname="custom_reception_status",
        label="Reception Status",
        fieldtype="Select",
        insert_after="status",
        options="Waiting\\nChecked In"
    )
    """

    if field_exists(doctype, fieldname):
        print(f"✓ {doctype}.{fieldname} already exists")
        return

    doc = frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": doctype,
            "fieldname": fieldname,
            "label": label,
            "fieldtype": fieldtype,
            "insert_after": insert_after,
            **kwargs,
        }
    )

    doc.insert(ignore_permissions=True)

    frappe.db.commit()

    print(f"✓ Created {doctype}.{fieldname}")


def delete_field(doctype: str, fieldname: str):
    """
    Delete a Custom Field if it exists.
    """

    name = frappe.db.exists(
        "Custom Field",
        {
            "dt": doctype,
            "fieldname": fieldname,
        },
    )

    if not name:
        print(f"✓ {doctype}.{fieldname} does not exist")
        return

    frappe.delete_doc(
        "Custom Field",
        name,
        force=True,
    )

    frappe.db.commit()

    print(f"✓ Deleted {doctype}.{fieldname}")


def test():
    """
    Simple toolkit test.
    """

    print("===================================")
    print("Clinify Dev Toolkit")
    print("Field Manager Loaded Successfully")
    print("===================================")
def install_fields(doctype, fields):
    """
    Install multiple fields on a DocType.

    Example:

    install_fields(
        "Clinic Configuration",
        FIELDS
    )
    """

    print(f"\nInstalling fields for {doctype}...\n")

    for field in fields:

        create_field(
            doctype=doctype,
            fieldname=field["fieldname"],
            label=field["label"],
            fieldtype=field["fieldtype"],
            insert_after=field["insert_after"],
            **{
                k: v
                for k, v in field.items()
                if k not in (
                    "fieldname",
                    "label",
                    "fieldtype",
                    "insert_after",
                )
            },
        )

    print(f"\nFinished installing {doctype}.\n")

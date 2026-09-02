import frappe


def create_or_update(
    name,
    lab_test_name,
    lab_test_code,
    department,
    rate,
):
    if frappe.db.exists("Lab Test Template", name):
        print("Already exists:", name)
        return

    doc = frappe.get_doc({
        "doctype": "Lab Test Template",
        "lab_test_name": lab_test_name,
        "lab_test_code": lab_test_code,
        "lab_test_group": "Laboratory",
        "department": department,
        "lab_test_template_type": "Single",
        "is_billable": 1,
        "lab_test_rate": rate,
        "disabled": 0,
        "link_existing_item": 0,
    })

    doc.insert(ignore_permissions=True)

    print(
        "Created:",
        doc.name,
        "| Item:",
        doc.item,
        "| Department:",
        doc.department,
    )


def execute():
    create_or_update(
        "LAB-CBC",
        "Complete Blood Count (CBC)",
        "LAB-CBC",
        "Haematology",
        500,
    )

    create_or_update(
        "LAB-HBA1C",
        "HbA1c",
        "LAB-HBA1C",
        "Biochemistry",
        400,
    )

    create_or_update(
        "LAB-URINE",
        "Urine Routine",
        "LAB-URINE",
        "Pathology",
        200,
    )

    frappe.db.commit()

    print("========================================")
    print("LAB TEST TEMPLATE CREATION COMPLETE")
    print("========================================")

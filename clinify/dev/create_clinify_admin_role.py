import frappe


def run():
    role_name = "Clinify Clinic Admin"

    if frappe.db.exists("Role", role_name):
        print(f"Already exists: {role_name}")
        return

    role = frappe.get_doc({
        "doctype": "Role",
        "role_name": role_name,
        "desk_access": 1,
        "is_custom": 1,
    })

    role.insert(ignore_permissions=True)
    frappe.db.commit()

    print(f"Created: {role_name}")

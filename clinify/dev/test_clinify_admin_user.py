import frappe


def run():
    email = "clinify-admin-test@example.com"
    role_name = "Clinify Clinic Admin"

    existing = frappe.db.exists("User", email)

    if existing:
        print(f"User already exists: {existing}")
        return

    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": "Clinify",
        "last_name": "Admin Test",
        "enabled": 1,
        "user_type": "System User",
        "send_welcome_email": 0,
        "roles": [
            {
                "doctype": "Has Role",
                "role": role_name,
            }
        ],
    })

    user.insert(ignore_permissions=True)
    frappe.db.commit()

    print(f"Created User: {user.name}")
    print(f"User Type: {user.user_type}")
    print("Roles:")
    for row in user.roles:
        print(f"  - {row.role}")

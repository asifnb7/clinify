import frappe

def execute(filters=None):
    user = frappe.session.user

    columns = [
        {
            "label": "Treatment Plan",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Dental Treatment Plan",
            "width": 200,
        },
        {
            "label": "Patient",
            "fieldname": "patient",
            "fieldtype": "Link",
            "options": "Patient",
            "width": 150,
        },
        {
            "label": "Doctor",
            "fieldname": "primary_doctor",
            "fieldtype": "Link",
            "options": "Doctor",
            "width": 150,
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Created On",
            "fieldname": "creation",
            "fieldtype": "Datetime",
            "width": 160,
        },
    ]

    data = frappe.db.get_all(
        "Dental Treatment Plan",
        filters={
            "owner": user,
            "status": "Active",
        },
        fields=[
            "name",
            "patient",
            "primary_doctor",
            "status",
            "creation",
        ],
        order_by="creation desc",
    )

    return columns, data

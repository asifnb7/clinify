import frappe

def run():
    print("=== CLINIFY TENANTS ===")
    print(frappe.db.sql("SELECT name, tenant_name, tenant_code, site_name, domain, administrator_name, administrator_email, provisioning_status, provisioning_error, provisioned_on, plan, subscription, subscription_status, enabled, clinic_status, last_verified_on FROM `tabClinify Tenant` ORDER BY creation", as_dict=True))

    print("=== CLINIC CONFIGURATION ===")
    print(frappe.db.sql("SELECT field, value FROM `tabSingles` WHERE doctype = 'Clinic Configuration' ORDER BY field", as_dict=True))

    print("=== CLINIFY SUBSCRIPTIONS ===")
    print(frappe.db.sql("SELECT name, clinic, plan, subscription_status, start_date, billing_cycle, price, currency, is_active FROM `tabClinify Subscription` ORDER BY creation", as_dict=True))

    print("=== IMPORT TEST USER ===")
    print(frappe.db.sql("SELECT name, email, first_name, last_name, enabled, user_type FROM `tabUser` WHERE email = '__IMPORT_TEST__'", as_dict=True))

    print("=== IMPORT TEST USER ROLES ===")
    print(frappe.db.sql("SELECT parent, role FROM `tabHas Role` WHERE parent = '__IMPORT_TEST__'", as_dict=True))

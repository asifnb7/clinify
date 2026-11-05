import frappe

from clinify.tenant_dental_config import (
    CONFIG_DOCTYPE,
    SERVICE_TYPE_CUSTOM,
)


@frappe.whitelist()
def get_active_dental_services():
    """
    Return the complete active Clinify Dental Service catalogue.

    Dental Service is the single authoritative catalogue.
    """

    return frappe.get_all(
        "Dental Service",
        filters={
            "is_active": 1,
        },
        fields=[
            "name",
            "service_code",
            "service_name",
            "default_qty",
            "minimum_price",
            "maximum_price",
            "pricing_basis",
            "requires_tooth",
            "erpnext_item",
        ],
        order_by="service_name asc",
    )


@frappe.whitelist()
def get_tenant_dental_services():
    """
    Return the current tenant's dental service configuration for management.

    Each row carries the tenant-owned pricing configuration (fixed price or
    variable options) plus the enabled/active state. This is the data source
    for the Clinic Admin management view. Records are naturally isolated to the
    current tenant by the per-site architecture; role permissions govern who
    may read them.
    """

    configs = frappe.get_all(
        CONFIG_DOCTYPE,
        fields=[
            "name",
            "service_type",
            "dental_service",
            "custom_service_name",
            "clinic_code",
            "erpnext_item",
            "pricing_type",
            "fixed_price",
            "is_enabled",
            "is_active",
            "requires_tooth",
            "default_qty",
        ],
        order_by="modified desc",
    )

    for config in configs:
        if config["service_type"] == SERVICE_TYPE_CUSTOM:
            config["service_name"] = config["custom_service_name"]
        else:
            config["service_name"] = frappe.db.get_value(
                "Dental Service",
                config["dental_service"],
                "service_name",
            )

        if config["pricing_type"] == "Variable":
            config["price_options"] = frappe.get_all(
                "Clinify Tenant Dental Price Option",
                filters={"parent": config["name"]},
                fields=["name", "option_label", "price", "is_enabled"],
                order_by="idx asc",
            )
        else:
            config["price_options"] = []

    return configs


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_encounter_dental_service_link_options(
    doctype,
    txt,
    searchfield,
    start,
    page_len,
    filters=None,
):
    """
    Return the active tenant Dental Service catalogue for the Encounter
    Link field.

    The Link value remains the authoritative Dental Service document name.
    The second returned column is the doctor-facing title and adds ``*`` to
    Variable services without changing the stored value.
    """

    if doctype != "Dental Service":
        return []

    configs = frappe.get_all(
        "Clinify Tenant Dental Service",
        filters={
            "is_enabled": 1,
            "is_active": 1,
        },
        fields=[
            "dental_service",
            "pricing_type",
        ],
    )

    service_names = [
        config["dental_service"]
        for config in configs
        if config.get("dental_service")
    ]

    if not service_names:
        return []

    services = frappe.get_all(
        "Dental Service",
        filters={
            "name": ["in", service_names],
            "is_active": 1,
        },
        fields=[
            "name",
            "service_name",
            "service_code",
        ],
    )

    by_name = {
        service["name"]: service
        for service in services
    }

    pricing_by_name = {
        config["dental_service"]: config["pricing_type"]
        for config in configs
        if config.get("dental_service")
    }

    needle = (txt or "").strip().casefold()
    results = []

    for service in services:
        name = service["name"]
        service_name = service.get("service_name") or name
        service_code = service.get("service_code") or ""

        if needle and (
            needle not in service_name.casefold()
            and needle not in service_code.casefold()
            and needle not in name.casefold()
        ):
            continue

        pricing_type = pricing_by_name.get(name) or "Fixed"

        if pricing_type == "Variable":
            label = f"{service_name} *"
            description = "Variable pricing — choose Minimum, Midpoint, or Maximum"
        else:
            label = service_name
            description = "Fixed pricing"

        results.append(
            (
                name,
                label,
                description,
            )
        )

    results.sort(key=lambda row: row[1].rstrip(" *").casefold())

    start = int(start or 0)
    page_len = int(page_len or 50)

    return results[start : start + page_len]


@frappe.whitelist()
def get_encounter_dental_service_options():
    """
    Return enabled, active tenant dental services for the doctor palette.

    Fixed services are returned with their resolved price so the doctor does
    not have to configure pricing. Variable services return their enabled
    price options so the doctor can select a predefined option. Disabled or
    inactive services are never returned.
    """

    configs = frappe.get_all(
        CONFIG_DOCTYPE,
        filters={"is_enabled": 1, "is_active": 1},
        fields=[
            "name",
            "service_type",
            "dental_service",
            "custom_service_name",
            "pricing_type",
            "fixed_price",
            "requires_tooth",
            "default_qty",
        ],
        order_by="modified desc",
    )

    options = []

    for config in configs:
        if config["service_type"] == SERVICE_TYPE_CUSTOM:
            service_name = config["custom_service_name"]
        else:
            service_name = frappe.db.get_value(
                "Dental Service",
                config["dental_service"],
                "service_name",
            )

        entry = {
            "name": config["name"],
            "dental_service": config["dental_service"],
            "service_name": service_name,
            "pricing_type": config["pricing_type"],
            "requires_tooth": config["requires_tooth"],
            "default_qty": config["default_qty"],
            "price_options": [],
        }

        if config["pricing_type"] == "Variable":
            entry["price_options"] = frappe.get_all(
                "Clinify Tenant Dental Price Option",
                filters={"parent": config["name"], "is_enabled": 1},
                fields=["name", "option_label", "price"],
                order_by="idx asc",
            )
        else:
            entry["fixed_price"] = config["fixed_price"]

        options.append(entry)

    return options

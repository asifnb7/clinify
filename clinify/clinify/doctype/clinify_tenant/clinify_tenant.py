# Copyright (c) 2026, Salniz Technologies and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime


TENANT_ID_LOCK_NAME = "clinify_tenant_id_generation"


def _clinic_abbreviation(tenant_name):
    """
    Generate a deterministic three-letter clinic abbreviation.

    Examples:
        Riyaz Dental Clinic -> RDC
        Riyaz Clinic        -> RCX
        Riyaz               -> RXX
    """

    words = re.findall(r"[A-Za-z0-9]+", str(tenant_name or "").upper())

    if not words:
        return "XXX"

    letters = []

    for word in words:
        if word:
            letters.append(word[0])

    if len(letters) >= 3:
        abbreviation = "".join(letters[:3])
    elif len(letters) == 2:
        abbreviation = letters[0] + letters[1] + "X"
    else:
        abbreviation = letters[0] + "XX"

    return abbreviation[:3]


def _next_monthly_sequence(subscription_start_date):
    """
    Return the next successful clinic sequence for the subscription month.

    Tenant IDs already issued for the same month are inspected.
    A database advisory lock prevents concurrent provisioning requests
    from receiving the same sequence number.
    """

    start_date = getdate(subscription_start_date)

    lock_acquired = frappe.db.sql(
        "SELECT GET_LOCK(%s, 15)",
        (TENANT_ID_LOCK_NAME,),
    )[0][0]

    if lock_acquired != 1:
        frappe.throw(
            "Could not acquire the Tenant ID generation lock. "
            "Please try provisioning again."
        )

    try:
        year = start_date.year
        month = start_date.month

        highest_sequence = frappe.db.sql(
            """
            SELECT COALESCE(
                MAX(CAST(SUBSTRING(tenant_id, 2, 2) AS UNSIGNED)),
                0
            )
            FROM `tabClinify Tenant`
            WHERE tenant_id IS NOT NULL
              AND tenant_id != ''
              AND SUBSTRING(tenant_id, 7, 2) = LPAD(%s, 2, '0')
              AND RIGHT(tenant_id, 2) = LPAD(%s, 2, '0')
            """,
            (month, year % 100),
        )[0][0]

        sequence = int(highest_sequence) + 1

        if sequence > 99:
            frappe.throw(
                "The monthly Tenant ID sequence has reached 99. "
                "A new Tenant ID cannot be generated."
            )

        return sequence

    finally:
        frappe.db.sql(
            "SELECT RELEASE_LOCK(%s)",
            (TENANT_ID_LOCK_NAME,),
        )


def generate_tenant_id(tenant_name, subscription_start_date):
    """
    Generate the Clinify business Tenant ID.

    Format:
        CMMXXXNNYY

    Example:
        C01RDC0926
    """

    start_date = getdate(subscription_start_date)
    sequence = _next_monthly_sequence(start_date)

    abbreviation = _clinic_abbreviation(tenant_name)

    tenant_id = "C{:02d}{}{:02d}{:02d}".format(
        sequence,
        abbreviation,
        start_date.month,
        start_date.year % 100,
    )

    if frappe.db.exists(
        "Clinify Tenant",
        {"tenant_id": tenant_id},
    ):
        frappe.throw(
            "Generated Tenant ID already exists: {}".format(
                tenant_id
            )
        )

    return tenant_id


class ClinifyTenant(Document):
    pass

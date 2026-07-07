"""
Clinify Development Toolkit

Clinic Configuration Installer

Creates the default Clinic Configuration fields required
for the Clinify MVP.
"""

import frappe

from clinify.dev.field_manager import create_field


def install():

    print("\n===================================")
    print("Installing Clinic Configuration...")
    print("===================================\n")

    #
    # Consultation Settings
    #

    create_field(
        doctype="Clinic Configuration",
        fieldname="consultation_section",
        label="Consultation Settings",
        fieldtype="Section Break",
        insert_after="section_break_xley",
    )

    create_field(
        doctype="Clinic Configuration",
        fieldname="free_followup_days",
        label="Free Follow-up Days",
        fieldtype="Int",
        insert_after="consultation_section",
        default="7",
    )

    create_field(
        doctype="Clinic Configuration",
        fieldname="allow_multiple_free_followups",
        label="Allow Multiple Free Follow-ups",
        fieldtype="Check",
        insert_after="free_followup_days",
        default="0",
    )

    print("\n===================================")
    print("Clinic Configuration Installed")
    print("===================================\n")

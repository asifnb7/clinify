import frappe


def run():
    print("")
    print("=" * 110)
    print("CLINIFY 5B.4-D — CONTROLLED DENTAL BILLING TEST")
    print("=" * 110)

    created_procedure = None
    created_invoice = None

    try:
        # -----------------------------------------------------
        # 1. Locate IOPA Dental Service
        # -----------------------------------------------------

        service = frappe.db.get_value(
            "Dental Service",
            {
                "service_code": "DENT-EXTRACTION",
                "is_active": 1,
            },
            [
                "name",
                "service_code",
                "service_name",
                "erpnext_item",
                "minimum_price",
                "maximum_price",
            ],
            as_dict=True,
        )

        if not service:
            frappe.throw(
                "DENT-EXTRACTION Dental Service was not found."
            )

        print("")
        print("STEP 1 — DENTAL SERVICE")
        print("-" * 110)
        print("Service      :", service.name)
        print("Code         :", service.service_code)
        print("Name         :", service.service_name)
        print("ERPNext Item :", service.erpnext_item)
        print("Min Price    :", service.minimum_price)
        print("Max Price    :", service.maximum_price)

        # -----------------------------------------------------
        # 2. Locate a suitable Treatment Plan
        # -----------------------------------------------------

        plans = frappe.get_all(
            "Dental Treatment Plan",
            fields=[
                "name",
                "patient",
                "primary_doctor",
            ],
            order_by="modified desc",
            limit_page_length=50,
        )

        plan = None

        for candidate in plans:
            if not candidate.patient or not candidate.primary_doctor:
                continue

            plan = candidate
            break

        if not plan:
            frappe.throw(
                "No suitable Dental Treatment Plan found."
            )

        print("")
        print("STEP 2 — TEST TREATMENT PLAN")
        print("-" * 110)
        print("Plan         :", plan.name)
        print("Patient      :", plan.patient)
        print("Doctor       :", plan.primary_doctor)

        # -----------------------------------------------------
        # 3. Create temporary linked planned procedure
        # -----------------------------------------------------

        procedure = frappe.get_doc(
            {
                "doctype": "Dental Planned Procedure",
                "parent": plan.name,
                "parenttype": "Dental Treatment Plan",
                "parentfield": "dental_planned_procedures",
                "dental_service": service.name,
                "procedure_type": service.service_name,
                "tooth_surface": "O",
                "planned_status": "Completed",
                "estimated_cost": service.minimum_price or 0,
            }
        )

        procedure.insert(
            ignore_permissions=True
        )

        created_procedure = procedure.name

        print("")
        print("STEP 3 — LINKED PROCEDURE CREATED")
        print("-" * 110)
        print("Procedure    :", procedure.name)
        print("Dental Service:", procedure.dental_service)
        print("Procedure Type:", procedure.procedure_type)
        print("Status       :", procedure.planned_status)
        print("Estimated Cost:", procedure.estimated_cost)

        # -----------------------------------------------------
        # 4. Execute billing engine
        # -----------------------------------------------------

        from clinify.billing import create_invoice_from_dental_plan

        print("")
        print("STEP 4 — BILLING ENGINE")
        print("-" * 110)

        invoice_name = create_invoice_from_dental_plan(
            plan.name
        )

        created_invoice = invoice_name

        print("Invoice      :", invoice_name)

        # -----------------------------------------------------
        # 5. Inspect invoice
        # -----------------------------------------------------

        invoice = frappe.get_doc(
            "Sales Invoice",
            invoice_name,
        )

        print("")
        print("STEP 5 — INVOICE VERIFICATION")
        print("-" * 110)

        dental_items = [
            item
            for item in invoice.items
            if item.item_code == service.erpnext_item
        ]

        print("Invoice Items:", len(invoice.items))
        print("IOPA Lines   :", len(dental_items))

        for item in dental_items:
            print(
                "ITEM         :",
                item.item_code,
                "| QTY=",
                item.qty,
                "| RATE=",
                item.rate,
                "| AMOUNT=",
                item.amount,
            )

        if len(dental_items) != 1:
            frappe.throw(
                "Expected exactly one IOPA invoice line."
            )

        item = dental_items[0]

        if item.item_code != service.erpnext_item:
            frappe.throw(
                "Incorrect ERPNext Item resolved."
            )

        if item.qty != 1:
            frappe.throw(
                "Unexpected IOPA quantity."
            )

        if item.rate != service.minimum_price:
            frappe.throw(
                f"Unexpected IOPA rate: {item.rate}. "
                f"Expected {service.minimum_price}."
            )

        # -----------------------------------------------------
        # 6. Verify billed_invoice linkage
        # -----------------------------------------------------

        linked_invoice = frappe.db.get_value(
            "Dental Planned Procedure",
            created_procedure,
            "billed_invoice",
        )

        print("")
        print("STEP 6 — BILLING LINK VERIFICATION")
        print("-" * 110)
        print("Procedure    :", created_procedure)
        print("Billed Invoice:", linked_invoice)

        if linked_invoice != invoice_name:
            frappe.throw(
                "Dental Planned Procedure was not linked "
                "to the created Sales Invoice."
            )

        print("")
        print("=" * 110)
        print("5B.4-D CONTROLLED BILLING TEST: PASS")
        print("=" * 110)
        print("")
        print("Dental Service → ERPNext Item : PASS")
        print("ERPNext Item → Selling Rate  : PASS")
        print("Sales Invoice creation       : PASS")
        print("Billed Invoice linkage       : PASS")
        print("")
        print("TEST DATA CREATED")
        print("Procedure :", created_procedure)
        print("Invoice   :", invoice_name)
        print("")
        print("NOTE: Test records were NOT automatically deleted.")
        print("They must be reviewed before cleanup.")
        print("=" * 110)

    except Exception:
        print("")
        print("=" * 110)
        print("5B.4-D CONTROLLED BILLING TEST: FAILED")
        print("=" * 110)
        print("")
        print("Procedure created :", created_procedure or "-")
        print("Invoice created   :", created_invoice or "-")
        print("")
        raise

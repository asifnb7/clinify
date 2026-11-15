import frappe
from frappe.model.document import Document

from clinify.medicine_catalogue_sync import (
    normalize_product_record,
    require_control_site_admin,
)


class ClinifyMedicineProduct(Document):
    def autoname(self):
        if not self.central_product_id:
            self.central_product_id = "CLM-" + frappe.generate_hash(length=20).upper()
        self.name = self.central_product_id

    def validate(self):
        require_control_site_admin()
        product = normalize_product_record(self.as_dict())
        self.central_product_id = product["central_product_id"]
        self.ingredient_name = product["ingredient_name"]
        self.composition = product["composition"]
        self.medicine_name = product["medicine_name"]
        self.strength = product["strength"]
        self.strength_uom = product["strength_uom"]
        self.dosage_form = product["dosage_form"]
        self.manufacturer = product["manufacturer"]
        self.pack_label = product["pack_label"]
        self.source_mrp = product["source_mrp"]
        self.source_selling_price = product["source_selling_price"]
        self.prescription_required = product["prescription_required"]
        self.source_provider = product["source_provider"]
        self.source_identifier = product["source_identifier"]
        self.source_revision = product["source_revision"]
        self.source_updated_at = product["source_updated_at"]
        self.is_active = product["is_active"]
        self.identity_hash = product["identity_hash"]
        self.clinical_identity_hash = product["clinical_identity_hash"]

        if self.name != self.central_product_id:
            frappe.throw("Central product identifier cannot be changed.")

        previous = self.get_doc_before_save()
        if previous:
            previous_product = normalize_product_record(previous.as_dict())
            if previous_product["identity_key"] != product["identity_key"]:
                frappe.throw(
                    "Medicine identity is immutable; discontinue it and create a new central product."
                )

    def on_trash(self):
        require_control_site_admin()
        frappe.throw("Central medicine products cannot be deleted; mark them inactive instead.")
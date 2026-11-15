import frappe
from frappe.model.document import Document

from clinify.medicine_catalogue_sync import normalize_product_record


class ClinifyMedicineProjection(Document):
    def autoname(self):
        self.name = self.central_product_id

    def validate(self):
        if not self.flags.get("clinify_catalogue_sync"):
            frappe.throw("Tenant medicine projections are read-only synchronized records.")

        product = normalize_product_record(self.as_dict())
        if self.name != product["central_product_id"]:
            frappe.throw("Projection name must match its central product identifier.")
        for fieldname in (
            "central_product_id",
            "ingredient_name",
            "composition",
            "medicine_name",
            "strength",
            "strength_uom",
            "dosage_form",
            "manufacturer",
            "pack_label",
            "source_mrp",
            "source_selling_price",
            "prescription_required",
            "clinical_identity_hash",
            "source_provider",
            "source_identifier",
            "source_revision",
            "source_updated_at",
            "is_active",
        ):
            setattr(self, fieldname, product[fieldname])

    def on_trash(self):
        frappe.throw("Medicine projections cannot be deleted; synchronize an inactive product instead.")
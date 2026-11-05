import unittest
from types import SimpleNamespace
from unittest.mock import patch

from clinify.dev import dental_catalogue


class FakeCatalogueDB:
    def __init__(self):
        self.items = set()
        self.dental_services = {"DENT-CUSTOM"}
        self.item_prices = {"DENT-CUSTOM": 24680}
        self.dental_service_values = {
            "DENT-CUSTOM": {
                "service_name": "Clinic Custom Crown",
                "is_active": 0,
                "pricing_basis": "Clinic Specific",
                "minimum_price": 9876,
                "maximum_price": 12345,
                "requires_tooth": 0,
                "default_qty": 3,
                "erpnext_item": "CUSTOM-CROWN-ITEM",
            }
        }
        self.commits = 0

    def exists(self, doctype, filters):
        if doctype == "Price List":
            return filters == "Standard Selling"
        if doctype == "Dental Service":
            code = filters["service_code"] if isinstance(filters, dict) else filters
            return code if code in self.dental_services else None
        if doctype == "Item":
            code = filters["item_code"] if isinstance(filters, dict) else filters
            return code if code in self.items else None
        raise AssertionError(f"Unexpected exists query: {doctype!r}, {filters!r}")

    def get_value(self, doctype, filters, fieldname):
        if doctype == "Item Price":
            code = filters["item_code"]
            return code if code in self.item_prices else None
        raise AssertionError(f"Unexpected get_value query: {doctype!r}, {filters!r}")

    def commit(self):
        self.commits += 1


class FakeCatalogueDoc:
    def __init__(self, values, database, writes):
        self.values = dict(values)
        self.database = database
        self.writes = writes
        self.doctype = self.values["doctype"]

    def insert(self, ignore_permissions=False):
        self.writes.append(dict(self.values))
        if self.doctype == "Item":
            self.database.items.add(self.values["item_code"])
        elif self.doctype == "Dental Service":
            self.database.dental_services.add(self.values["service_code"])
            self.database.dental_service_values[self.values["service_code"]] = dict(
                self.values
            )
        elif self.doctype == "Item Price":
            self.database.item_prices[self.values["item_code"]] = self.values[
                "price_list_rate"
            ]
        else:
            raise AssertionError(f"Unexpected inserted DocType: {self.doctype!r}")
        return self


class TestDentalCatalogueProvisioning(unittest.TestCase):
    def test_install_inserts_missing_service_and_preserves_existing_service_and_price(self):
        services = [
            {
                "code": "DENT-CUSTOM",
                "name": "Clinic Custom Crown",
                "minimum": 10,
                "maximum": 20,
                "basis": "Range",
                "requires_tooth": 1,
            },
            {
                "code": "DENT-NEW-STANDARD",
                "name": "New Standard Service",
                "minimum": 300,
                "maximum": 500,
                "basis": "Per Tooth",
                "requires_tooth": 1,
            },
        ]
        database = FakeCatalogueDB()
        database.item_prices["DENT-CUSTOM"] = 24680
        writes = []
        existing_service_before = dict(database.dental_service_values["DENT-CUSTOM"])
        existing_price_before = database.item_prices["DENT-CUSTOM"]

        def get_doc(*args):
            if len(args) == 1 and isinstance(args[0], dict):
                return FakeCatalogueDoc(args[0], database, writes)
            if args == ("Item", "DENT-NEW-STANDARD"):
                return SimpleNamespace(name="DENT-NEW-STANDARD")
            raise AssertionError(f"Unexpected get_doc call: {args!r}")

        fake_frappe = SimpleNamespace(
            db=database,
            get_doc=get_doc,
            ValidationError=RuntimeError,
        )

        with patch.object(dental_catalogue, "SERVICES", services), \
             patch.object(dental_catalogue, "frappe", fake_frappe):
            dental_catalogue.install()
            first_writes = list(writes)
            first_state = (
                set(database.items),
                set(database.dental_services),
                dict(database.item_prices),
                dict(database.dental_service_values),
            )
            dental_catalogue.install()

        self.assertEqual(writes, first_writes)
        self.assertEqual(
            (
                set(database.items),
                set(database.dental_services),
                dict(database.item_prices),
                dict(database.dental_service_values),
            ),
            first_state,
        )
        self.assertEqual(
            database.dental_service_values["DENT-CUSTOM"],
            existing_service_before,
        )
        self.assertEqual(
            database.item_prices["DENT-CUSTOM"],
            existing_price_before,
        )

        inserted_service = next(
            values for values in writes
            if values["doctype"] == "Dental Service"
        )
        self.assertEqual(inserted_service["service_code"], "DENT-NEW-STANDARD")
        self.assertEqual(inserted_service["service_name"], "New Standard Service")
        self.assertEqual(inserted_service["pricing_basis"], "Per Tooth")
        self.assertEqual(inserted_service["minimum_price"], 300)
        self.assertEqual(inserted_service["maximum_price"], 500)
        self.assertEqual(inserted_service["requires_tooth"], 1)
        self.assertEqual(inserted_service["default_qty"], 1)
        self.assertEqual(database.commits, 2)


if __name__ == "__main__":
    unittest.main()

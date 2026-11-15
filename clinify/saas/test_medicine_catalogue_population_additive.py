import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from clinify.saas import medicine_catalogue_population, orchestrator


def drug_item(item_code, item_name=None):
    return {
        "item_code": item_code,
        "item_name": item_name or item_code,
        "item_group": "Drug",
        "disabled": 0,
        "is_stock_item": 1,
        "is_sales_item": 1,
        "stock_uom": "Nos",
        "description": item_name or item_code,
    }


class TestAdditiveMedicineCataloguePopulation(unittest.TestCase):
    def test_inserts_missing_item_and_leaves_existing_item_untouched(self):
        created_item = SimpleNamespace(
            insert=Mock(),
        )
        fake_frappe = SimpleNamespace(
            db=SimpleNamespace(
                exists=Mock(
                    side_effect=lambda doctype, filters: (
                        doctype == "Item"
                        and filters["item_code"] == "TENANT-OWNED"
                    )
                ),
                commit=Mock(),
            ),
            get_doc=Mock(return_value=created_item),
        )
        items = [
            drug_item("CENTRAL-NEW"),
            drug_item("TENANT-OWNED", "Tenant's unchanged name"),
        ]

        with patch.object(
            medicine_catalogue_population, "frappe", fake_frappe
        ):
            result = medicine_catalogue_population.add_missing_drug_items(items)

        self.assertEqual(result, {"created": 1, "skipped": 1})
        fake_frappe.get_doc.assert_called_once_with(
            {
                **drug_item("CENTRAL-NEW"),
                "doctype": "Item",
            }
        )
        created_item.insert.assert_called_once_with(ignore_permissions=True)
        fake_frappe.db.commit.assert_called_once_with()
        self.assertEqual(
            fake_frappe.db.exists.call_args_list,
            [
                call("Item", {"item_code": "CENTRAL-NEW"}),
                call("Item", {"item_code": "TENANT-OWNED"}),
            ],
        )

    def test_invalid_batch_is_rejected_before_any_item_is_written(self):
        fake_frappe = SimpleNamespace(
            db=SimpleNamespace(exists=Mock(), commit=Mock()),
            get_doc=Mock(),
        )

        with patch.object(
            medicine_catalogue_population, "frappe", fake_frappe
        ):
            with self.assertRaisesRegex(ValueError, "non-Drug Item"):
                medicine_catalogue_population.add_missing_drug_items(
                    [
                        drug_item("CENTRAL-NEW"),
                        {
                            **drug_item("NOT-A-DRUG"),
                            "item_group": "Services",
                        },
                    ]
                )

        fake_frappe.db.exists.assert_not_called()
        fake_frappe.get_doc.assert_not_called()

    def test_control_site_transfers_only_requested_central_items(self):
        central_items = [
            drug_item("CENTRAL-A"),
            drug_item("CENTRAL-B"),
            drug_item("CENTRAL-C"),
        ]
        fake_frappe = SimpleNamespace(
            get_all=Mock(return_value=central_items),
        )
        site_name = "tenant.localhost"
        command_results = [json.dumps({"created": 2, "skipped": 0})]

        with patch.object(orchestrator, "frappe", fake_frappe), patch.object(
            orchestrator, "_run_bench", side_effect=command_results
        ) as run_bench:
            result = orchestrator._populate_tenant_medicine_catalogue(
                site_name,
                item_codes=["CENTRAL-A", "CENTRAL-C"],
            )

        self.assertEqual(result, {"created": 2, "skipped": 0})
        self.assertEqual(run_bench.call_count, 1)
        first_args = run_bench.call_args.args[0]
        self.assertEqual(first_args[1], site_name)
        first_batch = json.loads(first_args[-1])[0]
        self.assertEqual(
            [item["item_code"] for item in first_batch],
            ["CENTRAL-A", "CENTRAL-C"],
        )

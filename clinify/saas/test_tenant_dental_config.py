"""Source-level tests for the tenant dental service configuration layer.

These tests deliberately avoid any database writes. The price resolver is
pure and is exercised directly with lightweight stand-in objects; the DocType
JSON and permission matrix are validated statically. This mirrors the existing
Clinify test convention of mocked/source-level coverage.
"""

import json
import os
import unittest

from clinify.tenant_dental_config import (
    PRICING_TYPE_FIXED,
    PRICING_TYPE_VARIABLE,
    SERVICE_TYPE_CUSTOM,
    SERVICE_TYPE_STANDARD,
    DentalPriceResolutionError,
    resolve_tenant_dental_price,
)


def _config(**kwargs):
    """Build a dict stand-in for a Clinify Tenant Dental Service document."""
    base = {
        "name": "DENT-RCT",
        "service_type": SERVICE_TYPE_STANDARD,
        "dental_service": "DENT-RCT",
        "pricing_type": PRICING_TYPE_FIXED,
        "fixed_price": 0,
        "price_options": [],
        "is_enabled": 1,
        "is_active": 1,
    }
    base.update(kwargs)
    return base


def _option(name, price, is_enabled=1):
    return {"name": name, "price": price, "is_enabled": is_enabled}


DOCTYPES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "clinify",
    "doctype",
)


def _load_doctype_json(folder, filename):
    with open(os.path.join(DOCTYPES_DIR, folder, filename)) as handle:
        return json.load(handle)


class TestTenantDentalPriceResolution(unittest.TestCase):
    """The billing safety matrix (no database required)."""

    def test_active_fixed_service_with_valid_price_succeeds(self):
        config = _config(fixed_price=5500)
        self.assertEqual(
            resolve_tenant_dental_price(config),
            5500,
        )

    def test_active_variable_service_with_valid_option_succeeds(self):
        config = _config(
            pricing_type=PRICING_TYPE_VARIABLE,
            price_options=[
                _option("OPT-1", 4000),
                _option("OPT-2", 5500),
                _option("OPT-3", 7000),
            ],
        )
        self.assertEqual(
            resolve_tenant_dental_price(config, "OPT-2"),
            5500,
        )

    def test_variable_service_without_selected_option_is_rejected(self):
        config = _config(
            pricing_type=PRICING_TYPE_VARIABLE,
            price_options=[_option("OPT-1", 4000)],
        )
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(config)

    def test_missing_fixed_price_is_rejected(self):
        config = _config(fixed_price=0)
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(config)

    def test_missing_fixed_price_never_returns_zero(self):
        config = _config(fixed_price=0)
        try:
            resolve_tenant_dental_price(config)
        except DentalPriceResolutionError:
            return
        self.fail("Expected rejection instead of a zero rate.")

    def test_disabled_service_is_rejected(self):
        config = _config(fixed_price=5500, is_enabled=0)
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(config)

    def test_inactive_service_is_rejected(self):
        config = _config(fixed_price=5500, is_active=0)
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(config)

    def test_disabled_variable_option_is_rejected(self):
        config = _config(
            pricing_type=PRICING_TYPE_VARIABLE,
            price_options=[_option("OPT-1", 4000, is_enabled=0)],
        )
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(config, "OPT-1")

    def test_unknown_variable_option_is_rejected(self):
        config = _config(
            pricing_type=PRICING_TYPE_VARIABLE,
            price_options=[_option("OPT-1", 4000)],
        )
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(config, "OPT-OTHER-TENANT")

    def test_variable_option_with_zero_price_is_rejected(self):
        config = _config(
            pricing_type=PRICING_TYPE_VARIABLE,
            price_options=[_option("OPT-1", 0)],
        )
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(config, "OPT-1")

    def test_custom_service_fixed_price_resolves(self):
        config = _config(
            service_type=SERVICE_TYPE_CUSTOM,
            name="CUSTOM-WHITENING",
            custom_service_name="Teeth Whitening",
            dental_service=None,
            fixed_price=8000,
        )
        self.assertEqual(
            resolve_tenant_dental_price(config),
            8000,
        )

    def test_no_pricing_type_is_rejected(self):
        config = _config(pricing_type=None, fixed_price=100)
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(config)


class TestTenantDentalServiceDocType(unittest.TestCase):
    """Static validation of the tenant configuration DocType contract."""

    def setUp(self):
        self.doc = _load_doctype_json(
            "clinify_tenant_dental_service",
            "clinify_tenant_dental_service.json",
        )

    def _field(self, fieldname):
        for field in self.doc["fields"]:
            if field["fieldname"] == fieldname:
                return field
        return None

    def test_required_configuration_fields_exist(self):
        for fieldname in (
            "service_type",
            "dental_service",
            "custom_service_name",
            "clinic_code",
            "is_enabled",
            "is_active",
            "pricing_type",
            "fixed_price",
            "price_options",
            "erpnext_item",
        ):
            self.assertIsNotNone(
                self._field(fieldname),
                "Missing field: {0}".format(fieldname),
            )

    def test_tenant_selling_price_is_not_on_central_catalogue(self):
        central = _load_doctype_json(
            "dental_service",
            "dental_service.json",
        )
        central_fields = {f["fieldname"] for f in central["fields"]}
        # The tenant-owned selling price must never be added to the central
        # standard catalogue DocType.
        self.assertNotIn("fixed_price", central_fields)
        self.assertNotIn("price_options", central_fields)
        self.assertNotIn("pricing_type", central_fields)
        # Central reference prices remain untouched.
        self.assertIn("minimum_price", central_fields)
        self.assertIn("maximum_price", central_fields)

    def test_variable_options_child_table_is_istable(self):
        child = _load_doctype_json(
            "clinify_tenant_dental_price_option",
            "clinify_tenant_dental_price_option.json",
        )
        self.assertEqual(child.get("istable"), 1)
        child_fields = {f["fieldname"] for f in child["fields"]}
        for fieldname in ("option_label", "price", "is_enabled"):
            self.assertIn(fieldname, child_fields)

    def test_price_options_points_to_child_doctype(self):
        field = self._field("price_options")
        self.assertEqual(field["fieldtype"], "Table")
        self.assertEqual(
            field["options"],
            "Clinify Tenant Dental Price Option",
        )

    def test_no_two_or_three_option_limit_is_imposed(self):
        child = _load_doctype_json(
            "clinify_tenant_dental_price_option",
            "clinify_tenant_dental_price_option.json",
        )
        self.assertNotIn("max_attachments", child)


class TestTenantDentalPermissions(unittest.TestCase):
    """Clinic Admin manages config; Physician is read-only; SM full."""

    def setUp(self):
        self.doc = _load_doctype_json(
            "clinify_tenant_dental_service",
            "clinify_tenant_dental_service.json",
        )

    def _perms_for_role(self, role):
        for perm in self.doc["permissions"]:
            if perm.get("role") == role:
                return perm
        return None

    def test_clinic_admin_can_manage_configuration(self):
        perm = self._perms_for_role("Clinify Clinic Admin")
        self.assertIsNotNone(perm)
        for action in ("read", "write", "create", "delete"):
            self.assertEqual(perm.get(action), 1, action)

    def test_physician_is_read_only(self):
        perm = self._perms_for_role("Physician")
        self.assertIsNotNone(perm)
        self.assertEqual(perm.get("read"), 1)
        for action in ("write", "create", "delete"):
            self.assertFalse(perm.get(action), action)

    def test_system_manager_full_access(self):
        perm = self._perms_for_role("System Manager")
        self.assertIsNotNone(perm)
        for action in ("read", "write", "create", "delete"):
            self.assertEqual(perm.get(action), 1, action)

    def test_configuration_is_registered_in_admin_permission_matrix(self):
        bootstrap_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "tenant_bootstrap.py",
        )
        with open(bootstrap_path) as handle:
            source = handle.read()
        self.assertIn('"Clinify Tenant Dental Service"', source)


class TestEncounterServiceOptionFields(unittest.TestCase):
    """The encounter child row can carry a selected variable option."""

    def setUp(self):
        self.doc = _load_doctype_json(
            "clinify_encounter_service",
            "clinify_encounter_service.json",
        )

    def _field(self, fieldname):
        for field in self.doc["fields"]:
            if field["fieldname"] == fieldname:
                return field
        return None

    def test_selected_price_option_field_exists(self):
        field = self._field("selected_price_option")
        self.assertIsNotNone(field)
        self.assertEqual(field["fieldtype"], "Link")
        self.assertEqual(
            field["options"],
            "Clinify Tenant Dental Price Option",
        )

    def test_tenant_dental_service_field_exists_for_custom_services(self):
        field = self._field("tenant_dental_service")
        self.assertIsNotNone(field)
        self.assertEqual(field["fieldtype"], "Link")
        self.assertEqual(
            field["options"],
            "Clinify Tenant Dental Service",
        )

    def test_central_dental_service_link_is_not_mandatory(self):
        # A custom service row has no central Dental Service; exactly one of
        # the two links is enforced at billing time instead.
        field = self._field("dental_service")
        self.assertNotIn("reqd", field)


class TestProvisioningIdempotency(unittest.TestCase):
    """Provisioning/reconciliation only adds new services, never overwrites."""

    def _run_ensure(self, catalogue, store, created):
        class FakeDoc(dict):
            """Dict stand-in supporting attribute access and save()."""

            def __getattr__(self, item):
                # Frappe Documents return None for unset fields.
                return self.get(item)

            def __setattr__(self, key, value):
                self[key] = value

            def save(self, *args, **kwargs):
                return self

            def insert(self, *args, **kwargs):
                return self

        # Wrap pre-existing entries so attribute access works during the
        # reference-metadata sync performed on preserved configurations.
        for key in list(store):
            if not isinstance(store[key], FakeDoc):
                store[key] = FakeDoc(store[key])

        class FakeDB:
            @staticmethod
            def exists(doctype, name=None):
                if doctype == "DocType":
                    return True
                return name in store

            @staticmethod
            def commit():
                pass

        class FakeFrappe:
            db = FakeDB()

            @staticmethod
            def get_all(doctype, filters=None, fields=None, order_by=None):
                return [dict(row) for row in catalogue]

            @staticmethod
            def get_doc(*args):
                payload = args[0]
                if isinstance(payload, dict):
                    name = payload.get("dental_service") or payload.get(
                        "custom_service_name"
                    )
                    created.append(name)
                    store[name] = FakeDoc(payload)
                    return store[name]
                # get_doc(doctype, name) reference-metadata form.
                return store[args[1]]

        import clinify.tenant_dental_config as module

        original_frappe = module.frappe
        module.frappe = FakeFrappe()
        try:
            module.ensure_tenant_dental_service_configs()
        finally:
            module.frappe = original_frappe

    def _catalogue(self):
        return [
            {
                "name": "DENT-RCT",
                "service_code": "DENT-RCT",
                "service_name": "Root Canal Treatment",
                "erpnext_item": "DENT-RCT",
                "default_qty": 1,
                "requires_tooth": 1,
                "pricing_basis": "Range",
                "minimum_price": 3500,
            },
            {
                "name": "DENT-WHITENING",
                "service_code": "DENT-WHITENING",
                "service_name": "Whitening",
                "erpnext_item": "DENT-WHITENING",
                "default_qty": 1,
                "requires_tooth": 0,
                "pricing_basis": "Fixed",
                "minimum_price": 5000,
            },
        ]

    def test_reconcile_preserves_tenant_state_and_adds_new_service(self):
        store = {
            "DENT-RCT": {
                "service_type": SERVICE_TYPE_STANDARD,
                "dental_service": "DENT-RCT",
                "pricing_type": PRICING_TYPE_FIXED,
                "fixed_price": 9000,
                "is_enabled": 0,
                "is_active": 1,
                "price_options": [],
            }
        }
        created = []
        self._run_ensure(self._catalogue(), store, created)

        # The new central service was provisioned for the tenant.
        self.assertIn("DENT-WHITENING", created)
        # The existing tenant configuration was NOT recreated/overwritten.
        self.assertNotIn("DENT-RCT", created)
        self.assertEqual(store["DENT-RCT"]["fixed_price"], 9000)
        self.assertEqual(store["DENT-RCT"]["is_enabled"], 0)

    def test_second_run_is_a_no_op(self):
        store = {
            "DENT-RCT": {
                "service_type": SERVICE_TYPE_STANDARD,
                "dental_service": "DENT-RCT",
                "pricing_type": PRICING_TYPE_FIXED,
                "fixed_price": 9000,
                "is_enabled": 1,
                "is_active": 1,
                "price_options": [],
            }
        }
        created = []
        self._run_ensure(self._catalogue()[:1], store, created)
        self.assertEqual(created, [])
        self.assertEqual(store["DENT-RCT"]["fixed_price"], 9000)


class TestNewTenantConfigPricingSeed(unittest.TestCase):
    """How NEW tenant configurations are seeded from the central catalogue.

    Fixed services seed a Fixed selling price; Range services seed a Variable
    configuration with three enabled options (minimum/midpoint/maximum); every
    other basis stays Fixed. Existing tenant configurations are preserved.
    Uses the same database-free mocked-frappe convention as the sibling class.
    """

    def _run_ensure(self, catalogue, store, created):
        class FakeDoc(dict):
            """Dict stand-in supporting attribute access and save()."""

            def __getattr__(self, item):
                # Frappe Documents return None for unset fields.
                return self.get(item)

            def __setattr__(self, key, value):
                self[key] = value

            def save(self, *args, **kwargs):
                return self

            def insert(self, *args, **kwargs):
                return self

        # Wrap pre-existing entries so attribute access works during the
        # reference-metadata sync performed on preserved configurations.
        for key in list(store):
            if not isinstance(store[key], FakeDoc):
                store[key] = FakeDoc(store[key])

        class FakeDB:
            @staticmethod
            def exists(doctype, name=None):
                if doctype == "DocType":
                    return True
                return name in store

            @staticmethod
            def commit():
                pass

        class FakeFrappe:
            db = FakeDB()

            @staticmethod
            def get_all(doctype, filters=None, fields=None, order_by=None):
                return [dict(row) for row in catalogue]

            @staticmethod
            def get_doc(*args):
                payload = args[0]
                if isinstance(payload, dict):
                    name = payload.get("dental_service") or payload.get(
                        "custom_service_name"
                    )
                    created.append(name)
                    store[name] = FakeDoc(payload)
                    return store[name]
                # get_doc(doctype, name) reference-metadata form.
                return store[args[1]]

        import clinify.tenant_dental_config as module

        original_frappe = module.frappe
        module.frappe = FakeFrappe()
        try:
            return module.ensure_tenant_dental_service_configs()
        finally:
            module.frappe = original_frappe

    @staticmethod
    def _service(code, basis, minimum, maximum=None, requires_tooth=0):
        service = {
            "name": code,
            "service_code": code,
            "service_name": code.replace("DENT-", "").title(),
            "erpnext_item": code,
            "default_qty": 1,
            "requires_tooth": requires_tooth,
            "pricing_basis": basis,
            "minimum_price": minimum,
        }
        if maximum is not None:
            service["maximum_price"] = maximum
        return service

    # -- Fixed -------------------------------------------------------------

    def test_new_fixed_service_seeds_fixed_pricing(self):
        store = {}
        created = []
        self._run_ensure(
            [self._service("DENT-WHITENING", "Fixed", 5000, 5000)],
            store,
            created,
        )

        self.assertIn("DENT-WHITENING", created)
        config = store["DENT-WHITENING"]
        self.assertEqual(config["pricing_type"], PRICING_TYPE_FIXED)
        self.assertEqual(config["fixed_price"], 5000.0)
        # A Fixed service carries no variable options.
        self.assertFalse(config.get("price_options"))

    # -- Range -> Variable -------------------------------------------------

    def test_new_range_service_seeds_variable_pricing(self):
        store = {}
        created = []
        self._run_ensure(
            [self._service("DENT-RCT", "Range", 3500, 6000, requires_tooth=1)],
            store,
            created,
        )

        self.assertIn("DENT-RCT", created)
        config = store["DENT-RCT"]
        self.assertEqual(config["pricing_type"], PRICING_TYPE_VARIABLE)

    def test_range_creates_exactly_three_options(self):
        store = {}
        created = []
        self._run_ensure(
            [self._service("DENT-RCT", "Range", 3500, 6000)],
            store,
            created,
        )

        options = store["DENT-RCT"]["price_options"]
        self.assertEqual(len(options), 3)

    def test_range_option_values_are_min_mid_max(self):
        store = {}
        created = []
        self._run_ensure(
            [self._service("DENT-RCT", "Range", 3500, 6000)],
            store,
            created,
        )

        options = store["DENT-RCT"]["price_options"]
        self.assertEqual(
            [option["option_label"] for option in options],
            ["Minimum", "Midpoint", "Maximum"],
        )
        self.assertEqual(
            [option["price"] for option in options],
            [3500.0, 4750.0, 6000.0],
        )

    def test_range_options_are_enabled(self):
        store = {}
        created = []
        self._run_ensure(
            [self._service("DENT-RCT", "Range", 3500, 6000)],
            store,
            created,
        )

        options = store["DENT-RCT"]["price_options"]
        self.assertTrue(all(option["is_enabled"] for option in options))

    def test_range_midpoint_preserves_precision(self):
        # An odd-sum range yields a .5 midpoint that must not be truncated.
        store = {}
        created = []
        self._run_ensure(
            [self._service("DENT-RCT", "Range", 3500, 6001)],
            store,
            created,
        )

        options = store["DENT-RCT"]["price_options"]
        midpoint = next(o for o in options if o["option_label"] == "Midpoint")
        self.assertEqual(midpoint["price"], 4750.5)

    # -- Other bases stay Fixed -------------------------------------------

    def test_non_range_basis_stays_fixed(self):
        store = {}
        created = []
        self._run_ensure(
            [self._service("DENT-GIC", "Per Tooth", 1500, 1500)],
            store,
            created,
        )

        self.assertIn("DENT-GIC", created)
        config = store["DENT-GIC"]
        # Per Tooth is NOT Range, so it must remain a Fixed configuration.
        self.assertEqual(config["pricing_type"], PRICING_TYPE_FIXED)
        self.assertEqual(config["fixed_price"], 1500.0)
        self.assertFalse(config.get("price_options"))

    # -- Invalid Range bounds ---------------------------------------------

    def test_range_with_missing_maximum_is_not_created(self):
        store = {}
        created = []
        result = self._run_ensure(
            [self._service("DENT-RCT", "Range", 3500)],
            store,
            created,
        )

        self.assertNotIn("DENT-RCT", created)
        self.assertNotIn("DENT-RCT", store)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["created"], 0)

    def test_range_with_inverted_bounds_is_not_created(self):
        store = {}
        created = []
        result = self._run_ensure(
            [self._service("DENT-RCT", "Range", 6000, 3500)],
            store,
            created,
        )

        self.assertNotIn("DENT-RCT", created)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["created"], 0)

    def test_range_with_non_positive_bound_is_not_created(self):
        store = {}
        created = []
        result = self._run_ensure(
            [self._service("DENT-RCT", "Range", 0, 6000)],
            store,
            created,
        )

        self.assertNotIn("DENT-RCT", created)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["created"], 0)

    # -- Preservation ------------------------------------------------------

    def test_existing_variable_config_is_preserved(self):
        # A tenant that has customised a Variable service (tenant-specific
        # options, one disabled, service disabled) must be left untouched.
        tenant_options = [
            {"name": "OPT-LOW", "option_label": "Low", "price": 4200, "is_enabled": 1},
            {"name": "OPT-OFF", "option_label": "Retired", "price": 1, "is_enabled": 0},
        ]
        store = {
            "DENT-RCT": {
                "service_type": SERVICE_TYPE_STANDARD,
                "dental_service": "DENT-RCT",
                "pricing_type": PRICING_TYPE_VARIABLE,
                "price_options": tenant_options,
                "is_enabled": 0,
                "is_active": 1,
            }
        }
        created = []
        self._run_ensure(
            [self._service("DENT-RCT", "Range", 3500, 6000)],
            store,
            created,
        )

        self.assertNotIn("DENT-RCT", created)
        config = store["DENT-RCT"]
        self.assertEqual(config["pricing_type"], PRICING_TYPE_VARIABLE)
        self.assertEqual(config["price_options"], tenant_options)
        self.assertEqual(config["is_enabled"], 0)

    def test_existing_fixed_config_with_tenant_price_is_preserved(self):
        # A tenant Fixed price that differs from the central minimum must win;
        # reconciliation must not reseed it from the central reference.
        store = {
            "DENT-RCT": {
                "service_type": SERVICE_TYPE_STANDARD,
                "dental_service": "DENT-RCT",
                "pricing_type": PRICING_TYPE_FIXED,
                "fixed_price": 9000,
                "is_enabled": 0,
                "is_active": 1,
                "price_options": [],
            }
        }
        created = []
        result = self._run_ensure(
            [self._service("DENT-RCT", "Fixed", 3500, 3500)],
            store,
            created,
        )

        self.assertNotIn("DENT-RCT", created)
        config = store["DENT-RCT"]
        self.assertEqual(config["fixed_price"], 9000)
        self.assertEqual(config["is_enabled"], 0)
        self.assertEqual(result["preserved"], 1)
        self.assertEqual(result["created"], 0)



class TestVariableOptionLabelResolution(unittest.TestCase):
    """Variable services resolve by the human-facing ``option_label``.

    The UI/API contract selects a price option by its ``option_label``
    ("Minimum"/"Midpoint"/"Maximum"), while legacy callers and the encounter
    Link field pass the child row's database ``name``. Both must resolve.
    Mirrors the runtime DENT-CLEAR-ALIGNERS scenario (80000/140000/200000).
    Database-free: the module-level translation helper is stubbed so the
    fail-closed error paths never require a live Frappe site/logger.
    """

    OPTIONS = [
        {
            "name": "sr5lptnp3f",
            "option_label": "Minimum",
            "price": 80000,
            "is_enabled": 1,
        },
        {
            "name": "sr58lqk0p4",
            "option_label": "Midpoint",
            "price": 140000,
            "is_enabled": 1,
        },
        {
            "name": "sr5qg52mrb",
            "option_label": "Maximum",
            "price": 200000,
            "is_enabled": 1,
        },
    ]

    class _ChildDoc(dict):
        """Dict stand-in behaving like a Frappe child Document."""

        def __getattr__(self, item):
            return self.get(item)

    def setUp(self):
        import clinify.tenant_dental_config as module

        self._module = module
        self._original_translation = module._
        # Error paths call ``_(...)``; keep them site-independent.
        module._ = lambda message, *args, **kwargs: message

    def tearDown(self):
        self._module._ = self._original_translation

    def _variable_config(self, options=None):
        if options is None:
            options = self.OPTIONS
        return _config(
            name="DENT-CLEAR-ALIGNERS",
            dental_service="DENT-CLEAR-ALIGNERS",
            pricing_type=PRICING_TYPE_VARIABLE,
            price_options=list(options),
        )

    # -- Selection by option_label (the UI/API contract) --------------------

    def test_minimum_label_resolves_minimum_price(self):
        self.assertEqual(
            resolve_tenant_dental_price(self._variable_config(), "Minimum"),
            80000,
        )

    def test_midpoint_label_resolves_midpoint_price(self):
        self.assertEqual(
            resolve_tenant_dental_price(self._variable_config(), "Midpoint"),
            140000,
        )

    def test_maximum_label_resolves_maximum_price(self):
        self.assertEqual(
            resolve_tenant_dental_price(self._variable_config(), "Maximum"),
            200000,
        )

    # -- Selection by database name (legacy / Link-field contract) ----------

    def test_database_name_still_resolves(self):
        self.assertEqual(
            resolve_tenant_dental_price(self._variable_config(), "sr5lptnp3f"),
            80000,
        )

    # -- Fail-closed behaviour ----------------------------------------------

    def test_unknown_label_is_rejected(self):
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(self._variable_config(), "Foobar")

    def test_disabled_option_selected_by_label_is_rejected(self):
        options = [dict(option) for option in self.OPTIONS]
        options[0]["is_enabled"] = 0
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(self._variable_config(options), "Minimum")

    def test_disabled_option_selected_by_name_is_rejected(self):
        options = [dict(option) for option in self.OPTIONS]
        options[0]["is_enabled"] = 0
        with self.assertRaises(DentalPriceResolutionError):
            resolve_tenant_dental_price(self._variable_config(options), "sr5lptnp3f")

    # -- Fixed pricing is unaffected ----------------------------------------

    def test_fixed_price_service_ignores_selected_option(self):
        config = _config(fixed_price=5500)
        self.assertEqual(resolve_tenant_dental_price(config, "Minimum"), 5500)

    # -- Document-shaped child options (real Frappe child Documents) --------

    def test_document_shaped_option_resolves_by_label(self):
        options = [self._ChildDoc(option) for option in self.OPTIONS]
        self.assertEqual(
            resolve_tenant_dental_price(self._variable_config(options), "Minimum"),
            80000,
        )


if __name__ == "__main__":
    unittest.main()

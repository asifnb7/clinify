"""Validated platform-owned print footer settings."""

PRINT_FOOTER_SITE_CONFIG_KEY = "CLINIFY_PRINT_FOOTER_CONFIG"

DEFAULT_FOOTER = {
	"mode": "Powered by Clinify",
	"text": "Powered by Clinify",
	"alignment": "Center",
	"bold": True,
	"enabled": True,
}

DEFAULT_PRINT_FOOTER_CONFIG = {
	"prescription": dict(DEFAULT_FOOTER),
	"invoice": dict(DEFAULT_FOOTER),
}

FOOTER_MODES = {"None", "Powered by Clinify", "Custom Message", "Custom"}
FOOTER_ALIGNMENTS = {"Left", "Center", "Right"}


def _as_bool(value, default):
	if isinstance(value, bool):
		return value
	if value in (1, "1", "true", "True", "yes", "Yes", "on", "On"):
		return True
	if value in (0, "0", "false", "False", "no", "No", "off", "Off"):
		return False
	return default


def _normalize_footer(value, enabled_default=True):
	config = value if isinstance(value, dict) else {}
	mode = config.get("mode")
	if not isinstance(mode, str) or mode.strip() not in FOOTER_MODES:
		mode = DEFAULT_FOOTER["mode"]
	else:
		mode = mode.strip()
	if mode == "Custom":
		mode = "Custom Message"

	text = config.get("text")
	text = text.strip() if isinstance(text, str) else ""
	if mode == "Powered by Clinify":
		text = "Powered by Clinify"
	elif mode == "Custom Message" and not text:
		text = "Powered by Clinify"
	elif mode == "None":
		text = ""

	alignment = config.get("alignment")
	if not isinstance(alignment, str) or alignment.strip() not in FOOTER_ALIGNMENTS:
		alignment = "Center"
	else:
		alignment = alignment.strip()
	bold = _as_bool(config.get("bold"), True)
	return {
		"enabled": _as_bool(config.get("enabled"), enabled_default),
		"mode": mode,
		"text": text,
		"alignment": alignment,
		"alignment_class": {"Left": "left", "Center": "center", "Right": "right"}[alignment],
		"bold": bold,
		"weight_class": "bold" if bold else "normal",
	}


def normalize_print_footer_config(value):
	"""Normalize independently configurable prescription and invoice footers."""
	config = value if isinstance(value, dict) else {}
	if "prescription" in config or "invoice" in config:
		return {
			"prescription": _normalize_footer(config.get("prescription")),
			"invoice": _normalize_footer(config.get("invoice")),
		}

	# Read the previous shared projection during rollout and migrate its values
	# to both documents until the control-plane migration writes separate values.
	shared = {
		"mode": config.get("mode"),
		"text": config.get("text"),
		"alignment": config.get("alignment"),
		"bold": config.get("bold"),
	}
	return {
		"prescription": _normalize_footer({**shared, "enabled": config.get("show_on_prescription")}),
		"invoice": _normalize_footer({**shared, "enabled": config.get("show_on_invoice")}),
	}


def footer_config_from_tenant(tenant):
	"""Return validated footer settings from the control-site Clinify Tenant."""
	return normalize_print_footer_config({
		"prescription": {
			"mode": tenant.get("print_footer_mode"),
			"text": tenant.get("print_footer_text"),
			"alignment": tenant.get("print_footer_alignment"),
			"bold": tenant.get("print_footer_bold"),
			"enabled": tenant.get("show_footer_on_prescription"),
		},
		"invoice": {
			"mode": tenant.get("invoice_footer_mode"),
			"text": tenant.get("invoice_footer_text"),
			"alignment": tenant.get("invoice_footer_alignment"),
			"bold": tenant.get("invoice_footer_bold"),
			"enabled": tenant.get("show_footer_on_invoice"),
		},
	})


def tenant_fields_from_legacy_footer(legacy):
	"""Map a tenant's former branding values into control-plane fields."""
	legacy = legacy if isinstance(legacy, dict) else {}
	text = legacy.get("platform_attribution_text")
	text = text.strip() if isinstance(text, str) else ""
	position = legacy.get("platform_attribution_position")
	position = position.strip() if isinstance(position, str) else ""
	if position not in FOOTER_ALIGNMENTS:
		position = "Center"

	if text == "Powered by Clinify" or not text:
		mode = "Powered by Clinify"
		text = "Powered by Clinify"
	else:
		mode = "Custom Message"

	return {
		"print_footer_mode": mode,
		"print_footer_text": text,
		"print_footer_alignment": position,
		"print_footer_bold": 1,
		"show_footer_on_prescription": 1,
		"invoice_footer_mode": mode,
		"invoice_footer_text": text,
		"invoice_footer_alignment": position,
		"invoice_footer_bold": 1,
		"show_footer_on_invoice": 1,
	}

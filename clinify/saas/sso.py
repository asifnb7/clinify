import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.parse import urlsplit

import frappe
import requests
from frappe.utils import getdate, today


HANDOFF_TTL_SECONDS = 60
ACTIVE_SUBSCRIPTION_STATUSES = {"Active", "Trial"}
CLINIFY_ADMIN_ROLE = "Clinify Clinic Admin"
_TENANT_FIELDS = ["name", "tenant_code", "site_name", "domain", "administrator_email", "provisioning_status", "subscription_status", "subscription_end_date", "enabled", "clinic_status"]


def _setting(name):
    return os.environ.get(name) or frappe.conf.get(name)


def _secret():
    secret = _setting("CLINIFY_SSO_SECRET")
    if not secret:
        raise RuntimeError("Clinify SSO is not configured.")
    return secret.encode()


def _control_url():
    url = (_setting("CLINIFY_CONTROL_URL") or "").rstrip("/")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise RuntimeError("Clinify control URL must be an HTTPS origin.")
    return url


def _control_site():
    return (_setting("CLINIFY_CONTROL_SITE") or urlsplit(_control_url()).hostname or "").strip().lower()


def _is_control_site():
    return (frappe.local.site or "").lower() == _control_site()


def _tenant_domain(domain):
    domain = (domain or "").strip().lower()
    parsed = urlsplit("https://" + domain)
    local = (_setting("CLINIFY_SSO_LOCAL_DEVELOPMENT") or "").lower() in {"1", "true", "yes"}
    valid_local = local and domain.endswith(".localhost")
    if not domain or parsed.hostname != domain or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password or not (domain.endswith(".salniz.com") or valid_local):
        raise RuntimeError("Tenant domain is invalid.")
    return domain


def _tenant_audience(tenant):
    site, domain = (tenant.site_name or "").strip().lower(), _tenant_domain(tenant.domain)
    if not site or site != domain:
        raise RuntimeError("Tenant site and domain mapping is invalid.")
    return site + "|" + domain


def _validate_tenant(tenant):
    if not tenant.enabled or tenant.clinic_status != "Active":
        raise RuntimeError("Your Clinify Tenant is disabled.")
    if tenant.provisioning_status != "Ready":
        raise RuntimeError("Your Clinify Tenant is not ready.")
    if tenant.subscription_status not in ACTIVE_SUBSCRIPTION_STATUSES:
        raise RuntimeError("Your Clinify subscription is not active.")
    if not tenant.subscription_end_date or getdate(tenant.subscription_end_date) < getdate(today()):
        raise RuntimeError("Your Clinify subscription has expired.")
    tenant.domain = _tenant_domain(tenant.domain)
    _tenant_audience(tenant)
    return tenant


def _tenant_for_user(user):
    tenants = frappe.get_all("Clinify Tenant", filters={"administrator_email": user}, fields=_TENANT_FIELDS)
    if len(tenants) != 1:
        raise RuntimeError("Your account must be mapped to exactly one Clinify Tenant.")
    return _validate_tenant(tenants[0])


def _tenant_for_handoff(payload):
    tenant = frappe.db.get_value("Clinify Tenant", payload["tenant"], _TENANT_FIELDS, as_dict=True)
    if not tenant or tenant.administrator_email != payload["user"]:
        raise RuntimeError("The Clinify handoff tenant is invalid.")
    tenant = _validate_tenant(tenant)
    if tenant.site_name != payload["site"] or tenant.domain != payload["domain"] or _tenant_audience(tenant) != payload["aud"]:
        raise RuntimeError("The Clinify handoff destination is invalid.")
    return tenant


def _encode(payload):
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).rstrip(b"=").decode()
    return body + "." + hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()


def _decode(assertion):
    try:
        body, signature = assertion.split(".", 1)
        if not hmac.compare_digest(signature, hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()):
            raise ValueError
        payload = json.loads(base64.b64decode(body + "=" * (-len(body) % 4), altchars=b"-_", validate=True).decode("utf-8"))
        required = {"aud", "domain", "exp", "nonce", "site", "tenant", "user", "sid"}
        if not isinstance(payload, dict) or not required.issubset(payload) or not isinstance(payload["exp"], int) or payload["exp"] <= int(time.time()):
            raise ValueError
        return payload
    except (AttributeError, TypeError, ValueError, KeyError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError):
        raise RuntimeError("The Clinify handoff is invalid or expired.")


def _handoff_key(reference):
    return "clinify_sso_handoff:" + reference


def _session_key(sid):
    return "clinify_sso_session:" + sid


def _issue_handoff(tenant, user, sid):
    reference = secrets.token_urlsafe(32)
    payload = {"aud": _tenant_audience(tenant), "domain": tenant.domain, "exp": int(time.time()) + HANDOFF_TTL_SECONDS, "nonce": secrets.token_urlsafe(24), "site": tenant.site_name, "tenant": tenant.name, "user": user, "sid": sid}
    cache = frappe.cache()
    cache.set_value(_handoff_key(reference), _encode(payload), expires_in_sec=HANDOFF_TTL_SECONDS, shared=True)
    cache.set_value(_session_key(sid), reference, expires_in_sec=HANDOFF_TTL_SECONDS, shared=True)
    return reference


def _get_handoff(reference):
    if not isinstance(reference, str) or len(reference) < 40:
        raise RuntimeError("The Clinify handoff is invalid or expired.")
    assertion = frappe.cache().get_value(_handoff_key(reference), expires=True, shared=True)
    if not assertion:
        raise RuntimeError("The Clinify handoff is invalid or expired.")
    return _decode(assertion)


def _consume_handoff(reference):
    key, cache = _handoff_key(reference), frappe.cache()
    with cache.lock(cache.make_key(key + ":lock", shared=True), timeout=5):
        assertion = cache.get_value(key, expires=True, shared=True)
        if not assertion:
            raise RuntimeError("The Clinify handoff was already used or expired.")
        cache.delete_value(key, shared=True)
        return _decode(assertion)


def _handoff_page(destination, reference):
    # The template also emits the browser-enforced meta equivalent.
    frappe.local.response["headers"] = {"Referrer-Policy": "no-referrer", "Cache-Control": "no-store"}
    frappe.respond_as_web_page("Continuing to your Clinify site", "", primary_action=None, fullpage=True, template="clinify_sso_handoff", context={"handoff_destination": destination, "handoff_reference": reference})


def on_session_creation(login_manager=None):
    user = getattr(login_manager, "user", None) or frappe.session.user
    if user in {"Guest", "Administrator"}:
        return
    if not _is_control_site():
        return
    if frappe.db.get_value("User", user, "user_type") != "System User" or "System Manager" in frappe.get_roles(user):
        return
    try:
        reference = _issue_handoff(_tenant_for_user(user), user, frappe.session.sid)
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = _control_url() + "/api/method/clinify.saas.sso.begin_handoff"
    except Exception as exc:
        frappe.respond_as_web_page("Clinify sign-in unavailable", str(exc), http_status_code=403)


@frappe.whitelist(methods=["GET"])
def begin_handoff():
    try:
        if not _is_control_site() or frappe.session.user == "Guest":
            raise RuntimeError("Authentication is required.")
        reference = frappe.cache().get_value(_session_key(frappe.session.sid), expires=True, shared=True)
        payload = _get_handoff(reference)
        if payload["user"] != frappe.session.user or payload["sid"] != frappe.session.sid:
            raise RuntimeError("The Clinify handoff does not belong to this session.")
        _tenant_for_handoff(payload)
        _handoff_page("https://" + payload["domain"] + "/api/method/clinify.saas.sso.consume_handoff", reference)
    except Exception as exc:
        frappe.respond_as_web_page("Clinify sign-in unavailable", str(exc), http_status_code=403)


def _validate_local_identity(result):
    user = frappe.db.get_value("User", result["user"], ["name", "enabled", "user_type"], as_dict=True)
    if not user or not user.enabled or user.user_type != "System User" or not frappe.db.exists("Has Role", {"parent": result["user"], "role": CLINIFY_ADMIN_ROLE}):
        raise RuntimeError("The Clinify handoff user is invalid.")
    clinic = frappe.get_single("Clinic Configuration")
    if clinic.clinic_code != result["tenant_code"] or clinic.clinic_status != "Active":
        raise RuntimeError("The Clinify clinic is not active.")
    subscription = frappe.db.get_value("Clinify Subscription", {"clinic": "Clinic Configuration", "is_active": 1}, ["subscription_status", "end_date"], as_dict=True)
    if not subscription or subscription.subscription_status not in ACTIVE_SUBSCRIPTION_STATUSES or (subscription.end_date and getdate(subscription.end_date) < getdate(today())):
        raise RuntimeError("The Clinify subscription is not active.")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def consume_handoff(reference=None):
    try:
        site, domain = frappe.local.site, _tenant_domain(frappe.request.host)
        response = requests.post(_control_url() + "/api/method/clinify.saas.sso.redeem_handoff", json={"reference": reference, "site": site, "domain": domain}, timeout=5)
        result = response.json().get("message") if response.status_code == 200 else None
        if not result or result.get("site") != site or result.get("domain") != domain or result.get("aud") != site + "|" + domain:
            raise RuntimeError("The Clinify handoff was rejected.")
        _validate_local_identity(result)
        frappe.local.login_manager.login_as(result["user"])
        frappe.local.response["type"], frappe.local.response["location"] = "redirect", "/app"
    except Exception as exc:
        frappe.respond_as_web_page("Clinify sign-in unavailable", str(exc), http_status_code=403)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def redeem_handoff(reference=None, site=None, domain=None):
    try:
        if not _is_control_site():
            raise RuntimeError("The Clinify handoff is invalid.")
        payload = _get_handoff(reference)
        if site != payload["site"] or domain != payload["domain"] or payload["aud"] != site + "|" + domain:
            raise RuntimeError("The Clinify handoff audience is invalid.")
        tenant = _tenant_for_handoff(payload)
        _consume_handoff(reference)
        return {"site": tenant.site_name, "domain": tenant.domain, "aud": _tenant_audience(tenant), "user": tenant.administrator_email, "tenant_code": tenant.tenant_code}
    except Exception as exc:
        frappe.throw(str(exc), frappe.PermissionError)

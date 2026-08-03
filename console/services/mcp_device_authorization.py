# -*- coding: utf-8 -*-
import datetime
import hashlib
import hmac
import ipaddress
import re
import secrets
from collections import namedtuple

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from console.models.main import MCPDeviceAuthorization, MCPDeviceAuthorizationRateLimit


USER_CODE_ALPHABET = "23456789BCDFGHJKMNPQRTVWXY"
USER_CODE_LENGTH = 8
DEVICE_CODE_BYTES = 32
DEFAULT_EXPIRES_IN = 600
DEFAULT_POLLING_INTERVAL = 5
POLL_PENDING = "authorization_pending"
POLL_SLOW_DOWN = "slow_down"
POLL_APPROVED = "approved"
POLL_DENIED = "access_denied"
POLL_EXPIRED = "expired_token"
POLL_CONSUMED = "invalid_grant"
POLL_INVALID = "invalid_grant"

DeviceAuthorizationCreated = namedtuple(
    "DeviceAuthorizationCreated", "record_id device_code user_code expires_in interval")
DeviceAuthorizationInspection = namedtuple(
    "DeviceAuthorizationInspection", "record_id user_code client_id client_name scope expires_at status")
DeviceAuthorizationDecision = namedtuple("DeviceAuthorizationDecision", "record_id status")
DeviceAuthorizationPoll = namedtuple(
    "DeviceAuthorizationPoll", "status interval user_id enterprise_id record_id")


class DeviceAuthorizationError(Exception):

    def __init__(self, error, message=None):
        super(DeviceAuthorizationError, self).__init__(message or error)
        self.error = error


class DeviceAuthorizationRateLimited(DeviceAuthorizationError):

    def __init__(self, retry_after):
        super(DeviceAuthorizationRateLimited, self).__init__("rate_limited")
        self.retry_after = retry_after


def _secret_bytes():
    return settings.SECRET_KEY.encode("utf-8")


def _hmac_hex(domain, value):
    payload = (domain + ":" + value).encode("utf-8")
    return hmac.new(_secret_bytes(), payload, hashlib.sha256).hexdigest()


def hash_device_code(device_code):
    return hashlib.sha256(device_code.encode("utf-8")).hexdigest()


def hash_user_code(user_code):
    return _hmac_hex("rainskills-device-user-code-v1", normalize_user_code(user_code))


def generate_user_code():
    significant = "".join(secrets.choice(USER_CODE_ALPHABET) for _ in range(USER_CODE_LENGTH))
    return significant[:4] + "-" + significant[4:]


def normalize_user_code(value):
    significant = re.sub(r"[\s-]+", "", (value or "").upper())
    if len(significant) != USER_CODE_LENGTH or any(char not in USER_CODE_ALPHABET for char in significant):
        raise DeviceAuthorizationError("invalid_user_code")
    return significant[:4] + "-" + significant[4:]


def get_request_source(request):
    remote_addr = (request.META.get("REMOTE_ADDR") or "unknown").strip()
    trusted_cidrs = getattr(settings, "RAINBOND_MCP_DEVICE_TRUSTED_PROXY_CIDRS", ())
    try:
        remote_ip = ipaddress.ip_address(remote_addr)
        trusted = any(remote_ip in ipaddress.ip_network(cidr) for cidr in trusted_cidrs)
    except ValueError:
        trusted = False
    if trusted:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        candidate = forwarded.split(",", 1)[0].strip()
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
    try:
        return str(ipaddress.ip_address(remote_addr))
    except ValueError:
        return "unknown"


def _consume_rate_limit(kind, subject, limit, window_seconds, now):
    window_epoch = int(now.timestamp()) // window_seconds * window_seconds
    if timezone.is_aware(now):
        window_started_at = datetime.datetime.fromtimestamp(window_epoch, tz=datetime.timezone.utc)
    else:
        window_started_at = datetime.datetime.fromtimestamp(window_epoch)
    expires_at = window_started_at + datetime.timedelta(seconds=window_seconds)
    bucket_hash = _hmac_hex("rainskills-device-rate-v1", "{}:{}:{}".format(kind, subject, window_epoch))

    for _attempt in range(3):
        try:
            with transaction.atomic():
                try:
                    bucket = MCPDeviceAuthorizationRateLimit.objects.select_for_update().get(bucket_hash=bucket_hash)
                except MCPDeviceAuthorizationRateLimit.DoesNotExist:
                    bucket = MCPDeviceAuthorizationRateLimit.objects.create(
                        bucket_hash=bucket_hash,
                        count=0,
                        window_started_at=window_started_at,
                        expires_at=expires_at,
                    )
                if bucket.count >= limit:
                    retry_after = max(1, int((bucket.expires_at - now).total_seconds()))
                    raise DeviceAuthorizationRateLimited(retry_after)
                MCPDeviceAuthorizationRateLimit.objects.filter(pk=bucket.pk).update(count=F("count") + 1)
                return
        except IntegrityError:
            continue
    raise DeviceAuthorizationRateLimited(window_seconds)


def _clean_expired_rows(now):
    grace = now - datetime.timedelta(days=1)
    MCPDeviceAuthorization.objects.filter(expires_at__lt=grace).delete()
    MCPDeviceAuthorizationRateLimit.objects.filter(expires_at__lt=now).delete()


def create_device_authorization(client_id, client_name, scope, source, now=None):
    now = now or timezone.now()
    if client_id != "rainskills" or scope != "mcp":
        error = "invalid_client" if client_id != "rainskills" else "invalid_scope"
        raise DeviceAuthorizationError(error)
    _consume_rate_limit(
        "create", source, int(getattr(settings, "RAINBOND_MCP_DEVICE_RATE_LIMIT_CREATE", 20)), 60, now)
    _clean_expired_rows(now)

    for _attempt in range(5):
        device_code = secrets.token_urlsafe(DEVICE_CODE_BYTES)
        user_code = generate_user_code()
        try:
            with transaction.atomic():
                record = MCPDeviceAuthorization.objects.create(
                    device_code_hash=hash_device_code(device_code),
                    user_code_hash=hash_user_code(user_code),
                    client_id=client_id,
                    client_name=client_name,
                    scope=scope,
                    status=MCPDeviceAuthorization.STATUS_PENDING,
                    polling_interval=DEFAULT_POLLING_INTERVAL,
                    expires_at=now + datetime.timedelta(seconds=DEFAULT_EXPIRES_IN),
                )
            return DeviceAuthorizationCreated(
                record.pk, device_code, user_code, DEFAULT_EXPIRES_IN, DEFAULT_POLLING_INTERVAL)
        except IntegrityError:
            continue
    raise DeviceAuthorizationError("server_error", "could not allocate a unique device code")


def _get_user_code_record(user_code):
    normalized = normalize_user_code(user_code)
    try:
        record = MCPDeviceAuthorization.objects.get(user_code_hash=hash_user_code(normalized))
    except MCPDeviceAuthorization.DoesNotExist:
        raise DeviceAuthorizationError("invalid_user_code")
    return normalized, record


def _expire_record_if_needed(record, now):
    if record.expires_at <= now:
        MCPDeviceAuthorization.objects.filter(
            pk=record.pk,
            status__in=(MCPDeviceAuthorization.STATUS_PENDING, MCPDeviceAuthorization.STATUS_APPROVED),
        ).update(status=MCPDeviceAuthorization.STATUS_EXPIRED)
        record.status = MCPDeviceAuthorization.STATUS_EXPIRED
    return record


def _record_grant_inspection_failure(record):
    failure_limit = int(getattr(settings, "RAINBOND_MCP_DEVICE_GRANT_FAILURE_LIMIT", 5))
    changed = MCPDeviceAuthorization.objects.filter(
        pk=record.pk,
        failed_inspection_attempts__lt=failure_limit,
    ).update(failed_inspection_attempts=F("failed_inspection_attempts") + 1)
    if changed != 1:
        raise DeviceAuthorizationRateLimited(DEFAULT_EXPIRES_IN)


def inspect_user_code(user_code, user, source, now=None):
    now = now or timezone.now()
    _consume_rate_limit(
        "inspect", "{}:{}".format(source, user.user_id),
        int(getattr(settings, "RAINBOND_MCP_DEVICE_RATE_LIMIT_INSPECT", 5)),
        int(getattr(settings, "RAINBOND_MCP_DEVICE_RATE_LIMIT_INSPECT_WINDOW_SECONDS", 600)),
        now,
    )
    normalized, record = _get_user_code_record(user_code)
    record = _expire_record_if_needed(record, now)
    if record.status == MCPDeviceAuthorization.STATUS_EXPIRED:
        _record_grant_inspection_failure(record)
        raise DeviceAuthorizationError(POLL_EXPIRED)
    if record.status != MCPDeviceAuthorization.STATUS_PENDING:
        _record_grant_inspection_failure(record)
        raise DeviceAuthorizationError("already_decided")
    return DeviceAuthorizationInspection(
        record.pk, normalized, record.client_id, record.client_name, record.scope, record.expires_at, record.status)


def decide_user_code(user_code, user, decision, source, now=None):
    now = now or timezone.now()
    if decision not in ("approve", "deny"):
        raise DeviceAuthorizationError("invalid_decision")
    if not getattr(user, "is_active", False):
        raise DeviceAuthorizationError("inactive_user")
    inspected = inspect_user_code(user_code, user, source, now=now)
    status = MCPDeviceAuthorization.STATUS_APPROVED if decision == "approve" else MCPDeviceAuthorization.STATUS_DENIED
    timestamp_field = "approved_at" if decision == "approve" else "denied_at"
    updates = {
        "status": status,
        "approving_user_id": user.user_id,
        "enterprise_id": getattr(user, "enterprise_id", "") or "",
        timestamp_field: now,
    }
    changed = MCPDeviceAuthorization.objects.filter(
        pk=inspected.record_id,
        status=MCPDeviceAuthorization.STATUS_PENDING,
        expires_at__gt=now,
    ).update(**updates)
    if changed != 1:
        raise DeviceAuthorizationError("already_decided")
    return DeviceAuthorizationDecision(inspected.record_id, status)


def _poll_result(status, interval=None, user_id=None, enterprise_id=None, record_id=None):
    return DeviceAuthorizationPoll(status, interval, user_id, enterprise_id, record_id)


def mark_consumed_authorization_denied(record_id, now=None):
    now = now or timezone.now()
    MCPDeviceAuthorization.objects.filter(
        pk=record_id,
        status=MCPDeviceAuthorization.STATUS_CONSUMED,
    ).update(status=MCPDeviceAuthorization.STATUS_DENIED, denied_at=now)


def poll_device_token(device_code, client_id, source, now=None):
    now = now or timezone.now()
    try:
        record = MCPDeviceAuthorization.objects.get(
            device_code_hash=hash_device_code(device_code), client_id=client_id)
    except MCPDeviceAuthorization.DoesNotExist:
        _consume_rate_limit(
            "invalid-poll", source,
            int(getattr(settings, "RAINBOND_MCP_DEVICE_RATE_LIMIT_INVALID_POLL", 30)), 60, now)
        return _poll_result(POLL_INVALID)

    record = _expire_record_if_needed(record, now)
    if record.status == MCPDeviceAuthorization.STATUS_EXPIRED:
        return _poll_result(POLL_EXPIRED)
    if record.status == MCPDeviceAuthorization.STATUS_DENIED:
        return _poll_result(POLL_DENIED)
    if record.status == MCPDeviceAuthorization.STATUS_CONSUMED:
        return _poll_result(POLL_CONSUMED)

    if record.status == MCPDeviceAuthorization.STATUS_APPROVED:
        changed = MCPDeviceAuthorization.objects.filter(
            pk=record.pk, status=MCPDeviceAuthorization.STATUS_APPROVED, expires_at__gt=now)
        changed = changed.update(status=MCPDeviceAuthorization.STATUS_CONSUMED, consumed_at=now)
        if changed != 1:
            return _poll_result(POLL_CONSUMED)
        return _poll_result(
            POLL_APPROVED,
            record.polling_interval,
            record.approving_user_id,
            record.enterprise_id,
            record.pk,
        )

    earliest_poll = (record.last_polled_at or record.created_at) + datetime.timedelta(seconds=record.polling_interval)
    if now < earliest_poll:
        next_interval = record.polling_interval + 5
        MCPDeviceAuthorization.objects.filter(
            pk=record.pk, status=MCPDeviceAuthorization.STATUS_PENDING).update(polling_interval=next_interval)
        return _poll_result(POLL_SLOW_DOWN, next_interval)

    MCPDeviceAuthorization.objects.filter(
        pk=record.pk, status=MCPDeviceAuthorization.STATUS_PENDING).update(last_polled_at=now)
    return _poll_result(POLL_PENDING, record.polling_interval)

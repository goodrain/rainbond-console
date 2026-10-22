import logging
import re
import socket
import time
from urllib.parse import unquote

_KEY_MARKERS = ("password", "passwd", "pwd", "token", "secret", "apikey", "api_key", "api-key", "accesskey", "access_key",
                "access-key", "authorization", "authzcode", "authz_code", "authz-code", "privatekey", "private_key",
                "private-key", "signingkey", "signing_key", "signing-key", "signature", "credential", "cookie")
_HEADER_KEYS = frozenset(("authorization", "proxy-authorization", "proxy_authorization", "cookie", "set-cookie", "set_cookie"))
_FIELD_RE = re.compile(r'''(?<![\w-])(?P<quote>["']?)(?P<key>[\w-]+)(?P=quote)[ \t]*[:=][ \t]*''')
_PEM_RE = re.compile(r"-----BEGIN [A-Z0-9 ]+-----.*?(?:-----END [A-Z0-9 ]+-----|\Z)", re.DOTALL)
_URL_USERINFO_RE = re.compile(r"(?<![\w+.-])([A-Za-z][A-Za-z0-9+.-]*://)[^\s/?#]*@")
_AUTH_VALUE_RE = re.compile(r'''\b(?:Bearer|Basic)\s+[^\s,'";}\]]+''', re.IGNORECASE)
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2}\b")
_QUERY_PAIR_RE = re.compile(r'''([?&])([^?&#=\s"']+)=([^&#\s"']*)''')
_SENSITIVE_MARKERS = ("password", "passwd", "pwd", "token", "secret", "key", "authorization", "authz", "credential", "cookie",
                      "sig", "basic", "bearer", "://", "?", "&", "eyj", "-----begin")


def _is_sensitive_key(key):
    lowered = key.lower()
    return any(marker in lowered for marker in _KEY_MARKERS) or 'sig' in lowered.replace('-', '_').split('_')


def _container_end(text, start):
    """Find a complete JSON/Python-style value without evaluating it; malformed values fail closed."""
    brackets = []
    quote = None
    escaped = False
    for index in range(start, len(text)):
        character = text[index]
        if quote:
            if escaped:
                escaped = False
            elif character == '\\':
                escaped = True
            elif character == quote:
                quote = None
        elif character in ('"', "'"):
            quote = character
        elif character in '[{':
            brackets.append(']' if character == '[' else '}')
        elif character in ']}':
            if not brackets or character != brackets.pop():
                return len(text)
            if not brackets:
                return index + 1
    return len(text)


def _value_end(text, start, header):
    if start >= len(text):
        return start
    first = text[start]
    if first in '[{':
        return _container_end(text, start)
    if first in ('"', "'"):
        escaped = False
        for index in range(start + 1, len(text)):
            if escaped:
                escaped = False
            elif text[index] == '\\':
                escaped = True
            elif text[index] == first:
                return index + 1
        return len(text)
    end = start
    while end < len(text):
        character = text[end]
        if header:
            if character in '\r\n}':
                break
        elif character.isspace() or character in (',', ';', '&', '}', ']', '"', "'"):
            break
        end += 1
    return end


def _redact_assignments(text):
    # Match complete field names first; key classification never sits between ambiguous regex repetitions.
    parts = []
    cursor = 0
    for match in _FIELD_RE.finditer(text):
        if match.start() < cursor or not _is_sensitive_key(match.group('key')):
            continue
        start = match.end()
        parts.extend((text[cursor:start], '[REDACTED]'))
        cursor = _value_end(text, start, match.group('key').lower() in _HEADER_KEYS)
    parts.append(text[cursor:])
    return ''.join(parts)


def _redact_query_pair(match):
    # Decode names for classification only; keep non-sensitive names and all original value bytes unchanged.
    if _is_sensitive_key(unquote(match.group(2))):
        return '{}{}=[REDACTED]'.format(match.group(1), match.group(2))
    return match.group(0)


def _redact_log_text(text):
    lowered = text.lower()
    if not any(marker in lowered for marker in _SENSITIVE_MARKERS):
        return text
    text = _PEM_RE.sub("[REDACTED]", text)
    text = _URL_USERINFO_RE.sub(r"\1[REDACTED]@", text)
    text = _QUERY_PAIR_RE.sub(_redact_query_pair, text)
    text = _redact_assignments(text)
    text = _AUTH_VALUE_RE.sub("[REDACTED]", text)
    return _JWT_RE.sub("[REDACTED]", text)


class IPFormatter(logging.Formatter):
    def format(self, record):
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = 'unknown'
        timestamp = time.strftime('%Y/%m/%d %H:%M:%S')
        module = getattr(record, 'module', 'unknown')
        level = getattr(record, 'levelname', 'INFO') or 'INFO'
        parts = [f"{level}[{timestamp}] ip={ip} module={module} {record.getMessage()}"]
        exception_text = record.exc_text
        if record.exc_info and not exception_text:
            try:
                exception_text = self.formatException(record.exc_info)
            except Exception:
                exception_text = '[exception traceback unavailable]'
        if exception_text:
            parts.append(exception_text)
        if record.stack_info:
            try:
                parts.append(self.formatStack(record.stack_info))
            except Exception:
                parts.append('[stack information unavailable]')
        # Never cache raw exception text on a shared LogRecord; every handler gets one safe trace.
        return _redact_log_text('\n'.join(parts))

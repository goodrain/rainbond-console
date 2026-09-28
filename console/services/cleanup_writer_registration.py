"""Lazy, authenticated Console runtime announcement; never a readiness grant."""
import os
import re
import threading
from typing import Any

_announced: set[tuple[str, str, str, str]] = set()
_lock = threading.Lock()


def announce_console_writer(enterprise: str, region: str, api: Any) -> bool:
    pod = os.environ.get('POD_NAME', '')
    uid = os.environ.get('POD_UID', '')
    if (not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,252}', pod)
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}', uid)):
        return False
    identity = (enterprise, region, pod, uid)
    with _lock:
        if identity in _announced:
            return True
    try:
        status, response = api.register_cleanup_console_writer(enterprise, region, pod, uid)
        bean = response.get('bean', {})
        if status != 200 or type(bean.get('protocol')) is not int or bean['protocol'] != 1 or bean.get('recorded') is not True:
            return False
    except Exception:
        # Do not leak Region errors, and do not break read-only inventory on an
        # old Core. Missing evidence keeps deletion uncertified in Core.
        return False
    with _lock:
        if len(_announced) >= 64:
            _announced.clear()
        _announced.add(identity)
    return True

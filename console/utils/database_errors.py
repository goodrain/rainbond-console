# -*- coding: utf-8 -*-

TRANSIENT_DATABASE_ERROR_CODES = frozenset((2002, 2003, 2005, 2006, 2013))
TRANSIENT_DATABASE_ERROR_MESSAGES = (
    "can't connect",
    "database is locked",
    "lost connection",
    "server has gone away",
    "unknown server host",
)


def is_transient_database_error(exc):
    for arg in getattr(exc, "args", ()):
        try:
            if int(arg) in TRANSIENT_DATABASE_ERROR_CODES:
                return True
        except (TypeError, ValueError):
            continue
    message = str(exc).lower()
    return any(marker in message for marker in TRANSIENT_DATABASE_ERROR_MESSAGES)

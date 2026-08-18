#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check database state through Django without exposing connection details."""

import os
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def get_connection():
    """Return Django's configured default connection after loading its backend."""
    repository_root = str(REPOSITORY_ROOT)
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

    import django
    from django.db import connection

    django.setup()
    return connection


def ensure_database_ready(connection=None):
    """Open the configured connection and return it when it is available."""
    connection = connection or get_connection()
    connection.ensure_connection()
    return connection


def database_is_empty(connection=None):
    """Return whether the configured database has no tables."""
    connection = ensure_database_ready(connection)
    return not connection.introspection.table_names()


def enable_sqlite_wal(connection=None):
    """Keep the previous SQLite write-ahead-log initialization behavior."""
    connection = ensure_database_ready(connection)
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode = WAL;")


def main(argv):
    if len(argv) != 1 or argv[0] not in {"ready", "empty", "sqlite-wal"}:
        sys.stderr.write("usage: database_state.py {ready|empty|sqlite-wal}\\n")
        return 2

    try:
        command = argv[0]
        if command == "ready":
            ensure_database_ready()
            return 0
        if command == "empty":
            return 0 if database_is_empty() else 1
        enable_sqlite_wal()
        return 0
    except Exception:
        sys.stderr.write("database is unavailable\\n")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

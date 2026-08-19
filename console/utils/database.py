# -*- coding: utf-8 -*-
"""Small, explicit database dialect helpers for Console raw SQL boundaries."""
from __future__ import unicode_literals

import os
import re


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?$")


def database_type(value=None):
    """Return the configured database type without treating all backends as MySQL."""
    return (value if value is not None else os.environ.get("DB_TYPE", "sqlite3")).lower()


def is_dm(value=None):
    return database_type(value) == "dm"


def normalize_result_column(column, db_type=None):
    """Map DM's unquoted uppercase result labels to existing Console dictionary keys."""
    if is_dm(db_type):
        return column.lower()
    return column


def cast_integer(expression, db_type=None):
    if database_type(db_type) == "mysql":
        return "CAST({0} AS SIGNED)".format(expression)
    return "CAST({0} AS INTEGER)".format(expression)


def cast_text(expression, db_type=None):
    if database_type(db_type) == "mysql":
        return "CAST({0} AS CHAR)".format(expression)
    if is_dm(db_type):
        return "CAST({0} AS VARCHAR(255))".format(expression)
    return "CAST({0} AS TEXT)".format(expression)


def list_aggregate(expression, db_type=None, order_by=None):
    """Return the equivalent string aggregation expression for a trusted SQL expression."""
    if not is_dm(db_type):
        return "GROUP_CONCAT({0})".format(expression)

    order_by = order_by or expression
    if not _IDENTIFIER.match(order_by):
        raise ValueError("list aggregate order_by must be a SQL identifier")
    return "LISTAGG({0}, ',') WITHIN GROUP (ORDER BY {1})".format(expression, order_by)


def in_clause(values):
    """Return a parameter placeholder list and values for an SQL IN predicate."""
    values = list(values)
    if not values:
        return "(NULL)", []
    return "({0})".format(", ".join(["%s"] * len(values))), values


def pagination_clause(db_type, offset, limit):
    """Render a parameterized pagination suffix and matching values."""
    if is_dm(db_type):
        return " LIMIT %s OFFSET %s", [limit, offset]
    return " LIMIT %s, %s", [offset, limit]

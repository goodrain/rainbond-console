# -*- coding: utf-8 -*-
"""Test settings for local backend test runs."""

import os

os.environ["RAINBOND_TELEMETRY_DISABLED"] = "1"
os.environ["RAINBOND_ERROR_REPORTING_DISABLED"] = "1"

from .settings import *  # noqa: F401,F403,E402


DEBUG = False
TEMPLATE_DEBUG = False
DATABASE_TYPE = "sqlite3"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(DATA_DIR, "test_db.sqlite3"),  # noqa: F405
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "timeout": 20,
        },
    }
}
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

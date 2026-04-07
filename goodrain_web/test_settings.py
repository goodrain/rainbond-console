# -*- coding: utf-8 -*-
"""Test settings for local backend test runs."""

import os

from .settings import *  # noqa: F401,F403


DEBUG = False
TEMPLATE_DEBUG = False
DATABASE_TYPE = "sqlite3"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(DATA_DIR, "test_db.sqlite3"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "timeout": 20,
        },
    }
}
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

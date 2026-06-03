# -*- coding: utf8 -*-
import os

TRUE_VALUES = ("1", "true", "yes", "on")


def env_is_true(name):
    return str(os.getenv(name, "")).strip().lower() in TRUE_VALUES


def is_cloud_market_disabled():
    return env_is_true("DISABLE_DEFAULT_APP_MARKET") or env_is_true("DISABLE_CLOUD_MARKET")

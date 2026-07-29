# -*- coding: utf8 -*-
import os

TRUE_VALUES = ("1", "true", "yes", "on")


def env_is_true(name, env=None):
    source = os.environ if env is None else env
    return str(source.get(name, "")).strip().lower() in TRUE_VALUES


def is_offline_mode(env=None):
    return env_is_true("DISABLE_DEFAULT_APP_MARKET", env)


def is_cloud_market_disabled():
    return is_offline_mode() or env_is_true("DISABLE_CLOUD_MARKET")

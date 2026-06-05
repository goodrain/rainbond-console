#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import subprocess
import sys


TEST_FILE_SUFFIXES = ("_test.py", "_tests.py")
EXCLUDED_DIRS = {
    ".git",
    ".claude",
    ".tox",
    "__pycache__",
    "env",
    "venv",
    "venv3",
}
EXCLUDED_FILES = {
    os.path.join("goodrain_web", "test_settings.py"),
    os.path.join("scripts", "run_django_tests.py"),
}


def is_test_file(path):
    normalized = os.path.normpath(path)
    if normalized in EXCLUDED_FILES:
        return False

    name = os.path.basename(path)
    return (
        name == "tests.py"
        or name.startswith("test_") and name.endswith(".py")
        or name.endswith(TEST_FILE_SUFFIXES)
    )


def collect_test_files(paths):
    files = []
    for path in paths:
        if os.path.isfile(path):
            if is_test_file(path):
                files.append(path)
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [
                dirname for dirname in dirnames
                if dirname not in EXCLUDED_DIRS
            ]
            for name in filenames:
                candidate = os.path.join(dirpath, name)
                if is_test_file(candidate):
                    files.append(candidate)
    return sorted(set(files))


def run_worker(test_file, pytest_args):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    openapi_client_path = os.path.join(repo_root, "src", "openapi-client")
    pip_src_openapi_client_path = None
    if os.environ.get("PIP_SRC"):
        pip_src_openapi_client_path = os.path.join(os.environ["PIP_SRC"], "openapi-client")
    home_dir = os.environ.get("HOME_DIR", repo_root)
    data_dir = os.environ.get("DATA_DIR", os.path.join(home_dir, "data"))
    test_dir = os.path.abspath(os.path.dirname(test_file))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    if test_dir not in sys.path:
        sys.path.insert(0, test_dir)
    if pip_src_openapi_client_path and pip_src_openapi_client_path not in sys.path:
        sys.path.insert(0, pip_src_openapi_client_path)
    if openapi_client_path not in sys.path:
        sys.path.insert(0, openapi_client_path)

    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

    import django
    import pytest

    django.setup()
    return pytest.main(["-p", "no:django", test_file] + pytest_args)


def split_args(argv):
    if "--" in argv:
        separator = argv.index("--")
        return argv[:separator], argv[separator + 1:]
    return argv, []


def setup_test_database():
    """Create the sqlite test schema once before workers run.

    Workers run each test file with ``-p no:django``, so Django's test runner
    never calls ``setup_databases`` and the sqlite test DB stays empty. Tests
    that use ``django.test.TestCase`` and touch the ORM then fail with
    ``no such table``. We migrate the configured sqlite database (see
    ``goodrain_web.test_settings``) a single time here; each worker connects to
    the same file and TestCase wraps every test in a transaction that rolls
    back, so the shared schema stays clean across the sequentially-run workers.
    """
    import importlib
    import pkgutil

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    openapi_client_path = os.path.join(repo_root, "src", "openapi-client")
    pip_src_openapi_client_path = None
    if os.environ.get("PIP_SRC"):
        pip_src_openapi_client_path = os.path.join(os.environ["PIP_SRC"], "openapi-client")
    home_dir = os.environ.get("HOME_DIR", repo_root)
    data_dir = os.environ.get("DATA_DIR", os.path.join(home_dir, "data"))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    if pip_src_openapi_client_path and pip_src_openapi_client_path not in sys.path:
        sys.path.insert(0, pip_src_openapi_client_path)
    if openapi_client_path not in sys.path:
        sys.path.insert(0, openapi_client_path)
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

    import django
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connections

    django.setup()

    # Start from a clean schema every run so a stale file can't mask drift.
    db_name = settings.DATABASES["default"]["NAME"]
    if db_name and db_name != ":memory:" and os.path.exists(db_name):
        os.remove(db_name)

    # ``run_syncdb`` only creates tables for *registered* models. Some models
    # live in modules their app package does not import (e.g. www/models/label.py),
    # so import every model submodule first to register them.
    for package_name in ("www.models", "console.models", "console.cloud.models"):
        try:
            package = importlib.import_module(package_name)
        except Exception:
            continue
        if not hasattr(package, "__path__"):
            continue
        for module_info in pkgutil.walk_packages(package.__path__, package_name + "."):
            try:
                importlib.import_module(module_info.name)
            except Exception:
                pass

    call_command("migrate", run_syncdb=True, verbosity=0, interactive=False)
    connections.close_all()


def main(argv):
    if argv and argv[0] == "--worker":
        if len(argv) < 2:
            print("missing test file", file=sys.stderr)
            return 2
        return run_worker(argv[1], argv[2:])

    paths, pytest_args = split_args(argv)
    paths = paths or ["."]
    test_files = collect_test_files(paths)
    if not test_files:
        print("no test files found", file=sys.stderr)
        return 2

    setup_test_database()

    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

    failed = []
    for test_file in test_files:
        print("pytest {}".format(test_file), flush=True)
        code = subprocess.call([sys.executable, __file__, "--worker", test_file] + pytest_args, env=env)
        if code != 0:
            failed.append(test_file)

    if failed:
        print("\nfailed test files:")
        for test_file in failed:
            print("  {}".format(test_file))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

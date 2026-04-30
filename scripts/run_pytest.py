#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import subprocess
import sys


TEST_FILE_SUFFIXES = ("_test.py", "_tests.py")
EXCLUDED_DIRS = {
    ".git",
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
    test_dir = os.path.abspath(os.path.dirname(test_file))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    if test_dir not in sys.path:
        sys.path.insert(0, test_dir)
    if openapi_client_path not in sys.path:
        sys.path.insert(0, openapi_client_path)

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

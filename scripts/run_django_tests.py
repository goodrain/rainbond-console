#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from types import ModuleType


def main():
    repo_root = Path(__file__).resolve().parents[1]
    openapi_client_root = repo_root / "src" / "openapi-client"
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(openapi_client_root))
    sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(["manage.py", "test"] + sys.argv[1:])


if __name__ == "__main__":
    main()

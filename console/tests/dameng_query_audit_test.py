# -*- coding: utf-8 -*-
import ast
import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RAW_SQL_FILES = (
    "console/repositories/app.py",
    "console/repositories/user_role_repo.py",
    "console/services/service_services.py",
    "console/services/market_app_service.py",
)

BOUND_QUERY_FILES = (
    "console/syncservice/create_default_group.py",
    "console/syncservice/sync_manage.py",
    "console/repositories/app.py",
    "console/repositories/app_config.py",
    "console/repositories/enterprise_repo.py",
    "console/repositories/plugin/plugin.py",
    "console/repositories/service_repo.py",
    "console/repositories/share_repo.py",
    "console/repositories/team_repo.py",
    "console/repositories/tenant_region_repo.py",
    "console/repositories/user_repo.py",
    "console/services/app_config/domain_service.py",
    "console/services/app_config/plugin_service.py",
    "console/services/plugin/app_plugin.py",
    "console/services/service_services.py",
    "console/views/app_config/app_domain.py",
    "console/views/app_config/app_env.py",
    "console/views/public_areas.py",
    "openapi/views/enterprise_view.py",
    "openapi/v2/views/enterprise_view.py",
    "www/db/service_group_repository.py",
    "www/services/plugin.py",
)


# capability_id: console.database.dm-raw-sql-audit
class DamengQueryAuditTests(unittest.TestCase):
    def test_mysql_only_group_concat_is_not_left_in_production_queries(self):
        for relative_path in RAW_SQL_FILES:
            source = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(r"\bGROUP_CONCAT\s*\(", source, re.IGNORECASE),
                "{} still embeds a MySQL-only GROUP_CONCAT expression".format(relative_path),
            )

    def test_raw_query_calls_do_not_interpolate_runtime_values(self):
        for relative_path in BOUND_QUERY_FILES:
            source = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative_path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                if not isinstance(node.func, ast.Attribute) or node.func.attr not in ("execute", "query"):
                    continue
                query = node.args[0]
                self.assertFalse(
                    isinstance(query, ast.Call)
                    and isinstance(query.func, ast.Attribute)
                    and query.func.attr == "format",
                    "{}:{} interpolates a SQL query at execution time".format(relative_path, node.lineno),
                )
                self.assertFalse(
                    isinstance(query, ast.BinOp) and isinstance(query.op, ast.Mod),
                    "{}:{} applies percent interpolation to a SQL query at execution time".format(
                        relative_path, node.lineno
                    ),
                )

    def test_raw_pagination_is_centralized_in_database_capabilities(self):
        for relative_path in BOUND_QUERY_FILES:
            source = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(r"\\bLIMIT\\s+(?:\\{|%s\\s*,|\\?\\s*,)", source, re.IGNORECASE),
                "{} still embeds a database-specific pagination clause".format(relative_path),
            )


if __name__ == "__main__":
    unittest.main()

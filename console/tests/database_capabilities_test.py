# -*- coding: utf-8 -*-
import unittest

from console.utils.database import cast_integer, cast_text, in_clause, list_aggregate, normalize_result_column, pagination_clause


# capability_id: console.database.dm-query-capabilities
class DatabaseCapabilitiesTests(unittest.TestCase):
    def test_dm_normalizes_driver_column_labels(self):
        self.assertEqual(normalize_result_column("SERVICE_ID", "dm"), "service_id")
        self.assertEqual(normalize_result_column("quoted_alias", "dm"), "quoted_alias")

    def test_mysql_preserves_result_column_labels(self):
        self.assertEqual(normalize_result_column("SERVICE_ID", "mysql"), "SERVICE_ID")

    def test_list_aggregate_uses_a_dm_expression_and_keeps_mysql_expression(self):
        expression = "CONCAT('\"', service_id, '\"')"

        self.assertEqual(
            list_aggregate(expression, "mysql", order_by="service_id"),
            "GROUP_CONCAT(CONCAT('\"', service_id, '\"'))",
        )
        self.assertEqual(
            list_aggregate(expression, "dm", order_by="service_id"),
            "LISTAGG(CONCAT('\"', service_id, '\"'), ',') WITHIN GROUP (ORDER BY service_id)",
        )

    def test_pagination_preserves_mysql_and_uses_dm_limit_offset(self):
        self.assertEqual(pagination_clause("mysql", 20, 40), (" LIMIT %s, %s", [20, 40]))
        self.assertEqual(pagination_clause("dm", 20, 40), (" LIMIT %s OFFSET %s", [40, 20]))

    def test_in_clause_never_formats_values_into_sql(self):
        clause, values = in_clause(["team-a", "team-b"])

        self.assertEqual(clause, "(%s, %s)")
        self.assertEqual(values, ["team-a", "team-b"])

    def test_role_permission_casts_do_not_send_mysql_types_to_dameng(self):
        self.assertEqual(cast_integer("ur.role_id", "mysql"), "CAST(ur.role_id AS SIGNED)")
        self.assertEqual(cast_integer("ur.role_id", "dm"), "CAST(ur.role_id AS INTEGER)")
        self.assertEqual(cast_text("ri.ID", "dm"), "CAST(ri.ID AS VARCHAR(255))")


if __name__ == "__main__":
    unittest.main()

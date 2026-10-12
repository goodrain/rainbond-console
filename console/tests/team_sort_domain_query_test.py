# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.views import team as team_view_module  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# capability_id: console.team-domain-monitor.time-range-validation
class TeamSortDomainQueryTimeRangeTests(TestCase):
    def setUp(self):
        self.view = team_view_module.TeamSortDomainQueryView()
        self.view.tenant = Obj(tenant_id="tenant-id")

    def test_range_query_rejects_missing_start_or_end_before_region_call(self):
        for query in (
                {"repo": "2"},
                {"repo": "2", "start": "1710000000"},
                {"repo": "2", "page": "invalid"},
        ):
            with self.subTest(query=query), mock.patch.object(
                    team_view_module.region_api,
                    "get_query_range_data",
            ) as get_query_range:
                response = self.view.get(
                    Obj(GET=query),
                    team_name="demo-team",
                    region_name="demo-region",
                )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["msg_show"], "缺少时间范围参数")
            get_query_range.assert_not_called()

    def test_range_query_forwards_complete_time_range(self):
        body = {"data": {"result": []}}
        with mock.patch.object(
                team_view_module.region_api,
                "get_query_range_data",
                return_value=(mock.Mock(), body),
        ) as get_query_range:
            response = self.view.get(
                Obj(GET={"repo": "2", "start": "1710000000", "end": "1710003600"}),
                team_name="demo-team",
                region_name="demo-region",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], body)
        query = get_query_range.call_args[0][2]
        self.assertIn("start=1710000000", query)
        self.assertIn("end=1710003600", query)

    def test_rank_query_keeps_existing_pagination_behavior(self):
        body = {
            "data": {
                "result": [
                    {"metric": {"host": "one.example.com"}, "value": [0, "10"]},
                    {"metric": {"host": "two.example.com"}, "value": [0, "20"]},
                ]
            }
        }
        with mock.patch.object(
                team_view_module.region_api,
                "get_query_domain_access",
                return_value=(mock.Mock(), body),
        ):
            response = self.view.get(
                Obj(GET={"repo": "1", "page": "2", "page_size": "1"}),
                team_name="demo-team",
                region_name="demo-region",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"], [body["data"]["result"][1]])
        self.assertEqual(response.data["data"]["bean"], {"total": 2, "total_traffic": 30})

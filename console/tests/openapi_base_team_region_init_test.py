# -*- coding: utf-8 -*-
import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from openapi.views.base import TeamAPIView, TeamNoRegionAPIView  # noqa: E402
from openapi.views.exceptions import ErrTeamNotInitializedInRegion  # noqa: E402


# capability_id: openapi.base.team-not-initialized-in-region
class TeamAPIViewRegionInitTest(TestCase):

    def _run_initial(self, team_usable_regions_return):
        view = TeamAPIView()
        view.team = mock.Mock(tenant_name="team1")
        view.enterprise = mock.Mock(enterprise_id="ent1")
        view.region_name = None
        view.region = None

        request = mock.Mock()

        with mock.patch.object(TeamNoRegionAPIView, "initial"), \
             mock.patch("openapi.views.base.region_services") as mock_rs:
            mock_rs.get_enterprise_region_by_region_name.return_value = mock.Mock()
            mock_rs.get_team_usable_regions.return_value = team_usable_regions_return
            TeamAPIView.initial(view, request, region_name="rg1")

    def test_raises_when_team_regions_is_none(self):
        with self.assertRaises(type(ErrTeamNotInitializedInRegion)):
            self._run_initial(team_usable_regions_return=None)

    def test_raises_when_region_not_in_team_regions(self):
        mock_qs = mock.Mock()
        mock_qs.filter.return_value.exists.return_value = False
        with self.assertRaises(type(ErrTeamNotInitializedInRegion)):
            self._run_initial(team_usable_regions_return=mock_qs)

    def test_passes_when_region_exists_in_team_regions(self):
        mock_qs = mock.Mock()
        mock_qs.filter.return_value.exists.return_value = True
        self._run_initial(team_usable_regions_return=mock_qs)

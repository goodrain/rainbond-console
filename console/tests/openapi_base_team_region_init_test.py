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

from openapi.views.base import TeamAPIView  # noqa: E402
from openapi.views.exceptions import ErrTeamNotInitializedInRegion  # noqa: E402


# capability_id: openapi.base.team-not-initialized-in-region
class TeamAPIViewRegionInitTest(TestCase):

    def _make_request(self):
        request = mock.Mock()
        request.user.enterprise_id = "ent1"
        request.user.user_id = "user1"
        request.user.is_administrator = False
        return request

    @mock.patch("openapi.views.base.EnterpriseUserPerm")
    @mock.patch("openapi.views.base.TenantEnterprise")
    @mock.patch("openapi.views.base.region_services")
    @mock.patch("openapi.views.base.team_services")
    @mock.patch("openapi.views.base.enterprise_services")
    def test_raises_when_team_regions_is_none(self, mock_ent_svc, mock_team_svc,
                                             mock_region_svc, mock_tenant_ent, mock_eup):
        request = self._make_request()

        mock_ent = mock.Mock(ID=2, enterprise_id="ent1")
        mock_ent_svc.get_enterprise_by_id.return_value = mock_ent

        mock_team = mock.Mock(tenant_id="t1", tenant_name="team1",
                              enterprise_id="ent1", creater="user1")
        mock_team_svc.get_team_by_team_id_and_eid.return_value = mock_team

        mock_region_svc.get_enterprise_region_by_region_name.return_value = mock.Mock()

        mock_tenant_ent.filter.return_value.first.return_value = mock.Mock()
        mock_eup.filter.return_value.first.return_value = None

        view = TeamAPIView()
        view.team = mock_team
        view.enterprise = mock_ent

        with self.assertRaises(type(ErrTeamNotInitializedInRegion)):
            TeamAPIView.initial(view, request, region_name="rg1")

    @mock.patch("openapi.views.base.EnterpriseUserPerm")
    @mock.patch("openapi.views.base.TenantEnterprise")
    @mock.patch("openapi.views.base.region_services")
    @mock.patch("openapi.views.base.team_services")
    @mock.patch("openapi.views.base.enterprise_services")
    def test_raises_when_region_not_in_team_regions(self, mock_ent_svc, mock_team_svc,
                                                   mock_region_svc, mock_tenant_ent, mock_eup):
        request = self._make_request()

        mock_ent = mock.Mock(ID=2, enterprise_id="ent1")
        mock_ent_svc.get_enterprise_by_id.return_value = mock_ent

        mock_team = mock.Mock(tenant_id="t1", tenant_name="team1",
                              enterprise_id="ent1", creater="user1")
        mock_team_svc.get_team_by_team_id_and_eid.return_value = mock_team

        mock_region_svc.get_enterprise_region_by_region_name.return_value = mock.Mock()

        mock_qs = mock.Mock()
        mock_qs.filter.return_value.exists.return_value = False
        mock_region_svc.get_team_usable_regions.return_value = mock_qs

        mock_tenant_ent.filter.return_value.first.return_value = mock.Mock()
        mock_eup.filter.return_value.first.return_value = None

        view = TeamAPIView()
        view.team = mock_team
        view.enterprise = mock_ent

        with self.assertRaises(type(ErrTeamNotInitializedInRegion)):
            TeamAPIView.initial(view, request, region_name="rg1")

    @mock.patch("openapi.views.base.EnterpriseUserPerm")
    @mock.patch("openapi.views.base.TenantEnterprise")
    @mock.patch("openapi.views.base.region_services")
    @mock.patch("openapi.views.base.team_services")
    @mock.patch("openapi.views.base.enterprise_services")
    def test_passes_when_region_exists_in_team_regions(self, mock_ent_svc, mock_team_svc,
                                                     mock_region_svc, mock_tenant_ent, mock_eup):
        request = self._make_request()

        mock_ent = mock.Mock(ID=2, enterprise_id="ent1")
        mock_ent_svc.get_enterprise_by_id.return_value = mock_ent

        mock_team = mock.Mock(tenant_id="t1", tenant_name="team1",
                              enterprise_id="ent1", creater="user1")
        mock_team_svc.get_team_by_team_id_and_eid.return_value = mock_team

        mock_region_svc.get_enterprise_region_by_region_name.return_value = mock.Mock()

        mock_qs = mock.Mock()
        mock_qs.filter.return_value.exists.return_value = True
        mock_region_svc.get_team_usable_regions.return_value = mock_qs

        mock_tenant_ent.filter.return_value.first.return_value = mock.Mock()
        mock_eup.filter.return_value.first.return_value = None

        view = TeamAPIView()
        view.team = mock_team
        view.enterprise = mock_ent

        TeamAPIView.initial(view, request, region_name="rg1")

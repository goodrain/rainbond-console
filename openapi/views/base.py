# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework.views import APIView
from openapi.auth.authentication import OpenAPIAuthentication, OpenAPIManageAuthentication
from openapi.auth.permissions import OpenAPIPermissions
from console.services.enterprise_services import enterprise_services
from console.services.region_services import region_services
from console.services.team_services import team_services
from openapi.views.exceptions import ErrTeamNotFound, ErrEnterpriseNotFound, ErrRegionNotFound
from rest_framework import generics


class ListAPIView(generics.ListAPIView):
    authentication_classes = [OpenAPIManageAuthentication]
    permission_classes = [OpenAPIPermissions]


class BaseOpenAPIView(APIView):
    authentication_classes = [OpenAPIAuthentication]
    permission_classes = [OpenAPIPermissions]

    def __init__(self):
        super(BaseOpenAPIView, self).__init__()
        self.enterprise = None
        self.regions = None

    def initial(self, request, *args, **kwargs):
        super(BaseOpenAPIView, self).initial(request, *args, **kwargs)
        request.user.is_administrator = False
        if hasattr(request.user, "enterprise_id"):
            self.enterprise = enterprise_services.get_enterprise_by_id(request.user.enterprise_id)
            if not self.enterprise:
                raise ErrEnterpriseNotFound
            if self.enterprise.ID == 1:
                request.user.is_administrator = True


class TeamAPIView(BaseOpenAPIView):
    def __init__(self):
        super(TeamAPIView, self).__init__()
        self.team = None
        self.region_name = None

    def initial(self, request, *args, **kwargs):
        super(TeamAPIView, self).initial(request, *args, **kwargs)
        team_id = kwargs.get("team_id")
        self.region_name = kwargs.get("region_name")
        if self.region_name:
            self.region = region_services.get_enterprise_region_by_region_name(enterprise_id=self.enterprise.enterprise_id,
                                                                               region_name=self.region_name)
        if not self.region:
            raise ErrRegionNotFound
        if team_id:
            # team_id support id and name
            self.team = team_services.get_enterprise_tenant_by_tenant_name(enterprise_id=self.enterprise.enterprise_id,
                                                                           tenant_name=team_id)
            if not self.team:
                self.team = team_services.get_team_by_team_id_and_eid(team_id=team_id,
                                                                      enterprise_id=self.enterprise.enterprise_id)
            if not self.team:
                raise ErrTeamNotFound
            self.team_regions = region_services.get_team_usable_regions(self.team.tenant_name, self.enterprise.enterprise_id)

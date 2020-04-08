# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework.views import APIView
from openapi.auth.authentication import OpenAPIAuthentication
from openapi.auth.permissions import OpenAPIPermissions
from console.services.enterprise_services import enterprise_services
from console.services.region_services import region_services
from console.services.team_services import team_services
from rest_framework import generics


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
            if self.enterprise.ID == 1:
                request.user.is_administrator = True


class ListAPIView(generics.ListAPIView):
    authentication_classes = [OpenAPIAuthentication]
    permission_classes = [OpenAPIPermissions]


class TeamAPIView(BaseOpenAPIView):
    def __init__(self):
        super(TeamAPIView, self).__init__()
        self.team = None

    def initial(self, request, *args, **kwargs):
        super(TeamAPIView, self).initial(request, *args, **kwargs)
        team_id = kwargs.get("team_id")
        if team_id:
            self.team = team_services.get_team_by_team_id(team_id)
            self.team_regions = region_services.get_team_usable_regions(self.team.tenant_name)

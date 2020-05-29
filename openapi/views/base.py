# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework.views import APIView
from rest_framework import generics

from console.exception.main import NoPermissionsError
from console.exception.main import ServiceHandleException
from console.services.enterprise_services import enterprise_services
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.services.group_service import group_service
from console.models.main import EnterpriseUserPerm
from console.models.main import PermsInfo
from console.models.main import UserRole
from console.models.main import RoleInfo
from console.models.main import RolePerms
from www.models.main import TenantEnterprise

from openapi.auth.authentication import OpenAPIAuthentication
from openapi.auth.permissions import OpenAPIPermissions


class BaseOpenAPIView(APIView):
    authentication_classes = [OpenAPIAuthentication]
    permission_classes = [OpenAPIPermissions]

    def __init__(self):
        super(BaseOpenAPIView, self).__init__()
        self.enterprise = None
        self.regions = None
        self.user = None
        self.is_enterprise_admin = None

    def check_perms(self, request, *args, **kwargs):
        if kwargs.get("__message"):
            request_perms = kwargs["__message"][request.META.get("REQUEST_METHOD").lower()]["perms"]
            if request_perms:
                if len(set(request_perms) & set(self.user_perms)) != len(set(request_perms)):
                    raise NoPermissionsError

    def has_perms(self, request_perms):
        if request_perms:
            if len(set(request_perms) & set(self.user_perms)) != len(set(request_perms)):
                raise NoPermissionsError

    def get_perms(self):
        self.user_perms = []
        if self.is_enterprise_admin:
            self.user_perms = list(PermsInfo.objects.all().values_list("code", flat=True))
            self.user_perms.extend([100000, 200000])
        roles = RoleInfo.objects.filter(kind="enterprise", kind_id=self.user.enterprise_id)
        if roles:
            role_ids = roles.values_list("ID", flat=True)
            user_roles = UserRole.objects.filter(user_id=self.user.user_id, role_id__in=role_ids)
            if user_roles:
                user_role_ids = user_roles.values_list("role_id", flat=True)
                role_perms = RolePerms.objects.filter(role_id__in=user_role_ids)
                if role_perms:
                    self.user_perms = role_perms.values_list("perm_code", flat=True)
        self.user_perms = list(set(self.user_perms))

    def initial(self, request, *args, **kwargs):
        super(BaseOpenAPIView, self).initial(request, *args, **kwargs)
        request.user.is_administrator = False
        if hasattr(request.user, "enterprise_id"):
            self.enterprise = enterprise_services.get_enterprise_by_id(request.user.enterprise_id)
            if self.enterprise.ID == 1:
                request.user.is_administrator = True
        self.user = request.user


class ListAPIView(generics.ListAPIView):
    authentication_classes = [OpenAPIAuthentication]
    permission_classes = [OpenAPIPermissions]


class TeamAPIView(BaseOpenAPIView):
    def __init__(self):
        super(TeamAPIView, self).__init__()
        self.team = None
        self.region_name = None
        self.is_team_owner = False

    def get_perms(self):
        self.user_perms = []
        if self.is_enterprise_admin:
            self.user_perms = list(PermsInfo.objects.all().values_list("code", flat=True))
            self.user_perms.extend([100000, 200000])
        else:
            ent_roles = RoleInfo.objects.filter(kind="enterprise", kind_id=self.user.enterprise_id)
            if ent_roles:
                ent_role_ids = ent_roles.values_list("ID", flat=True)
                ent_user_roles = UserRole.objects.filter(user_id=self.user.user_id, role_id__in=ent_role_ids)
                if ent_user_roles:
                    ent_user_role_ids = ent_user_roles.values_list("role_id", flat=True)
                    ent_role_perms = RolePerms.objects.filter(role_id__in=ent_user_role_ids)
                    if ent_role_perms:
                        self.user_perms = list(ent_role_perms.values_list("perm_code", flat=True))

        if self.is_team_owner:
            team_perms = list(PermsInfo.objects.filter(kind="team").values_list("code", flat=True))
            self.user_perms.extend(team_perms)
            self.user_perms.append(200000)
        else:
            team_roles = RoleInfo.objects.filter(kind="team", kind_id=self.team.tenant_id)
            if team_roles:
                role_ids = team_roles.values_list("ID", flat=True)
                team_user_roles = UserRole.objects.filter(user_id=self.user.user_id, role_id__in=role_ids)
                if team_user_roles:
                    team_user_role_ids = team_user_roles.values_list("role_id", flat=True)
                    team_role_perms = RolePerms.objects.filter(role_id__in=team_user_role_ids)
                    if team_role_perms:
                        self.user_perms.extend(list(team_role_perms.values_list("perm_code", flat=True)))
        self.user_perms = list(set(self.user_perms))

    def initial(self, request, *args, **kwargs):
        super(TeamAPIView, self).initial(request, *args, **kwargs)
        team_id = kwargs.get("team_id")
        app_id = kwargs.get("app_id")
        region_name = kwargs.get("region_name")
        if region_name:
            self.region_name = region_name
        if team_id:
            self.team = team_services.get_team_by_team_id(team_id)
        if app_id:
            app = group_service.get_app_by_id(app_id)
            self.region_name = app.region_name
            self.team = team_services.get_team_by_team_id(app.tenant_id)
        if not self.team:
            raise ServiceHandleException(msg_show=u"团队不存在", msg="no found team", status_code=404)
        self.team_regions = region_services.get_team_usable_regions(self.team.tenant_name)
        if self.user.user_id == self.team.creater:
            self.is_team_owner = True
        self.enterprise = TenantEnterprise.objects.filter(enterprise_id=self.team.enterprise_id).first()
        self.is_enterprise_admin = False
        enterprise_user_perms = EnterpriseUserPerm.objects.filter(
            enterprise_id=self.team.enterprise_id, user_id=self.user.user_id).first()
        if enterprise_user_perms:
            self.is_enterprise_admin = True
        self.get_perms()
        self.check_perms(request, *args, **kwargs)

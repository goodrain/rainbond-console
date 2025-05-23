# -*- coding: utf-8 -*-
# creater by: barnett
import os

from rest_framework import generics
from rest_framework.views import APIView

from console.services.user_services import user_services
from console.exception.main import NoPermissionsError, ServiceHandleException
from console.models.main import (EnterpriseUserPerm, OAuthServices, PermsInfo, RoleInfo, RolePerms, UserOAuthServices, UserRole)
from console.repositories.group import group_service_relation_repo
from console.repositories.region_repo import region_repo
from console.services.enterprise_services import enterprise_services
from console.services.group_service import group_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.utils.oauth.oauth_types import get_oauth_instance
from openapi.auth.authentication import (OpenAPIAuthentication, OpenAPIManageAuthentication)
from openapi.auth.permissions import OpenAPIPermissions
from openapi.views.exceptions import ErrEnterpriseNotFound, ErrRegionNotFound
from www.models.main import TenantEnterprise, TenantServiceInfo
from console.utils import perms


class ListAPIView(generics.ListAPIView):
    authentication_classes = [OpenAPIManageAuthentication]
    permission_classes = [OpenAPIPermissions]


class BaseOpenAPIView(APIView):
    authentication_classes = [OpenAPIAuthentication]
    permission_classes = [OpenAPIPermissions]

    def __init__(self):
        super(BaseOpenAPIView, self).__init__()
        self.enterprise = None
        self.region_name = None
        self.regions = None
        self.user = None

    def check_perms(self, request, *args, **kwargs):
        if kwargs.get("__message"):
            if kwargs.get("app_id"):
                pass
            request_perms = kwargs["__message"][request.META.get("REQUEST_METHOD").lower()]["perms"]
            if request_perms and (len(set(request_perms) & set(self.user_perms)) != len(set(request_perms))):
                raise NoPermissionsError

    def has_perms(self, request_perms):
        if request_perms and (len(set(request_perms) & set(self.user_perms)) != len(set(request_perms))):
            raise NoPermissionsError

    def get_perms(self):
        self.user_perms = []
        admin_roles = user_services.list_roles(self.user.enterprise_id, self.user.user_id)
        self.user_perms = list(perms.list_enterprise_perm_codes_by_roles(admin_roles))

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
        request.user.is_ = False
        if hasattr(request.user, "enterprise_id"):
            self.enterprise = enterprise_services.get_enterprise_by_id(request.user.enterprise_id)
        if not self.enterprise:
            raise ErrEnterpriseNotFound
        self.region_name = kwargs.get("region_name")
        if not self.region_name:
            self.region_name = kwargs.get("region_id")
        if self.region_name:
            self.region = region_services.get_enterprise_region_by_region_name(
                enterprise_id=self.enterprise.enterprise_id, region_name=self.region_name)
            if not self.region:
                self.region = region_repo.get_region_by_id(self.enterprise.enterprise_id, self.region_name)
        # Temporary logic
        if self.enterprise.ID == 1:
            request.user.is_administrator = True
        self.user = request.user
        self.get_perms()
        self.check_perms(request, *args, **kwargs)


class TeamNoRegionAPIView(BaseOpenAPIView):
    def __init__(self):
        super(TeamNoRegionAPIView, self).__init__()
        self.team = None
        self.is_team_owner = False

    def get_perms(self):
        self.user_perms = []
        admin_roles = user_services.list_roles(self.user.enterprise_id, self.user.user_id)
        self.user_perms = list(perms.list_enterprise_perm_codes_by_roles(admin_roles))

        if self.is_team_owner:
            team_perms = list(PermsInfo.objects.filter(kind="team").values_list("code", flat=True))
            self.user_perms.extend(team_perms)
            self.user_perms.append(100001)
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
        request.user.is_administrator = False
        if hasattr(request.user, "enterprise_id"):
            self.enterprise = enterprise_services.get_enterprise_by_id(request.user.enterprise_id)
        if not self.enterprise:
            raise ErrEnterpriseNotFound
        if self.enterprise.ID == 1:
            request.user.is_administrator = True
        self.user = request.user
        self.is_team_owner = False
        team_id = kwargs.get("team_id")
        if team_id:
            self.team = team_services.get_team_by_team_id_and_eid(team_id, self.enterprise.enterprise_id)
        if not self.team:
            self.team = team_services.get_enterprise_tenant_by_tenant_name(self.enterprise.enterprise_id, team_id)
        if not self.team:
            raise ServiceHandleException(msg_show="团队不存在", msg="no found team", status_code=404)
        self.team_regions = region_services.get_team_usable_regions(self.team.tenant_name, self.enterprise.enterprise_id)
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


class TeamAPIView(TeamNoRegionAPIView):
    def __init__(self):
        super(TeamAPIView, self).__init__()
        self.region_name = None
        self.region = None

    def initial(self, request, *args, **kwargs):
        super(TeamAPIView, self).initial(request, *args, **kwargs)
        self.region_name = kwargs.get("region_name")
        if self.region_name:
            self.region = region_services.get_enterprise_region_by_region_name(
                enterprise_id=self.enterprise.enterprise_id, region_name=self.region_name)
        else:
            raise ErrRegionNotFound
        if not self.region:
            raise ErrRegionNotFound


class TeamAppAPIView(TeamAPIView):
    def __init__(self):
        super(TeamAppAPIView, self).__init__()
        self.app = None

    def initial(self, request, *args, **kwargs):
        super(TeamAppAPIView, self).initial(request, *args, **kwargs)
        app_id = kwargs.get("app_id")
        if app_id:
            self.app = group_service.get_app_by_id(self.team, self.region_name, app_id)
        if not self.app:
            raise ServiceHandleException(msg_show="应用不存在", msg="no found app", status_code=404)


class TeamAppServiceAPIView(TeamAppAPIView):
    def __init__(self):
        super(TeamAppServiceAPIView, self).__init__()
        self.service = None

    def initial(self, request, *args, **kwargs):
        super(TeamAppServiceAPIView, self).initial(request, *args, **kwargs)
        service_id = kwargs.get("service_id")
        self.service = TenantServiceInfo.objects.filter(
            tenant_id=self.team.tenant_id, service_region=self.region_name, service_id=service_id).first()
        if not self.service:
            self.service = TenantServiceInfo.objects.filter(
                tenant_id=self.team.tenant_id, service_region=self.region_name, service_alias=service_id).first()
        if not self.service:
            raise ServiceHandleException(msg_show="组件不存在", msg="no found component", status_code=404)
        gsr = group_service_relation_repo.get_services_by_group(self.app.ID)
        if gsr:
            service_ids = gsr.values_list("service_id", flat=True)
            if self.service.service_id not in service_ids:
                raise ServiceHandleException(msg_show="组件不属于指定应用", msg="component not belong to this app", status_code=404)


class EnterpriseServiceOauthView(APIView):
    def __init__(self, *args, **kwargs):
        super(EnterpriseServiceOauthView, self).__init__(*args, **kwargs)
        self.oauth_instance = None
        self.oauth = None
        self.oauth_user = None

    def initial(self, request, *args, **kwargs):
        super(EnterpriseServiceOauthView, self).initial(request, *args, **kwargs)
        try:
            oauth_service = OAuthServices.objects.get(oauth_type="enterprisecenter", ID=1, user_id=request.user.user_id)
            pre_enterprise_center = os.getenv("PRE_ENTERPRISE_CENTER", None)
            if pre_enterprise_center:
                oauth_service = OAuthServices.objects.get(name=pre_enterprise_center, oauth_type="enterprisecenter", user_id=request.user.user_id)
            oauth_user = UserOAuthServices.objects.get(service_id=oauth_service.ID, user_id=request.user.user_id)
        except OAuthServices.DoesNotExist:
            raise ServiceHandleException(
                msg="not found enterprise center oauth server config", msg_show="未找到企业中心OAuth配置", status_code=404)
        except UserOAuthServices.DoesNotExist:
            raise ServiceHandleException(msg="user not authorize in enterprise center oauth", msg_show="用户身份未在企业中心认证")
        self.oauth_instance = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
        if not self.oauth_instance:
            raise ServiceHandleException(msg="no found enterprise service OAuth", msg_show="未找到企业中心OAuth服务类型", status_code=404)

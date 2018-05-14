# -*- coding: utf-8 -*-
import logging

from django.db.models import Q

from backends.models import RegionConfig
from backends.services.exceptions import TenantNotExistError, UserNotExistError
from www.models import PermRelTenant, Users, Tenants, TenantRegionInfo, ServiceGroupRelation
from console.models.main import TeamGitlabInfo

logger = logging.getLogger("default")


class TeamRepo(object):
    def get_tenant_perms(self, tenant_id, user_id):
        perms = PermRelTenant.objects.filter(tenant_id=tenant_id, user_id=user_id)
        return perms

    def get_tenant_by_tenant_name(self, tenant_name, exception=True):
        tenants = Tenants.objects.filter(tenant_name=tenant_name)
        if not tenants and exception:
            return None
        return tenants[0]

    def get_tenant_users_by_tenant_ID(self, tenant_ID):
        """
        返回一个团队中所有用户对象
        :param tenant_ID:
        :return:
        """
        user_id_list = PermRelTenant.objects.filter(tenant_id=tenant_ID).values_list("user_id", flat=True)
        if not user_id_list:
            return []
        user_list = Users.objects.filter(user_id__in=user_id_list)
        return user_list

    def get_tenants_by_user_id(self, user_id):
        tenant_ids = PermRelTenant.objects.filter(user_id=user_id).values_list("tenant_id", flat=True)
        tenants = Tenants.objects.filter(ID__in=tenant_ids)
        return tenants

    def get_user_perms_in_permtenant(self, user_id, tenant_id):
        tenant_perms = PermRelTenant.objects.filter(user_id=user_id, tenant_id=tenant_id)
        if not tenant_perms:
            return None
        return tenant_perms

    def get_user_perms_in_permtenant_list(self, user_id, tenant_id):
        """
        获取一个用户在一个团队中的所有身份列表
        :param user_id: 用户id  int
        :param tenant_id: 团队id  int
        :return: 获取一个用户在一个团队中的所有身份列表
        """
        tenant_perms_list = PermRelTenant.objects.filter(user_id=user_id, tenant_id=tenant_id).values_list("identity",flat=True)
        if not tenant_perms_list:
            return None
        return tenant_perms_list

    def delete_tenant(self, tenant_name):
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        PermRelTenant.objects.filter(tenant_id=tenant.ID).delete()
        row = Tenants.objects.filter(ID=tenant.ID).delete()
        return row > 0

    def get_region_alias(self, region_name):
        try:
            region = RegionConfig.objects.filter(region_name=region_name)
            if region:
                region = region[0]
                region_alias = region.region_alias
                return region_alias
            else:
                return None
        except Exception as e:
            logger.exception(e)
            return u"测试Region"

    def get_team_by_team_name(self, team_name):
        try:
            return Tenants.objects.get(tenant_name=team_name)
        except Tenants.DoesNotExist:
            return None

    def delete_user_perms_in_permtenant(self, user_id, tenant_id):
        PermRelTenant.objects.filter(Q(user_id=user_id, tenant_id=tenant_id) & ~Q(identity='owner')).delete()

    def get_team_by_team_id(self, team_id):
        team = Tenants.objects.filter(tenant_id=team_id)
        if not team:
            return None
        else:
            return team[0]

    def get_teams_by_enterprise_id(self, enterprise_id):
        return Tenants.objects.filter(enterprise_id=enterprise_id)

    def create_tenant(self, **params):
        return Tenants.objects.create(**params)

    def get_team_by_team_alias(self, team_alias):
        return Tenants.objects.filter(tenant_alias=team_alias).first()

    def get_team_by_team_ids(self, team_ids):
        return Tenants.objects.filter(tenant_id__in=team_ids)


class TeamGitlabRepo(object):
    def get_team_gitlab_by_team_id(self, team_id):
        return TeamGitlabInfo.objects.filter(team_id=team_id)

    def create_team_gitlab_info(self, **params):
        return TeamGitlabInfo.objects.create(**params)

    def get_team_repo_by_code_name(self, team_id, repo_name):
        tgi = TeamGitlabInfo.objects.filter(team_id=team_id, repo_name=repo_name)
        if tgi:
            return tgi[0]
        return None


team_repo = TeamRepo()
team_gitlab_repo = TeamGitlabRepo()

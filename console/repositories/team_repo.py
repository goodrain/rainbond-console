# -*- coding: utf-8 -*-
import logging

from console.exception.exceptions import TenantNotExistError
from console.exception.main import ServiceHandleException
from console.models.main import RegionConfig, TeamGitlabInfo, TeamRegistryAuth
from console.repositories.base import BaseConnection
from django.db.models import Q
from www.models.main import (PermRelTenant, TenantEnterprise, TenantRegionInfo, Tenants, Users, TeamInvitation)
from www.utils.crypt import make_tenant_id

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

    def get_tenants_by_user_id(self, user_id, name=None, team_name=""):
        tenant_ids = PermRelTenant.objects.filter(user_id=user_id).values_list("tenant_id", flat=True)
        filters = Q(ID__in=tenant_ids)
        if name:
            filters &= Q(tenant_alias__contains=name)

        tenants = Tenants.objects.filter(filters).order_by("-create_time")
        if team_name:
            tenants = tenants | Tenants.objects.filter(tenant_name=team_name).order_by("-create_time")

        return tenants

    def get_user_tenant_by_name(self, user_id, name):
        tenant_ids = PermRelTenant.objects.filter(user_id=user_id).values_list("tenant_id", flat=True)
        tenant = Tenants.objects.filter(ID__in=tenant_ids, tenant_name=name).first()
        return tenant

    def get_tenants_by_user_id_and_eid(self, eid, user_id, name=None):
        tenants = []
        enterprise = TenantEnterprise.objects.filter(enterprise_id=eid).first()
        if not enterprise:
            return enterprise
        tenant_ids = list(
            PermRelTenant.objects.filter(enterprise_id=enterprise.ID, user_id=user_id).values_list("tenant_id",
                                                                                                   flat=True).order_by("-ID"))
        tenant_ids = sorted(set(tenant_ids), key=tenant_ids.index)
        if name:
            for tenant_id in tenant_ids:
                tn = Tenants.objects.filter(ID=tenant_id, tenant_alias__contains=name).first()
                if tn:
                    tenants.append(tn)
        else:
            for tenant_id in tenant_ids:
                tn = Tenants.objects.filter(ID=tenant_id).first()
                if tn:
                    tenants.append(tn)
        return tenants

    @staticmethod
    def get_user_notjoin_teams(eid, user_id, name=None):
        enterprise = TenantEnterprise.objects.filter(enterprise_id=eid).first()
        if not enterprise:
            return []
        tenant_ids = list(
            PermRelTenant.objects.filter(user_id=user_id, enterprise_id=enterprise.ID).values_list("tenant_id",
                                                                                                   flat=True).order_by("-ID"))
        q = ~Q(ID__in=tenant_ids)
        if name:
            q &= Q(tenant_alias__contains=name)
        return Tenants.objects.filter(q)

    def get_user_perms_in_permtenant(self, user_id, tenant_id):
        tenant_perms = PermRelTenant.objects.filter(user_id=user_id, tenant_id=tenant_id)
        if not tenant_perms:
            return None
        return tenant_perms

    def get_not_join_users(self, enterprise, tenant, query):
        where = """(SELECT DISTINCT user_id FROM tenant_perms WHERE tenant_id="{}" AND enterprise_id={})""".format(
            tenant.ID, enterprise.ID)

        sql = """
            SELECT user_id, nick_name, enterprise_id, email
            FROM user_info
            WHERE user_id NOT IN {where}
            AND enterprise_id="{enterprise_id}"
        """.format(
            where=where, enterprise_id=enterprise.enterprise_id)
        if query:
            sql += """
            AND nick_name like "%{query}%"
            """.format(query=query)
        conn = BaseConnection()
        result = conn.query(sql)

        return result

    # 返回该团队下的所有管理员
    def get_tenant_admin_by_tenant_id(self, tenant):
        admins = Users.objects.filter(user_id=tenant.creater)
        return admins

    def get_user_perms_in_permtenant_list(self, user_id, tenant_id):
        """
        获取一个用户在一个团队中的所有身份列表
        :param user_id: 用户id  int
        :param tenant_id: 团队id  int
        :return: 获取一个用户在一个团队中的所有身份列表
        """
        tenant_perms_list = PermRelTenant.objects.filter(
            user_id=user_id, tenant_id=tenant_id).values_list(
                "identity", flat=True)
        if not tenant_perms_list:
            return None
        return tenant_perms_list

    def delete_tenant(self, tenant_name):
        # TODO: use transaction
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        PermRelTenant.objects.filter(tenant_id=tenant.ID).delete()
        row = Tenants.objects.filter(ID=tenant.ID).delete()
        return len(row) > 0

    def delete_by_tenant_id(self, tenant_id):
        # TODO: use transaction
        tenant = Tenants.objects.get(tenant_id=tenant_id)
        PermRelTenant.objects.filter(tenant_id=tenant.ID).delete()
        row = Tenants.objects.filter(ID=tenant.ID).delete()
        return len(row) > 0

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
            return "测试Region"

    def get_team_by_team_name(self, team_name):
        try:
            return Tenants.objects.get(tenant_name=team_name)
        except Tenants.DoesNotExist:
            return None

    def get_team_by_team_name_and_eid(self, eid, team_name):
        try:
            return Tenants.objects.get(tenant_name=team_name, enterprise_id=eid)
        except Tenants.DoesNotExist:
            raise ServiceHandleException(msg_show="团队不存在", msg="team not found")

    def delete_user_perms_in_permtenant(self, user_id, tenant_id):
        PermRelTenant.objects.filter(Q(user_id=user_id, tenant_id=tenant_id) & ~Q(identity='owner')).delete()

    def get_team_by_team_id(self, team_id):
        try:
            return Tenants.objects.get(tenant_id=team_id)
        except Tenants.DoesNotExist:
            raise TenantNotExistError

    def get_teams_by_enterprise_id(self, enterprise_id, user_id=None, query=None):
        q = Q(enterprise_id=enterprise_id)
        if user_id:
            q &= Q(creater=user_id)
        if query:
            q &= Q(tenant_alias__contains=query)
        return Tenants.objects.filter(q).order_by("-create_time")

    def get_fuzzy_tenants_by_tenant_alias_and_enterprise_id(self, enterprise_id, tenant_alias):
        return Tenants.objects.filter(enterprise_id=enterprise_id, tenant_alias__contains=tenant_alias)

    def create_tenant(self, **params):
        if not params.get("tenant_id"):
            params["tenant_id"] = make_tenant_id()
        if not params.get("namespace"):
            params["namespace"] = params["tenant_id"]
        if Tenants.objects.filter(namespace=params["namespace"]).count() > 0:
            raise ServiceHandleException(msg="namespace exists", msg_show="命名空间已存在")
        return Tenants.objects.create(**params)

    def get_team_by_team_alias(self, team_alias):
        return Tenants.objects.filter(tenant_alias=team_alias).first()

    def get_team_by_team_ids(self, team_ids):
        return Tenants.objects.filter(tenant_id__in=team_ids)

    def get_team_map_by_team_ids(self, team_ids):
        tenants = Tenants.objects.filter(tenant_id__in=team_ids)
        tenants_map = {t.tenant_id: t.to_dict() for t in tenants}
        return tenants_map

    def get_team_by_team_names(self, team_names):
        return Tenants.objects.filter(tenant_name__in=team_names)

    def create_team_perms(self, **params):
        return PermRelTenant.objects.create(**params)

    def get_team_by_enterprise_id(self, enterprise_id):
        return Tenants.objects.filter(enterprise_id=enterprise_id)

    def get_enterprise_team_by_name(self, enterprise_id, team_name):
        return Tenants.objects.filter(enterprise_id=enterprise_id, tenant_name=team_name).first()

    def update_by_tenant_id(self, tenant_id, **data):
        return Tenants.objects.filter(tenant_id=tenant_id).update(**data)

    def list_teams_v2(self, query="", page=None, page_size=None):
        where = "WHERE t.creater = u.user_id"
        if query:
            where += " AND t.tenant_alias LIKE '%{query}%'".format(query=query)
        limit = ""
        if page is not None and page_size is not None:
            page = (page - 1) * page_size
            limit = "LIMIT {page}, {page_size}".format(page=page, page_size=page_size)
        sql = """
        SELECT
            t.tenant_name,
            t.tenant_alias,
            t.region,
            t.limit_memory,
            t.enterprise_id,
            t.tenant_id,
            t.create_time,
            t.is_active,
            u.nick_name AS creater,
            count( s.ID ) AS service_num
        FROM
            tenant_info t
            LEFT JOIN tenant_service s ON t.tenant_id = s.tenant_id,
            user_info u
        {where}
        GROUP BY
            tenant_id
        ORDER BY
            service_num DESC
        {limit}
        """.format(
            where=where, limit=limit)
        conn = BaseConnection()
        result = conn.query(sql)
        return result

    def list_by_user_id(self, eid, user_id, query="", page=None, page_size=None):
        limit = ""
        if page is not None and page_size is not None:
            page = page if page > 0 else 1
            page = (page - 1) * page_size
            limit = "Limit {page}, {size}".format(page=page, size=page_size)
        where = """WHERE a.ID = b.tenant_id
                AND c.user_id = b.user_id
                AND b.user_id = {user_id}
                AND a.enterprise_id = '{eid}'
                """.format(
            user_id=user_id, eid=eid)
        if query:
            where += """AND ( a.tenant_alias LIKE "%{query}%" OR c.nick_name LIKE "%{query}%" )""".format(query=query)
        sql = """
            SELECT DISTINCT
                a.ID,
                a.tenant_id,
                a.tenant_name,
                a.tenant_alias,
                a.is_active,
                a.enterprise_id,
                a.create_time,
                c.nick_name as creater
            FROM
                tenant_info a,
                tenant_perms b,
                user_info c
            {where}
            {limit}
            """.format(
            where=where, limit=limit)
        conn = BaseConnection()
        result = conn.query(sql)
        return result

    def count_by_user_id(self, eid, user_id, query=""):
        where = """WHERE a.ID = b.tenant_id
                AND c.user_id = b.user_id
                AND b.user_id = {user_id}
                AND a.enterprise_id = '{eid}'
                """.format(
            user_id=user_id, eid=eid)
        if query:
            where += """AND a.tenant_alias LIKE "%{query}%" """.format(query=query)
        sql = """
        SELECT
            count( * ) AS total
        FROM
            (
            SELECT DISTINCT
                a.tenant_id AS tenant_id
            FROM
                tenant_info a,
                tenant_perms b,
                user_info c
            {where}
            ) as tmp""".format(where=where)
        conn = BaseConnection()
        result = conn.query(sql)
        return result[0].get("total")

    def get_team_regions(self, team_id):
        region_names = TenantRegionInfo.objects.filter(tenant_id=team_id).values_list("region_name", flat=True)
        return RegionConfig.objects.filter(region_name__in=region_names)

    def get_team_region_names(self, team_id):
        return self.get_team_regions(team_id).values_list("region_name", flat=True)

    def get_team_region_by_name(self, team_id, region_name):
        return TenantRegionInfo.objects.filter(tenant_id=team_id, region_name=region_name)

    def get_teams_by_create_user(self, enterprise_id, user_id):
        return Tenants.objects.filter(creater=user_id, enterprise_id=enterprise_id)


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


class TeamRegistryAuthRepo(object):
    def list_by_team_id(self, tenant_id, region_name, user_id):
        return TeamRegistryAuth.objects.filter(tenant_id=tenant_id, region_name=region_name, user_id=user_id)

    def check_exist_registry_auth(self, secret_id, user_id):
        return TeamRegistryAuth.objects.filter(secret_id=secret_id, user_id=user_id)

    def create_team_registry_auth(self, **params):
        return TeamRegistryAuth.objects.create(**params)

    def update_team_registry_auth(self, tenant_id, region_name, secret_id, **params):
        return TeamRegistryAuth.objects.filter(
            tenant_id=tenant_id, region_name=region_name, secret_id=secret_id).update(**params)

    def delete_team_registry_auth(self, tenant_id, region_name, secret_id, user_id):
        return TeamRegistryAuth.objects.filter(tenant_id=tenant_id, region_name=region_name, secret_id=secret_id, user_id=user_id).delete()

    def get_by_secret_id(self, secret_id):
        return TeamRegistryAuth.objects.filter(secret_id=secret_id)

    def get_by_team_id_domain(self, tenant_id, region_name, domain):
        return TeamRegistryAuth.objects.filter(tenant_id=tenant_id, region_name=region_name, domain=domain)


class TeamInvitationRepo(object):
    def list_by_user_id(self, user_id):
        """获取用户收到的所有邀请"""
        return TeamInvitation.objects.filter(user_id=user_id)
    
    def get_invitation_by_id(self, invitation_id):
        """通过ID获取邀请信息"""
        return TeamInvitation.objects.filter(invitation_id=invitation_id).first()
    
    def list_by_team_id(self, team_id):
        """获取团队所有邀请记录"""
        return TeamInvitation.objects.filter(tenant_id=team_id)
    
    def create_invitation(self, **params):
        """创建新的团队邀请"""
        return TeamInvitation.objects.create(**params)
    
    def delete_invitation(self, invitation_id):
        """删除团队邀请"""
        return TeamInvitation.objects.filter(invitation_id=invitation_id).delete()
    
    def update_invitation(self, invitation_id, **params):
        """更新邀请信息"""
        return TeamInvitation.objects.filter(invitation_id=invitation_id).update(**params)


team_repo = TeamRepo()
team_gitlab_repo = TeamGitlabRepo()
team_registry_auth_repo = TeamRegistryAuthRepo()
team_invitation_repo = TeamInvitationRepo()
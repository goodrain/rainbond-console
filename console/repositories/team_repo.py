# -*- coding: utf-8 -*-
import logging

from console.exception.exceptions import TenantNotExistError
from console.exception.main import ServiceHandleException
from console.models.main import RegionConfig, TeamGitlabInfo
from console.repositories.base import BaseConnection
from django.db.models import Q
from www.models.main import (PermRelTenant, ServiceGroup, TenantEnterprise, TenantRegionInfo, Tenants, Users)

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

    def get_tenants_by_user_id(self, user_id, name=None):
        tenant_ids = PermRelTenant.objects.filter(user_id=user_id).values_list("tenant_id", flat=True)
        if name:
            tenants = Tenants.objects.filter(ID__in=tenant_ids, tenant_alias__contains=name).order_by("-create_time")
        else:
            tenants = Tenants.objects.filter(ID__in=tenant_ids).order_by("-create_time")
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

    def get_active_tenants_by_user_id(self, user_id):
        active_tenants_list = []
        tenant_ids = PermRelTenant.objects.filter(user_id=user_id).values_list("tenant_id", flat=True)
        tenants = Tenants.objects.filter(ID__in=tenant_ids)
        if tenants:
            for tenant in tenants:
                active_tenants_list.append({
                    "tenant_id": tenant.tenant_id,
                    "team_alias": tenant.tenant_alias,
                    "owner": tenant.creater,
                    "enterprise_id": tenant.enterprise_id,
                    "create_time": tenant.create_time,
                    "team_name": tenant.tenant_name,
                    "region": tenant.region,
                    "num": len(ServiceGroup.objects.filter(tenant_id=tenant.tenant_id))
                })
            active_tenants_list.sort(key=lambda x: x["num"])
            active_tenants_list = active_tenants_list[:3]
        return active_tenants_list

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
        return row > 0

    def delete_by_tenant_id(self, tenant_id):
        # TODO: use transaction
        tenant = Tenants.objects.get(tenant_id=tenant_id)
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
        return Tenants.objects.create(**params)

    def get_team_by_team_alias(self, team_alias):
        return Tenants.objects.filter(tenant_alias=team_alias).first()

    def get_team_by_team_ids(self, team_ids):
        return Tenants.objects.filter(tenant_id__in=team_ids)

    def get_team_by_team_names(self, team_names):
        return Tenants.objects.filter(tenant_name__in=team_names)

    def create_team_perms(self, **params):
        return PermRelTenant.objects.create(**params)

    def get_team_by_enterprise_id(self, enterprise_id):
        return Tenants.objects.filter(enterprise_id=enterprise_id)

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
                AND a.creater = d.user_id
                AND b.user_id = {user_id}
                AND a.enterprise_id = '{eid}'
                """.format(
            user_id=user_id, eid=eid)
        if query:
            where += """AND ( a.tenant_alias LIKE "%{query}%" OR d.nick_name LIKE "%{query}%" )""".format(query=query)
        sql = """
            SELECT DISTINCT
                a.ID,
                a.tenant_id,
                a.tenant_name,
                a.tenant_alias,
                a.is_active,
                a.enterprise_id,
                a.create_time,
                d.nick_name as creater
            FROM
                tenant_info a,
                tenant_perms b,
                user_info c,
                user_info d
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
        return TenantRegionInfo.objects.filter(tenant_id=team_id)

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


team_repo = TeamRepo()
team_gitlab_repo = TeamGitlabRepo()

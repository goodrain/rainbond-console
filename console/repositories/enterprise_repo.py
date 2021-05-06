# -*- coding: utf-8 -*-
import logging

from console.enum.enterprise_enum import EnterpriseRolesEnum
from console.exception.exceptions import (ExterpriseNotExistError, UserNotExistError)
from console.models.main import (Applicants, EnterpriseUserPerm, RainbondCenterApp)
from console.repositories.base import BaseConnection
from console.repositories.group import group_repo, group_service_relation_repo
from console.repositories.service_repo import service_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.repositories.user_role_repo import (UserRoleNotFoundException, user_role_repo)
from django.db.models import Q
from www.models.main import (PermRelTenant, ServiceGroup, ServiceGroupRelation, TenantEnterprise, TenantRegionInfo, Tenants,
                             Users)

logger = logging.getLogger("default")


class TenantEnterpriseRepo(object):
    def is_user_admin_in_enterprise(self, user, enterprise_id):
        """判断用户在该企业下是否为管理员"""
        if user.enterprise_id != enterprise_id:
            return False
        if not enterprise_user_perm_repo.is_admin(enterprise_id, user.user_id):
            users = user_repo.get_enterprise_users(enterprise_id).order_by("user_id")
            if users:
                admin_user = users[0]
                # 如果有，判断用户最开始注册的用户和当前用户是否为同一人，如果是，添加数据返回true
                if admin_user.user_id == user.user_id:
                    enterprise_user_perm_repo.create_enterprise_user_perm(user.user_id, enterprise_id, "admin")
                    return True
                else:
                    return False
        else:
            return True

    def get_team_enterprises(self, tenant_id):
        enterprise_ids = TenantRegionInfo.objects.filter(tenant_id=tenant_id).values_list("enterprise_id", flat=True)
        return TenantEnterprise.objects.filter(enterprise_id__in=enterprise_ids)

    def get_enterprises_by_user_id(self, user_id):
        try:
            user = user_repo.get_user_by_user_id(user_id)
            tenant_ids = team_repo.get_tenants_by_user_id(user_id).values_list("tenant_id", flat=True)
            enterprise_ids = list(
                TenantRegionInfo.objects.filter(tenant_id__in=tenant_ids).values_list("enterprise_id", flat=True))
            enterprise_ids.append(user.enterprise_id)
            enterprises = TenantEnterprise.objects.filter(enterprise_id__in=enterprise_ids)
            return enterprises
        except Exception:
            raise ExterpriseNotExistError

    def get_enterprise_apps(self, enterprise_id):
        tenant_ids = TenantRegionInfo.objects.filter(enterprise_id=enterprise_id).values_list("tenant_id", flat=True)
        return ServiceGroup.objects.filter(tenant_id__in=tenant_ids)

    def get_enterprise_services(self, enterprise_id):
        tenant_ids = TenantRegionInfo.objects.filter(enterprise_id=enterprise_id).values_list("tenant_id", flat=True)
        if not tenant_ids:
            return []
        group_ids = ServiceGroup.objects.filter(tenant_id__in=tenant_ids).values_list("ID")
        if not group_ids:
            return []
        return ServiceGroupRelation.objects.filter(group_id__in=group_ids).values_list("service_id")

    def get_enterprise_users(self, enterprise_id):
        return Users.objects.filter(enterprise_id=enterprise_id)

    def get_enterprise_user_teams(self, enterprise_id, user_id, name=None):
        return team_repo.get_tenants_by_user_id_and_eid(enterprise_id, user_id, name)

    def get_enterprise_user_join_teams(self, enterprise_id, user_id):
        team_ids = []
        teams = self.get_enterprise_user_teams(enterprise_id, user_id)
        if not teams:
            return teams
        team_ids = [team.tenant_id for team in teams]
        return Applicants.objects.filter(user_id=user_id, is_pass=1, team_id__in=team_ids).order_by("-apply_time")

    def get_enterprise_teams(self, enterprise_id, name=None):
        if name:
            return Tenants.objects.filter(
                enterprise_id=enterprise_id, is_active=True, tenant_alias__contains=name).order_by("-create_time")
        else:
            return Tenants.objects.filter(enterprise_id=enterprise_id, is_active=True).order_by("-create_time")

    def get_enterprise_shared_app_nums(self, enterprise_id):
        apps = RainbondCenterApp.objects.filter(enterprise_id=enterprise_id)
        if not apps:
            return 0
        return len(set(apps.values_list("app_id", flat=True)))

    def get_enterprise_user_active_teams(self, enterprise_id, user_id):
        tenants = self.get_enterprise_user_teams(enterprise_id, user_id)
        if not tenants:
            return None
        active_tenants_list = []
        for tenant in tenants:
            owner = None
            try:
                owner = user_repo.get_user_by_user_id(tenant.creater)
                role = user_role_repo.get_role_names(user_id, tenant.tenant_id)
            except UserNotExistError:
                pass
            except UserRoleNotFoundException:
                if tenant.creater == user_id:
                    role = "owner"
                else:
                    role = None
            region_name_list = team_repo.get_team_region_names(tenant.tenant_id)
            team_item = {
                "tenant_id": tenant.tenant_id,
                "team_alias": tenant.tenant_alias,
                "owner": tenant.creater,
                "owner_name": owner.get_name() if owner else "",
                "enterprise_id": tenant.enterprise_id,
                "create_time": tenant.create_time,
                "team_name": tenant.tenant_name,
                "region": region_name_list[0] if region_name_list else "",
                "region_list": region_name_list,
                "num": len(ServiceGroup.objects.filter(tenant_id=tenant.tenant_id)),
                "role": role
            }
            if not team_item["region"] and len(region_name_list) > 0:
                team_item["region"] = region_name_list[0]
            active_tenants_list.append(team_item)
        active_tenants_list.sort(key=lambda x: x["num"], reverse=True)
        active_tenants_list = active_tenants_list[:3]
        return active_tenants_list

    def get_enterprise_by_enterprise_name(self, enterprise_name):
        enterprise = TenantEnterprise.objects.filter(enterprise_name=enterprise_name)
        if not enterprise:
            return None
        else:
            return enterprise[0]

    def get_enterprise_first(self):
        """
        获取第一条企业名
        :return:
        """
        enterprise = TenantEnterprise.objects.first()
        if not enterprise:
            return None
        else:
            return enterprise

    def get_enterprise_by_enterprise_id(self, enterprise_id, exception=True):
        enterprise = TenantEnterprise.objects.filter(enterprise_id=enterprise_id)
        if not enterprise:
            return None
        else:
            return enterprise[0]

    def create_enterprise(self, **params):
        return TenantEnterprise.objects.create(**params)

    def get_enterprises_by_enterprise_ids(self, eids):
        return TenantEnterprise.objects.filter(enterprise_id__in=eids)

    def get_by_enterprise_alias(self, enterprise_alias):
        return TenantEnterprise.objects.filter(enterprise_alias=enterprise_alias).first()

    def list_all(self, query):
        if query:
            return TenantEnterprise.objects.filter(Q(enterprise_name__contains=query)
                                                   | Q(enterprise_alias__contains=query)).all().order_by("-create_time")
        return TenantEnterprise.objects.all().order_by("-create_time")

    def update(self, eid, **data):
        TenantEnterprise.objects.filter(enterprise_id=eid).update(**data)

    def list_appstore_infos(self, query="", page=None, page_size=None):
        limit = ""
        if page is not None and page_size is not None:
            page = page if page > 0 else 1
            page = (page - 1) * page_size
            limit = "Limit {page}, {size}".format(page=page, size=page_size)
        where = ""
        if query:
            where = "WHERE a.enterprise_alias LIKE '%{query}%' OR a.enterprise_name LIKE '%{query}%'".format(query=query)
        sql = """
        SELECT
            a.enterprise_id,
            a.enterprise_name,
            a.enterprise_alias,
            b.access_url
        FROM
            tenant_enterprise a
            JOIN tenant_enterprise_token b ON a.id = b.enterprise_id
        {where}
        {limit}
        """.format(
            where=where, limit=limit)

        conn = BaseConnection()
        result = conn.query(sql)
        return result

    def count_appstore_infos(self, query=""):
        where = ""
        if query:
            where = "WHERE a.enterprise_alias LIKE '%{query}%' OR a.enterprise_name LIKE '%{query}%'".format(query=query)
        sql = """
        SELECT
            count(*) as total
        FROM
            tenant_enterprise a
            JOIN tenant_enterprise_token b ON a.id = b.enterprise_id
        {where}
        """.format(where=where)

        conn = BaseConnection()
        result = conn.query(sql)
        return result[0]["total"]

    def get_enterprise_user_request_join(self, enterprise_id, user_id):
        team_ids = self.get_enterprise_teams(enterprise_id).values_list("tenant_id", flat=True)
        return Applicants.objects.filter(user_id=user_id, team_id__in=team_ids).order_by("is_pass", "-apply_time")

    def get_enterprise_tenant_ids(self, enterprise_id, user=None):
        if user is None or self.is_user_admin_in_enterprise(user, enterprise_id):
            teams = Tenants.objects.filter(enterprise_id=enterprise_id)
            if not teams:
                return None
            team_ids = teams.values_list("tenant_id", flat=True)
        else:
            enterprise = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id)
            if not enterprise:
                return None
            user_teams_perm = PermRelTenant.objects.filter(enterprise_id=enterprise.ID, user_id=user.user_id)
            if not user_teams_perm:
                return None
            tenant_auto_ids = user_teams_perm.values_list("tenant_id", flat=True)
            teams = Tenants.objects.filter(ID__in=tenant_auto_ids)
            if not teams:
                return None
            team_ids = teams.values_list("tenant_id", flat=True)
        tenants = TenantRegionInfo.objects.filter(tenant_id__in=team_ids)
        if not tenants:
            return None
        else:
            return tenants.values_list("region_tenant_id", flat=True)

    def get_enterprise_app_list(self, enterprise_id, user, page=1, page_size=10):
        tenant_ids = self.get_enterprise_tenant_ids(enterprise_id, user)
        if not tenant_ids:
            return [], 0
        enterprise_apps = group_repo.get_groups_by_tenant_ids(tenant_ids)
        if not enterprise_apps:
            return [], 0
        return enterprise_apps[(page - 1) * page_size:page * page_size], enterprise_apps.count()

    def get_enterprise_app_component_list(self, app_id, page=1, page_size=10):
        group_relation_services = group_service_relation_repo.get_services_by_group(app_id)
        if not group_relation_services:
            return [], 0
        service_ids = group_relation_services.values_list("service_id", flat=True)
        services = service_repo.get_service_by_service_ids(service_ids)
        return services[(page - 1) * page_size:page * page_size], services.count()


class TenantEnterpriseUserPermRepo(object):
    def create_enterprise_user_perm(self, user_id, enterprise_id, identity, token=None):
        if token is None:
            return EnterpriseUserPerm.objects.create(user_id=user_id, enterprise_id=enterprise_id, identity=identity)
        else:
            return EnterpriseUserPerm.objects.create(
                user_id=user_id, enterprise_id=enterprise_id, identity=identity, token=token)

    def update_roles(self, enterprise_id, user_id, identity):
        EnterpriseUserPerm.objects.filter(enterprise_id=enterprise_id, user_id=user_id).update(identity=identity)

    def get_user_enterprise_perm(self, user_id, enterprise_id):
        return EnterpriseUserPerm.objects.filter(user_id=user_id, enterprise_id=enterprise_id)

    def get_backend_enterprise_admin_by_user_id(self, user_id):
        """
        管理后台查询企业管理员，只有一个企业
        :param user_id:
        :param enterprise_id:
        :return:
        """
        enter_admin = EnterpriseUserPerm.objects.filter(user_id=user_id).first()
        if enter_admin:
            return enter_admin
        else:
            return None

    def count_by_eid(self, eid):
        return EnterpriseUserPerm.objects.filter(enterprise_id=eid).count()

    def delete_backend_enterprise_admin_by_user_id(self, user_id):
        """
        管理后台删除企业管理员，只有一个企业
        :param user_id:
        :param enterprise_id:
        :return:
        """
        EnterpriseUserPerm.objects.filter(user_id=user_id).delete()

    def get_by_token(self, token):
        return EnterpriseUserPerm.objects.filter(token=token).first()

    @staticmethod
    def is_admin(eid, user_id):
        try:
            perm = EnterpriseUserPerm.objects.get(enterprise_id=eid, user_id=user_id)
            return EnterpriseRolesEnum.admin.name in perm.identity
        except EnterpriseUserPerm.DoesNotExist:
            return False

    def get(self, enterprise_id, user_id):
        return EnterpriseUserPerm.objects.get(enterprise_id=enterprise_id, user_id=user_id)


enterprise_repo = TenantEnterpriseRepo()
enterprise_user_perm_repo = TenantEnterpriseUserPermRepo()

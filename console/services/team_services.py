# -*- coding: utf-8 -*-
import datetime
import logging
import random
import string

from django.conf import settings
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from console.repositories.enterprise_repo import enterprise_repo
from console.models.main import TenantUserRole
from console.repositories.perm_repo import role_perm_repo
from console.repositories.perm_repo import role_repo
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.repositories.tenant_region_repo import tenant_region_repo
from console.repositories.user_repo import user_repo
from console.services.enterprise_services import enterprise_services
from console.services.exception import ErrAllTenantDeletionFailed
from console.services.exception import ErrStillHasServices
from console.services.exception import ErrTenantRegionNotFound
from console.services.perm_services import perm_services
from console.services.region_services import region_services
from console.services.perm_services import user_kind_role_service
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import PermRelTenant
from www.models.main import Tenants
from www.models.main import TenantServiceInfo
from console.repositories.user_role_repo import user_role_repo
from console.repositories.exceptions import UserRoleNotFoundException
from console.exception.exceptions import UserNotExistError

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class TeamService(object):
    def get_tenant_by_tenant_name(self, tenant_name, exception=True):
        return team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=exception)

    def get_tenant(self, tenant_name):
        if not Tenants.objects.filter(tenant_name=tenant_name).exists():
            raise Tenants.DoesNotExist
        return Tenants.objects.get(tenant_name=tenant_name)

    def get_enterprise_tenant_by_tenant_name(self, enterprise_id, tenant_name):
        return Tenants.objects.filter(tenant_name=tenant_name, enterprise_id=enterprise_id).first()

    def get_team_by_team_alias_and_eid(self, team_alias, enterprise_id):
        return Tenants.objects.filter(tenant_alias=team_alias, enterprise_id=enterprise_id).first()

    def random_tenant_name(self, enterprise=None, length=8):
        """
        生成随机的云帮租户（云帮的团队名），副需要符合k8s的规范(小写字母,_)
        :param enterprise 企业信息
        :param length:
        :return:
        """
        tenant_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        while Tenants.objects.filter(tenant_name=tenant_name).count() > 0:
            tenant_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        return tenant_name

    def add_user_to_team(self, request, tenant, user_ids, identitys):
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        if enterprise:
            user = request.user
            user_perms = self.get_user_perm_identitys_in_permtenant(user_id=user.user_id, tenant_name=tenant.tenant_name)
            user_ids = [int(r) for r in list(set(user_ids))]
            exist_team_user = PermRelTenant.objects.filter(tenant_id=tenant.ID, user_id__in=user_ids).all()
            exist = []
            for user in exist_team_user:
                exist.append(user.user_id)
            new_user_list = list()
            if ('admin' in user_perms) or ('owner' in user_perms):
                for user_id in user_ids:
                    if user_id not in exist:
                        for identity in identitys:
                            new_user_list.append(
                                PermRelTenant(
                                    user_id=user_id, tenant_id=tenant.pk, identity=identity, enterprise_id=enterprise.ID))
            if new_user_list:
                try:
                    PermRelTenant.objects.bulk_create(new_user_list)
                except Exception as e:
                    logging.exception(e)
        else:
            return None

    def get_team_users(self, team):
        users = team_repo.get_tenant_users_by_tenant_ID(team.ID)
        return users

    def get_tenant_users_by_tenant_name(self, tenant_name):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        user_list = team_repo.get_tenant_users_by_tenant_ID(tenant_ID=tenant.ID)
        return user_list

    def update_tenant_alias(self, tenant_name, new_team_alias):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=True)
        tenant.tenant_alias = new_team_alias
        tenant.save()
        return tenant

    def get_user_perms_in_permtenant(self, user_id, tenant_name):
        tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
        user_perms = team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID)
        return user_perms

    def get_not_join_users(
            self,
            enterprise,
            tenant,
            query,
    ):
        return team_repo.get_not_join_users(enterprise, tenant, query)

    def get_user_perms_in_permtenant_list(self, user_id, tenant_name):
        """
        一个用户在一个团队中的身份列表
        :return: 一个用户在一个团队中的身份列表
        """
        tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
        user_perms_list = team_repo.get_user_perms_in_permtenant_list(user_id=user_id, tenant_id=tenant.ID)
        return user_perms_list

    def get_user_perm_identitys_in_permtenant(self, user_id, tenant_name):
        """获取用户在一个团队的身份列表"""
        user = user_repo.get_by_user_id(user_id)
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        # user_perms = team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID)
        user_roles = user_kind_role_service.get_user_roles(kind_id=tenant.ID, kind="team", user=user)
        if tenant.creater == user_id:
            user_roles["roles"].append("owner")
        return user_roles

    def get_user_perm_role_in_permtenant(self, user_id, tenant_name):
        """获取一个用户在一个团队的角色名称列表"""
        tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
        user_perms = team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID)
        if not user_perms:
            return []
        role_id_list = []
        for role_id in [perm.role_id for perm in user_perms]:
            if not role_id:
                continue
            role_id_list.append(role_id)
        return [role_repo.get_role_name_by_role_id(role_id=i) for i in role_id_list]

    def get_user_perm_role_id_in_permtenant(self, user_id, tenant_name):
        """获取一个用户在一个团队的角色ID列表"""
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        user_perms = team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID)
        if not user_perms:
            return []
        role_id_list = []
        for role_id in [perm.role_id for perm in user_perms]:
            if not role_id:
                continue
            role_id_list.append(role_id)
        return role_id_list

    def get_user_perm_in_tenant(self, user_id, tenant_name):
        """获取一个用户在一个团队中的拥有权限元祖"""
        tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
        user_perms = team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID)
        if not user_perms:
            return ()
        role_id_list = [perm.role_id for perm in user_perms]
        role_perm_tuple = ()
        for role_id in role_id_list:
            if not role_id:
                continue
            perm_tuple = role_perm_repo.get_perm_by_role_id(role_id=role_id)
            role_perm_tuple += perm_tuple
        return role_perm_tuple

    def get_all_team_role_id(self, tenant_name, allow_owner=False):
        """获取一个团队中的所有可选角色ID列表"""
        try:
            team_obj = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            team_obj = self.get_team_by_team_id(tenant_name)
            if team_obj is None:
                raise Tenants.DoesNotExist()

        filter = Q(is_default=True)
        if not allow_owner:
            filter &= ~Q(role_name="owner")
        default_role_id_list = TenantUserRole.objects.filter(filter).values_list("pk", flat=True)
        team_role_id_list = TenantUserRole.objects.filter(tenant_id=team_obj.pk, is_default=False).values_list("pk", flat=True)
        return list(default_role_id_list) + list(team_role_id_list)

    def add_role_by_team_name_perm_list(self, role_name, tenant_name, perm_id_list):
        """添加一个角色"""
        tenant = self.get_tenant(tenant_name=tenant_name)
        role_obj = role_repo.add_role_by_tenant_pk_perm_list(
            role_name=role_name, tenant_pk=tenant.pk, perm_id_list=perm_id_list)
        return role_obj

    def del_role_by_team_name_role_name_role_id(self, role_id, tenant_name):
        """删除一个角色"""
        tenant = self.get_tenant(tenant_name=tenant_name)
        role_repo.del_role_by_team_pk_role_name_role_id(tenant_pk=tenant.pk, role_id=role_id)

    def update_role_by_team_name_role_name_perm_list(self, tenant_name, role_id, new_role_name, perm_id_list):
        """更新一个角色的权限"""
        tenant = self.get_tenant(tenant_name=tenant_name)
        role_obj = role_repo.update_role_by_team_name_role_name_perm_list(
            tenant_pk=tenant.pk, new_role_name=new_role_name, role_id=role_id, perm_id_list=perm_id_list)
        return role_obj

    def get_tenant_role_by_tenant_name(self, tenant_name):
        """获取一个团队中的所有角色和角色对应的权限信息"""
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        return role_repo.get_tenant_role_by_tenant_id(tenant_id=tenant.pk)

    def get_tenant_roles(self, tenant_id, page=None, page_size=None):
        """获取一个团队中的所有角色和角色对应的权限信息"""
        tenant = team_repo.get_team_by_team_id(tenant_id)
        if tenant is None:
            raise Tenants.DoesNotExist()

        role_list = role_repo.get_tenant_role_by_tenant_id(tenant_id=tenant.pk, allow_owner=True)
        if page is not None and page_size is None:
            paginator = Paginator(role_list, page_size)
            try:
                role_list = paginator.page(page).object_list
            except PageNotAnInteger:
                page = 1
                role_list = paginator.page(1).object_list
            except EmptyPage:
                page = paginator.num_pages
                role_list = paginator.page(paginator.num_pages).object_list
        return role_list

    def change_tenant_role(self, user_id, tenant_name, role_id_list):
        """修改用户在团队中的角色"""
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        user_role = role_repo.update_user_role_in_tenant_by_user_id_tenant_id_role_id(
            user_id=user_id, tenant_id=tenant.pk, enterprise_id=enterprise.pk, role_id_list=role_id_list)
        return user_role

    def create_tenant_role(self, user_id, tenant_name, role_id_list):
        """修改用户在团队中的角色"""
        tenant = self.get_tenant(tenant_name=tenant_name)
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        user_role = role_repo.add_user_role_in_tenant_by_user_id_tenant_id_role_id(
            user_id=user_id, tenant_id=tenant.pk, enterprise_id=enterprise.pk, role_id_list=role_id_list)
        return user_role

    def add_user_role_to_team(self, tenant, user_ids, role_ids):
        """在团队中添加一个用户并给用户分配一个角色"""
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        if enterprise:
            for user_id in user_ids:
                # for role_id in role_ids:
                PermRelTenant.objects.update_or_create(
                    user_id=user_id,
                    tenant_id=tenant.pk,
                    enterprise_id=enterprise.pk)
                        # role_id=role_id,
                        # defaults={"role_id": role_id})
                user = user_repo.get_by_user_id(user_id)
                user_kind_role_service.update_user_roles(kind="team", kind_id=tenant.tenant_id, user=user, role_ids=role_ids)

    def add_user_to_team_by_viewer(self, tenant, user_id):
        """在团队中添加一个用户并给用户分配一个默认viewer权限"""
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        if enterprise:
            viewer = user_role_repo.get_viewer_role()
            PermRelTenant.objects.update_or_create(
                user_id=user_id, tenant_id=tenant.pk, identity="viewer", enterprise_id=enterprise.pk, role_id=viewer.pk)

    def user_is_exist_in_team(self, user_list, tenant_name):
        """判断一个用户是否存在于一个团队中"""
        try:
            tenant = self.get_tenant(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = self.get_team_by_team_id(tenant_name)
            if tenant is None:
                raise Tenants.DoesNotExist()
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        for user_id in user_list:
            obj = PermRelTenant.objects.filter(user_id=user_id, tenant_id=tenant.pk, enterprise_id=enterprise.pk)
            if obj:
                return obj[0].user_id
        else:
            return False

    def get_team_service_count_by_team_name(self, team_name):
        tenant = self.get_tenant_by_tenant_name(tenant_name=team_name)
        if tenant is None:
            raise Tenants.DoesNotExist()
        return TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id).count()

    def count_by_tenant_id(self, tenant_id):
        return TenantServiceInfo.objects.filter(tenant_id=tenant_id).count()

    def get_service_source(self, service_alias):
        service_source = TenantServiceInfo.objects.filter(service_alias=service_alias)
        if service_source:
            return service_source[0]
        else:
            return []

    def delete_tenant(self, tenant_name):
        team_repo.delete_tenant(tenant_name=tenant_name)

    def delete_by_tenant_id(self, tenant_id):
        service_count = self.count_by_tenant_id(tenant_id=tenant_id)
        if service_count >= 1:
            raise ErrStillHasServices

        # list all related regions
        tenant_regions = region_repo.list_by_tenant_id(tenant_id)
        success_count = 0
        for tenant_region in tenant_regions:
            try:
                # There is no guarantee that the deletion of each tenant can be successful.
                region_api.delete_tenant(tenant_region["region_name"], tenant_region["tenant_name"])
                success_count = success_count + 1
            except Exception as e:
                logger.error("tenantid: {}; region name: {}; delete tenant: {}".format(tenant_id, tenant_region["tenant_name"],
                                                                                       e))
        # The current strategy is that if a tenant is deleted successfully, it is considered successful.
        # For tenants that have not been deleted successfully, other deletion paths need to be taken.
        if success_count == 0:
            raise ErrAllTenantDeletionFailed

        team_repo.delete_by_tenant_id(tenant_id=tenant_id)

    def get_current_user_tenants(self, user_id):
        tenants = team_repo.get_tenants_by_user_id(user_id=user_id)
        return tenants

    def get_active_user_tenants(self, user_id):
        return team_repo.get_active_tenants_by_user_id(user_id=user_id)

    @transaction.atomic
    def change_tenant_admin(self, user_id, other_user_id, tenant_name):
        s_id = transaction.savepoint()
        enterprise = enterprise_services.get_enterprise_first()
        try:
            tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
            team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID).delete()
            team_repo.get_user_perms_in_permtenant(user_id=other_user_id, tenant_id=tenant.ID).delete()
            own_perm_info = {"user_id": user_id, "tenant_id": tenant.ID, "identity": "viewer", "enterprise_id": enterprise.ID}
            other_perm_info = {
                "user_id": other_user_id,
                "tenant_id": tenant.ID,
                "identity": "owner",
                "enterprise_id": enterprise.ID
            }
            perm_services.add_user_tenant_perm(own_perm_info)
            perm_services.add_user_tenant_perm(other_perm_info)
            transaction.savepoint_commit(s_id)
            return 200, u"授权成功"
        except Exception as e:
            logger.exception(e)
            transaction.savepoint_rollback(s_id)
            return 400, u"授权失败"

    def change_tenant_identity(self, user_id, tenant_name, new_identitys):
        tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        team_repo.delete_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID)
        new_perm_list = list()
        for identity in new_identitys:
            new_perm_list.append(
                PermRelTenant(user_id=user_id, tenant_id=tenant.pk, identity=identity, enterprise_id=enterprise.ID))
        if new_perm_list:
            try:
                PermRelTenant.objects.bulk_create(new_perm_list)
            except Exception as e:
                logging.exception(e)

    @transaction.atomic
    def exit_current_team(self, team_name, user_id):
        s_id = transaction.savepoint()
        try:
            tenant = self.get_tenant_by_tenant_name(tenant_name=team_name)
            team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID).delete()
            transaction.savepoint_commit(s_id)
            return 200, u"退出团队成功"
        except Exception as e:
            logger.exception(e)
            transaction.savepoint_rollback(s_id)
            return 400, u"退出团队失败"

    def get_team_by_team_id(self, team_id):
        team = team_repo.get_team_by_team_id(team_id=team_id)
        if team:
            user = user_repo.get_by_user_id(team.creater)
            team.creater = user.user_id
        return team

    def create_team(self, user, enterprise, region_list=None, team_alias=None):
        team_name = self.random_tenant_name(enterprise=user.enterprise_id, length=8)
        is_public = settings.MODULES.get('SSO_LOGIN')
        if not is_public:
            pay_type = 'payed'
            pay_level = 'company'
        else:
            pay_type = 'free'
            pay_level = 'company'
        expired_day = 7
        if hasattr(settings, "TENANT_VALID_TIME"):
            expired_day = int(settings.TENANT_VALID_TIME)
        expire_time = datetime.datetime.now() + datetime.timedelta(days=expired_day)
        if not region_list:
            region_list = [r.region_name for r in region_repo.get_usable_regions()]
            if not region_list:
                return 404, "无可用数据中心", None
        default_region = region_list[0]
        if not team_alias:
            team_alias = "{0}的团队".format(user.nick_name)
        params = {
            "tenant_name": team_name,
            "pay_type": pay_type,
            "pay_level": pay_level,
            "creater": user.user_id,
            "region": default_region,
            "expired_time": expire_time,
            "tenant_alias": team_alias,
            "enterprise_id": enterprise.enterprise_id,
            "limit_memory": 0,
        }
        team = team_repo.create_tenant(**params)
        create_perm_param = {
            "user_id": user.user_id,
            "tenant_id": team.ID,
            "identity": "owner",
            "enterprise_id": enterprise.ID,
        }
        team_repo.create_team_perms(**create_perm_param)
        return 200, "success", team

    def delete_team_region(self, team_id, region_name):
        # check team
        tenant = team_repo.get_team_by_team_id(team_id)
        # check region
        region_services.get_by_region_name(region_name)

        tenant_region = region_repo.get_team_region_by_tenant_and_region(team_id, region_name)
        if not tenant_region:
            raise ErrTenantRegionNotFound()

        region_api.delete_tenant(region_name, tenant.tenant_name)

        tenant_region.delete()

    def get_enterprise_teams(self, enterprise_id, query=None, page=None, page_size=None, user=None):
        tall = team_repo.get_teams_by_enterprise_id(enterprise_id, query=query)
        total = tall.count()
        if page is not None and page_size is not None:
            paginator = Paginator(tall, page_size)
            raw_tenants = paginator.page(page)
        else:
            raw_tenants = tall
        tenants = []
        for tenant in raw_tenants:
            tenants.append(self.__team_with_region_info(tenant, user))
        return tenants, total

    def list_teams_v2(self, eid, query=None, page=None, page_size=None):
        if query:
            total = Tenants.objects.filter(tenant_alias__contains=query).count()
        else:
            total = Tenants.objects.count()
        tenants = team_repo.list_teams_v2(query, page, page_size)
        for tenant in tenants:
            region_num = tenant_region_repo.count_by_tenant_id(tenant["tenant_id"])
            tenant["region_num"] = region_num
        return tenants, total

    def list_by_tenant_names(self, tenant_names):
        query_set = Tenants.objects.filter(tenant_name__in=tenant_names)
        return [qs.to_dict() for qs in query_set]

    # used by open api before version 5.2
    def list_teams_by_user_id(self, eid, user_id, query=None, page=None, page_size=None):
        tenants = team_repo.list_by_user_id(eid, user_id, query, page, page_size)
        total = team_repo.count_by_user_id(eid, user_id, query)

        for tenant in tenants:
            # 获取一个用户在一个团队中的身份列表
            perms_identitys = self.get_user_perm_identitys_in_permtenant(user_id=user_id, tenant_name=tenant["tenant_id"])
            # 获取一个用户在一个团队中的角色ID列表
            perms_role_list = self.get_user_perm_role_id_in_permtenant(user_id=user_id, tenant_name=tenant["tenant_id"])

            role_infos = []
            for identity in perms_identitys:
                if identity == "access":
                    role_infos.append({"role_name": identity, "role_id": None})
                else:
                    role_id = role_repo.get_role_id_by_role_name(identity)
                    role_infos.append({"role_name": identity, "role_id": role_id})
            for role in perms_role_list:
                role_name = role_repo.get_role_name_by_role_id(role)
                role_infos.append({"role_name": role_name, "role_id": role})
            tenant["role_infos"] = role_infos
        return tenants, total

    def __team_with_region_info(self, tenant, request_user=None):
        try:
            user = user_repo.get_user_by_user_id(tenant.creater)
            owner_name = user.get_name()
        except UserNotExistError:
            owner_name = None

        user_role_list = user_kind_role_service.get_user_roles(kind="team", kind_id=tenant.tenant_id, user=request_user)
        roles = map(lambda x: x["role_name"], user_role_list["roles"])
        if tenant.creater == request_user.user_id:
            roles.append("owner")
        region_info_map = []
        region_list = team_repo.get_team_regions(tenant.tenant_id)
        if region_list:
            region_name_list = region_list.values_list("region_name", flat=True)
            region_infos = region_repo.get_region_by_region_names(region_name_list)
            if region_infos:
                for region in region_infos:
                    region_info_map.append({"region_name": region.region_name, "region_alias": region.region_alias})
        info = {
            "team_name": tenant.tenant_name,
            "team_alias": tenant.tenant_alias,
            "team_id": tenant.tenant_id,
            "create_time": tenant.create_time,
            "region": tenant.region,
            "region_list": region_info_map,
            "enterprise_id": tenant.enterprise_id,
            "owner": tenant.creater,
            "owner_name": owner_name,
        }
        if request_user:
            info["roles"] = roles
        return info

    def get_teams_region_by_user_id(self, enterprise_id, user, name=None):
        teams_list = list()
        tenants = enterprise_repo.get_enterprise_user_teams(enterprise_id, user.user_id, name)
        if tenants:
            for tenant in tenants:
                teams_list.append(self.__team_with_region_info(tenant, user))
        return teams_list

    def check_and_get_user_team_by_name_and_region(self, user_id, tenant_name, region_name):
        tenant = team_repo.get_user_tenant_by_name(user_id, tenant_name)
        if not tenant:
            return tenant
        if not team_repo.get_team_region_by_name(tenant.tenant_id, region_name):
            return None
        else:
            return tenant

    def get_team_by_team_alias(self, team_alias):
        return team_repo.get_team_by_team_alias(team_alias)

    def get_fuzzy_tenants_by_tenant_alias_and_enterprise_id(self, enterprise_id, tenant_alias):
        return team_repo.get_fuzzy_tenants_by_tenant_alias_and_enterprise_id(enterprise_id, tenant_alias)

    def update_by_tenant_id(self, tenant_id, data):
        d = {}
        if data.get("enterprise", ""):
            d["enterprise_id"] = data.get("enterprise_id")
        if data.get("region", ""):
            d["region"] = data.get("region")
        if data.get("is_active", None):
            d["is_active"] = data.get("is_active")
        if data.get("creater", 0):
            d["creater"] = data.get("creater")
        if data.get("tenant_alias", ""):
            d["tenant_alias"] = data.get("tenant_alias")
        team_repo.update_by_tenant_id(tenant_id).update(**d)


team_services = TeamService()

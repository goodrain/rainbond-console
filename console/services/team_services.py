# -*- coding: utf-8 -*-
import datetime
import logging
import random
import string

from django.conf import settings
from django.db import transaction

from backends.models.main import RegionConfig
from backends.services.exceptions import *
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.services.enterprise_services import enterprise_services
from console.services.perm_services import perm_services
from console.services.region_services import region_services
from www.models.main import Tenants, PermRelTenant, TenantServiceInfo

logger = logging.getLogger("default")


class TeamService(object):

    def get_tenant_by_tenant_name(self, tenant_name, exception=True):
        return team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=exception)

    def get_tenant(self, tenant_name):
        if not Tenants.objects.filter(tenant_name=tenant_name).exists():
            raise Tenants.DoesNotExist
        return Tenants.objects.get(tenant_name=tenant_name)

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

    # def add_team(self, team_alias, user, region_names):
    #     team_name = self.random_tenant_name(enterprise=user.enterprise_id, length=8)
    #     if not user:
    #         return "400", u"用户不存在", None
    #     creater = user.user_id
    #     enterprise_id = user.enterprise_id
    #     pay_type = 'payed'
    #     pay_level = 'company'
    #     expired_day = 7
    #     if hasattr(settings, "TENANT_VALID_TIME"):
    #         expired_day = int(settings.TENANT_VALID_TIME)
    #     expire_time = datetime.datetime.now() + datetime.timedelta(
    #         days=expired_day)
    #     if Tenants.objects.filter(
    #             tenant_name=team_name).exists():
    #         return "400", u"团队已存在", None
    #     if not RegionConfig.objects.filter(region_name__in=region_names).exists():
    #         return "400", u"数据中心不存在", None
    #
    #     tenant = Tenants.objects.create(tenant_name=team_name, pay_type=pay_type, pay_level=pay_level,
    #                                     creater=creater,
    #                                     expired_time=expire_time, tenant_alias=team_alias,
    #                                     enterprise_id=enterprise_id)
    #     tenant.save()
    #     try:
    #         for region_name in region_names:
    #             region_services.open_team_region(team_name=team_name, region_name=region_name)
    #         return "200", u"成功", tenant
    #     except Exception as e:
    #         logger.exception(e)
    #         tenant.delete()
    #         return "500", u"开通数据中心错误", None

    def add_user_to_tenant(self, tenant, user):
        perm_tenants = PermRelTenant.objects.filter(tenant_id=tenant.ID, user_id=user.user_id)
        if perm_tenants:
            raise PermTenantsExistError("用户{0}已存在于租户{1}下".format(user.nick_name, tenant.tenant_name))
        perm_tenant = PermRelTenant.objects.create(
            user_id=user.pk, tenant_id=tenant.pk, identity='viewer')
        return perm_tenant

    def add_user_to_team(self, request, tenant, user_ids, identitys):
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=tenant.enterprise_id)
        if enterprise:
            user = request.user
            user_perms = team_services.get_user_perm_identitys_in_permtenant(user_id=user.user_id,
                                                                             tenant_name=tenant.tenant_name)
            user_ids = [int(r) for r in list(set(user_ids))]
            exist_team_user = PermRelTenant.objects.filter(tenant_id=tenant.ID, user_id__in=user_ids).all()
            remove_ids = list()
            exist = []
            for user in exist_team_user:
                exist.append(user.user_id)
            new_user_list = list()
            if ('admin' in user_perms) or ('owner' in user_perms):
                for user_id in user_ids:
                    if user_id not in exist:
                        for identity in identitys:
                            new_user_list.append(PermRelTenant(
                                user_id=user_id, tenant_id=tenant.pk, identity=identity, enterprise_id=enterprise.ID
                            ))
            if new_user_list:
                try:
                    PermRelTenant.objects.bulk_create(new_user_list)
                except Exception as e:
                    logging.exception(e)
                finally:
                    return remove_ids
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

    def get_user_perm_identitys_in_permtenant(self, user_id, tenant_name):
        tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
        user_perms = team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID)
        return [perm.identity for perm in user_perms]

    def get_team_service_count_by_team_name(self, team_name):
        tenant = self.get_tenant_by_tenant_name(tenant_name=team_name)
        return TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id).count()

    def delete_tenant(self, tenant_name):
        status = team_repo.delete_tenant(tenant_name=tenant_name)
        return status

    def get_current_user_tenants(self, user_id):
        tenants = team_repo.get_tenants_by_user_id(user_id=user_id)
        return tenants

    @transaction.atomic
    def change_tenant_admin(self, user_id, other_user_id, tenant_name):
        s_id = transaction.savepoint()
        enterprise = enterprise_services.get_enterprise_first()
        try:
            tenant = self.get_tenant_by_tenant_name(tenant_name=tenant_name)
            team_repo.get_user_perms_in_permtenant(user_id=user_id, tenant_id=tenant.ID).delete()
            team_repo.get_user_perms_in_permtenant(user_id=other_user_id, tenant_id=tenant.ID).delete()
            own_perm_info = {"user_id": user_id, "tenant_id": tenant.ID, "identity": "viewer",
                             "enterprise_id": enterprise.ID}
            other_perm_info = {"user_id": other_user_id, "tenant_id": tenant.ID, "identity": "owner",
                               "enterprise_id": enterprise.ID}
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
            new_perm_list.append(PermRelTenant(
                user_id=user_id, tenant_id=tenant.pk, identity=identity, enterprise_id=enterprise.ID
            ))
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
            "limit_memory": 4096
        }
        team = team_repo.create_tenant(**params)
        return 200, "success", team

    def get_enterprise_teams(self, enterprise_id):
        return team_repo.get_teams_by_enterprise_id(enterprise_id)

team_services = TeamService()

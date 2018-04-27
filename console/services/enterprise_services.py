# -*- coding: utf-8 -*-
import datetime as dt
import logging
import random
import string

# from django.core.mail import send_mail

from backends.services.exceptions import TenantExistError
from console.repositories.enterprise_repo import enterprise_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import *
from www.monitorservice.monitorhook import MonitorHook
from www.utils.conf_tool import regionConfig

logger = logging.getLogger('default')
monitor_hook = MonitorHook()

notify_mail_list = ['21395930@qq.com', 'zhanghy@goodrain.com']


class EnterpriseServices(object):
    """
    企业服务接口，提供以企业为中心的操作集合，企业在云帮体系中为最大业务隔离单元，企业下有团队（也就是tenant）
    """

    def create_and_init_tenant(self, user_id, tenant_name='', region_names=[], enterprise_id='', tenant_alias=''):
        """
        创建一个团队，并完成团队对指定数据中心的初始化
        :param user_id: 用户id
        :param tenant_name: 团队英文, 兼容历史的tenant租户名称信息
        :param tenant_alias: 团队别名, 对团队显示名称
        :param region_names: 指定需要开通的数据中心名字列表
        :param enterprise_id: 企业ID,（兼容实现，如果未指定则使用团队的tenant_id)
        :return:
        """
        logger.debug('create_and_init_tenant.....')
        logger.debug('user_id: {}'.format(user_id))
        logger.debug('tenant_name: {}'.format(tenant_name))
        logger.debug('region_names: {}'.format(region_names))
        logger.debug('enterprise_id: {}:'.format(enterprise_id))
        logger.debug('tenant_alias: {}'.format(tenant_alias))
        # 判断用户是否存在, 如果有enterprise_id意味着用户与enterprise已经绑定
        if enterprise_id:
            user = Users.objects.get(user_id=user_id, enterprise_id=enterprise_id)
            enterprise = TenantEnterprise.objects.get(enterprise_id=enterprise_id)
        else:
            user = Users.objects.get(user_id=user_id)
            enterprise = None

        # if user.is_active:
        #     logger.info('user is already active, return default tenant')
        #     return Tenants.objects.get(creater=user.user_id)

        tenant_name_regx = re.compile(r'^[a-z0-9-]*$')
        if tenant_name and not tenant_name_regx.match(tenant_name):
            logger.error('bad team_name!')
            raise Exception('team_name  must consist of lower case alphanumeric characters or -')

        # 判断团队是否存在
        if not tenant_name:
            tenant_name = self.random_tenant_name()
            logger.info('team_name not specify, generator [{}]'.format(tenant_name))

        tenants_num = Tenants.objects.filter(tenant_name=tenant_name).count()
        if tenants_num > 0:
            raise TenantExistError('team {} already existed!'.format(tenant_name))

        # 私有云默认是企业付费用户
        pay_type = 'payed'
        pay_level = 'company'

        expired_day = 7
        if hasattr(settings, "TENANT_VALID_TIME"):
            expired_day = int(settings.TENANT_VALID_TIME)
        expire_time = dt.datetime.now() + dt.timedelta(days=expired_day)

        # 计算此团队需要初始化的数据中心
        region_configs = {r.get('name'): r for r in regionConfig.regions()}

        if not region_configs:
            raise Exception('please config one region at least.')

        prepare_init_regions = []
        if region_names:
            for region_name in region_names:
                if region_name in region_configs:
                    prepare_init_regions.append(region_configs.get(region_name))
        else:
            prepare_init_regions.extend(region_configs.values())

        if not prepare_init_regions:
            raise Exception('please init one region at least.')

        logger.info('prepared init region: {}'.format([r.get('name') for r in prepare_init_regions]))
        # 团队管理的默认数据中心
        default_region = prepare_init_regions[0]

        # 使用已存在的企业
        if enterprise:
            logger.info('enterprise existed: {}'.format(enterprise.enterprise_name))

            if not tenant_alias:
                tenant_alias = u'{0}的团队'.format(enterprise.enterprise_alias)
            # 创建团队
            tenant = Tenants.objects.create(tenant_name=tenant_name, pay_type=pay_type, pay_level=pay_level,
                                            creater=user_id, region=default_region.get('name'),
                                            expired_time=expire_time, tenant_alias=tenant_alias,
                                            enterprise_id=enterprise.enterprise_id)
            logger.info('create tenant:{}'.format(tenant.to_dict()))

        # 兼容用现有的团队id建立企业信息
        else:
            logger.info('enterprise not existed, use tenant for default enterprise.')
            if not tenant_alias:
                tenant_alias = u'{0}的团队'.format(tenant_name)

            # 创建团队
            tenant = Tenants.objects.create(tenant_name=tenant_name, pay_type=pay_type, pay_level=pay_level,
                                            creater=user_id, region=default_region.get('name'),
                                            expired_time=expire_time, tenant_alias=tenant_alias)
            logger.info('create tenant:{}'.format(tenant.to_dict()))

            # 依赖团队信息创建企业信息
            enterprise = TenantEnterprise.objects.create(enterprise_name=tenant_name,
                                                         enterprise_alias=tenant_name,
                                                         enterprise_id=tenant.tenant_id)
            logger.info('create enterprise with tenant:{}'.format(enterprise.to_dict()))

            # 将企业id关联到团队之上
            tenant.enterprise_id = enterprise.enterprise_id
            tenant.save()

            # 将此用户与企业关系绑定
            user.enterprise_id = enterprise.enterprise_id

        monitor_hook.tenantMonitor(tenant, user, "create_tenant", True)

        # 创建用户团队企业关系及权限，创建团队的用户即为此团队的管理员
        logger.debug('create tenant_perm! user_pk: {0}, tenant_pk:{1}, enterprise_pk:{2}'.format(user_id, tenant.pk,
                                                                                                 enterprise.pk))
        PermRelTenant.objects.create(user_id=user_id, tenant_id=tenant.pk, identity='owner',
                                     enterprise_id=enterprise.pk)

        # 初始化数据中心并建立团队与数据中心的关系
        api = RegionInvokeApi()
        for region in prepare_init_regions:
            tenant_region = TenantRegionInfo.objects.create(tenant_id=tenant.tenant_id,
                                                            region_name=region.get('name'),
                                                            enterprise_id=enterprise.enterprise_id)
            try:
                res, body = api.create_tenant(region.get('name'), tenant.tenant_name, tenant.tenant_id,
                                              enterprise.enterprise_id)
                logger.debug(res)
                logger.debug(body)
                tenant_region.is_active = True
                tenant_region.is_init = True

                # todo 将从数据中心获取的租户信息记录到tenant_region, 当前只是用tenant的数据填充
                tenant_region.region_tenant_id = tenant.tenant_id
                tenant_region.region_tenant_name = tenant.tenant_name
                tenant_region.region_scope = 'public'

                tenant_region.save()
                logger.info("tenant_region[{0}] = {1}, {2}, {3}".format(tenant_region.region_name,
                                                                        tenant_region.region_tenant_id,
                                                                        tenant_region.region_tenant_name,
                                                                        tenant_region.region_scope))

                monitor_hook.tenantMonitor(tenant, user, "init_tenant", True)
                logger.info("init success!")
            except Exception as e:
                logger.error("init failed: {}".format(e.message))
                logger.exception(e)

                tenant_region.is_init = False
                tenant_region.is_active = False
                tenant_region.save()
                monitor_hook.tenantMonitor(tenant, user, "init_tenant", False)

        user.is_active = True
        user.save()

        # content = '新用户: {0}, 租户: {1}, 邮箱: {2}, 企业: {3}'.format(user.nick_name, tenant.tenant_name, user.email,
        #                                                        enterprise.enterprise_alias)
        # send_mail("new user active tenant", content, 'no-reply@goodrain.com', notify_mail_list)
        return tenant

    def random_tenant_name(self, enterprise=None, length=8):
        """
        生成随机的云帮租户（云帮的团队名），副需要符合k8s的规范(小写字母,_)
        :param enterprise 企业信息
        :param length:
        :return:
        """

        # todo 可以根据enterprise的信息来生成租户名
        tenant_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        while Tenants.objects.filter(tenant_name=tenant_name).count() > 0:
            tenant_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        return tenant_name

    def random_enterprise_name(self, length=8):
        """
        生成随机的云帮企业名，副需要符合k8s的规范(小写字母,_)
        :param length:
        :return:
        """

        enter_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        while TenantEnterprise.objects.filter(enterprise_name=enter_name).count() > 0:
            enter_name = ''.join(random.sample(string.ascii_lowercase + string.digits, length))
        return enter_name

    def create_enterprise(self, enterprise_name='', enterprise_alias=''):
        """
        创建一个本地的企业信息, 并生成本地的企业ID

        :param enterprise_name: 企业的英文名, 如果没有则自动生成一个, 如果存在则需要保证传递的名字在数据库中唯一
        :param enterprise_alias: 企业的别名, 可以中文, 用于展示用, 如果为空则自动生成一个
        :return:
        """
        enterprise = TenantEnterprise()

        # 处理企业英文名
        if enterprise_name:
            enterprise_name_regx = re.compile(r'^[a-z0-9-]*$')
            if enterprise_name and not enterprise_name_regx.match(enterprise_name):
                logger.error('bad enterprise_name: {}'.format(enterprise_name))
                raise Exception('enterprise_name  must consist of lower case alphanumeric characters or -')

            if TenantEnterprise.objects.filter(enterprise_name=enterprise_name).count() > 0:
                raise Exception('enterprise_name [{}] already existed!'.format(enterprise_name))
            else:
                enter_name = enterprise_name
        else:
            enter_name = self.random_enterprise_name()
        enterprise.enterprise_name = enter_name

        # 根据企业英文名确认UUID
        enterprise.enterprise_id = make_uuid(enter_name)

        # 处理企业别名
        if not enterprise_alias:
            enterprise.enterprise_alias = '企业{0}'.format(enter_name)
        else:
            enterprise.enterprise_alias = enterprise_alias

        enterprise.save()
        return enterprise

    def get_enterprise_by_id(self, enterprise_id):
        try:
            return TenantEnterprise.objects.get(enterprise_id=enterprise_id)
        except TenantEnterprise.DoesNotExist:
            return None

    def active(self, enterprise, enterprise_token):
        """
        绑定企业与云市的访问的api token
        :param enterprise:
        :param enterprise_token:
        :return:
        """
        enterprise.enterprise_token = enterprise_token
        enterprise.is_active = 1
        enterprise.save()
        return True

    def get_enterprise_by_enterprise_name(self, enterprise_name, exception=True):
        """
        通过企业名查找企业
        :param enterprise_name: 企业名
        :param exception: 控制如果企业不存在抛异常与否
        :return: 返回 None 或者企业
        """
        return enterprise_repo.get_enterprise_by_enterprise_name(enterprise_name=enterprise_name, exception=exception)

    def get_enterprise_first(self):
        return enterprise_repo.get_enterprise_first()

    def get_enterprise_by_enterprise_id(self, enterprise_id, exception=True):
        return enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id=enterprise_id, exception=exception)

    def create_tenant_enterprise(self, enterprise_id, enterprise_name, enterprise_alias, is_active=True):
        params = {
            "enterprise_id": enterprise_id,
            "enterprise_name": enterprise_name,
            "enterprise_alias": enterprise_alias,
            "is_active": is_active,
        }
        return enterprise_repo.create_enterprise(**params)

    # def get_enterprise_tenants(self,enterprise):
    def get_enterprise_by_eids(self,eid_list):
        return enterprise_repo.get_enterprises_by_enterprise_ids(eid_list)

    def get_enterprise_by_enterprise_alias(self, enterprise_alias):
        return enterprise_repo.get_by_enterprise_alias(enterprise_alias)

enterprise_services = EnterpriseServices()

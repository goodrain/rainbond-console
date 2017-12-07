# -*- coding: utf8 -*-
import datetime
import logging

from django.conf import settings

from www.models import TenantServiceInfo, TenantServicesPort, Tenants, ServiceAttachInfo, ServiceConsume, ServiceFeeBill, \
    TenantRegionInfo
from www.models.main import ServiceGroup, ServiceGroupRelation
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import TenantAccountService, ServiceAttachInfoManage

from www.apiclient.regionapi import RegionInvokeApi


logger = logging.getLogger('default')
tenantAccountService = TenantAccountService()
region_api = RegionInvokeApi()
monitorhook = MonitorHook()
attach_manager = ServiceAttachInfoManage()


class TenantService(object):
    def get_tenant_by_name(self, tenant_name):
        try:
            return Tenants.objects.get(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            return None

    def list_tenant_group_on_region(self, tenant, region_name):
        return ServiceGroup.objects.filter(tenant_id=tenant.tenant_id, region_name=region_name)

    def get_tenant_group_on_region_by_id(self, tenant, group_id, region_name):
        try:
            return ServiceGroup.objects.get(tenant_id=tenant.tenant_id, pk=group_id, region_name=region_name)
        except ServiceGroup.DoesNotExist:
            return None

    def list_tenant_group_service(self, tenant, group):
        svc_relations = ServiceGroupRelation.objects.filter(tenant_id=tenant.tenant_id, group_id=group.ID)
        if not svc_relations:
            return list()

        svc_ids = [svc_rel.service_id for svc_rel in svc_relations]
        return TenantServiceInfo.objects.filter(service_id__in=svc_ids)

    def get_tenant_service_by_alias(self, tenant, service_alias):
        try:
            return TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_alias)
        except TenantServiceInfo.DoesNotExist:
            return None

    def get_access_url(self, tenant, service):
        tenant_ports = TenantServicesPort.objects.filter(tenant_id=tenant.tenant_id, service_id=service.service_id,
                                                         is_outer_service=1)
        if not tenant_ports:
            return ''

        # 如果有多个对外端口，取第一个
        tenant_port = tenant_ports[0]
        wild_domain = settings.WILD_DOMAINS[service.service_region]
        wild_domain_port = settings.WILD_PORTS[service.service_region]

        access_url = 'http://{0}.{1}.{2}{3}:{4}'.format(tenant_port.container_port,
                                                        service.service_alias,
                                                        tenant.tenant_name,
                                                        wild_domain,
                                                        wild_domain_port)
        return access_url

    def __get_tenant_service_pay_status(self, tenant, service, service_current_status):
        rt_status = "unknown"
        rt_tips = "应用支付状态未知"
        rt_money = 0.0
        need_pay_money = 0.0
        start_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        now = datetime.datetime.now()
        try:
            service_attach_info = ServiceAttachInfo.objects.get(tenant_id=tenant.tenant_id,
                                                                service_id=service.service_id)
        except ServiceAttachInfo.DoesNotExist:
            return rt_status, rt_tips, rt_money, need_pay_money, start_time_str

        buy_start_time = service_attach_info.buy_start_time
        buy_end_time = service_attach_info.buy_end_time
        memory_pay_method = service_attach_info.memory_pay_method
        disk_pay_method = service_attach_info.disk_pay_method

        service_consume_list = ServiceConsume.objects.filter(tenant_id=tenant.tenant_id,
                                                             service_id=service.service_id).order_by("-ID")
        last_hour_cost = None
        if service_consume_list:
            last_hour_cost = service_consume_list[0]
            rt_money = last_hour_cost.pay_money

        service_unpay_bill_list = ServiceFeeBill.objects.filter(service_id=service.service_id,
                                                                tenant_id=tenant.tenant_id,
                                                                pay_status="unpayed")
        buy_start_time_str = buy_start_time.strftime("%Y-%m-%d %H:%M:%S")
        diff_minutes = int((buy_start_time - now).total_seconds() / 60)
        if service_current_status == "running":
            if diff_minutes > 0:
                if memory_pay_method == "prepaid" or disk_pay_method == "prepaid":
                    if service_unpay_bill_list:
                        rt_status = "wait_for_pay"
                        rt_tips = "请于{0}前支付{1}元".format(buy_start_time_str,
                                                        service_unpay_bill_list[0].prepaid_money)
                        need_pay_money = service_unpay_bill_list[0].prepaid_money
                        start_time_str = buy_start_time_str
                    else:
                        rt_status = "soon"
                        rt_tips = "将于{0}开始计费".format(buy_start_time_str)
                else:
                    rt_status = "soon"
                    rt_tips = "将于{0}开始计费".format(buy_start_time_str)
            else:
                if memory_pay_method == "prepaid" or disk_pay_method == "prepaid":
                    if now < buy_end_time:
                        rt_status = "show_money"
                        rt_tips = "包月包年项目于{0}到期".format(buy_end_time.strftime("%Y-%m-%d %H:%M:%S"))
                    else:
                        rt_status = "show_money"
                        rt_tips = "包月包年项目已于{0}到期,应用所有项目均按需结算".format(buy_end_time.strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    rt_status = "show_money"
                    rt_tips = "当前应用所有项目均按小时结算"
        else:
            if diff_minutes > 0:
                rt_status = "debugging"
                rt_tips = "应用尚未运行"
            else:
                rt_status = "show_money"
                rt_tips = "应用尚未运行"

        return rt_status, rt_tips, rt_money, need_pay_money, start_time_str

    def get_tenant_service_status(self, tenant, service):
        result = {}
        if tenantAccountService.isOwnedMoney(tenant, service.service_region):
            service_attach_info = ServiceAttachInfo.objects.get(tenant_id=tenant.tenant_id,service_id=service.service_id)
            is_prepaid = attach_manager.is_during_monthly_payment(service_attach_info)
            if not is_prepaid:
                result["totalMemory"] = 0
                result["status"] = "Owed"
                result["service_pay_status"] = "no_money"
                result["tips"] = "请为账户充值,然后重启应用"
                return result

        if service.deploy_version is None or service.deploy_version == "":
            result["totalMemory"] = 0
            result["status"] = "undeploy"
            result["service_pay_status"] = "debugging"
            result["tips"] = "应用尚未运行"
            return result

        try:
            body = region_api.check_service_status(service.service_region,tenant.tenant_name,service.service_alias,tenant.enterprise_id)
            bean = body["bean"]

        except Exception, e:
            logger.debug(service.service_region + "-" + service.service_id + " check_service_status is error")
            logger.exception(e)

            result["totalMemory"] = 0
            result['status'] = "failure"
            result["service_pay_status"] = "unknown"
            result["tips"] = "服务状态未知"
            return result

        status = bean["cur_status"]
        result["status"] = status
        if status == "running":
            result["totalMemory"] = service.min_node * service.min_memory
        else:
            result["totalMemory"] = 0

        service_pay_status, tips, cost_money, need_pay_money, start_time_str = self.__get_tenant_service_pay_status(
            tenant, service, status)
        result["service_pay_status"] = service_pay_status
        result["tips"] = tips
        result["cost_money"] = cost_money
        result["need_pay_money"] = need_pay_money
        result["start_time_str"] = start_time_str

        return result

    def init_region_tenant(self, tenant, region):
        """
        为团队初始化所在数据中心数据，如果tenant_region存在记录，且未初始化，将记录更新
        :param tenant:
        :param region:
        :return: 成功返回True,失败返回False
        """
        logger.debug("init region tenant...")
        success = True
        tenant_region = self.get_tenant_region_info(tenant, region)
        if not tenant_region:
            tenant_region = TenantRegionInfo()
            tenant_region.tenant_id = tenant.tenant_id
            tenant_region.region_name = region
            tenant_region.save()
        if not tenant_region.is_init:
            api = RegionInvokeApi()
            logger.debug(
                "create tenant {0} with tenant_id {1} on region {2}".format(tenant.tenant_name,
                                                                            tenant.tenant_id,
                                                                            region))
            logger.info("start invoking api to init region tenant !")
            try:
                res, body = api.create_tenant(region, tenant.tenant_name, tenant.tenant_id, tenant.enterprise_id)
                logger.debug(res, body)
                tenant_region.is_active = True
                tenant_region.is_init = True
                # todo 将从数据中心获取的租户信息记录到tenant_region, 当前只是用tenant的数据填充
                tenant_region.region_tenant_id = tenant.tenant_id
                tenant_region.region_tenant_name = tenant.tenant_name
                tenant_region.region_scope = 'public'
                tenant_region.enterprise_id = tenant.enterprise_id

                tenant_region.save()
            except api.CallApiError, e:
                logger.error("create tenant {0} failed".format(tenant.tenant_name))
                logger.exception(e)
                success = False
        # 部分初始化但是
        else:
            if (not tenant_region.region_tenant_id) or \
                    (not tenant_region.region_tenant_name) or \
                    (not tenant_region.enterprise_id):
                tenant_region.region_tenant_id = tenant.tenant_id
                tenant_region.region_tenant_name = tenant.tenant_name
                tenant_region.region_scope = 'public'
                tenant_region.enterprise_id = tenant.enterprise_id
                tenant_region.save()
        return success

    def get_tenant_region_info(self, tenant, region):
        try:
            return TenantRegionInfo.objects.get(tenant_id=tenant.tenant_id, region_name=region)
        except TenantRegionInfo.DoesNotExist:
            return None

    def init_for_region(self, region, tenant_name, tenant_id, user):
        tenant = Tenants.objects.get(tenant_id=tenant_id)
        is_init_success = self.init_region_tenant(tenant,region)
        monitorhook.tenantMonitor(tenant, user, "init_tenant", is_init_success)
        return is_init_success
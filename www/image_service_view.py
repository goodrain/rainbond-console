# -*- coding: utf8 -*-
import json
import logging

from django.http.response import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from share.manager.region_provier import RegionProviderManager
from www.decorator import perm_required
from www.models.main import TenantServiceInfo, ServiceInfo, ImageServiceRelation, TenantServiceEnvVar, \
    TenantServicesPort, TenantServiceVolume, ServiceAttachInfo, ServiceGroupRelation, ServiceFeeBill
from www.monitorservice.monitorhook import MonitorHook
from www.service_http import RegionServiceApi
from www.tenantservice.baseservice import TenantRegionService, TenantAccountService, TenantUsedResource, \
    BaseTenantService
from www.utils.crypt import make_uuid
from www.views.base import AuthedView
from www.views.mixin import LeftSideBarMixin
from django.conf import settings
import httplib2
import datetime
from dateutil.relativedelta import relativedelta
from www.utils import sn

logger = logging.getLogger('default')
tenantRegionService = TenantRegionService()
tenantAccountService = TenantAccountService()
tenantUsedResource = TenantUsedResource()
baseService = BaseTenantService()
monitorhook = MonitorHook()
regionClient = RegionServiceApi()
rpmManager = RegionProviderManager()


class ImageServiceDeploy(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/css/style.css', 'www/css/style-responsive.css', 'www/js/jquery.cookie.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/respond.min.js', 'www/js/app-create.js')
        return media

    def get_estimate_service_fee(self, service_attach_info):
        """根据附加信心获取服务的预估价格"""
        total_price = 0
        regionBo = rpmManager.get_work_region_by_name(self.response_region)
        pre_paid_memory_price = regionBo.memory_package_price
        pre_paid_disk_price = regionBo.disk_package_price
        if service_attach_info.memory_pay_method == "prepaid":
            total_price += service_attach_info.min_node * service_attach_info.min_memory / 1024 * pre_paid_memory_price
        if service_attach_info.disk_pay_method == "prepaid":
            total_price += service_attach_info.disk / 1024 * pre_paid_disk_price
        total_price = total_price * service_attach_info.pre_paid_period * 30 * 24
        return round(total_price, 2)

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        choose_region = request.GET.get("region", None)
        if choose_region is not None:
            self.response_region = choose_region

        context = self.get_context()
        context["createApp"] = "active"
        service_id = request.GET.get("id", "")

        try:
            if service_id != "":
                imags = ImageServiceRelation.objects.get(service_id=service_id)
                context["image_url"] = imags.image_url
                context["service_id"] = service_id
            regionBo = rpmManager.get_work_region_by_name(self.response_region)
            context['pre_paid_memory_price'] = regionBo.memory_package_price
            context['post_paid_memory_price'] = regionBo.memory_trial_price
            context['pre_paid_disk_price'] = regionBo.disk_package_price
            context['post_paid_disk_price'] = regionBo.disk_trial_price
            context['post_paid_net_price'] = regionBo.net_trial_price
            # 是否为免费租户
            context['is_tenant_free'] = (self.tenant.pay_type == "free")

            context['cloud_assistant'] = sn.instance.cloud_assistant
            context["is_private"] = sn.instance.is_private()
            # 判断云帮是否为公有云
            context["is_public_clound"] = sn.instance.cloud_assistant == "goodrain" and (not sn.instance.is_private())

        except Exception as e:
            logger.error(e)
        return TemplateResponse(self.request, "www/app_create_step_two.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        result = {}
        service_id = ""
        try:
            tenant_id = self.tenant.tenant_id
            service_id = request.POST.get("service_id", "")
            image_url = request.POST.get("image_url", "")
            service_cname = request.POST.get("create_app_name", "")
            result["image_url"] = image_url
            if image_url != "":
                imagesr = None
                if service_id != "":
                    try:
                        imagesr = ImageServiceRelation.objects.get(service_id=service_id)
                    except Exception:
                        pass

                if imagesr is None:
                    imagesr = ImageServiceRelation()
                    service_id = make_uuid(self.tenant.tenant_id)

                imagesr.tenant_id = self.tenant.tenant_id
                imagesr.service_id = service_id
                imagesr.image_url = image_url
                imagesr.service_cname = service_cname
                imagesr.save()

                # save service attach info
                min_memory = int(request.POST.get("service_min_memory", 128))
                # 将G转换为M
                if min_memory < 128:
                    min_memory *= 1024
                min_node = int(request.POST.get("service_min_node", 1))

                # judge region tenant is init
                success = tenantRegionService.init_for_region(self.response_region, self.tenantName, tenant_id,
                                                              self.user)
                if not success:
                    result["status"] = "failure"
                    return JsonResponse(result, status=200)

                # if tenantAccountService.isOwnedMoney(self.tenant, self.response_region):
                #     result["status"] = "owed"
                #     return JsonResponse(result, status=200)

                # calculate resource
                tempService = TenantServiceInfo()
                tempService.min_memory = min_memory
                tempService.service_region = self.response_region
                tempService.min_node = min_node
                diffMemory = min_node * min_memory
                rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, tempService, diffMemory, False)
                if not flag:
                    if rt_type == "memory":
                        result["status"] = "over_memory"
                    else:
                        result["status"] = "over_money"
                    return JsonResponse(result, status=200)

                memory_pay_method = request.POST.get("memory_pay_method", "prepaid")
                disk_pay_method = request.POST.get("disk_pay_method", "prepaid")
                pre_paid_period = int(request.POST.get("pre_paid_period", 1))
                disk = int(request.POST.get("disk_num", 0))
                # 将G转换为M
                if disk < 1024:
                    disk *= 1024

                create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                startTime = datetime.datetime.now() + datetime.timedelta(hours=1)
                endTime = startTime + relativedelta(months=int(pre_paid_period))
                # 保存配套信息
                sai = ServiceAttachInfo()
                sai.tenant_id = tenant_id
                sai.service_id = service_id
                sai.memory_pay_method = memory_pay_method
                sai.disk_pay_method = disk_pay_method
                sai.min_memory = min_memory
                sai.min_node = min_node
                sai.disk = disk
                sai.pre_paid_period = pre_paid_period
                sai.buy_start_time = startTime
                sai.buy_end_time = endTime
                sai.create_time = create_time
                sai.pre_paid_money = self.get_estimate_service_fee(sai)
                sai.save()
                # 创建预付费订单
                if sai.pre_paid_money > 0:
                    ServiceFeeBill.objects.create(tenant_id=tenant_id, service_id=service_id,
                                                  prepaid_money=sai.pre_paid_money, pay_status="unpayed",
                                                  cost_type="firs_create", node_memory=min_memory, node_num=min_node,
                                                  disk=disk, buy_period=pre_paid_period * 24 * 30)

                result["status"] = "success"
                result["id"] = service_id
                group_id = request.POST.get("select_group_id", "")
                # 创建关系
                if group_id != "":
                    group_id = int(group_id)
                    if group_id > 0:
                        ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id,
                                                            tenant_id=self.tenant.tenant_id, region_name=self.response_region)
            else:
                result["status"] = "no_image_url"
                return JsonResponse(result, status=500)
        except Exception as e:
            logger.exception(e)
            if service_id != "" and service_id is not None:
                ImageServiceRelation.objects.filter(service_id=service_id).delete()
                ServiceAttachInfo.objects.filter(service_id=service_id).delete()
            result["status"] = "failure"
            return JsonResponse(result, status=500)
        return JsonResponse(result, status=200)


class ImageParamsViews(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/css/style.css', 'www/css/style-responsive.css', 'www/js/jquery.cookie.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/respond.min.js')
        return media

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        choose_region = request.GET.get("region", None)
        if choose_region is not None:
            self.response_region = choose_region

        context = self.get_context()
        try:
            service_id = request.GET.get("id", "")
            context["service_id"] = service_id
            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
            context["service_alias"]="gr" + service_id[-6:]

            deployTenantServices = TenantServiceInfo.objects.filter(
                tenant_id=self.tenant.tenant_id,
                service_region=self.response_region,
                service_origin='assistant').exclude(category='application')
            context["deployTenantServices"] = deployTenantServices

            tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user, self.tenant.tenant_id,
                                                             region=self.response_region)
            context["tenantServiceList"] = tenantServiceList
            try:
                imsr = ImageServiceRelation.objects.get(service_id=service_id)
                context["service_cname"] = imsr.service_cname
            except ImageServiceRelation.DoesNotExist:
                pass

            return TemplateResponse(self.request, "www/app_create_docker_3.html", context)
        except Exception as e:
            logger.exception(e)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        service_id = request.POST.get("service_id", "")
        result = {}
        try:
            imsr = ImageServiceRelation.objects.get(service_id=service_id)
            tenant_id = imsr.tenant_id
            image_url = imsr.image_url
            service_cname = imsr.service_cname
        except Exception as e:
            logger.exception(e)
            result["status"] = "notfound"
            return JsonResponse(result, status=200)

        service_alias = "gr" + service_id[-6:]
        try:
            success = tenantRegionService.init_for_region(self.response_region, self.tenantName, tenant_id, self.user)

            # 从url中分析出来service_cname 和 version

            version = ""
            if ":" in image_url:
                index = image_url.rindex(":")
                if service_cname is None or service_cname == "":
                    str_tmp = image_url.split(":")
                    service_cname = str_tmp[len(str_tmp)-2]
                version = image_url[index + 1:]
            else:
                if service_cname is None or service_cname == "":
                    service_cname = image_url
                version = "lastest"

            # 端口信息
            port_list = json.loads(request.POST.get("port_list", "[]"))
            # 环境变量信息
            env_list = json.loads(request.POST.get("env_list", "[]"))
            # 持久化目录信息
            volume_list = json.loads(request.POST.get("volume_list", "[]"))
            # 依赖服务id
            depIds = json.loads(request.POST.get("depend_list", "[]"))
            # 挂载其他服务目录
            service_alias_list = json.loads(request.POST.get("mnt_list", "[]"))
            # 资源内存(从上一步获取)
            image_service_memory = 128
            try:
                sai = ServiceAttachInfo.objects.get(service_id=service_id)
                image_service_memory = sai.min_memory
            except ServiceAttachInfo.DoesNotExist:
                pass
            # 启动命令
            start_cmd = request.POST.get("start_cmd", "")

            if not success:
                result["status"] = "failure"
                return JsonResponse(result, status=200)
            # if tenantAccountService.isOwnedMoney(self.tenant, self.response_region):
            #     result["status"] = "owed"
            #     return JsonResponse(result, status=200)
            # if tenantAccountService.isExpired(self.tenant,self.service):
            #     result["status"] = "expired"
            #     return JsonResponse(result, status=200)

            service = ServiceInfo()
            service.service_key = "0000"
            service.desc = ""
            service.category = "app_publish"
            service.image = image_url
            service.cmd = start_cmd
            service.setting = ""
            service.extend_method = "stateless"
            service.env = ","
            service.min_node = 1
            cm = 128
            ccpu = 20
            if image_service_memory != "":
                cm = int(image_service_memory)
                ccpu = int(cm / 128) * 20
            service.min_memory = cm
            service.min_cpu = ccpu
            service.inner_port = 0
            # version version需要从image_url中分析出来
            service.version = version
            service.namespace = "goodrain"
            service.update_version = 1
            service.volume_mount_path = ""
            service.service_type = "application"
            # service host_path
            service.host_path = "/grdata/tenant/" + self.tenant.tenant_id + "/service/" + service_id
            # calculate resource
            tempService = TenantServiceInfo()
            tempService.min_memory = cm
            tempService.service_region = self.response_region
            tempService.min_node = int(service.min_node)

            diffMemory = cm
            # 判断是否超出资源
            rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, tempService, diffMemory, False)
            if not flag:
                if rt_type == "memory":
                    result["status"] = "over_memory"
                else:
                    result["status"] = "over_money"
                return JsonResponse(result, status=200)

            newTenantService = baseService.create_service(service_id, tenant_id, service_alias, service_cname, service,
                                                          self.user.pk,
                                                          region=self.response_region)
            newTenantService.code_from = "image_manual"
            newTenantService.language = "docker-image"
            newTenantService.save()
            monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'create_service', True)
            self.save_ports_envs_and_volumes(port_list, env_list, volume_list, newTenantService)

            # 创建挂载目录
            for dep_service_alias in service_alias_list:
                baseService.create_service_mnt(self.tenant.tenant_id, newTenantService.service_id,
                                               dep_service_alias["otherName"],
                                               newTenantService.service_region)

            baseService.create_region_service(newTenantService, self.tenantName, self.response_region,
                                              self.user.nick_name, dep_sids=json.dumps([]))
            # self.send_task("aws-jp-1", "image_manual", newTenantService)
            monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'init_region_service', True)

            logger.debug(depIds)
            # 添加GD_ADAPTER环境变量
            if len(depIds) > 0:
                self.saveAdapterEnv(newTenantService)
            for sid in depIds:
                try:
                    baseService.create_service_dependency(self.tenant.tenant_id, newTenantService.service_id, sid,
                                                          self.response_region)
                except Exception as e:
                    logger.exception(e)

            result["status"] = "success"
            result["service_id"] = service_id
            result["service_alias"] = service_alias
            # 设置服务购买的起始时间
            attach_info = ServiceAttachInfo.objects.get(service_id=service_id)
            pre_paid_period = attach_info.pre_paid_period

            if self.tenant.pay_type == "free":
                # 免费租户的应用过期时间为7天
                startTime = datetime.datetime.now() + datetime.timedelta(days=7)+datetime.timedelta(hours=1)
                startTime = startTime.strftime("%Y-%m-%d %H:00:00")
                service = self.service
                service.expired_time = startTime
                service.save()
                endTime = startTime + relativedelta(months=int(pre_paid_period))
                ServiceAttachInfo.objects.filter(service_id=self.service.service_id).update(buy_start_time=startTime,
                                                                                            buy_end_time=endTime)
            else:
                # 付费用户一个小时调试
                startTime = datetime.datetime.now() + datetime.timedelta(hours=2)
                startTime = startTime.strftime("%Y-%m-%d %H:00:00")
                # startTime = datetime.datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
                endTime = startTime + relativedelta(months=int(pre_paid_period))
                ServiceAttachInfo.objects.filter(service_id=self.service.service_id).update(buy_start_time=startTime,
                                                                                            buy_end_time=endTime)
            # if self.tenant.pay_type == "free":
            #     # 免费租户的应用过期时间为7天
            #     service = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id, service_id=service_id)
            #     service.expired_time = datetime.datetime.now() + datetime.timedelta(days=7)
            #     service.save()
            #     startTime = datetime.datetime.now() + datetime.timedelta(days=7)
            #     endTime = startTime + relativedelta(months=int(pre_paid_period))
            #     ServiceAttachInfo.objects.filter(service_id=service_id).update(buy_start_time=startTime,
            #                                                                    buy_end_time=endTime)
            # else:
            #     startTime = datetime.datetime.now() + datetime.timedelta(hours=1)
            #     endTime = startTime + relativedelta(months=int(pre_paid_period))
            #     ServiceAttachInfo.objects.filter(service_id=service_id).update(buy_start_time=startTime,
            #                                                                    buy_end_time=endTime)

        except Exception as e:
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service_id).delete()
            TenantServicesPort.objects.filter(service_id=service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service_id).delete()
            logger.exception(e)

        return JsonResponse(result, status=200)

    def save_ports_envs_and_volumes(self, ports, envs, volumes, tenant_serivce):
        """保存端口,环境变量和持久化目录"""
        for port in ports:
            baseService.addServicePort(tenant_serivce, False, container_port=int(port["container_port"]),
                                       protocol=port["protocol"], port_alias=port["port_alias"],
                                       is_inner_service=port["is_inner_service"],
                                       is_outer_service=port["is_outer_service"])

        for env in envs:
            baseService.saveServiceEnvVar(tenant_serivce.tenant_id, tenant_serivce.service_id, 0,
                                          env["name"], env["attr_name"], env["attr_value"], True, "inner")

        for volume in volumes:
            baseService.add_volume_list(tenant_serivce, volume["volume_path"])
        
        if len(volumes) > 0:
            temp_service = TenantServiceInfo.objects.get(service_id=tenant_serivce.service_id)
            if temp_service.host_path is None or temp_service.host_path == "":
                    temp_service.host_path = "/grdata/tenant/" + temp_service.tenant_id + "/service/" + temp_service.service_id
                    temp_service.save()

    def send_task(self, region, topic, tenant_service):
        body = {"image": tenant_service.image_name,
                "deploy_version": tenant_service.deploy_version,
                "service_id": tenant_service.service_id,
                "service_alias": tenant_service.service_alias,
                "app_version": tenant_service.service_version,
                "namespace": tenant_service.namespace,
                "operator": tenant_service.operator,
                "action": "download_and_deploy",
                "dep_sids": json.dumps([])}
        regionClient.send_task(region, topic, body)

    def saveAdapterEnv(self, service):
        num = TenantServiceEnvVar.objects.filter(service_id=service.service_id, attr_name="GD_ADAPTER").count()
        if num < 1:
            attr = {"tenant_id": service.tenant_id, "service_id": service.service_id, "name": "GD_ADAPTER",
                    "attr_name": "GD_ADAPTER", "attr_value": "true", "is_change": 0, "scope": "inner", "container_port":-1}
            TenantServiceEnvVar.objects.create(**attr)
            data = {"action": "add", "attrs": attr}
            regionClient.createServiceEnv(service.service_region, service.service_id, json.dumps(data))
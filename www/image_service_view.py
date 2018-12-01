# -*- coding: utf8 -*-
import base64
import datetime
import json
import logging

from django.http.response import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from share.manager.region_provier import RegionProviderManager
from www.apiclient.regionapi import RegionInvokeApi
from www.db import svc_grop_repo
from www.decorator import perm_required
from www.models.main import TenantServiceInfo, ServiceInfo, ImageServiceRelation, TenantServiceEnvVar, \
    TenantServicesPort, TenantServiceVolume, ServiceAttachInfo, ServiceGroupRelation, ServiceEvent
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import TenantAccountService, TenantUsedResource, \
    BaseTenantService, AppCreateService, ServiceAttachInfoManage
from www.utils import sn
from www.utils.crypt import make_uuid
from www.utils.imageD import ImageAnalyst
from www.views.base import AuthedView
from www.views.mixin import LeftSideBarMixin
from www.services import tenant_svc

logger = logging.getLogger('default')
tenantAccountService = TenantAccountService()
tenantUsedResource = TenantUsedResource()
baseService = BaseTenantService()
monitorhook = MonitorHook()
rpmManager = RegionProviderManager()
appCreateService = AppCreateService()
region_api = RegionInvokeApi()
attach_info_mamage = ServiceAttachInfoManage()


class ImageServiceDeploy(LeftSideBarMixin, AuthedView):
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
            context["is_public_clound"] = (sn.instance.cloud_assistant == "goodrain" and (not sn.instance.is_private()))

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
            image_input = request.POST.get("image_url", "")
            service_cname = request.POST.get("create_app_name", "")
            _is, list_args, run_execs = ImageAnalyst.analystImage(image_input)
            if not run_execs:
                run_execs = ""
            image_url = list_args[-1]
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
                logger.debug("setp2 image url is {}".format(image_url))
                # save service attach info
                # min_memory = int(request.POST.get("service_min_memory", 128))
                # # 将G转换为M
                # if min_memory < 128:
                #     min_memory *= 1024
                # min_node = int(request.POST.get("service_min_node", 1))

                # judge region tenant is init
                success = tenant_svc.init_for_region(self.response_region, self.tenantName, tenant_id,
                                                     self.user)
                if not success:
                    result["status"] = "failure"
                    return JsonResponse(result, status=200)

                result["status"] = "success"
                result["id"] = service_id
                group_id = request.POST.get("select_group_id", "")
                # 创建关系
                if group_id != "":
                    group_id = int(group_id)
                    if group_id > 0:
                        ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id,
                                                            tenant_id=self.tenant.tenant_id,
                                                            region_name=self.response_region)
                if _is == "is_docker":
                    args = ""
                    for mm in list_args[:-1]:
                        if args:
                            args = "{0}^_^{1}=={2}".format(args, mm[0], mm[1])
                        else:
                            args = "{0}=={1}".format(mm[0], mm[1])
                    if args:
                        args += "^_^{0}=={1}^_^{2}=={3}".format("image", image_url, "run_exec", run_execs)
                    else:
                        args = "{0}=={1}^_^{2}=={3}".format("image", image_url, "run_exec", run_execs)
                    logger.debug(args)
                    result["params"] = base64.b64encode(args)
            else:
                result["status"] = "no_image_url"
                return JsonResponse(result, status=500)
        except Exception as e:
            logger.exception(e)
            if service_id != "" and service_id is not None:
                ImageServiceRelation.objects.filter(service_id=service_id).delete()
                ServiceAttachInfo.objects.filter(service_id=service_id).delete()
            result["status"] = "failure"
            result["fail_info"] = 900
            return JsonResponse(result, status=500)
        return JsonResponse(result, status=200)


class ImageParamsViews(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/css/style.css', 'www/css/style-responsive.css', 'www/js/jquery.cookie.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/respond.min.js')
        return media

    def create_service_event(self, service, tenant, action):
        event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                             tenant_id=tenant.tenant_id, type="{0}".format(action),
                             deploy_version=service.deploy_version,
                             old_deploy_version=service.deploy_version,
                             user_name=self.user.nick_name, start_time=datetime.datetime.now())
        event.save()
        return event

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
            context["service_alias"] = "gr" + service_id[-6:]

            deployTenantServices = TenantServiceInfo.objects.filter(
                tenant_id=self.tenant.tenant_id,
                service_region=self.response_region,
                service_origin='assistant')
            openInnerServices = []
            for dts in deployTenantServices:
                if TenantServicesPort.objects.filter(service_id=dts.service_id, is_inner_service=True):
                    openInnerServices.append(dts)

            context["openInnerServices"] = openInnerServices

            tenantServiceList = baseService.get_service_list(
                self.tenant.pk, self.user, self.tenant.tenant_id, region=self.response_region
            )

            shared_vols = []
            for ten in tenantServiceList:
                vols = baseService.get_volumes_by_type(TenantServiceVolume.SHARE, ten.service_id)
                for vol in vols:
                    svc_group_rel = svc_grop_repo.get_rel_region(vol.service_id, self.tenant.tenant_id,
                                                                 self.response_region)
                    svc_group = None
                    if svc_group_rel:
                        svc_group = svc_grop_repo.get_by_pk(svc_group_rel.group_id)
                    shared_vols.append({
                        'dep_app_name': ten.service_cname, 'dep_vol_path': vol.volume_path, 'dep_vol_id': vol.ID,
                        'dep_app_group': svc_group.group_name if svc_group else '未分组',
                        'dep_app_name': tenantServiceList.get(service_id=vol.service_id).service_cname
                    })

            context['shared_vols'] = shared_vols
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

            # 从url中分析出来service_cname 和 version

            version = ""
            if ":" in image_url:
                index = image_url.rindex(":")
                if service_cname is None or service_cname == "":
                    str_tmp = image_url.split(":")
                    service_cname = str_tmp[len(str_tmp) - 2]
                version = image_url[index + 1:]
            else:
                if service_cname is None or service_cname == "":
                    service_cname = image_url
                version = "latest"

            # 端口信息
            port_list = json.loads(request.POST.get("port_list", "[]"))
            # 环境变量信息
            env_list = json.loads(request.POST.get("env_list", "[]"))
            # 持久化目录信息
            volume_list = json.loads(request.POST.get("volume_list", "[]"))
            # 依赖服务id
            depIds = json.loads(request.POST.get("depend_list", "[]"))
            # 挂载其他服务目录
            service_alias_list = json.loads(request.POST.get('mnt_list', '[]'))
            # 服务内存
            image_service_memory = int(request.POST.get("service_min_memory", 512))
            # 服务扩展方式
            service_status = request.POST.get("methodval", "stateless")

            # 判断是否持久化路径是否合法
            from www.utils.path_judge import is_path_legal
            for volume_url in volume_list:
                url = volume_url.get("volume_path", None)
                if url:
                    if not is_path_legal(url):
                        result["status"] = "failure"
                        result["msg"] = "路径:{0}不合法".format(url)
                        return JsonResponse(result, status=200)

            image_url2 = request.POST.get("image_url", "")
            logger.debug("image_url2 is {}".format(image_url2))
            if image_url2 != "" and image_url2 != image_url:
                image_url = image_url2
                try:
                    ImageServiceRelation.objects.filter(service_id=service_id).update(image_url=image_url)
                    logger.debug("update image_url image_url {0} to image_url2 {1}".format(image_url, image_url2))
                except Exception, e:
                    logger.error("update image_url error, {}".format(str(e)))
                    result["status"] = "failure"
                    return JsonResponse(result, status=200)
            logger.debug("image_url is {}".format(image_url))
            #  启动命令
            start_cmd = request.POST.get("start_cmd", "")

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
            if image_service_memory != "":
                cm = int(image_service_memory)
                if cm < 128:
                    cm *= 1024
            service.min_memory = cm
            service.min_cpu = baseService.calculate_service_cpu(self.response_region, cm)
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
                    result["tenant_type"] = self.tenant.pay_type
                else:
                    result["status"] = "over_money"
                return JsonResponse(result, status=200)

            newTenantService = baseService.create_service(
                service_id, tenant_id, service_alias, service_cname, service, self.user.pk, region=self.response_region
            )
            newTenantService.code_from = "image_manual"
            newTenantService.language = "docker-image"
            newTenantService.save()
            self.service = newTenantService

            sai = attach_info_mamage.create_service_attach_info(newTenantService,
                                                                newTenantService.min_memory * newTenantService.min_node,
                                                                0)

            monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'create_service', True)

            self.save_ports_envs_and_volumes(port_list, env_list, volume_list, newTenantService)
            baseService.create_region_service(
                newTenantService, self.tenantName, self.response_region, self.user.nick_name, dep_sids=json.dumps([])
            )

            baseService.batch_add_dep_volume_v2(self.tenant, self.service, service_alias_list)

            data = {}
            data["label_values"] = "无状态的应用" if service_status == "stateless" else "有状态的应用"
            data["enterprise_id"] = self.tenant.enterprise_id
            region_api.update_service_state_label(self.response_region, self.tenantName, self.service.service_alias,
                                                  data)
            self.service.extend_method = service_status
            self.service.save()

            # 发送build请求
            body = {}
            event = self.create_service_event(newTenantService, self.tenant, "deploy")
            kind = "image"
            body["event_id"] = event.event_id
            body["deploy_version"] = newTenantService.deploy_version
            body["operator"] = self.user.nick_name
            body["action"] = "upgrade"
            body["kind"] = kind

            envs = {}
            buildEnvs = TenantServiceEnvVar.objects.filter(service_id=service_id, attr_name__in=(
                "COMPILE_ENV", "NO_CACHE", "DEBUG", "PROXY", "SBT_EXTRAS_OPTS"))
            for benv in buildEnvs:
                envs[benv.attr_name] = benv.attr_value
            body["envs"] = envs

            body["enterprise_id"] = self.tenant.enterprise_id
            region_api.build_service(
                newTenantService.service_region, self.tenantName, newTenantService.service_alias, body)

            monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'init_region_service', True)

            logger.debug(depIds)
            for sid in depIds:
                try:
                    baseService.create_service_dependency(self.tenant, newTenantService, sid,
                                                          self.response_region)
                except Exception as e:
                    logger.exception(e)

            result["status"] = "success"
            result["service_id"] = service_id
            result["service_alias"] = service_alias

            attach_info_mamage.update_attach_info_by_tenant(self.tenant, self.service)

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
            baseService.add_volume_with_type(tenant_serivce, volume['volume_path'], volume['volume_type'],
                                             volume['volume_name'])

        if len(volumes) > 0:
            temp_service = TenantServiceInfo.objects.get(service_id=tenant_serivce.service_id)
            if temp_service.host_path is None or temp_service.host_path == "":
                temp_service.host_path = "/grdata/tenant/" + temp_service.tenant_id + "/service/" + temp_service.service_id
                temp_service.save()

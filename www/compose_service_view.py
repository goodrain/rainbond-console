# -*- coding: utf8 -*-
from decimal import Decimal

from django.http.response import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
from www.services import tenant_svc

from share.manager.region_provier import RegionProviderManager
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.models import ComposeServiceRelation, TenantServiceInfo, ServiceInfo, TenantServiceEnvVar, TenantServicesPort, \
    TenantServiceVolume, ServiceFeeBill, ServiceEvent
from www.models.main import ServiceGroup, ServiceGroupRelation, ServiceAttachInfo
from www.tenantservice.baseservice import  TenantAccountService, TenantUsedResource, \
    BaseTenantService, AppCreateService, ServiceAttachInfoManage
from www.utils.docker.compose_parse import compose_list
from www.utils.crypt import make_uuid
from www.views import LeftSideBarMixin
from www.views.base import AuthedView
from www.monitorservice.monitorhook import MonitorHook
import logging
import json
import datetime
from dateutil.relativedelta import relativedelta
from www.utils import sn

logger = logging.getLogger('default')
tenantAccountService = TenantAccountService()
tenantUsedResource = TenantUsedResource()
baseService = BaseTenantService()
monitorhook = MonitorHook()
rpmManager = RegionProviderManager()
appCreateService = AppCreateService()
region_api = RegionInvokeApi()
attach_info_mamage = ServiceAttachInfoManage()

class ComposeServiceDeploy(LeftSideBarMixin, AuthedView):
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
        compose_file_id = request.GET.get("id")
        if compose_file_id is not None:
            ComposeServiceRelation.objects.filter(compose_file_id=compose_file_id).delete()
        context = self.get_context()
        context["createApp"] = "active"
        return TemplateResponse(self.request, "www/app_create_step_three.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        tenant_id = self.tenant.tenant_id
        compose_file_id = make_uuid(tenant_id)
        compose_file = request.FILES['compose_file']
        group_name = request.POST.get("group_name", "")
        try:
            count = ComposeServiceRelation.objects.filter(compose_file_id=compose_file_id).count()
            if count > 1:
                ComposeServiceRelation.objects.filter(compose_file_id=compose_file_id).delete()
                count = 0
            if count == 0:
                compose_info = ComposeServiceRelation()
                compose_info.compose_file_id = compose_file_id
                compose_info.tenant_id = tenant_id
                compose_info.compose_file = compose_file
            else:
                compose_info = ComposeServiceRelation.objects.filter(compose_file_id=compose_file_id)
                compose_info.compose_file = compose_file
            compose_info.save()
            if group_name != "":
                if ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, group_name=group_name,
                                               region_name=self.response_region).count() > 0:
                    return JsonResponse({"success": False, "info": "group_exist"}, status=200)
                else:
                    ServiceGroup.objects.create(tenant_id=self.tenant.tenant_id, group_name=group_name,
                                                region_name=self.response_region)

            compose_file_url = ComposeServiceRelation.objects.get(compose_file_id=compose_file_id).compose_file.path

            group_id = ""
            try:
                group = ServiceGroup.objects.get(tenant_id=self.tenant.tenant_id, group_name=group_name,
                                                 region_name=self.response_region)
                group_id = group.ID
            except Exception as e:
                logger.debug("Tenant {0} in Region {1} Group Name {2} is not found".format(self.tenant.tenant_id,
                                                                                           self.response_region,
                                                                                           group_name))
                pass

            data = {"success": True, "code": 200, "compose_file_url": compose_file_url,
                    "compose_file_id": compose_file_id, "group_id": group_id}
        except Exception as e:
            data = {"sucess": False}
            ComposeServiceRelation.objects.filter(compose_file_id=compose_file_id).delete()
            logger.exception(e)
        return JsonResponse(data, status=200)


class ComposeCreateStep2(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/css/style.css', 'www/css/style-responsive.css', 'www/js/jquery.cookie.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/respond.min.js')
        return media

    def json_loads(self, json_string):
        """将json字符串转为python对象"""
        if json_string is not None and json_string.strip() != "":
            return json.loads(json_string)
        else:
            return ""

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        choose_region = request.GET.get("region", None)
        if choose_region is not None:
            self.response_region = choose_region
        context = self.get_context()
        try:
            context["createApp"] = "active"
            compose_file_id = request.GET.get("id", "")
            group_id = request.GET.get("group_id", "")
            context["group_id"] = group_id
            context["compose_file_id"] = compose_file_id
            group_name = ""
            try:
                group_id = int(group_id)
                group_name = ServiceGroup.objects.get(ID=group_id).group_name
                # context["group_name"] = group_name
            except ServiceGroup.DoesNotExist:
                pass

            yaml_file = ComposeServiceRelation.objects.get(compose_file_id=compose_file_id)
            compose_file_path = yaml_file.compose_file.path
            context["compose_file_name"] = yaml_file.compose_file.name
            service_list, info = compose_list(compose_file_path)
            context["compose_file_path"] = compose_file_path
            tenant_id = self.tenant.tenant_id
            linked = []
            compose_relations = {}
            if service_list is None:
                context["parse_error"] = "parse_error"
                context["parse_error_info"] = info
            else:
                for docker_service in service_list:
                    temp = []
                    service_id = make_uuid(tenant_id)
                    docker_service.service_id = service_id
                    env_var_json = docker_service.environment
                    docker_service.environment = self.json_loads(env_var_json)
                    logger.debug("---------------------------- \n")
                    logger.debug("env_var_json : {}".format(env_var_json))
                    logger.debug("---------------------------- \n")
                    outer_port_json = docker_service.ports
                    docker_service.ports = self.json_loads(outer_port_json)
                    inner_port_json = docker_service.expose
                    docker_service.expose = self.json_loads(inner_port_json)
                    links_json = docker_service.links
                    docker_service.links = self.json_loads(links_json)
                    volumes_json = docker_service.volumes
                    docker_service.volumes = self.json_loads(volumes_json)
                    depends_on_json = docker_service.depends_on
                    docker_service.depends_on = self.json_loads(depends_on_json)
                    linked.extend(docker_service.links)
                    linked.extend(docker_service.depends_on)
                    temp.extend(docker_service.links)
                    temp.extend(docker_service.depends_on)
                    compose_relations[docker_service.name] = temp

            regionBo = rpmManager.get_work_region_by_name(self.response_region)
            context['pre_paid_memory_price'] = regionBo.memory_package_price
            context['post_paid_memory_price'] = regionBo.memory_trial_price
            context['pre_paid_disk_price'] = regionBo.disk_package_price
            context['post_paid_disk_price'] = regionBo.disk_trial_price
            context['post_paid_net_price'] = regionBo.net_trial_price
            # 是否为免费租户
            context['is_tenant_free'] = (self.tenant.pay_type == "free")

            context["compose_relations"] = json.dumps(compose_relations)
            # linked去重
            linked = list(set(linked))
            context["linked_service"] = linked
            context["service_list"] = service_list
            context["compose_file_id"] = compose_file_id
            context["tenantName"] = self.tenant.tenant_name
            context["compose_group_name"] = group_name

            context['cloud_assistant'] = sn.instance.cloud_assistant
            context["is_private"] = sn.instance.is_private()
            # 判断云帮是否为公有云
            context["is_public_clound"] = (sn.instance.cloud_assistant == "goodrain" and (not sn.instance.is_private()))
        except Exception as e:
            context["parse_error"] = "parse_error"
            logger.error(e)

        return TemplateResponse(self.request, "www/app_create_step_compose_2.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        result = {}
        tenant_id = self.tenant.tenant_id
        compose_file_id = request.POST.get("compose_file_id", "")
        group_id = request.POST.get("group_id", "")
        try:
            # judge region tenant is init
            success = tenant_svc.init_for_region(self.response_region, self.tenantName, tenant_id, self.user)
            if not success:
                result["status"] = "failure"
                return JsonResponse(result, status=200)

            # if tenantAccountService.isOwnedMoney(self.tenant, self.response_region):
            #     result["status"] = "owed"
            #     return JsonResponse(result, status=200)
            if group_id == "":
                result["status"] = "no_group"
                return JsonResponse(result, status=200)

            services_attach_infos = request.POST.get("services_attach_infos", "")
            services_attach_infos = self.json_loads(services_attach_infos)

            deps = {}
            services_list = []
            for service_attach_info in services_attach_infos:
                service_cname = service_attach_info.get("app_name")
                service_id = service_attach_info.get("service_id")
                deps[service_cname] = service_id
                ts = TenantServiceInfo()
                min_memory = int(service_attach_info.get("service_min_memory", 128))
                # 将G转换为M
                if min_memory < 128:
                    min_memory *= 1024
                min_node = int(service_attach_info.get("service_min_node", 1))
                ts.min_memory = min_memory
                ts.min_node = min_node
                services_list.append(ts)
            res = tenantUsedResource.predict_batch_services_memory(self.tenant, services_list, self.response_region)
            if not res:
                result["status"] = "over_memory"
                result["tenant_type"] = self.tenant.pay_type
                return JsonResponse(result, status=200)

            for service_attach_info in services_attach_infos:
                service_cname = service_attach_info.get("app_name", "")
                if service_cname == "":
                    result["status"] = "empty"
                    return JsonResponse(result, status=200)
                min_memory = int(service_attach_info.get("service_min_memory", 128))
                # 将G转换为M
                if min_memory < 128:
                    min_memory *= 1024
                min_node = int(service_attach_info.get("service_min_node", 1))

                # calculate resource
                tempService = TenantServiceInfo()
                tempService.min_memory = min_memory
                tempService.service_region = self.response_region
                tempService.min_node = int(min_node)

                diffMemory = min_memory
                # 判断是否超出资源
                rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, tempService, diffMemory, False)
                if not flag:
                    if rt_type == "memory":
                        result["status"] = "over_memory"
                        result["tenant_type"] = self.tenant.pay_type
                    else:
                        result["status"] = "over_money"
                    return JsonResponse(result, status=200)

                service_id = service_attach_info.get("service_id", None)
                if service_id is None:
                    result["status"] = "no_service"
                    return JsonResponse(result, status=200)

                service_alias = "gr" + service_id[-6:]
                service_image = service_attach_info.get("service_image")

                version = ""
                if ":" in service_image:
                    index = service_image.index(":")
                    version = service_image[index + 1:]
                else:
                    version = "latest"

                service = ServiceInfo()
                service.service_key = "0000"
                service.desc = ""
                service.category = "app_publish"
                service.image = service_image
                service.cmd = ""
                service.setting = ""
                service.extend_method = "stateless"
                service.env = ","
                service.min_node = min_node
                cm = min_memory
                if min_memory != "":
                    cm = int(min_memory)

                service.min_memory = cm
                service.min_cpu = baseService.calculate_service_cpu(self.response_region, cm)
                service.inner_port = 0
                service.volume_mount_path = ""

                service.version = version
                service.namespace = "goodrain"
                service.update_version = 1
                service.volume_mount_path = ""
                service.service_type = "application"

                # service host_path
                service.host_path = "/grdata/tenant/" + self.tenant.tenant_id + "/service/" + service_id

                # 创建服务
                newTenantService = baseService.create_service(service_id, tenant_id, service_alias, service_cname,
                                                              service,
                                                              self.user.pk,
                                                              region=self.response_region)
                newTenantService.code_from = "image_manual"
                newTenantService.language = "docker-compose"
                newTenantService.save()
                sai = attach_info_mamage.create_service_attach_info(newTenantService,
                                                                    newTenantService.min_memory * newTenantService.min_node,
                                                                    0)
                monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'create_service', True)
                ServiceGroupRelation.objects.create(service_id=service_id, group_id=int(group_id), tenant_id=tenant_id,
                                                    region_name=self.response_region)
                result[service_id] = {"service_id": service_id, "service_cname": service_cname,
                                      "service_alias": service_alias}
            result["status"] = "success"
            result["group_id"] = group_id
            result["compose_file_id"] = compose_file_id

        except Exception as e:
            ServiceGroupRelation.objects.filter(group_id=int(group_id)).delete()
            logger.exception(e)
        return JsonResponse(result, status=200)


class ComposeCreateStep3(LeftSideBarMixin, AuthedView):
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
        try:
            compose_file_id = request.GET.get("id", "")
            group_id = request.GET.get("group_id", "")
            # 根据group_id 查询group中的所有service,根据service查出service_name
            service_id_list = ServiceGroupRelation.objects.filter(group_id=group_id,
                                                                  region_name=self.response_region).values("service_id")
            group_service_list = TenantServiceInfo.objects.filter(service_id__in=service_id_list,
                                                                  tenant_id=self.tenant.tenant_id)
            if len(group_service_list) == 0:
                context["parse_error"] = "parse_error"
                context["parse_error_info"] = "当前组无法找到对应的服务"
                return TemplateResponse(self.request, "www/app_create_step_five.html", context)
            service_map = {}
            for service in group_service_list:
                service_map[service.service_cname] = service.service_id

            yaml_file = ComposeServiceRelation.objects.get(compose_file_id=compose_file_id)
            compose_file_path = yaml_file.compose_file.path
            context["compose_file_name"] = yaml_file.compose_file.name
            service_list, info = compose_list(compose_file_path)
            linked = []
            compose_relations = {}
            if service_list is None:
                context["parse_error"] = "parse_error"
                context["parse_error_info"] = info
            else:
                for docker_service in service_list:
                    temp = []
                    docker_service.entrypoint = self.json_loads(docker_service.entrypoint)
                    service_id = service_map.get(docker_service.name, None)
                    if service_id:
                        docker_service.service_id = service_id
                    else:
                        raise ValueError, "Have no service_id for docker_service in compose step 3."

                    docker_service.environment = self.json_loads(docker_service.environment)

                    docker_service.ports = self.json_loads(docker_service.ports)
                    logger.debug("docker_service.ports is {}".format(docker_service.ports))

                    # expose port dockercompose outnetwork
                    docker_service.expose = self.json_loads(docker_service.expose)
                    logger.debug("docker_service.expose is {}".format(docker_service.expose))

                    docker_service.links = self.json_loads(docker_service.links)

                    docker_service.volumes = self.json_loads(docker_service.volumes)

                    docker_service.depends_on = self.json_loads(docker_service.depends_on)

                    linked.extend(docker_service.links)
                    linked.extend(docker_service.depends_on)
                    temp.extend(docker_service.links)
                    temp.extend(docker_service.depends_on)
                    temp.extend(docker_service.entrypoint)
                    compose_relations[docker_service.name] = temp

            context["compose_relations"] = json.dumps(compose_relations)
            context["linked_service"] = linked
            context["service_list"] = service_list
            context["compose_file_id"] = compose_file_id
            context["tenantName"] = self.tenant.tenant_name
        except Exception as e:
            context["parse_error"] = "parse_error"
            logger.error(e)

        return TemplateResponse(self.request, "www/app_create_step_five.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):

        result = {}
        tenant_id = self.tenant.tenant_id
        try:

            service_configs = request.POST.get("service_configs", "")
            service_configs = self.json_loads(service_configs)
            logger.debug("in post compose 3 config %s" % tenant_id)
            if service_configs != "":
                deps = {}
                for config in service_configs:
                    service_cname = config.get("service_cname")
                    service_id = config.get("service_id")
                    deps[service_cname] = service_id

                for service_config in service_configs:
                    service_id = service_config.get("service_id")
                    service_alias = "gr" + service_id[-6:]
                    service_cname = service_config.get("service_cname")
                    port_list = service_config.get("port_list")
                    env_list = service_config.get("env_list")
                    volume_list = service_config.get("volume_list")

                    start_cmd = service_config.get("start_cmd")

                    depends_services_list = service_config.get("depends_services")
                    # depends_services 去重
                    depends_services_list = list(set(depends_services_list))
                    newTenantService = None
                    try:
                        newTenantService = TenantServiceInfo.objects.get(service_id=service_id)

                    except TenantServiceInfo.DoesNotExist:
                        pass
                    if newTenantService is None:
                        result["status"] = "no_service"
                        return JsonResponse(result, status=500)
                    newTenantService.cmd = start_cmd
                    logger.debug("newTenantServie start_cmd is %s" % start_cmd)

                    min_memory = int(service_config.get("service_min_memory", 512))
                    if min_memory < 128:
                        min_memory *= 1024
                    newTenantService.min_memory = min_memory
                    newTenantService.save()

                    self.save_ports_envs_and_volumes(port_list, env_list, volume_list, newTenantService)
                    # if len(depends_services_list) > 0:
                    #     self.saveAdapterEnv(newTenantService)
                    baseService.create_region_service(newTenantService, self.tenantName, self.response_region,
                                                      self.user.nick_name, dep_sids=json.dumps([]))

                    service_status = service_config.get("methodval", "stateless")

                    data = {}
                    data["label_values"] = "无状态的应用" if service_status == "stateless" else "有状态的应用"
                    data["enterprise_id"] = self.tenant.enterprise_id
                    region_api.update_service_state_label(self.response_region, self.tenantName, newTenantService.service_alias, data)
                    newTenantService.extend_method = service_status
                    newTenantService.save()
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
                    region_api.build_service(newTenantService.service_region, self.tenantName, newTenantService.service_alias, body)

                    monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'init_region_service', True)
                    for dep_service in depends_services_list:
                        dep_service_id = deps[dep_service]
                        baseService.create_service_dependency(self.tenant, newTenantService, dep_service_id,
                                                              self.response_region)

                    result["status"] = "success"
                    result["service_id"] = service_id
                    result["service_alias"] = service_alias

                    attach_info_mamage.update_attach_info_by_tenant(self.tenant, newTenantService)

        except Exception as e:
            logger.exception(e)
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service_id).delete()
            TenantServicesPort.objects.filter(service_id=service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service_id).delete()

        return JsonResponse(result, status=200)

    def create_service_event(self, service, tenant, action):
        event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                             tenant_id=tenant.tenant_id, type="{0}".format(action),
                             deploy_version=service.deploy_version,
                             old_deploy_version=service.deploy_version,
                             user_name=self.user.nick_name, start_time=datetime.datetime.now())
        event.save()
        return event

    def json_loads(self, json_string):
        """将json字符串转为python对象"""
        if json_string is not None and json_string.strip() != "":
            return json.loads(json_string)
        else:
            return ""

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
            baseService.add_volume_with_type(tenant_serivce, volume['volume_path'], volume['volume_type'], volume['volume_name'])

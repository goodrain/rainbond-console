# -*- coding: utf8 -*-
from django.http.response import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from www.decorator import perm_required
from www.models import ComposeServiceRelation, TenantServiceInfo, ServiceInfo, TenantServiceEnvVar, TenantServicesPort, \
    TenantServiceVolume
from www.tenantservice.baseservice import TenantRegionService, TenantAccountService, TenantUsedResource, \
    BaseTenantService
from www.utils.docker.compose_parse import compose_list
from www.utils.crypt import make_uuid
from www.views import LeftSideBarMixin
from www.views.base import AuthedView
from www.monitorservice.monitorhook import MonitorHook
import logging
import json

logger = logging.getLogger('default')
tenantRegionService = TenantRegionService()
tenantAccountService = TenantAccountService()
tenantUsedResource = TenantUsedResource()
baseService = BaseTenantService()
monitorhook = MonitorHook()


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
        ComposeServiceRelation.objects.filter(compose_file_id=compose_file_id).delete()
        context = self.get_context()
        return TemplateResponse(self.request, "www/app_create_step_three.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        tenant_id = self.tenant.tenant_id
        compose_file_id = make_uuid(tenant_id)
        compose_file = request.FILES['compose_file']
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
            compose_file_url = ComposeServiceRelation.objects.get(compose_file_id=compose_file_id).compose_file.path
            data = {"success": True, "code": 200, "compose_file_url": compose_file_url,
                    "compose_file_id": compose_file_id}
        except Exception as e:
            data = {"sucess": False}
            ComposeServiceRelation.objects.filter(compose_file_id=compose_file_id).delete()
            logger.exception(e)
        return JsonResponse(data, status=200)


class ComposeServiceParams(LeftSideBarMixin, AuthedView):
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
            compose_file_id = request.GET.get("id", "")
            compose_file_path = ComposeServiceRelation.objects.get(compose_file_id=compose_file_id).compose_file.path
            service_list, success = compose_list(compose_file_path)
            tenant_id = self.tenant.tenant_id
            linked = []
            if service_list is None:
                context["parse_error"] = "parse_error"
                logger.error(success)
            else:
                for docker_service in service_list:
                    service_id = make_uuid(tenant_id)
                    docker_service.service_id = service_id
                    env_var_json = docker_service.environment
                    docker_service.environment = self.json_loads(env_var_json)
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
            # judge region tenant is init
            success = tenantRegionService.init_for_region(self.response_region, self.tenantName, tenant_id, self.user)
            if not success:
                result["status"] = "failure"
                return JsonResponse(result, status=200)

            if tenantAccountService.isOwnedMoney(self.tenant, self.response_region):
                result["status"] = "owed"
                return JsonResponse(result, status=200)

            if tenantAccountService.isExpired(self.tenant):
                result["status"] = "expired"
                return JsonResponse(result, status=200)

            service_configs = request.POST.get("service_configs", "")
            service_configs = self.json_loads(service_configs)

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
                    num = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_cname=service_cname).count()
                    if num > 0:
                        result["status"] = "exist"
                        result["info"] = '{0} is already exist'
                        return JsonResponse(result, status=200)
                    port_list = service_config.get("port_list")
                    env_list = service_config.get("env_list")
                    volume_list = service_config.get("volume_list")

                    service_memory = int(service_config.get("compose_service_memory"))
                    start_cmd = service_config.get("start_cmd")
                    service_image = service_config.get("service_image")

                    depends_services_list = service_config.get("depends_services")

                    version = ""
                    if ":" in service_image:
                        index = service_image.index(":")
                        version = service_image[index + 1:]
                    else:
                        version = "lastest"

                    service = ServiceInfo()
                    service.service_key = "0000"
                    service.desc = ""
                    service.category = "application"
                    service.image = service_image
                    service.cmd = start_cmd
                    service.setting = ""
                    service.extend_method = "stateless"
                    service.env = ","
                    service.min_node = 1
                    cm = 128
                    ccpu = 20
                    if service_memory != "":
                        cm = int(service_memory)
                        ccpu = int(cm / 128) * 20
                    service.min_memory = cm
                    service.min_cpu = ccpu
                    service.inner_port = 0

                    service.version = version
                    service.namespace = "goodrain"
                    service.update_version = 1
                    service.volume_mount_path = ""
                    service.service_type = "application"

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
                    newTenantService = baseService.create_service(service_id, tenant_id, service_alias, service_cname,
                                                                  service,
                                                                  self.user.pk,
                                                                  region=self.response_region)
                    newTenantService.code_from = "image_manual"
                    newTenantService.language = "docker-compose"
                    newTenantService.save()
                    monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'create_service', True)

                    self.save_ports_envs_and_volumes(port_list, env_list, volume_list, newTenantService)
                    baseService.create_region_service(newTenantService, self.tenantName, self.response_region,
                                                      self.user.nick_name, dep_sids=json.dumps([]))
                    monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'init_region_service', True)
                    for dep_service in depends_services_list:
                        dep_service_id = deps[dep_service]
                        baseService.create_service_dependency(tenant_id,service_id,dep_service_id,self.response_region)
                    result["status"] = "success"
                    result["service_id"] = service_id
                    result["service_alias"] = service_alias

        except Exception as e:
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service_id).delete()
            TenantServicesPort.objects.filter(service_id=service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service_id).delete()
            print e
            logger.error(e)
        return JsonResponse(result, status=200)

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
            baseService.add_volume_list(tenant_serivce, volume["volume_path"])

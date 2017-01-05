# -*- coding: utf8 -*-
from django.http.response import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from share.manager.region_provier import RegionProviderManager
from www.decorator import perm_required
from www.models import ComposeServiceRelation, TenantServiceInfo, ServiceInfo, TenantServiceEnvVar, TenantServicesPort, \
    TenantServiceVolume
from www.models.main import ServiceGroup, ServiceGroupRelation, ServiceAttachInfo
from www.tenantservice.baseservice import TenantRegionService, TenantAccountService, TenantUsedResource, \
    BaseTenantService
from www.utils.docker.compose_parse import compose_list
from www.utils.crypt import make_uuid
from www.views import LeftSideBarMixin
from www.views.base import AuthedView
from www.monitorservice.monitorhook import MonitorHook
import logging
import json
import datetime
from dateutil.relativedelta import relativedelta

logger = logging.getLogger('default')
tenantRegionService = TenantRegionService()
tenantAccountService = TenantAccountService()
tenantUsedResource = TenantUsedResource()
baseService = BaseTenantService()
monitorhook = MonitorHook()
rpmManager = RegionProviderManager()


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
        try:
            compose_file_id = request.GET.get("id", "")
            group_id = request.GET.get("group_id", "")
            context["group_id"] = group_id
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
            context["linked_service"] = linked
            context["service_list"] = service_list
            context["compose_file_id"] = compose_file_id
            context["tenantName"] = self.tenant.tenant_name
            context["compose_group_name"] = group_name
        except Exception as e:
            context["parse_error"] = "parse_error"
            logger.error(e)

        return TemplateResponse(self.request, "www/app_create_step_compose_2.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        result = {}
        tenant_id = self.tenant.tenant_id
        group_id = request.POST.get("group_id", "")
        try:
            # judge region tenant is init
            success = tenantRegionService.init_for_region(self.response_region, self.tenantName, tenant_id, self.user)
            if not success:
                result["status"] = "failure"
                return JsonResponse(result, status=200)

            if tenantAccountService.isOwnedMoney(self.tenant, self.response_region):
                result["status"] = "owed"
                return JsonResponse(result, status=200)
            if group_id == "":
                result["status"] = "no_group"
                return JsonResponse(result, status=200)

            services_attach_infos = request.POST.get("services_attach_infos", "")
            services_attach_infos = self.json_loads(services_attach_infos)

            deps = {}
            for service_attach_info in services_attach_infos:
                service_cname = service_attach_info.get("service_cname")
                service_id = service_attach_info.get("service_id")
                deps[service_cname] = service_id

            for service_attach_info in services_attach_infos:
                service_cname = service_attach_info.get("create_app_name", "")
                if service_cname is None:
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
                    else:
                        result["status"] = "over_money"
                    return JsonResponse(result, status=200)

                service_id = service_attach_info.get("service_id", None)
                if service_id is None:
                    result["status"] = "no_service"
                    return JsonResponse(result, status=200)

                memory_pay_method = service_attach_info.get("memory_pay_method", "prepaid")
                disk_pay_method = service_attach_info.get("disk_pay_method", "prepaid")
                pre_paid_period = int(service_attach_info.get("pre_paid_period", 1))
                disk = int(service_attach_info.get("disk_num", 0))
                # 将G转换为M
                if disk < 1024:
                    disk *= 1024

                create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                startTime = datetime.datetime.now() + datetime.timedelta(hours=1)
                endTime = datetime.datetime.now() + relativedelta(months=int(pre_paid_period))
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

                service_alias = "gr" + service_id[-6:]
                service_image = service_attach_info.get("service_image")

                version = ""
                if ":" in service_image:
                    index = service_image.index(":")
                    version = service_image[index + 1:]
                else:
                    version = "lastest"

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
                ccpu = 20
                if min_memory != "":
                    cm = int(min_memory)
                    ccpu = int(cm / 128) * 20
                service.min_memory = cm
                service.min_cpu = ccpu
                service.inner_port = 0

                service.version = version
                service.namespace = "goodrain"
                service.update_version = 1
                service.volume_mount_path = ""
                service.service_type = "application"


                # 创建服务
            #     newTenantService = baseService.create_service(service_id, tenant_id, service_alias, service_cname,
            #                                                   service,
            #                                                   self.user.pk,
            #                                                   region=self.response_region)
            #     newTenantService.code_from = "image_manual"
            #     newTenantService.language = "docker-compose"
            #     newTenantService.save()
            #
            #     monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'create_service', True)
            #     ServiceGroupRelation.objects.create(service_id=service_id, group_id=int(group_id), tenant_id=tenant_id,
            #                                         region_name=self.response_region)
            #     result[service_id] = {"service_id": service_id, "service_cname": service_cname,
            #                           "service_alias": service_alias}
            # result["status"] = "success"
            # result["group_id"] = group_id

        except Exception as e:
            ServiceGroupRelation.objects.filter(group_id=int(group_id)).delete()
            logger.exception(e)
        return JsonResponse(result, status=200)


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
            yaml_file = ComposeServiceRelation.objects.get(compose_file_id=compose_file_id)
            compose_file_path = yaml_file.compose_file.path
            context["compose_file_name"] = yaml_file.compose_file.name
            service_list, info = compose_list(compose_file_path)
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

            context["compose_relations"] = json.dumps(compose_relations)
            context["linked_service"] = linked
            context["service_list"] = service_list
            context["compose_file_id"] = compose_file_id
            context["tenantName"] = self.tenant.tenant_name
            context["compose_group_name"] = "compose" + compose_file_id[-6:]
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

            # if tenantAccountService.isExpired(self.tenant,self.service):
            #     result["status"] = "expired"
            #     return JsonResponse(result, status=200)
            service_configs = request.POST.get("service_configs", "")
            service_configs = self.json_loads(service_configs)
            compose_group_name = request.POST.get("compose_group_name", "")
            if compose_group_name is None or compose_group_name.strip() == "":
                compose_group_name = "compose" + make_uuid(self.tenant.tenant_id)[-6:]

            if service_configs != "":
                deps = {}
                for config in service_configs:
                    service_cname = config.get("service_cname")
                    service_id = config.get("service_id")
                    deps[service_cname] = service_id
                group_name = compose_group_name
                group = ServiceGroup.objects.create(tenant_id=self.tenant.tenant_id, region_name=self.response_region,
                                                    group_name=group_name)

                for service_config in service_configs:
                    service_id = service_config.get("service_id")
                    service_alias = "gr" + service_id[-6:]
                    service_cname = service_config.get("service_cname")
                    # num = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_cname=service_cname).count()
                    # if num > 0:
                    #     result["status"] = "exist"
                    #     ServiceGroup.objects.filter(ID=group.ID).delete()
                    #     return JsonResponse(result, status=200)
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
                    service.category = "app_publish"
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
                        baseService.create_service_dependency(tenant_id, service_id, dep_service_id,
                                                              self.response_region)

                    ServiceGroupRelation.objects.create(service_id=service_id, group_id=group.ID, tenant_id=tenant_id,
                                                        region_name=self.response_region)
                    result["status"] = "success"
                    result["service_id"] = service_id
                    result["service_alias"] = service_alias


        except Exception as e:
            logger.exception(e)
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service_id).delete()
            TenantServicesPort.objects.filter(service_id=service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service_id).delete()
            ServiceGroup.objects.filter(ID=group.ID).delete()

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

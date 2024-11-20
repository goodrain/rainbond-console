# -*- coding: utf8 -*-
"""
  Created on 18/1/11.
"""
import base64
import datetime
import json
import logging
import random
import string
from addict import Dict

from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict

# enum
from console.enum.component_enum import ComponentType
# exception
from console.exception.main import AbortRequest
from console.exception.main import ServiceHandleException
from console.exception.bcode import ErrThirdComponentStartFailed
from console.constants import AppConstants, PluginImage, SourceCodeType
from console.appstore.appstore import app_store
from console.models.main import (AppMarket, RainbondCenterApp, RainbondCenterAppVersion, PackageUploadRecord)
from console.repositories.app import (app_market_repo, service_repo, service_source_repo)
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import domain_repo as http_rule_repo
from console.repositories.app_config import (env_var_repo, mnt_repo, port_repo, service_endpoints_repo, tcp_domain, volume_repo)
from console.repositories.probe_repo import probe_repo
from console.repositories.region_app import region_app_repo
from console.repositories.service_group_relation_repo import \
    service_group_relation_repo
from console.services.app_config import label_service, volume_service
from console.services.app_config.arch_service import arch_service
from console.services.app_config.port_service import AppPortService
from console.services.app_config.probe_service import ProbeService
from console.services.app_config.service_monitor import service_monitor_repo
from console.utils.oauth.oauth_types import support_oauth_type
from console.utils.validation import validate_endpoints_info
from www.apiclient.regionapi import RegionInvokeApi
from www.github_http import GitHubApi
# model
from www.models.main import ServiceGroupRelation
from www.models.main import ServiceConsume, TenantServiceInfo
from www.models.main import ThirdPartyServiceEndpoints
from www.models.main import TenantServicesPort
from www.models.main import ServiceGroup
from www.tenantservice.baseservice import (BaseTenantService, CodeRepositoriesService, ServicePluginResource,
                                           TenantUsedResource)
from www.utils.crypt import make_uuid
from www.utils.status_translate import get_status_info_map

tenantUsedResource = TenantUsedResource()
logger = logging.getLogger("default")
region_api = RegionInvokeApi()
codeRepositoriesService = CodeRepositoriesService()
baseService = BaseTenantService()
servicePluginResource = ServicePluginResource()
gitHubClient = GitHubApi()
port_service = AppPortService()
probe_service = ProbeService()


class AppService(object):
    def is_k8s_component_name_duplicate(self, app_id, k8s_component_name, component_id=""):
        components = []
        component_ids = service_group_relation_repo.get_components_by_app_id(app_id).values_list("service_id")
        if len(component_ids) > 0:
            components = service_repo.list_by_ids(component_ids)
        for component in components:
            if component.k8s_component_name == k8s_component_name and component.service_id != component_id:
                return True
        return False

    def check_service_cname(self, tenant, service_cname, region):
        if not service_cname:
            return False, "组件名称不能为空"
        if len(service_cname) > 100:
            return False, "组件名称最多支持100个字符"
        return True, "success"

    def __init_source_code_app(self, region):
        """
        初始化源码创建的组件默认数据,未存入数据库
        """
        tenant_service = TenantServiceInfo()
        tenant_service.service_region = region
        tenant_service.service_key = "application"
        tenant_service.desc = "application info"
        tenant_service.category = "application"
        tenant_service.image = PluginImage.RUNNER
        tenant_service.cmd = ""
        tenant_service.setting = ""
        tenant_service.extend_method = ComponentType.stateless_multiple.value
        tenant_service.env = ""
        tenant_service.min_node = 1
        tenant_service.min_memory = 128
        tenant_service.min_cpu = baseService.calculate_service_cpu(region, 128)
        tenant_service.inner_port = 5000
        tenant_service.version = "81701"
        tenant_service.namespace = "goodrain"
        tenant_service.update_version = 1
        tenant_service.port_type = "multi_outer"
        tenant_service.create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tenant_service.deploy_version = ""
        tenant_service.git_project_id = 0
        tenant_service.service_type = "application"
        tenant_service.total_memory = 128
        tenant_service.volume_mount_path = ""
        tenant_service.host_path = ""
        tenant_service.service_source = AppConstants.SOURCE_CODE
        tenant_service.create_status = "creating"
        return tenant_service

    def create_source_code_app(self,
                               region,
                               tenant,
                               user,
                               service_code_from,
                               service_cname,
                               service_code_clone_url,
                               service_code_id,
                               service_code_version,
                               server_type,
                               check_uuid=None,
                               event_id=None,
                               oauth_service_id=None,
                               git_full_name=None,
                               k8s_component_name="",
                               arch="amd64"):
        service_cname = service_cname.rstrip().lstrip()
        is_pass, msg = self.check_service_cname(tenant, service_cname, region)
        if not is_pass:
            return 412, msg, None
        new_service = self.__init_source_code_app(region)
        new_service.tenant_id = tenant.tenant_id
        new_service.service_cname = service_cname
        service_id = make_uuid(tenant.tenant_id)
        service_alias = self.create_service_alias(service_id)
        new_service.service_id = service_id
        new_service.service_alias = service_alias
        new_service.creater = user.pk
        new_service.server_type = server_type
        new_service.k8s_component_name = k8s_component_name if k8s_component_name else service_alias
        new_service.arch = arch
        new_service.save()
        code, msg = self.init_repositories(new_service, user, service_code_from, service_code_clone_url, service_code_id,
                                           service_code_version, check_uuid, event_id, oauth_service_id, git_full_name)
        if code != 200:
            return code, msg, new_service
        logger.debug("service.create, user:{0} create service from source code".format(user.nick_name))
        ts = TenantServiceInfo.objects.get(service_id=new_service.service_id, tenant_id=new_service.tenant_id)
        return 200, "创建成功", ts

    def init_repositories(self, service, user, service_code_from, service_code_clone_url, service_code_id, service_code_version,
                          check_uuid, event_id, oauth_service_id, git_full_name):
        if service_code_from == SourceCodeType.GITLAB_MANUAL or service_code_from == SourceCodeType.GITLAB_DEMO:
            service_code_id = "0"

        if service_code_from in (SourceCodeType.GITLAB_EXIT, SourceCodeType.GITLAB_MANUAL, SourceCodeType.GITLAB_DEMO):
            if not service_code_clone_url or not service_code_id:
                return 403, "代码信息不全"
            service.git_project_id = service_code_id
            service.git_url = service_code_clone_url
            service.code_from = service_code_from
            service.code_version = service_code_version
            service.save()
        elif service_code_from == SourceCodeType.GITHUB:
            if not service_code_clone_url:
                return 403, "代码信息不全"
            service.git_project_id = service_code_id
            service.git_url = service_code_clone_url
            service.code_from = service_code_from
            service.code_version = service_code_version
            service.save()
            code_user = service_code_clone_url.split("/")[3]
            code_project_name = service_code_clone_url.split("/")[4].split(".")[0]
            gitHubClient.createReposHook(code_user, code_project_name, user.github_token)
        elif service_code_from.split("oauth_")[-1] in list(support_oauth_type.keys()):

            if not service_code_clone_url:
                return 403, "代码信息不全"
            if check_uuid:
                service.check_uuid = check_uuid
            if event_id:
                service.check_event_id = event_id
            service.git_project_id = service_code_id
            service.git_url = service_code_clone_url
            service.code_from = service_code_from
            service.code_version = service_code_version
            service.oauth_service_id = oauth_service_id
            service.git_full_name = git_full_name
            service.save()

        return 200, "success"

    def create_service_source_info(self, tenant, service, user_name, password):
        params = {
            "team_id": tenant.tenant_id,
            "service_id": service.service_id,
            "user_name": user_name,
            "password": password,
        }
        return service_source_repo.create_service_source(**params)

    def __init_package_build_app(self, region):
        """
        初始化本地文件创建的组件默认数据,未存入数据库
        """
        tenant_service = TenantServiceInfo()
        tenant_service.service_region = region
        tenant_service.service_key = "application"
        tenant_service.desc = "application info"
        tenant_service.category = "package"
        tenant_service.image = PluginImage.RUNNER
        tenant_service.cmd = ""
        tenant_service.setting = ""
        tenant_service.extend_method = ComponentType.stateless_multiple.value
        tenant_service.env = ""
        tenant_service.min_node = 1
        tenant_service.min_memory = 128
        tenant_service.min_cpu = baseService.calculate_service_cpu(region, 128)
        tenant_service.inner_port = 5000
        tenant_service.version = "81701"
        tenant_service.namespace = "goodrain"
        tenant_service.update_version = 1
        tenant_service.port_type = "multi_outer"
        tenant_service.create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tenant_service.deploy_version = ""
        tenant_service.git_project_id = 0
        tenant_service.service_type = "pkg"
        tenant_service.total_memory = 128
        tenant_service.volume_mount_path = ""
        tenant_service.host_path = ""
        tenant_service.service_source = AppConstants.PACKAGE_BUILD
        tenant_service.create_status = "creating"
        return tenant_service

    def create_package_upload_info(self, region, tenant, user, service_cname, k8s_component_name, event_id, pkg_create_time,
                                   arch):
        service_cname = service_cname.rstrip().lstrip()
        is_pass, msg = self.check_service_cname(tenant, service_cname, region)
        if not is_pass:
            return 412, msg, None
        new_service = self.__init_package_build_app(region)
        new_service.tenant_id = tenant.tenant_id
        new_service.service_cname = service_cname
        service_id = make_uuid(tenant.tenant_id)
        service_alias = self.create_service_alias(service_id)
        new_service.service_id = service_id
        new_service.service_alias = service_alias
        new_service.creater = user.pk
        new_service.server_type = "pkg"
        new_service.k8s_component_name = k8s_component_name if k8s_component_name else service_alias
        new_service.git_url = "/grdata/package_build/components/" + service_id + "/events/" + event_id
        new_service.code_version = pkg_create_time
        new_service.arch = arch
        new_service.save()
        ts = TenantServiceInfo.objects.get(service_id=new_service.service_id, tenant_id=new_service.tenant_id)
        return ts

    def change_package_upload_info(self, service_id, event_id, pkg_create_time):
        data = {
            "git_url": "/grdata/package_build/components/" + service_id + "/events/" + event_id,
            "code_version": pkg_create_time
        }
        return TenantServiceInfo.objects.filter(service_id=service_id).update(**data)

    def __init_docker_image_app(self, region):
        """
        初始化docker image创建的组件默认数据,未存入数据库
        """
        tenant_service = TenantServiceInfo()
        tenant_service.service_region = region
        tenant_service.service_key = "0000"
        tenant_service.desc = "docker run application"
        tenant_service.category = "app_publish"
        tenant_service.setting = ""
        tenant_service.extend_method = ComponentType.stateless_multiple.value
        tenant_service.env = ","
        tenant_service.min_node = 1
        tenant_service.min_memory = 512
        tenant_service.min_cpu = 0
        tenant_service.inner_port = 0
        tenant_service.version = "latest"
        tenant_service.namespace = "goodrain"
        tenant_service.update_version = 1
        tenant_service.port_type = "multi_outer"
        tenant_service.create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tenant_service.deploy_version = ""
        tenant_service.git_project_id = 0
        tenant_service.service_type = "application"
        tenant_service.total_memory = 128
        tenant_service.volume_mount_path = ""
        tenant_service.host_path = ""
        tenant_service.code_from = "image_manual"
        tenant_service.language = "docker-image"
        tenant_service.create_status = "creating"
        return tenant_service

    def __init_vm_image_app(self, region):
        """
        初始化vm image创建的组件默认数据,未存入数据库
        """
        tenant_service = TenantServiceInfo()
        tenant_service.service_region = region
        tenant_service.service_key = "00000"
        tenant_service.desc = "vm run application"
        tenant_service.category = "app_publish"
        tenant_service.setting = ""
        tenant_service.extend_method = ComponentType.vm.value
        tenant_service.min_node = 1
        tenant_service.min_memory = 1024
        tenant_service.min_cpu = 1000
        tenant_service.inner_port = 0
        tenant_service.version = ""
        tenant_service.namespace = "goodrain"
        tenant_service.update_version = 1
        tenant_service.port_type = "multi_outer"
        tenant_service.create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tenant_service.deploy_version = ""
        tenant_service.git_project_id = 0
        tenant_service.service_type = "application"
        tenant_service.total_memory = 1024
        tenant_service.volume_mount_path = ""
        tenant_service.host_path = ""
        tenant_service.code_from = "image_manual"
        tenant_service.language = ""
        tenant_service.create_status = "creating"
        tenant_service.service_source = "vm_run"
        return tenant_service

    def create_service_alias(self, service_id):
        service_alias = "gr" + service_id[-6:]
        svc = service_repo.get_service_by_service_alias(service_alias)
        if svc is None:
            return service_alias
        service_alias = self.create_service_alias(make_uuid(service_id))
        return service_alias

    def create_docker_run_app(self,
                              region,
                              tenant,
                              user,
                              service_cname,
                              docker_cmd,
                              image_type,
                              k8s_component_name,
                              image="",
                              arch="amd64"):
        is_pass, msg = self.check_service_cname(tenant, service_cname, region)
        if not is_pass:
            return 412, msg, None
        new_service = self.__init_docker_image_app(region)
        new_service.tenant_id = tenant.tenant_id
        new_service.service_cname = service_cname
        new_service.service_source = image_type
        service_id = make_uuid(tenant.tenant_id)
        service_alias = self.create_service_alias(service_id)
        new_service.service_id = service_id
        new_service.service_alias = service_alias
        new_service.creater = user.pk
        new_service.host_path = "/grdata/tenant/" + tenant.tenant_id + "/service/" + service_id
        new_service.docker_cmd = docker_cmd
        new_service.k8s_component_name = k8s_component_name if k8s_component_name else service_alias
        new_service.image = image
        new_service.arch = arch
        new_service.save()
        # # 创建镜像和组件的关系（兼容老的流程）
        # if not image_service_relation_repo.get_image_service_relation(tenant.tenant_id, service_id):
        #     image_service_relation_repo.create_image_service_relation(tenant.tenant_id, service_id, docker_cmd,
        #                                                               service_cname)

        logger.debug("service.create", "user:{0} create service from docker run command !".format(user.nick_name))
        ts = TenantServiceInfo.objects.get(service_id=new_service.service_id, tenant_id=new_service.tenant_id)

        return 200, "创建成功", ts

    def create_vm_run_app(self,
                          region,
                          tenant,
                          user,
                          service_cname,
                          k8s_component_name,
                          image="",
                          arch="amd64",
                          event_id="",
                          vm_url=""):
        is_pass, msg = self.check_service_cname(tenant, service_cname, region)
        if not is_pass:
            return 412, msg, None
        new_service = self.__init_vm_image_app(region)
        new_service.tenant_id = tenant.tenant_id
        new_service.service_cname = service_cname
        service_id = make_uuid(tenant.tenant_id)
        service_alias = self.create_service_alias(service_id)
        new_service.service_id = service_id
        new_service.service_alias = service_alias
        new_service.creater = user.pk
        new_service.host_path = "/grdata/tenant/" + tenant.tenant_id + "/service/" + service_id
        new_service.k8s_component_name = k8s_component_name if k8s_component_name else service_alias
        new_service.image = image
        new_service.arch = arch
        if vm_url != "":
            new_service.git_url = vm_url
        if event_id != "":
            new_service.git_url = "/grdata/package_build/temp/events/" + event_id
        new_service.save()
        ts = TenantServiceInfo.objects.get(service_id=new_service.service_id, tenant_id=new_service.tenant_id)
        return 200, "创建成功", ts

    def __init_third_party_app(self, region):
        """
        初始化创建外置组件的默认数据,未存入数据库
        """
        tenant_service = TenantServiceInfo()
        tenant_service.service_region = region
        tenant_service.service_key = "application"
        tenant_service.desc = "third party service"
        tenant_service.category = "application"
        tenant_service.image = "third_party"
        tenant_service.cmd = ""
        tenant_service.setting = ""
        tenant_service.extend_method = ComponentType.stateless_multiple.value
        tenant_service.env = ""
        tenant_service.min_node = 0
        tenant_service.min_memory = 0
        tenant_service.min_cpu = 0
        tenant_service.version = "81701"
        tenant_service.namespace = "third_party"
        tenant_service.update_version = 1
        tenant_service.port_type = "multi_outer"
        tenant_service.create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tenant_service.deploy_version = ""
        tenant_service.git_project_id = 0
        tenant_service.service_type = "application"
        tenant_service.total_memory = 0
        tenant_service.volume_mount_path = ""
        tenant_service.host_path = ""
        tenant_service.service_source = AppConstants.THIRD_PARTY
        tenant_service.create_status = "creating"
        return tenant_service

    def create_third_party_app(self,
                               region,
                               tenant,
                               user,
                               service_cname,
                               static_endpoints,
                               endpoints_type,
                               source_config={},
                               k8s_component_name=""):
        new_service = self._create_third_component(tenant, region, user, service_cname, k8s_component_name)
        new_service.save()
        if endpoints_type == "kubernetes":
            service_endpoints_repo.create_kubernetes_endpoints(tenant, new_service, source_config["service_name"],
                                                               source_config["namespace"])
        if endpoints_type == "static" and static_endpoints:
            from console.views.app_create.source_outer import check_endpoints
            errs, is_domain = check_endpoints(static_endpoints)
            if errs:
                return 400, "组件地址不合法", None
            port_list = []
            prefix = ""
            protocol = "tcp"
            for endpoint in static_endpoints:
                if 'https://' in endpoint:
                    endpoint = endpoint.split('https://')[1]
                    prefix = "https"
                    protocol = "http"
                if 'http://' in endpoint:
                    endpoint = endpoint.split('http://')[1]
                    prefix = "http"
                    protocol = "http"
                if ':' in endpoint:
                    port_list.append(endpoint.split(':')[1])
            if len(port_list) == 0 and is_domain is True and prefix != "":
                port_list.append(443 if prefix == "https" else 80)
            port_re = list(set(port_list))
            if len(port_re) == 1:
                port = int(port_re[0])
                if port:
                    port_alias = new_service.service_alias.upper().replace("-", "_") + str(port)
                    service_port = {
                        "tenant_id": tenant.tenant_id,
                        "service_id": new_service.service_id,
                        "container_port": port,
                        "mapping_port": port,
                        "protocol": protocol,
                        "port_alias": port_alias,
                        "is_inner_service": False,
                        "is_outer_service": False,
                        "k8s_service_name": new_service.service_alias + "-" + str(port),
                    }
                    port_repo.add_service_port(**service_port)
            service_endpoints_repo.update_or_create_endpoints(tenant, new_service, static_endpoints)

        ts = TenantServiceInfo.objects.get(service_id=new_service.service_id, tenant_id=new_service.tenant_id)
        return ts

    def create_third_components(self, tenant, region_name, user, app: ServiceGroup, component_type, services):
        if component_type != "kubernetes":
            raise AbortRequest("unsupported third component type: {}".format(component_type))
        components = self.create_third_components_kubernetes(tenant, region_name, user, app, services)

        # start the third components
        component_ids = [cpt.component_id for cpt in components]
        try:
            from console.services.app_actions import app_manage_service
            app_manage_service.batch_operations(tenant, region_name, user, "start", component_ids)
        except Exception as e:
            logger.exception(e)
            raise ErrThirdComponentStartFailed()

    @transaction.atomic
    def create_third_components_kubernetes(self, tenant, region_name, user, app: ServiceGroup, services):
        components = []
        relations = []
        endpoints = []
        new_ports = []
        envs = []
        component_bodies = []
        for service in services:
            # components
            component_cname = service["service_name"]
            component = self._create_third_component(tenant, region_name, user, component_cname)
            component.create_status = "complete"
            components.append(component)

            relation = ServiceGroupRelation(
                group_id=app.app_id,
                tenant_id=component.tenant_id,
                service_id=component.component_id,
                region_name=region_name,
            )
            relations.append(relation)

            # endpoints
            endpoints.append(
                ThirdPartyServiceEndpoints(
                    tenant_id=component.tenant_id,
                    service_id=component.service_id,
                    service_cname=component_cname,
                    endpoints_type="kubernetes",
                    endpoints_info=json.dumps({
                        'serviceName': service["service_name"],
                        'namespace': service["namespace"],
                    }),
                ))
            endpoint = {
                "kubernetes": {
                    'serviceName': service["service_name"],
                    'namespace': service["namespace"],
                }
            }

            # ports
            ports = service.get("ports")
            if not ports:
                continue
            for port in ports:
                new_port = TenantServicesPort(
                    tenant_id=component.tenant_id,
                    service_id=component.service_id,
                    container_port=port["port"],
                    mapping_port=port["port"],
                    protocol="udp" if port["protocol"].lower() == "udp" else "tcp",
                    port_alias=component.service_alias.upper() + str(port["port"]),
                    is_inner_service=True,
                    is_outer_service=False,
                    k8s_service_name=component.service_alias + "-" + str(port["port"]),
                )
                new_ports.append(new_port)

                # port envs
                port_envs = port_service.create_envs_4_ports(component, new_port, app.governance_mode)
                envs.extend(port_envs)

            component_body = self._create_third_component_body(component, endpoint, new_ports, envs)
            component_bodies.append(component_body)

        region_app_id = region_app_repo.get_region_app_id(region_name, app.app_id)

        self._sync_third_components(tenant.tenant_name, region_name, region_app_id, component_bodies)

        try:
            self._save_third_components(components, relations, endpoints, new_ports, envs)
        except Exception as e:
            self._rollback_third_components(tenant.tenant_name, region_name, region_app_id, components)
            raise e

        return components

    def _create_third_component(self, tenant, region_name, user, service_cname, k8s_component_name=""):
        service_cname = service_cname.rstrip().lstrip()
        is_pass, msg = self.check_service_cname(tenant, service_cname, region_name)
        if not is_pass:
            raise ServiceHandleException(msg=msg, msg_show="组件名称不合法", status_code=400, error_code=400)
        component = self.__init_third_party_app(region_name)
        component.tenant_id = tenant.tenant_id
        component.service_cname = service_cname
        service_id = make_uuid(tenant.tenant_id)
        service_alias = self.create_service_alias(service_id)
        component.service_id = service_id
        component.service_alias = service_alias
        component.creater = user.pk
        component.server_type = ''
        component.protocol = 'tcp'
        component.k8s_component_name = k8s_component_name if k8s_component_name else service_alias
        return component

    @staticmethod
    def _save_third_components(components, relations, third_endpoints, ports, envs):
        service_repo.bulk_create(components)
        service_group_relation_repo.bulk_create(relations)
        service_endpoints_repo.bulk_create(third_endpoints)
        port_repo.bulk_create(ports)
        env_var_repo.bulk_create(envs)

    @staticmethod
    def _create_third_component_body(component, endpoint, ports, envs):
        component_base = component.to_dict()
        component_base["component_id"] = component_base["service_id"]
        component_base["component_name"] = component_base["service_name"]
        component_base["component_alias"] = component_base["service_alias"]
        component_base["container_cpu"] = component.min_cpu
        component_base["container_memory"] = component.min_memory
        component_base["replicas"] = component.min_node
        component_base["kind"] = "third_party"

        return {
            "component_base": component_base,
            "envs": [env.to_dict() for env in envs],
            "ports": [port.to_dict() for port in ports],
            "endpoint": endpoint,
        }

    @staticmethod
    def _sync_third_components(tenant_name, region_name, region_app_id, component_bodies):
        body = {
            "components": component_bodies,
        }
        region_api.sync_components(tenant_name, region_name, region_app_id, body)

    @staticmethod
    def _rollback_third_components(tenant_name, region_name, region_app_id, components: [TenantServiceInfo]):
        body = {
            "delete_component_ids": [component.component_id for component in components],
        }
        region_api.sync_components(tenant_name, region_name, region_app_id, body)

    def get_app_list(self, tenant_id, region, dep_app_name):
        q = Q(tenant_id=tenant_id, service_region=region)
        if dep_app_name:
            q &= Q(service_cname__contains=dep_app_name)

        return TenantServiceInfo.objects.filter(q)

    def get_service_status(self, tenant, service):
        """获取组件状态"""
        start_time = ""
        try:
            body = region_api.check_service_status(service.service_region, tenant.tenant_name, service.service_alias,
                                                   tenant.enterprise_id)
            bean = body["bean"]
            status = bean["cur_status"]
            start_time = bean["start_time"]
        except Exception as e:
            logger.exception(e)
            status = "unKnow"
        status_info_map = get_status_info_map(status)
        status_info_map["start_time"] = start_time
        return status_info_map

    def get_service_resource_with_plugin(self, tenant, service, status):
        disk = 0

        service_consume = ServiceConsume.objects.filter(
            tenant_id=tenant.tenant_id, service_id=service.service_id).order_by("-ID")
        if service_consume:
            disk = service_consume[0].disk

        if status != "running":
            return {"disk": disk, "total_memory": 0}

        plugin_memory = servicePluginResource.get_service_plugin_resource(service.service_id)

        total_memory = service.min_node * (service.min_memory + plugin_memory)
        return {"disk": disk, "total_memory": total_memory}

    def create_region_service(self, tenant, service, user_name, do_deploy=True, dep_sids=None):
        data = self.__init_create_data(tenant, service, user_name, do_deploy, dep_sids)
        service_dep_relations = dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id)
        # handle dependencies attribute
        depend_ids = [{
            "dep_order": dep.dep_order,
            "dep_service_type": dep.dep_service_type,
            "depend_service_id": dep.dep_service_id,
            "service_id": dep.service_id,
            "tenant_id": dep.tenant_id
        } for dep in service_dep_relations]
        data["depend_ids"] = depend_ids
        # handle port attribute
        ports = port_repo.get_service_ports(tenant.tenant_id, service.service_id)
        ports_info = ports.values('container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service',
                                  'is_outer_service', 'k8s_service_name')

        if ports_info:
            data["ports_info"] = list(ports_info)
        # handle env attribute
        envs_info = env_var_repo.get_service_env(tenant.tenant_id, service.service_id).values(
            'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if envs_info:
            data["envs_info"] = list(envs_info)
        # handle volume attribute
        volume_info = volume_repo.get_service_volumes_with_config_file(service.service_id)
        if volume_info:
            volume_list = []
            for volume in volume_info:
                volume_info = model_to_dict(volume)
                if volume.volume_type == "config-file":
                    config_file = volume_repo.get_service_config_file(volume)
                    if config_file:
                        volume_info.update({"file_content": config_file.file_content})
                volume_list.append(volume_info)
            data["volumes_info"] = volume_list

        logger.debug(tenant.tenant_name + " start create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        # handle dep volume attribute
        mnt_info = mnt_repo.get_service_mnts(service.tenant_id, service.service_id)
        if mnt_info:
            data["dep_volumes_info"] = [{
                "dep_service_id": mnt.dep_service_id,
                "volume_path": mnt.mnt_dir,
                "volume_name": mnt.mnt_name
            } for mnt in mnt_info]

        # etcd keys
        data["etcd_key"] = service.check_uuid

        # runtime os name
        data["os_type"] = label_service.get_service_os_name(service)

        # app id
        app_id = service_group_relation_repo.get_group_id_by_service(service)
        region_app_id = region_app_repo.get_region_app_id(service.service_region, app_id)
        data["app_id"] = region_app_id

        # handle component monitor
        monitors = service_monitor_repo.get_component_service_monitors(tenant.tenant_id, service.service_id).values(
            'name', 'service_show_name', 'path', 'port', 'interval')
        if monitors:
            data["component_monitors"] = list(monitors)

        # handle component probe
        probes = probe_repo.get_service_probe(service.service_id).values(
            'service_id', 'probe_id', 'mode', 'scheme', 'path', 'port', 'cmd', 'http_header', 'initial_delay_second',
            'period_second', 'timeout_second', 'is_used', 'failure_threshold', 'success_threshold')
        if probes:
            probes = list(probes)
            for i in range(len(probes)):
                probes[i]['is_used'] = 1 if probes[i]['is_used'] else 0
            data["component_probes"] = probes
        # handle gateway rules
        http_rules = http_rule_repo.get_service_domains(service.service_id)
        if http_rules:
            rule_data = []
            for rule in http_rules:
                rule_data.append(self.__init_http_rule_for_region(tenant, service, rule, user_name))
            data["http_rules"] = rule_data

        stream_rule = tcp_domain.get_service_tcpdomains(service.service_id)
        if stream_rule:
            rule_data = []
            for rule in stream_rule:
                rule_data.append(self.__init_stream_rule_for_region(tenant, service, rule, user_name))
            data["tcp_rules"] = rule_data
        if not service.k8s_component_name:
            service.k8s_component_name = service.service_alias
        data["k8s_component_name"] = service.k8s_component_name
        data["job_strategy"] = service.job_strategy
        # create in region
        region_api.create_service(service.service_region, tenant.tenant_name, data)
        # conponent install complete
        service.create_status = "complete"
        service.save()
        arch_service.update_affinity_by_arch(service.arch, tenant, service.service_region, service)
        return service

    def __init_stream_rule_for_region(self, tenant, service, rule, user_name):

        data = dict()
        data["tcp_rule_id"] = rule.tcp_rule_id
        data["service_id"] = service.service_id
        data["container_port"] = rule.container_port
        hp = rule.end_point.split(":")
        if len(hp) == 2:
            data["ip"] = hp[0]
            data["port"] = int(hp[1])
        if rule.rule_extensions:
            rule_extensions = []
            for ext in rule.rule_extensions.split(","):
                ext_info = ext.split(":")
                if len(ext_info) == 2:
                    rule_extensions.append({"key": ext_info[0], "value": ext_info[1]})
            data["rule_extensions"] = rule_extensions
        return data

    def __init_http_rule_for_region(self, tenant, service, rule, user_name):
        certificate_info = None
        if rule.certificate_id:
            certificate_info = http_rule_repo.get_certificate_by_pk(int(rule.certificate_id))
        data = dict()
        data["uuid"] = make_uuid(rule.domain_name)
        data["domain"] = rule.domain_name
        data["service_id"] = service.service_id
        data["tenant_id"] = tenant.tenant_id
        data["tenant_name"] = tenant.tenant_name
        data["protocol"] = rule.protocol
        data["container_port"] = int(rule.container_port)
        data["add_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data["add_user"] = user_name
        data["enterprise_id"] = tenant.enterprise_id
        data["http_rule_id"] = rule.http_rule_id
        data["path"] = rule.domain_path
        data["cookie"] = rule.domain_cookie
        data["header"] = rule.domain_heander
        data["weight"] = rule.the_weight
        if rule.rule_extensions:
            rule_extensions = []
            for ext in rule.rule_extensions.split(","):
                ext_info = ext.split(":")
                if len(ext_info) == 2:
                    rule_extensions.append({"key": ext_info[0], "value": ext_info[1]})
            data["rule_extensions"] = rule_extensions
        data["certificate"] = ""
        data["private_key"] = ""
        data["certificate_name"] = ""
        data["certificate_id"] = ""
        if certificate_info:
            data["certificate"] = base64.b64decode(certificate_info.certificate).decode()
            data["private_key"] = certificate_info.private_key
            data["certificate_name"] = certificate_info.alias
            data["certificate_id"] = certificate_info.certificate_id
        data["path_rewrite"] = rule.path_rewrite
        rewrites = rule.rewrites if rule.rewrites else []
        if isinstance(rewrites, str):
            rewrites = eval(rewrites)
        data["rewrites"] = rewrites
        return data

    def __init_create_data(self, tenant, service, user_name, do_deploy, dep_sids):
        data = dict()
        data["tenant_id"] = tenant.tenant_id
        data["service_id"] = service.service_id
        data["service_key"] = service.service_key
        data["comment"] = service.desc
        data["image_name"] = service.image
        data["container_cpu"] = int(service.min_cpu)
        data["container_gpu"] = int(service.container_gpu)
        data["container_memory"] = int(service.min_memory)
        data["volume_path"] = "vol" + service.service_id[0:10]
        data["extend_method"] = service.extend_method
        data["status"] = 0
        data["replicas"] = service.min_node
        data["service_alias"] = service.service_alias
        data["service_version"] = service.version
        data["container_env"] = service.env
        data["container_cmd"] = service.cmd
        data["node_label"] = ""
        data["deploy_version"] = service.deploy_version if do_deploy else None
        data["domain"] = tenant.tenant_name
        data["category"] = service.category
        data["operator"] = user_name
        data["service_type"] = service.service_type
        data["extend_info"] = {"ports": [], "envs": []}
        data["namespace"] = service.namespace
        data["code_from"] = service.code_from
        data["dep_sids"] = dep_sids
        data["port_type"] = service.port_type
        data["ports_info"] = []
        data["envs_info"] = []
        data["volumes_info"] = []
        data["enterprise_id"] = tenant.enterprise_id
        data["service_name"] = service.service_name
        return data

    def add_service_default_porbe(self, tenant, service):
        ports = port_service.get_service_ports(service)
        port_length = len(ports)
        if port_length >= 1:
            container_port = ports[0].container_port
            for p in ports:
                if p.is_outer_service:
                    container_port = p.container_port
            data = {
                "service_id": service.service_id,
                "scheme": "tcp",
                "path": "",
                "port": container_port,
                "cmd": "",
                "http_header": "",
                "initial_delay_second": 4,
                "period_second": 3,
                "timeout_second": 5,
                "failure_threshold": 3,
                "success_threshold": 1,
                "is_used": True,
                "probe_id": make_uuid(),
                "mode": "readiness"
            }
            return probe_service.add_service_probe(tenant, service, data)
        return 200, "success", None

    def update_check_app(self, tenant, service, data, user):

        service_source = service_source_repo.get_service_source(tenant.tenant_id, service.service_id)
        if service.extend_method == "vm":
            volumes = volume_repo.get_service_volumes_with_config_file(service.service_id)
            disk_cap = data.get("disk_cap")
            if len(volumes) == 0:
                settings = {}
                settings['volume_capacity'] = disk_cap
                volume_service.add_service_volume(
                    tenant, service, "/disk", "vm-file", "disk", "", settings, user.nick_name, mode=None)
            else:
                volume = volumes.first()
                volume.volume_capacity = disk_cap
                volume.save()

        service_cname = data.get("service_cname", service.service_cname)
        image = data.get("image", service.image)
        cmd = data.get("cmd", service.cmd)
        docker_cmd = data.get("docker_cmd", service.docker_cmd)
        git_url = data.get("git_url", service.git_url)
        min_memory = data.get("min_memory", service.min_memory)
        min_memory = int(min_memory)
        min_cpu = data.get("min_cpu")
        job_strategy = data.get("job_strategy")
        if isinstance(min_cpu, str):
            min_cpu = int(min_cpu)
        if type(min_cpu) != int or min_cpu < 0:
            min_cpu = baseService.calculate_service_cpu(service.service_region, min_memory)

        extend_method = data.get("extend_method", service.extend_method)

        service.service_cname = service_cname
        service.min_memory = min_memory
        service.min_cpu = min_cpu
        service.extend_method = extend_method
        service.image = image
        service.cmd = cmd
        service.git_url = git_url
        service.docker_cmd = docker_cmd
        service.job_strategy = job_strategy
        service.save()

        user_name = data.get("user_name", None)
        password = data.get("password", None)
        if user_name is not None:
            if not service_source:
                params = {
                    "team_id": tenant.tenant_id,
                    "service_id": service.service_id,
                    "user_name": user_name,
                    "password": password,
                }
                service_source_repo.create_service_source(**params)
            else:
                service_source.user_name = user_name
                service_source.password = password
                service_source.save()
        return 200, "success"

    def generate_service_cname(self, tenant, service_cname, region):
        rt_name = service_cname
        while True:
            service = service_repo.get_service_by_region_tenant_and_name(tenant.tenant_id, rt_name, region)
            if service:
                temp_name = ''.join(random.sample(string.ascii_lowercase + string.digits, 4))
                rt_name = "{0}_{1}".format(service_cname, temp_name)
            else:
                break
        return rt_name

    def create_third_party_service(self, tenant, service, user_name, is_inner_service=False):
        data = self.__init_third_party_data(tenant, service, user_name)
        # env var
        envs_info = env_var_repo.get_service_env(tenant.tenant_id, service.service_id).values(
            'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if envs_info:
            data["envs_info"] = list(envs_info)
        # 端口
        ports = port_repo.get_service_ports(tenant.tenant_id, service.service_id)
        ports_info = ports.values('container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service',
                                  'is_outer_service', 'k8s_service_name')
        if ports_info:
            data["ports_info"] = list(ports_info)

        # endpoints
        endpoints = service_endpoints_repo.get_service_endpoints_by_service_id(service.service_id).first()
        if endpoints:
            if endpoints.endpoints_type == "static":
                eps = json.loads(endpoints.endpoints_info)
                validate_endpoints_info(eps)
            endpoints_dict = dict()
            # endpoint source config
            endpoints_dict[endpoints.endpoints_type] = json.loads(endpoints.endpoints_info)
            data["endpoints"] = endpoints_dict
        data["kind"] = service.service_source
        # etcd keys
        data["etcd_key"] = service.check_uuid
        # 数据中心创建
        app_id = service_group_relation_repo.get_group_id_by_service(service)
        region_app_id = region_app_repo.get_region_app_id(service.service_region, app_id)
        data["app_id"] = region_app_id
        if not service.k8s_component_name:
            service.k8s_component_name = service.service_alias
        data["k8s_component_name"] = service.k8s_component_name
        logger.debug('create third component from region, data: {0}'.format(data))
        region_api.create_service(service.service_region, tenant.tenant_name, data)
        # 将组件创建状态变更为创建完成
        service.create_status = "complete"
        service.save()
        return service

    def __init_third_party_data(self, tenant, service, user_name):
        data = dict()
        data["tenant_id"] = tenant.tenant_id
        data["service_id"] = service.service_id
        data["service_alias"] = service.service_alias
        data["protocol"] = service.protocol
        data["ports_info"] = []
        data["enterprise_id"] = tenant.enterprise_id
        data["operator"] = user_name
        data["namespace"] = service.namespace
        data["service_key"] = service.service_key
        data["port_type"] = service.port_type
        return data

    def get_service_by_service_key(self, service, dep_service_key):
        """
        get service according to service_key that is sometimes called service_share_uuid.
        """
        group_id = service_group_relation_repo.get_group_id_by_service(service)
        dep_services = service_repo.list_by_svc_share_uuids(group_id, [dep_service_key])
        if not dep_services:
            logger.warning("service share uuid: {}; failed to get dep service: \
                service not found".format(dep_service_key))
            return None
        return dep_services[0]

    def get_code_long_build_version(self, eid, region, lang):
        return region_api.get_lang_version(eid, region, lang).get("list", [])


class AppMarketService(object):
    def get_app_markets(self, enterprise_id, extend):
        markets = app_market_repo.get_app_markets(enterprise_id)
        app_market_repo.create_default_app_market_if_not_exists(markets, enterprise_id)
        market_list = []
        for market in markets:
            dt = {
                "access_key": market.access_key,
                "name": market.name,
                "url": market.url,
                "enterprise_id": market.enterprise_id,
                "type": market.type,
                "domain": market.domain,
                "ID": market.ID,
            }
            if extend == "true":
                version = "1.0"
                try:
                    extend_info = app_store.get_market(market)
                    market.description = extend_info.description
                    market.alias = extend_info.name
                    market.status = extend_info.status
                    market.create_time = extend_info.create_time
                    market.access_actions = extend_info.access_actions
                    version = extend_info.version if hasattr(extend_info, "version") else version
                except Exception as e:
                    logger.exception(e)
                    market.description = None
                    market.alias = market.name
                    market.status = 0
                    market.create_time = None
                    market.access_actions = []
                dt.update({
                    "description": market.description,
                    "alias": market.alias,
                    "status": market.status,
                    "access_actions": market.access_actions,
                    "version": version
                })
            market_list.append(dt)
        return market_list

    def get_app_market(self, enterprise_id, market_name, extend="false", raise_exception=False):
        market = app_market_repo.get_app_market_by_name(enterprise_id, market_name, raise_exception)
        dt = {
            "access_key": market.access_key,
            "name": market.name,
            "url": market.url,
            "type": market.type,
            "domain": market.domain,
            "ID": market.ID,
        }
        if extend == "true":
            version = "1.0"
            try:
                extend_info = app_store.get_market(market)
                market.description = extend_info.description
                market.alias = extend_info.name
                market.status = extend_info.status
                market.access_actions = extend_info.access_actions
                version = extend_info.version if extend_info.version else version
            except Exception as e:
                logger.debug(e)
                market.description = None
                market.alias = None
                market.status = 0
                market.access_actions = []
            if raise_exception:
                if market.status == 0:
                    raise ServiceHandleException(msg="call market error", msg_show="应用商店状态异常")
            dt.update({
                "description": market.description,
                "alias": market.alias,
                "status": market.status,
                "access_actions": market.access_actions,
                "version": version
            })
        return dt, market

    def get_app_market_by_name(self, enterprise_id, name, raise_exception=False):
        return app_market_repo.get_app_market_by_name(enterprise_id, name, raise_exception=raise_exception)

    def get_app_market_by_domain_url(self, enterprise_id, domain, url, raise_exception=False):
        return app_market_repo.get_app_market_by_domain_url(enterprise_id, domain, url, raise_exception=raise_exception)

    def create_app_market(self, data):
        exit_market = app_market_repo.get_app_market_by_name(enterprise_id=data["enterprise_id"], name=data["name"])
        if exit_market:
            raise ServiceHandleException(msg="name exist", msg_show="标识已存在", status_code=400)
        return app_market_repo.create_app_market(**data)

    @transaction.atomic
    def batch_create_app_market(self, eid, data):
        if data is not None:
            for dt in data:
                exist_market = app_market_repo.get_app_market_by_name(enterprise_id=eid, name=dt["name"])
                if exist_market:
                    app_market_repo.update_access_key(enterprise_id=eid, name=dt["name"], access_key=dt["access_key"])
                    continue
                app_market_repo.create_app_market(**dt)
        return self.get_app_markets(eid, extend="true")

    def update_app_market(self, app_market, data):
        exit_market = app_market_repo.get_app_market_by_name(enterprise_id=data["enterprise_id"], name=data["name"])
        if exit_market:
            if exit_market.ID != app_market.ID:
                raise ServiceHandleException(msg="name exist", msg_show="标识已存在", status_code=400)
        app_market.name = data["name"]
        app_market.type = data["type"]
        app_market.enterprise_id = data["enterprise_id"]
        app_market.url = data["url"]
        app_market.access_key = data["access_key"]
        app_market.domain = data["domain"]
        app_market.save()
        return app_market

    def app_models_serializers(self, market, data, extend=False):
        app_models = []

        if data:
            for dt in data:
                versions = []
                app_arch = dict()
                for version in dt.versions:
                    arch = version.arch if version.arch else "amd64"
                    app_arch[arch] = 1
                    versions.append({
                        "arch": arch,
                        "is_plugin": version.is_plugin,
                        "app_key_id": version.app_key_id,
                        "app_version": version.app_version,
                        "app_version_alias": version.app_version_alias,
                        "create_time": version.create_time,
                        "desc": version.desc,
                        "rainbond_version": version.desc,
                        "update_time": version.update_time,
                        "update_version": version.update_version,
                    })
                market_info = {
                    "app_id": dt.app_key_id,
                    "app_name": dt.name,
                    "update_time": dt.update_time,
                    "local_market_id": market.ID,
                    "local_market_name": market.name,
                    "enterprise_id": market.enterprise_id,
                    "source": "market",
                    "versions": versions,
                    "arch": app_arch.keys(),
                    "tags": [t for t in dt.tags],
                    "logo": dt.logo,
                    "market_id": dt.market_id,
                    "market_name": dt.market_name,
                    "market_url": dt.market_url,
                    "install_number": dt.install_count,
                    "describe": dt.desc,
                    "dev_status": dt.dev_status,
                    "app_detail_url": dt.app_detail_url,
                    "create_time": dt.create_time,
                    "download_number": dt.download_count,
                    "details": dt.introduction,
                    "details_html": dt.introduction_html,
                    "is_official": dt.is_official,
                    "publish_type": dt.publish_type,
                    "start_count": dt.start_count,
                }
                app_models.append(Dict(market_info))
        return app_models

    def app_model_serializers(self, market, data, extend=False):
        app_model = {}
        if data:
            app_model = {
                "app_id": data.app_key_id,
                "app_name": data.name,
                "update_time": data.update_time,
                "local_market_id": market.ID,
                "enterprise_id": market.enterprise_id,
                "source": "market",
            }
            if extend:
                app_model.update({
                    "market_id": data.market_id,
                    "logo": data.logo,
                    "market_name": data.market_name,
                    "market_url": data.market_url,
                    "install_number": data.install_count,
                    "describe": data.desc,
                    "dev_status": data.dev_status,
                    "app_detail_url": data.app_detail_url,
                    "create_time": data.create_time,
                    "download_number": data.download_count,
                    "details": data.introduction,
                    "details_html": data.introduction_html,
                    "is_official": data.is_official,
                    "publish_type": data.publish_type,
                    "start_count": data.start_count,
                    "versions": data.versions,
                    "tags": data.tags,
                })
        return Dict(app_model)

    def app_model_versions_serializers(self, market, data, extend=False):
        app_models = []
        if data:
            for dt in data:
                version = {
                    "app_id": dt.app_key_id,
                    "version": dt.app_version,
                    "version_alias": dt.app_version_alias,
                    "update_version": dt.update_version,
                    "app_version_info": dt.desc,
                    "rainbond_version": dt.rainbond_version,
                    "create_time": dt.create_time,
                    "update_time": dt.update_time,
                    "enterprise_id": market.enterprise_id,
                    "local_market_id": market.ID,
                }
                app_models.append(Dict(version))
        return app_models

    def app_model_version_serializers(self, market, data, extend=False):
        version = {}
        if data:
            version = {
                "is_plugin": data.is_plugin,
                "template_type": data.template_type,
                "template": data.template,
                "delivery_mode": data.delivery_mode,
                "update_time": data.update_time,
                "version": data.version,
                "version_alias": data.version_alias,
                "update_version": data.update_version,
                "app_version_info": data.description,
                "rainbond_version": data.rainbond_version,
                "create_time": data.create_time,
                "app_id": data.app_key_id,
                "app_name": data.app_name,
                "enterprise_id": market.enterprise_id,
                "local_market_id": market.ID,
            }
        return Dict(version)

    def get_market_app_list(self, market, page=1, page_size=10, query=None, query_all=False, extend=False, arch=""):
        results = app_store.get_apps(market, page=page, page_size=page_size, query=query, query_all=query_all, arch=arch)
        data = self.app_models_serializers(market, results.apps, extend=extend)
        return data, results.page, results.page_size, results.total

    def get_market_plugins_apps(self, market, page=1, page_size=10, query=None, query_all=False, extend=False):
        results = app_store.get_plugins_apps(market, page=page, page_size=page_size, query=query, query_all=query_all)
        data = self.app_models_serializers(market, results.apps, extend=extend)
        return data, results.page, results.page_size, results.total

    def get_market_app_models(self, market, page=1, page_size=10, query=None, query_all=False, extend=False):
        results = app_store.get_apps_templates(market, page=page, page_size=page_size, query=query, query_all=query_all)
        data = self.app_models_serializers(market, results.apps, extend=extend)
        return data, results.page, results.page_size, results.total

    def get_market_app_model(self, market, app_id, extend=False):
        results = app_store.get_app(market, app_id)
        return self.app_model_serializers(market, results, extend=extend)

    def get_market_app_model_versions(self, market: AppMarket, app_id, query_all=False, extend=False):
        if not app_id:
            raise ServiceHandleException(msg="param app_id can`t be null", msg_show="参数app_id不能为空")
        results = app_store.get_app_versions(market, app_id, query_all=query_all)
        data = self.app_model_versions_serializers(market, results.versions, extend=extend)
        return data

    def get_market_app_model_version(self, market, app_id, version, for_install=False, extend=False, get_template=False):
        if not app_id:
            raise ServiceHandleException(msg="param app_id can`t be null", msg_show="参数app_id不能为空")
        results = app_store.get_app_version(market, app_id, version, for_install=for_install, get_template=get_template)
        data = self.app_model_version_serializers(market, results, extend=extend)
        return data

    def cloud_app_model_to_db_model(self, market: AppMarket, app_id, version, for_install=False):
        app = app_store.get_app(market, app_id)
        rainbond_app_version = None
        app_template = None
        try:
            if version:
                app_template = app_store.get_app_version(market, app_id, version, for_install=for_install, get_template=True)
        except ServiceHandleException as e:
            if e.status_code != 404:
                logger.exception(e)
            app_template = None
        rainbond_app = RainbondCenterApp(
            app_id=app.app_key_id,
            app_name=app.name,
            dev_status=app.dev_status,
            source="market",
            scope="goodrain",
            describe=app.desc,
            details=app.introduction,
            pic=app.logo,
            create_time=app.create_time,
            update_time=app.update_time)
        rainbond_app.market_name = market.name
        if app_template:
            rainbond_app_version = RainbondCenterAppVersion(
                app_id=app.app_key_id,
                app_template=app_template.template,
                version=app_template.version,
                version_alias=app_template.version_alias,
                template_version=app_template.rainbond_version,
                app_version_info=app_template.description,
                update_time=app_template.update_time,
                is_official=1,
                arch=app_template.arch,
            )
            rainbond_app_version.template_type = app_template.template_type
        return rainbond_app, rainbond_app_version

    def create_market_app_model(self, market, body):
        return app_store.create_app(market, body)

    def create_market_app_model_version(self, market, app_id, body):
        app_store.create_app_version(market, app_id, body)

    def list_bindable_markets(self, eid, market_name, market_url, access_key):
        if market_name:
            market = app_market_service.get_app_market_by_name(eid, market_name)
        else:
            market = AppMarket(url=market_url, access_key=access_key)

        bindable_markets = app_store.list_bindable_markets(market)
        if not bindable_markets:
            return []

        return [bm.to_dict() for bm in bindable_markets]

    def get_market_orgs(self, market):
        results = app_store.get_orgs(market)
        return self.org_serializers(results)

    def org_serializers(self, data):
        organizations = []
        if not data:
            return []
        for dt in data:
            org = {
                "eid": dt.eid,
                "name": dt.name,
                "org_id": dt.org_id,
                "desc": dt.desc,
            }
            organizations.append(Dict(org))
        return organizations

    def update_market_app(self, app_id, upgrade_group_id, app_model_key, version):
        # plugins
        # config groups
        # app
        # create update record
        # build, update or nothing
        return


class PackageUploadService(object):
    def get_upload_record(self, team_name, region, event_id):
        return PackageUploadRecord.objects.filter(team_name=team_name, region=region, event_id=event_id).first()

    def create_upload_record(self, **params):
        return PackageUploadRecord.objects.create(**params)

    def get_last_upload_record(self, team_name, region, component_id):
        if component_id:
            return PackageUploadRecord.objects.filter(
                team_name=team_name, region=region, component_id=component_id,
                status="unfinished").order_by("-create_time").first()
        return PackageUploadRecord.objects.filter(
            team_name=team_name, region=region, status="unfinished").order_by("-create_time").first()

    def update_upload_record(self, team_name, event_id, **data):
        return PackageUploadRecord.objects.filter(team_name=team_name, event_id=event_id).update(**data)

    def get_name_by_component_id(self, component_ids):
        package_names = []
        for component_id in component_ids:
            res = PackageUploadRecord.objects.filter(
                component_id=component_id, status="finished").order_by("-create_time").first()
            if res:
                package_name = eval(res.source_dir)
                package_names += package_name
        return package_names


app_service = AppService()
app_market_service = AppMarketService()
package_upload_service = PackageUploadService()

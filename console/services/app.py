# -*- coding: utf8 -*-
"""
  Created on 18/1/11.
"""
import datetime
import json
import logging
import random
import string
from addict import Dict

from django.db.models import Q

from console.constants import AppConstants
from console.constants import PluginImage
from console.constants import SourceCodeType
from console.enum.component_enum import ComponentType
from console.exception.main import ServiceHandleException
from console.exception.main import ErrDoNotSupportMultiDomain
from console.models.main import RainbondCenterApp
from console.models.main import RainbondCenterAppVersion
from console.repositories.app import service_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import env_var_repo
from console.repositories.app_config import mnt_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import service_endpoints_repo
from console.repositories.app_config import volume_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo
from console.repositories.app import app_market_repo
from console.services.app_config import label_service
from console.services.app_config.port_service import AppPortService
from console.services.app_config.probe_service import ProbeService
from console.utils.oauth.oauth_types import support_oauth_type
from console.utils.validation import validate_endpoint_address
from console.appstore.appstore import app_store
from www.apiclient.regionapi import RegionInvokeApi
from www.github_http import GitHubApi
from www.models.main import ServiceConsume
from www.models.main import TenantServiceInfo
from www.tenantservice.baseservice import BaseTenantService
from www.tenantservice.baseservice import CodeRepositoriesService
from www.tenantservice.baseservice import ServicePluginResource
from www.tenantservice.baseservice import TenantUsedResource
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
    def check_service_cname(self, tenant, service_cname, region):
        if not service_cname:
            return False, u"组件名称不能为空"
        if len(service_cname) > 100:
            return False, u"组件名称最多支持100个字符"
        return True, u"success"

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
                               git_full_name=None):
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
        new_service.save()
        code, msg = self.init_repositories(new_service, user, service_code_from, service_code_clone_url, service_code_id,
                                           service_code_version, check_uuid, event_id, oauth_service_id, git_full_name)
        if code != 200:
            return code, msg, new_service
        logger.debug("service.create", "user:{0} create service from source code".format(user.nick_name))
        ts = TenantServiceInfo.objects.get(service_id=new_service.service_id, tenant_id=new_service.tenant_id)
        return 200, u"创建成功", ts

    def init_repositories(self, service, user, service_code_from, service_code_clone_url, service_code_id, service_code_version,
                          check_uuid, event_id, oauth_service_id, git_full_name):
        if service_code_from == SourceCodeType.GITLAB_MANUAL or service_code_from == SourceCodeType.GITLAB_DEMO:
            service_code_id = "0"

        if service_code_from in (SourceCodeType.GITLAB_EXIT, SourceCodeType.GITLAB_MANUAL, SourceCodeType.GITLAB_DEMO):
            if not service_code_clone_url or not service_code_id:
                return 403, u"代码信息不全"
            service.git_project_id = service_code_id
            service.git_url = service_code_clone_url
            service.code_from = service_code_from
            service.code_version = service_code_version
            service.save()
        elif service_code_from == SourceCodeType.GITHUB:
            if not service_code_clone_url:
                return 403, u"代码信息不全"
            service.git_project_id = service_code_id
            service.git_url = service_code_clone_url
            service.code_from = service_code_from
            service.code_version = service_code_version
            service.save()
            code_user = service_code_clone_url.split("/")[3]
            code_project_name = service_code_clone_url.split("/")[4].split(".")[0]
            gitHubClient.createReposHook(code_user, code_project_name, user.github_token)
        elif service_code_from.split("oauth_")[-1] in support_oauth_type.keys():

            if not service_code_clone_url:
                return 403, u"代码信息不全"
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

        return 200, u"success"

    def create_service_source_info(self, tenant, service, user_name, password):
        params = {
            "team_id": tenant.tenant_id,
            "service_id": service.service_id,
            "user_name": user_name,
            "password": password,
        }
        return service_source_repo.create_service_source(**params)

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
        tenant_service.min_memory = 128
        tenant_service.min_cpu = baseService.calculate_service_cpu(region, 128)
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

    def create_service_alias(self, service_id):
        service_alias = "gr" + service_id[-6:]
        svc = service_repo.get_service_by_service_alias(service_alias)
        if svc is None:
            return service_alias
        service_alias = self.create_service_alias(make_uuid(service_id))
        return service_alias

    def create_docker_run_app(self, region, tenant, user, service_cname, docker_cmd, image_type):
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
        new_service.save()
        # # 创建镜像和组件的关系（兼容老的流程）
        # if not image_service_relation_repo.get_image_service_relation(tenant.tenant_id, service_id):
        #     image_service_relation_repo.create_image_service_relation(tenant.tenant_id, service_id, docker_cmd,
        #                                                               service_cname)

        logger.debug("service.create", "user:{0} create service from docker run command !".format(user.nick_name))
        ts = TenantServiceInfo.objects.get(service_id=new_service.service_id, tenant_id=new_service.tenant_id)

        return 200, u"创建成功", ts

    def __init_third_party_app(self, region, end_point):
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
        tenant_service.min_node = len(end_point)
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

    def create_third_party_app(self, region, tenant, user, service_cname, endpoints, endpoints_type):
        service_cname = service_cname.rstrip().lstrip()
        is_pass, msg = self.check_service_cname(tenant, service_cname, region)
        if not is_pass:
            return 412, msg, None
        # 初始化
        new_service = self.__init_third_party_app(region, endpoints)
        new_service.tenant_id = tenant.tenant_id
        new_service.service_cname = service_cname
        service_id = make_uuid(tenant.tenant_id)
        service_alias = self.create_service_alias(service_id)
        new_service.service_id = service_id
        new_service.service_alias = service_alias
        new_service.creater = user.pk
        new_service.server_type = ''
        new_service.protocol = 'tcp'
        new_service.save()
        if endpoints_type == "static":
            # 如果只有一个端口，就设定为默认端口，没有或有多个端口，不设置默认端口
            if endpoints:
                from console.views.app_create.source_outer import check_endpoints
                errs, isDomain = check_endpoints(endpoints)
                if errs:
                    return 400, u"组件地址不合法", None
                port_list = []
                prefix = ""
                protocol = "tcp"
                for endpoint in endpoints:
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
                if len(port_list) == 0 and isDomain is True and prefix != "":
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
                            "is_outer_service": False
                        }
                        service_port = port_repo.add_service_port(**service_port)

        # 保存endpoints数据
        service_endpoints = {
            "tenant_id": tenant.tenant_id,
            "service_id": new_service.service_id,
            "service_cname": new_service.service_cname,
            "endpoints_info": json.dumps(endpoints),
            "endpoints_type": endpoints_type
        }
        logger.debug('------service_endpoints------------->{0}'.format(service_endpoints))
        service_endpoints_repo.add_service_endpoints(service_endpoints)

        ts = TenantServiceInfo.objects.get(service_id=new_service.service_id, tenant_id=new_service.tenant_id)
        return 200, u"创建成功", ts

    def get_app_list(self, tenant_id, region, query=""):
        q = Q(tenant_id=tenant_id, service_region=region)
        if query:
            q &= Q(service_cname__contains=query)
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
        # 依赖
        depend_ids = [{
            "dep_order": dep.dep_order,
            "dep_service_type": dep.dep_service_type,
            "depend_service_id": dep.dep_service_id,
            "service_id": dep.service_id,
            "tenant_id": dep.tenant_id
        } for dep in service_dep_relations]
        data["depend_ids"] = depend_ids
        # 端口
        ports = port_repo.get_service_ports(tenant.tenant_id, service.service_id)
        ports_info = ports.values('container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service',
                                  'is_outer_service')

        for port_info in ports_info:
            port_info["is_inner_service"] = False
            port_info["is_outer_service"] = False

        if ports_info:
            data["ports_info"] = list(ports_info)
        # 环境变量
        envs_info = env_var_repo.get_service_env(tenant.tenant_id, service.service_id).values(
            'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if envs_info:
            data["envs_info"] = list(envs_info)
        # 持久化目录
        volume_info = volume_repo.get_service_volumes_with_config_file(service.service_id).values(
            'ID', 'service_id', 'category', 'volume_name', 'volume_path', 'volume_type')
        if volume_info:
            logger.debug('--------volume_info----->{0}'.format(volume_info))
            for volume in volume_info:
                volume_id = volume['ID']
                config_file = volume_repo.get_service_config_file(volume_id)
                if config_file:
                    volume.update({"file_content": config_file.file_content})
            logger.debug('--------volume_info22222----->{0}'.format(volume_info))
            data["volumes_info"] = list(volume_info)

        logger.debug(tenant.tenant_name + " start create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        # 挂载信息
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
        # 数据中心创建
        region_api.create_service(service.service_region, tenant.tenant_name, data)
        # 将组件创建状态变更为创建完成
        service.create_status = "complete"
        self.__handle_service_ports(tenant, service, ports)
        service.save()
        return service

    def __init_create_data(self, tenant, service, user_name, do_deploy, dep_sids):
        data = dict()
        data["tenant_id"] = tenant.tenant_id
        data["service_id"] = service.service_id
        data["service_key"] = service.service_key
        data["comment"] = service.desc
        data["image_name"] = service.image
        data["container_cpu"] = service.min_cpu
        data["container_memory"] = service.min_memory
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

    def __handle_service_ports(self, tenant, service, ports):
        """处理创建组件的端口。对于打开了对内或对外端口的组件，需由业务端手动打开"""
        try:
            for port in ports:
                if port.is_outer_service:
                    code, msg, data = port_service.manage_port(tenant, service, service.service_region, port.container_port,
                                                               "open_outer", port.protocol, port.port_alias)
                    if code != 200:
                        logger.error("create service manage port error : {0}".format(msg))
                if port.is_inner_service:
                    code, msg, data = port_service.manage_port(tenant, service, service.service_region, port.container_port,
                                                               "open_inner", port.protocol, port.port_alias)
                    if code != 200:
                        logger.error("create service manage port error : {0}".format(msg))
        except Exception as e:
            logger.exception(e)

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

    def update_check_app(self, tenant, service, data):

        service_source = service_source_repo.get_service_source(tenant.tenant_id, service.service_id)
        service_cname = data.get("service_cname", service.service_cname)
        image = data.get("image", service.image)
        cmd = data.get("cmd", service.cmd)
        docker_cmd = data.get("docker_cmd", service.docker_cmd)
        git_url = data.get("git_url", service.git_url)
        min_memory = data.get("min_memory", service.min_memory)
        min_memory = int(min_memory)
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

    def create_third_party_service(self, tenant, service, user_name):
        data = self.__init_third_party_data(tenant, service, user_name)
        # 端口
        ports = port_repo.get_service_ports(tenant.tenant_id, service.service_id)
        ports_info = ports.values('container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service',
                                  'is_outer_service')

        for port_info in ports_info:
            port_info["is_inner_service"] = False
            port_info["is_outer_service"] = False

        if ports_info:
            data["ports_info"] = list(ports_info)

        # endpoints
        endpoints = service_endpoints_repo.get_service_endpoints_by_service_id(service.service_id)
        if endpoints.endpoints_type == "static":
            eps = json.loads(endpoints.endpoints_info)
            for address in eps:
                if "https://" in address:
                    address = address.partition("https://")[2]
                if "http://" in address:
                    address = address.partition("http://")[2]
                if ":" in address:
                    address = address.rpartition(":")[0]
                errs = validate_endpoint_address(address)
                if errs:
                    if len(eps) > 1:
                        raise ErrDoNotSupportMultiDomain("do not support multi domain address")
        endpoints_dict = dict()
        if endpoints:
            endpoints_dict[endpoints.endpoints_type] = endpoints.endpoints_info
            data["endpoints"] = endpoints_dict
        data["kind"] = service.service_source

        # etcd keys
        data["etcd_key"] = service.check_uuid
        # 数据中心创建
        logger.debug('-----------data-----------_>{0}'.format(data))
        region_api.create_service(service.service_region, tenant.tenant_name, data)
        # 将组件创建状态变更为创建完成
        service.create_status = "complete"
        self.__handle_service_ports(tenant, service, ports)
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


class AppMarketService(object):
    def get_app_markets(self, enterprise_id, extend):
        market_list = []
        markets = app_market_repo.get_app_markets(enterprise_id)
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
                try:
                    extend_info = app_store.get_market(market)
                    market.description = extend_info.description
                    market.alias = extend_info.name
                    market.status = extend_info.status
                    market.create_time = extend_info.create_time
                except Exception as e:
                    logger.debug(e)
                    market.description = None
                    market.alias = None
                    market.status = 0,
                    market.create_time = None
                dt.update({
                    "description": market.description,
                    "alias": market.alias,
                    "status": market.status,
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
            try:
                extend_info = app_store.get_market(market)
                market.description = extend_info.description
                market.alias = extend_info.name
                market.status = extend_info.status
            except Exception as e:
                logger.debug(e)
                market.description = None
                market.alias = None
                market.status = 0
            if raise_exception:
                if market.status == 0:
                    raise ServiceHandleException(msg="call market error", msg_show=u"应用商店状态异常")
            dt.update({
                "description": market.description,
                "alias": market.alias,
                "status": market.status,
            })
        return dt, market

    def get_app_market_by_name(self, enterprise_id, name, raise_exception=False):
        return app_market_repo.get_app_market_by_name(enterprise_id, name, raise_exception=raise_exception)

    def create_app_market(self, data):
        exit_market = app_market_repo.get_app_market_by_name(enterprise_id=data["enterprise_id"], name=data["name"])
        if exit_market:
            raise ServiceHandleException(msg="name exist", msg_show=u"名称已存在", status_code=400)
        return app_market_repo.create_app_market(**data)

    def update_app_market(self, app_market, data):
        exit_market = app_market_repo.get_app_market_by_name(enterprise_id=data["enterprise_id"], name=data["name"])
        if exit_market:
            if exit_market.ID != app_market.ID:
                raise ServiceHandleException(msg="name exist", msg_show=u"名称已存在", status_code=400)
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
                for version in dt.versions:
                    versions.append({
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
                    "tags": [t for t in dt.tags],
                    "logo": dt.logo,
                    "market_id": dt.market_id,
                    "market_name": dt.market_name,
                    "market_url": dt.market_url,
                    "install_number": dt.install_count,
                    "describe": dt.desc,
                    "dev_status": dt.dev_status,
                    "app_url": dt.app_detail_url,
                    "create_time": dt.create_time,
                    "download_number": dt.download_count,
                    "details": dt.introduction,
                    "details_html": dt.introduction_html,
                    "is_official": dt.is_official,
                    "publish_type": dt.publish_type,
                    "start_count": dt.start_count,
                }
                app_models.append(market_info)
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
                    "app_url": data.app_detail_url,
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

    def get_market_app_models(self, market, page=1, page_size=10, query=None, extend=False):
        results = app_store.get_apps(market, page=page, page_size=page_size, query=query)
        data = self.app_models_serializers(market, results.apps, extend=extend)
        return data, results.page, results.page_size, results.total

    def get_market_app_model(self, market, app_id, extend=False):
        results = app_store.get_app(market, app_id)
        return self.app_model_serializers(market, results, extend=extend)

    def get_market_app_model_versions(self, market, app_id, extend=False):
        if not app_id:
            raise ServiceHandleException(msg="param app_id can`t be null", msg_show="参数app_id不能为空")
        results = app_store.get_app_versions(market, app_id)
        data = self.app_model_versions_serializers(market, results.versions, extend=extend)
        return data

    def get_market_app_model_version(self, market, app_id, version, for_install=False, extend=False):
        if not app_id:
            raise ServiceHandleException(msg="param app_id can`t be null", msg_show="参数app_id不能为空")
        results = app_store.get_app_version(market, app_id, version, for_install=for_install)
        data = self.app_model_version_serializers(market, results, extend=extend)
        return data

    def cloud_app_model_to_db_model(self, market, app_id, version):
        app = app_store.get_app(market, app_id)
        app_template = app_store.get_app_version(market, app_id, version, for_install=True)
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
        rainbond_app_version = RainbondCenterAppVersion(
            app_id=app.app_key_id,
            app_template=app_template.template,
            version=app_template.version,
            version_alias=app_template.version_alias,
            template_version=app_template.rainbond_version,
            app_version_info=app_template.description,
            update_time=app_template.update_time,
            is_official=1)
        rainbond_app_version.template_type = app_template.template_type
        return rainbond_app, rainbond_app_version

    def create_market_app_model(self, market, body):
        return app_store.create_app(market, body)

    def create_market_app_model_version(self, market, app_id, body):
        app_store.create_app_version(market, app_id, body)


app_service = AppService()
app_market_service = AppMarketService()

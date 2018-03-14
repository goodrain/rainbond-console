# -*- coding: utf8 -*-
"""
  Created on 18/1/11.
"""
import datetime
import logging

from console.constants import AppConstants
from console.repositories.app_config import dep_relation_repo, port_repo, env_var_repo, volume_repo, mnt_repo
from console.repositories.app import service_source_repo, service_repo
from console.repositories.base import BaseConnection
from console.repositories.perm_repo import perms_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.github_http import GitHubApi
from www.models import TenantServiceInfo, ServiceConsume
from www.tenantservice.baseservice import TenantUsedResource, CodeRepositoriesService, BaseTenantService, \
    ServicePluginResource
from www.utils.crypt import make_uuid
from www.utils.status_translate import get_status_info_map
from console.constants import SourceCodeType
from console.services.app_config import port_service, probe_service
import re

tenantUsedResource = TenantUsedResource()
logger = logging.getLogger("default")
region_api = RegionInvokeApi()
codeRepositoriesService = CodeRepositoriesService()
baseService = BaseTenantService()
servicePluginResource = ServicePluginResource()
gitHubClient = GitHubApi()


class AppService(object):
    def check_service_cname(self, tenant, service_cname):
        if not service_cname:
            return False, u"应用名称不能为空"
        if len(service_cname) > 20:
            return False, u"应用名称最多支持20个字符"
        r = re.compile(u'^[a-zA-Z0-9_\\-\u4e00-\u9fa5]+$')
        if not r.match(service_cname.decode("utf-8")):
            return False, u"应用名称只支持中英文下划线和中划线"
        service = service_repo.get_service_by_tenant_and_name(tenant.tenant_id, service_cname)
        if service:
            return False, u"当前团队下已存在相同名称应用"
        return True, u"success"

    def __init_source_code_app(self, region):
        """
        初始化源码创建的应用默认数据,未存入数据库
        """
        tenant_service = TenantServiceInfo()
        tenant_service.service_region = region
        tenant_service.service_key = "application"
        tenant_service.desc = "application info"
        tenant_service.category = "application"
        tenant_service.image = "goodrain.me/runner"
        tenant_service.cmd = "start web"
        tenant_service.setting = ""
        tenant_service.extend_method = "stateless"
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

    def create_source_code_app(self, region, tenant, user, service_code_from, service_cname, service_code_clone_url,
                               service_code_id,
                               service_code_version):
        service_cname = service_cname.rstrip().lstrip()
        is_pass, msg = self.check_service_cname(tenant, service_cname)
        if not is_pass:
            return 412, msg, None
        new_service = self.__init_source_code_app(region)
        new_service.tenant_id = tenant.tenant_id
        new_service.service_cname = service_cname
        service_id = make_uuid(tenant.tenant_id)
        service_alias = "gr" + service_id[-6:]
        # 判断是否超过资源
        allow_create, tips = self.check_tenant_resource(tenant, new_service.min_node * new_service.min_memory)
        if not allow_create:
            return 412, tips, None
        new_service.service_id = service_id
        new_service.service_alias = service_alias
        new_service.creater = user.pk
        new_service.save()
        code, msg = self.init_repositories(new_service, user, service_code_from, service_code_clone_url,
                                           service_code_id,
                                           service_code_version)
        if code != 200:
            return code, msg, new_service
        logger.debug("service.create", "user:{0} create service from source code".format(user.nick_name))
        ts = TenantServiceInfo.objects.get(service_id=new_service.service_id, tenant_id=new_service.tenant_id)
        return 200, u"创建成功", ts

    def init_repositories(self, service, user, service_code_from, service_code_clone_url, service_code_id,
                          service_code_version):
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

        return 200, u"success"

    def check_tenant_resource(self, tenant, new_add_memory):
        """检测租户资源"""
        allow_create = True
        tips = u"success"
        tenant_cur_used_resource = tenantUsedResource.calculate_real_used_resource(tenant)
        if tenant.pay_type == "free":
            # 免费用户最多使用1G内存
            if new_add_memory + tenant_cur_used_resource > tenant.limit_memory:
                allow_create = False
                tips = u"您最多使用{0}G内存".format(tenant.limit_memory / 1024)
        return allow_create, tips

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
        初始化docker image创建的应用默认数据,未存入数据库
        """
        tenant_service = TenantServiceInfo()
        tenant_service.service_region = region
        tenant_service.service_key = "0000"
        tenant_service.desc = "docker run application"
        tenant_service.category = "app_publish"
        # tenant_service.image = "goodrain.me/runner"
        # tenant_service.cmd = "start web"
        tenant_service.setting = ""
        tenant_service.extend_method = "stateless"
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

    def create_docker_run_app(self, region, tenant, user, service_cname, docker_cmd, image_type):
        is_pass, msg = self.check_service_cname(tenant, service_cname)
        if not is_pass:
            return 412, msg, None
        new_service = self.__init_docker_image_app(region)
        new_service.tenant_id = tenant.tenant_id
        new_service.service_cname = service_cname
        new_service.service_source = image_type
        service_id = make_uuid(tenant.tenant_id)
        service_alias = "gr" + service_id[-6:]
        allow_create, tips = self.check_tenant_resource(tenant, new_service.min_node * new_service.min_memory)
        if not allow_create:
            return 412, tips, None
        new_service.service_id = service_id
        new_service.service_alias = service_alias
        new_service.creater = user.pk
        new_service.host_path = "/grdata/tenant/" + tenant.tenant_id + "/service/" + service_id
        new_service.docker_cmd = docker_cmd
        new_service.save()
        # # 创建镜像和服务的关系（兼容老的流程）
        # if not image_service_relation_repo.get_image_service_relation(tenant.tenant_id, service_id):
        #     image_service_relation_repo.create_image_service_relation(tenant.tenant_id, service_id, docker_cmd,
        #                                                               service_cname)

        logger.debug("service.create", "user:{0} create service from docker run command !".format(user.nick_name))
        ts = TenantServiceInfo.objects.get(service_id=new_service.service_id, tenant_id=new_service.tenant_id)

        return 200, u"创建成功", ts

    def get_app_list(self, tenant_pk, user, tenant_id, region):
        user_pk = user.pk
        services = []
        if user.is_sys_admin:
            services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region)
        else:
            perm = perms_repo.get_user_tenant_perm(tenant_pk, user_pk)
            if not perm:
                if tenant_pk == 5073:
                    services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region).order_by(
                        'service_alias')

            else:
                if perm.identity in ('admin', 'developer', 'viewer', 'gray', 'owner'):
                    services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region).order_by(
                        'service_alias')
                else:
                    dsn = BaseConnection()
                    add_sql = ''
                    query_sql = '''
                          select s.* from tenant_service s, service_perms sp where s.tenant_id = "{tenant_id}"
                          and sp.user_id = {user_id} and sp.service_id = s.ID and s.service_region = "{region}" {add_sql} order by s.service_alias
                          '''.format(tenant_id=tenant_id, user_id=user_pk, region=region,
                                     add_sql=add_sql)
                    services = dsn.query(query_sql)

        return services

    def get_service_status(self, tenant, service):
        """获取应用状态"""
        try:
            body = region_api.check_service_status(service.service_region, tenant.tenant_name,
                                                   service.service_alias, tenant.enterprise_id)

            bean = body["bean"]
            status = bean["cur_status"]
        except Exception as e:
            logger.exception(e)
            status = "unKnow"
        status_info_map = get_status_info_map(status)

        return status_info_map

    def get_service_resource_with_plugin(self, tenant, service, status):
        disk = 0

        service_consume = ServiceConsume.objects.filter(
            tenant_id=tenant.tenant_id, service_id=service.service_id
        ).order_by("-ID")
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
        ports_info = ports.values(
            'container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')

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
        volume_info = volume_repo.get_service_volumes(service.service_id).values(
            'service_id', 'category', 'volume_name', 'volume_path', 'volume_type')
        if volume_info:
            data["volumes_info"] = list(volume_info)
        logger.debug(
            tenant.tenant_name + " start create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        # 挂载信息
        mnt_info = mnt_repo.get_service_mnts(service.tenant_id, service.service_id)
        if mnt_info:
            data["dep_volumes_info"] = [
                {"dep_service_id": mnt.dep_service_id, "volume_path": mnt.mnt_dir, "volume_name": mnt.mnt_name}
                for mnt in mnt_info]

        # 数据中心创建
        region_api.create_service(service.service_region, tenant.tenant_name, data)
        # 将服务创建状态变更为创建完成
        service.create_status = "complete"
        self.__handle_service_ports(tenant, service, ports)
        service.save()
        return service

    def __init_create_data(self, tenant, service, user_name, do_deploy, dep_sids):
        data = {}
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
        data[
            "service_label"] = "StatefulServiceType " if service.extend_method == "state" else "StatelessServiceType"
        return data

    def __handle_service_ports(self, tenant, service, ports):
        """处理创建应用的端口。对于打开了对内或对外端口的应用，需由业务端手动打开"""
        for port in ports:
            if port.is_outer_service:
                code, msg, data = port_service.manage_port(tenant, service, port.container_port, "open_outer",
                                                           port.protocol,
                                                           port.port_alias)
                if code != 200:
                    logger.error("create service manage port error : {0}".format(msg))
            if port.is_inner_service:
                code, msg, data = port_service.manage_port(tenant, service, port.container_port, "open_inner",
                                                           port.protocol,
                                                           port.port_alias)
                if code != 200:
                    logger.error("create service manage port error : {0}".format(msg))

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
                "initial_delay_second": 2,
                "period_second": 3,
                "timeout_second": 30,
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
        if user_name:
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


app_service = AppService()

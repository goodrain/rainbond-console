# -*- coding: utf8 -*-
"""
  Created on 18/2/8.
"""
from console.constants import AppConstants
from www.apiclient.regionapi import RegionInvokeApi
from www.models import TenantServiceInfo
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid
from console.utils.timeutil import current_time_str
from console.repositories.compose_repo import compose_repo, compose_relation_repo
from console.repositories.app import service_repo
import logging
import yaml
import datetime
from console.services.app import app_service
from StringIO import StringIO
from console.services.app_check_service import AppCheckService
from console.services.app_config.app_relation_service import AppServiceRelationService
from console.repositories.group import group_repo
from console.services.app_actions import app_manage_service
from console.services.group_service import group_service

region_api = RegionInvokeApi()
logger = logging.getLogger("default")
baseService = BaseTenantService()
app_check_service = AppCheckService()
app_relation_service = AppServiceRelationService()


class ComposeService(object):
    def yaml_to_json(self, compose_tontent):
        try:
            buf = StringIO(compose_tontent)
            res = yaml.safe_load(buf)
            return 200, "success", res
        except yaml.YAMLError as exc:
            return 400, "yaml内容格式不正确{0}".format(exc.message), {}

    def create_group_compose(self, tenant, region, group_id, compose_content):
        gc = compose_repo.get_group_compose_by_group_id(group_id)
        if gc:
            return 409, "该组已与其他compose组关联", None
        # 将yaml格式信息转成json数据
        group_compose_data = {
            "group_id": group_id,
            "team_id": tenant.tenant_id,
            "region": region,
            "compose_content": compose_content,
            "compose_id": make_uuid(),
            "create_status": "creating",
            "create_time": current_time_str("%Y-%m-%d %H:%M:%S"),
        }

        group_compose = compose_repo.create_group_compose(**group_compose_data)
        return 200, "创建groupcompose成功", group_compose

    def check_compose(self, region, tenant, compose_id):
        group_compose = compose_repo.get_group_compose_by_compose_id(compose_id)
        if not group_compose:
            return 404, "未找到对应的compose内容", None
        body = dict()
        body["tenant_id"] = tenant.tenant_id
        body["source_type"] = "docker-compose"
        body["source_body"] = group_compose.compose_content
        res, body = region_api.service_source_check(region, tenant.tenant_name, body)
        bean = body["bean"]
        group_compose.check_uuid = bean["check_uuid"]
        group_compose.check_event_id = bean["event_id"]
        group_compose.create_status = "checking"
        group_compose.save()
        group = group_repo.get_group_by_pk(tenant.tenant_id, region, group_compose.group_id)
        compose_bean = group_compose.to_dict()
        if group:
            compose_bean["group_name"] = group.group_name
        return 200, "success", compose_bean

    def get_group_compose_by_compose_id(self, compose_id):
        return compose_repo.get_group_compose_by_compose_id(compose_id)

    def get_group_compose_by_group_id(self, group_id):
        return compose_repo.get_group_compose_by_group_id(group_id)

    def save_compose_services(self, tenant, user, region, group_compose, data):
        service_list = []
        try:
            if data["check_status"] == "success":
                if group_compose.create_status == "checking":
                    logger.debug("checking compose service install,save info into database")
                # 先删除原来创建的应用
                self.__delete_created_compose_info(tenant, group_compose.compose_id)
                # 保存compose检测结果
                if data["check_status"] == "success":
                    service_info_list = data["service_info"]
                    service_dep_map = {}
                    # 服务列表
                    name_service_map = {}
                    for service_info in service_info_list:
                        service_cname = service_info.get("image_alias", service_info["image"]["name"])
                        image = service_info["image"]["name"] + ":" + service_info["image"]["tag"]
                        # 保存信息
                        service = self.__init_compose_service(tenant, user, service_cname, image, region)
                        group_service.add_service_to_group(tenant, region, group_compose.group_id, service.service_id)
                        service_list.append(service)
                        name_service_map[service_cname] = service
                        code, msg = app_check_service.save_service_info(tenant, service, service_info)
                        if code != 200:
                            return code, msg, None
                        dependencies = service_info.get("depends", None)
                        if dependencies:
                            service_dep_map[service_cname] = dependencies

                    # 保存compose-relation
                    self.__save_compose_relation(service_list, tenant.tenant_id, group_compose.compose_id)
                    # 保存依赖关系
                    self.__save_service_dep_relation(tenant, service_dep_map, name_service_map)

                    for s in service_list:
                        s.create_status = "checked"
                        s.save()
                group_compose.create_status = "checked"
                group_compose.save()
        except Exception as e:
            logger.exception(e)
            return 500, "{0}".format(e.message),service_list

        return 200, "success", service_list

    def verify_compose_services(self, tenant, region, data):
        if data["check_status"] == "success":
            service_info_list = data["service_info"]
            # 默认128 M
            new_add_memory = len(service_info_list) * 128
            return app_service.verify_source(tenant, region, new_add_memory, "compose创建")
        else:
            return True, "check is not success"

    def __save_service_dep_relation(self, tenant, service_dep_map, name_service_map):
        if service_dep_map:
            for key in service_dep_map.keys():
                dep_services_names = service_dep_map[key]
                s = name_service_map[key]
                for dep_name in dep_services_names:
                    dep_service = name_service_map[dep_name]
                    code, msg, d = app_relation_service.add_service_dependency(tenant, s,
                                                                               dep_service.service_id)
                    if code != 200:
                        logger.error("compose add service error {0}".format(msg))

    def __save_compose_relation(self, services, team_id, compose_id):
        service_id_list = [s.service_id for s in services]
        compose_relation_repo.bulk_create_compose_service_relation(service_id_list, team_id, compose_id)

    def __init_compose_service(self, tenant, user, service_cname, image, region):
        """
        初始化docker compose创建的应用默认数据
        """
        tenant_service = TenantServiceInfo()
        tenant_service.tenant_id = tenant.tenant_id
        tenant_service.service_id = make_uuid()
        tenant_service.service_cname = app_service.generate_service_cname(tenant, service_cname, region)
        tenant_service.service_alias = "gr" + tenant_service.service_id[-6:]
        tenant_service.creater = user.pk
        tenant_service.image = image
        tenant_service.service_region = region
        tenant_service.service_key = "0000"
        tenant_service.desc = "docker compose application"
        tenant_service.category = "app_publish"
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
        tenant_service.host_path = "/grdata/tenant/" + tenant.tenant_id + "/service/" + tenant_service.service_id
        tenant_service.code_from = "image_manual"
        tenant_service.language = "docker-compose"
        tenant_service.service_source = AppConstants.DOCKER_COMPOSE
        tenant_service.create_status = "creating"
        # 保存并返回
        tenant_service.save()
        return tenant_service

    def update_compose(self, group_id, compose_content):
        group_compose = self.get_group_compose_by_group_id(group_id)
        if not group_compose:
            return 404, "需要修改的对象不存在", None
        group_compose.compose_content = compose_content
        group_compose.save()
        return 200, "success", group_compose

    def get_compose_services(self, compose_id):
        compse_service_relations = compose_relation_repo.get_compose_service_relation_by_compose_id(compose_id)
        service_ids = [csr.service_id for csr in compse_service_relations]
        service_ids = list(service_ids)
        return service_repo.get_services_by_service_ids(*service_ids)

    def give_up_compose_create(self, tenant, group_id, compose_id):
        self.__delete_created_compose_info(tenant,compose_id)

        compose_repo.delete_group_compose_by_compose_id(compose_id)
        group_service.delete_group(group_id)

    def __delete_created_compose_info(self, tenant, compose_id):
        services = self.get_compose_services(compose_id)
        for s in services:
            # 彻底删除服务
            code, msg = app_manage_service.truncate_service(tenant, s)
            if code != 200:
                logger.error("delete compose services error {0}".format(msg))

        compose_relation_repo.delete_compose_service_relation_by_compose_id(compose_id)


    def wrap_compose_check_info(self, data):
        rt_info = dict()
        rt_info["check_status"] = data["check_status"]
        rt_info["error_infos"] = data["error_infos"]
        service_info_list = data["service_info"]
        compose_service_wrap_list = []
        if service_info_list:
            for service_info in service_info_list:
                compose_service_wrap_map = dict()
                service_attr_list = []
                if service_info["ports"]:
                    service_port_bean = {
                        "type": "ports",
                        "key": "端口信息",
                        "value": [str(port["container_port"]) + "(" + port["protocol"] + ")" for port in
                                  service_info["ports"]]
                    }
                    service_attr_list.append(service_port_bean)
                if service_info["volumes"]:
                    service_volume_bean = {
                        "type": "volumes",
                        "key": "持久化目录",
                        "value": [volume["volume_path"] + "(" + volume["volume_type"] + ")" for volume in
                                  service_info["volumes"]]
                    }
                    service_attr_list.append(service_volume_bean)
                if service_info["image"]:
                    service_image_bean = {
                        "type": "image",
                        "key": "镜像名称",
                        "value": service_info["image"]["name"] + ":" + service_info["image"]["tag"]
                    }
                    service_attr_list.append(service_image_bean)

                # service_name_bean = {
                #     "type": "service_name",
                #     "key": "服务名称",
                #     "value": service_info["image_alias"]
                # }
                # service_attr_list.append(service_name_bean)

                compose_service_wrap_map["service_cname"] = service_info["image_alias"]
                compose_service_wrap_map["service_info"] = service_attr_list

                compose_service_wrap_list.append(compose_service_wrap_map)

        rt_info["service_info"] = compose_service_wrap_list
        return rt_info

    def get_service_compose_id(self, service):
        return compose_relation_repo.get_compose_id_by_service_id(service.service_id)

compose_service = ComposeService()

# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
import json
import logging

from django.db import transaction

from console.constants import AppConstants
from console.exception.main import ServiceHandleException
from console.utils.oauth.oauth_types import get_oauth_instance
from console.repositories.oauth_repo import oauth_repo
from console.repositories.oauth_repo import oauth_user_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import service_endpoints_repo
from console.services.app_config import compile_env_service
from console.services.app_config import env_var_service
from console.services.app_config import port_service
from console.services.app_config import volume_service
from console.services.app_config import label_service
from console.services.common_services import common_services
from www.apiclient.regionapi import RegionInvokeApi

from www.models.main import Tenants
from console.enum.component_enum import ComponentType

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class AppCheckService(object):
    def __get_service_region_type(self, service_source):
        if service_source == AppConstants.SOURCE_CODE:
            return "sourcecode"
        elif service_source == AppConstants.DOCKER_RUN or service_source == AppConstants.DOCKER_IMAGE:
            return "docker-run"
        elif service_source == AppConstants.THIRD_PARTY:
            return "third-party-service"

    def check_service(self, tenant, service, is_again, user=None):
        # if service.create_status == "complete":
        #     return 409, "组件完成创建,请勿重复检测", None
        body = dict()
        body["tenant_id"] = tenant.tenant_id
        body["source_type"] = self.__get_service_region_type(service.service_source)
        source_body = ""
        service_source = service_source_repo.get_service_source(tenant.tenant_id, service.service_id)
        user_name = ""
        password = ""
        service.service_source = self.__get_service_source(service)
        if service_source:
            user_name = service_source.user_name
            password = service_source.password
        if service.service_source == AppConstants.SOURCE_CODE:
            if service.oauth_service_id:
                try:
                    oauth_service = oauth_repo.get_oauth_services_by_service_id(service.oauth_service_id)
                    oauth_user = oauth_user_repo.get_user_oauth_by_user_id(
                        service_id=service.oauth_service_id, user_id=user.user_id)
                except Exception as e:
                    logger.debug(e)
                    return 400, u"未找到oauth服务, 请检查该服务是否存在且属于开启状态", None
                if oauth_user is None:
                    return 400, u"未成功获取第三方用户信息", None

                try:
                    instance = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
                except Exception as e:
                    logger.debug(e)
                    return 400, u"未找到OAuth服务", None
                if not instance.is_git_oauth():
                    return 400, u"该OAuth服务不是代码仓库类型", None
                tenant = Tenants.objects.get(tenant_name=tenant.tenant_name)
                try:
                    service_code_clone_url = instance.get_clone_url(service.git_url)
                except Exception as e:
                    logger.debug(e)
                    return 400, u"Access Token 已过期", None
            else:
                service_code_clone_url = service.git_url

            sb = {
                "server_type": service.server_type,
                "repository_url": service_code_clone_url,
                "branch": service.code_version,
                "user": user_name,
                "password": password,
                "tenant_id": tenant.tenant_id
            }
            source_body = json.dumps(sb)
        elif service.service_source == AppConstants.DOCKER_RUN or service.service_source == AppConstants.DOCKER_IMAGE:
            source_body = service.docker_cmd
        elif service.service_source == AppConstants.THIRD_PARTY:
            # endpoints信息
            service_endpoints = service_endpoints_repo.get_service_endpoints_by_service_id(service.service_id)
            if service_endpoints:
                if service_endpoints.endpoints_type == "discovery":
                    source_body = service_endpoints.endpoints_info

        body["username"] = user_name
        body["password"] = password
        body["source_body"] = source_body
        res, body = region_api.service_source_check(service.service_region, tenant.tenant_name, body)
        bean = body["bean"]
        service.check_uuid = bean["check_uuid"]
        service.check_event_id = bean["event_id"]
        # 更新创建状态
        if not is_again:
            service.create_status = "checking"
        service.save()
        bean = dict()
        bean.update(service.to_dict())
        bean.update({"user_name": user_name, "password": password})
        bean.update(self.__wrap_check_service(service))
        return 200, u"success", bean

    def __get_service_source(self, service):
        if service.service_source:
            return service.service_source
        else:
            if service.category == "application":
                return AppConstants.SOURCE_CODE
            if service.category == "app_publish":
                return AppConstants.MARKET
            if service.language == "docker-compose":
                return AppConstants.DOCKER_COMPOSE
            if service.language == "docker-image":
                return AppConstants.DOCKER_IMAGE
            return AppConstants.DOCKER_RUN

    def __wrap_check_service(self, service):
        return {
            "service_code_from": service.code_from,
            "service_code_clone_url": service.git_url,
            "service_code_version": service.code_version,
        }

    def get_service_check_info(self, tenant, region, check_uuid):
        rt_msg = dict()
        try:
            res, body = region_api.get_service_check_info(region, tenant.tenant_name, check_uuid)
            bean = body["bean"]
            if not bean["check_status"]:
                bean["check_status"] = "checking"
            bean["check_status"] = bean["check_status"].lower()
            rt_msg = bean
        except region_api.CallApiError as e:
            rt_msg["error_infos"] = [{
                "error_type": "api invoke error",
                "solve_advice": "重新尝试",
                "error_info": "{}".format(e.message)
            }]
            rt_msg["check_status"] = "failure"
            rt_msg["service_info"] = []
            logger.exception(e)

        return 200, "success", rt_msg

    def update_service_check_info(self, tenant, service, data):
        if data["check_status"] != "success":
            return
        sid = None
        try:
            sid = transaction.savepoint()
            # 删除原有build类型env，保存新检测build类型env
            save_code, save_msg = self.upgrade_service_env_info(tenant, service, data)
            if save_code != 200:
                logger.error('upgrade service env  by code check failure {0}'.format(save_msg))
            # 重新检测后对端口做加法
            save_code, save_msg = self.add_service_check_port(tenant, service, data)
            if save_code != 200:
                logger.error('upgrade service port  by code check failure {0}'.format(save_msg))
            lang = data["service_info"][0]["language"]
            if lang == "dockerfile":
                service.cmd = ""
            elif service.service_source == AppConstants.SOURCE_CODE:
                service.cmd = "start web"
            service.language = lang
            service.save()
            transaction.savepoint_commit(sid)
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            raise ServiceHandleException(
                status_code=400, msg="handle check service code info failure", msg_show="处理检测结果失败")

    def save_service_check_info(self, tenant, service, data):
        # 检测成功将信息存储
        if data["check_status"] == "success":
            if service.create_status == "checking":
                logger.debug("checking service info install,save info into database")
                service_info_list = data["service_info"]
                sid = None
                try:
                    sid = transaction.savepoint()
                    code, msg = self.save_service_info(tenant, service, service_info_list[0])
                    if code != 200:
                        return code, msg
                    # save service info, checked 表示检测完成
                    service.create_status = "checked"
                    service.save()
                    transaction.savepoint_commit(sid)
                except Exception as e:
                    if sid:
                        transaction.savepoint_rollback(sid)
                    logger.exception(e)
                    return 400, "解析并存储组件属性发生错误"
        return 200, "success"

    def upgrade_service_env_info(self, tenant, service, data):
        # 更新构建时环境变量
        if data["check_status"] == "success":
            service_info_list = data["service_info"]
            code, msg = self.upgrade_service_info(tenant, service, service_info_list[0])
            if code != 200:
                return code, msg
        return 200, "success"

    def add_service_check_port(self, tenant, service, data):
        # 更新构建时环境变量
        if data["check_status"] == "success":
            service_info_list = data["service_info"]
            code, msg = self.add_check_ports(tenant, service, service_info_list[0])
            if code != 200:
                return code, msg
        return 200, "success"

    def add_check_ports(self, tenant, service, check_service_info):
        service_info = check_service_info
        ports = service_info.get("ports", None)
        if not ports:
            return 200, "success"
        # 更新构建时环境变量
        code, msg = self.__save_check_port(tenant, service, ports)
        if code != 200:
            return code, msg
        return code, msg

    def upgrade_service_info(self, tenant, service, check_service_info):
        service_info = check_service_info
        envs = service_info["envs"]
        # 更新构建时环境变量
        code, msg = self.__upgrade_env(tenant, service, envs)
        if code != 200:
            return code, msg
        return code, msg

    def __save_check_port(self, tenant, service, ports):
        if ports:
            for port in ports:
                code, msg, port_data = port_service.add_service_port(
                    tenant, service, int(port["container_port"]), port["protocol"],
                    service.service_alias.upper() + str(port["container_port"]))
                if code != 200:
                    logger.error("service.check", "save service check info port error {0}".format(msg))
                    # return code, msg
        return 200, "success"

    def __upgrade_env(self, tenant, service, envs):
        if envs:
            # 删除原有的build类型环境变量
            env_var_service.delete_service_build_env(tenant, service)
            SENSITIVE_ENV_NAMES = (
                'TENANT_ID', 'SERVICE_ID', 'TENANT_NAME', 'SERVICE_NAME', 'SERVICE_VERSION', 'MEMORY_SIZE',
                'SERVICE_EXTEND_METHOD', 'SLUG_URL', 'DEPEND_SERVICE', 'REVERSE_DEPEND_SERVICE', 'POD_ORDER', 'PATH',
                'PORT', 'POD_NET_IP', 'LOG_MATCH')
            for env in envs:
                if env["name"] in SENSITIVE_ENV_NAMES:
                    continue
                # BUILD_开头的env保存为build类型的环境变量
                elif env["name"].startswith("BUILD_"):
                    code, msg, data = env_var_service.add_service_build_env_var(
                        tenant, service, 0, env["name"], env["name"], env["value"], True)
                    if code != 200:
                        logger.error("service.check", "save service check info env error {0}".format(msg))
        return 200, "success"

    def save_service_info(self, tenant, service, check_service_info):
        service_info = check_service_info
        service.language = service_info.get("language", "")
        memory = service_info.get("memory", 128)
        min_cpu = common_services.calculate_cpu(service.service_region, memory)
        service.min_memory = memory - memory % 32
        service.min_cpu = min_cpu
        # Set the deployment type based on the test results
        logger.debug("save svc extend_method {0}".format(service_info.get("service_type",
                                                         ComponentType.stateless_multiple.value)))
        service.extend_method = service_info.get("service_type", ComponentType.stateless_multiple.value)
        args = service_info.get("args", None)
        if args:
            service.cmd = " ".join(args)
        else:
            service.cmd = ""
        image = service_info.get("image", None)
        if image:
            service_image = image["name"] + ":" + image["tag"]
            service.image = service_image
            service.version = image["tag"]

        envs = service_info.get("envs", None)
        ports = service_info.get("ports", None)
        volumes = service_info.get("volumes", None)
        service_runtime_os = service_info.get("os", "linux")
        if service_runtime_os == "windows":
            label_service.set_service_os_label(tenant, service, service_runtime_os)
        code, msg = self.__save_compile_env(tenant, service, service.language)
        if code != 200:
            return code, msg

        # 先保存env,再保存端口，因为端口需要处理env
        code, msg = self.__save_env(tenant, service, envs)
        if code != 200:
            return code, msg
        code, msg = self.__save_port(tenant, service, ports)
        if code != 200:
            return code, msg

        code, msg = self.__save_volume(tenant, service, volumes)
        if code != 200:
            return code, msg
        return 200, "success"

    def __save_compile_env(self, tenant, service, language):
        # 删除原有 compile env
        logger.debug("save tenant {0} compile service env {1}".format(tenant.tenant_name, service.service_cname))
        compile_env_service.delete_service_compile_env(service)
        if not language:
            language = False
        check_dependency = {
            "language": language,
        }
        check_dependency_json = json.dumps(check_dependency)
        # 添加默认编译环境
        user_dependency = compile_env_service.get_service_default_env_by_language(language)
        user_dependency_json = json.dumps(user_dependency)
        compile_env_service.save_compile_env(service, language, check_dependency_json, user_dependency_json)
        return 200, "success"

    def __save_env(self, tenant, service, envs):
        if envs:
            # 删除原有env
            env_var_service.delete_service_env(tenant, service)
            # 删除原有的build类型环境变量
            env_var_service.delete_service_build_env(tenant, service)
            SENSITIVE_ENV_NAMES = (
                'TENANT_ID', 'SERVICE_ID', 'TENANT_NAME', 'SERVICE_NAME', 'SERVICE_VERSION', 'MEMORY_SIZE',
                'SERVICE_EXTEND_METHOD', 'SLUG_URL', 'DEPEND_SERVICE', 'REVERSE_DEPEND_SERVICE', 'POD_ORDER', 'PATH',
                'POD_NET_IP')
            for env in envs:
                if env["name"] in SENSITIVE_ENV_NAMES:
                    continue
                # BUILD_开头的env保存为build类型的环境变量
                elif env["name"].startswith("BUILD_"):
                    code, msg, data = env_var_service.add_service_build_env_var(
                        tenant, service, 0, env["name"], env["name"], env["value"], True)
                    if code != 200:
                        logger.error("service.check", "save service check info env error {0}".format(msg))
                else:
                    code, msg, env_data = env_var_service.add_service_env_var(
                        tenant, service, 0, env["name"], env["name"], env["value"], True, "inner")
                    if code != 200:
                        logger.error("service.check", "save service check info env error {0}".format(msg))
                        # return code, msg
        return 200, "success"

    def __save_port(self, tenant, service, ports):
        if ports:
            # 删除原有port
            port_service.delete_service_port(tenant, service)
            for port in ports:
                code, msg, port_data = port_service.add_service_port(
                    tenant, service, int(port["container_port"]), port["protocol"],
                    service.service_alias.upper() + str(port["container_port"]))
                if code != 200:
                    logger.error("service.check", "save service check info port error {0}".format(msg))
                    # return code, msg
        else:
            if service.service_source == AppConstants.SOURCE_CODE:
                port_service.delete_service_port(tenant, service)
                # 添加默认5000端口
                port_service.add_service_port(tenant, service, 5000, "http",
                                              service.service_alias.upper() + str(5000), False, True)
        return 200, "success"

    def __save_volume(self, tenant, service, volumes):
        if volumes:
            volume_service.delete_service_volumes(service)
            index = 0
            for volume in volumes:
                index += 1
                volume_name = service.service_alias.upper() + "_" + str(index)
                if "file_content" in volume.keys():
                    volume_service.add_service_volume(
                        tenant, service, volume["volume_path"], volume["volume_type"], volume_name, volume["file_content"])
                else:
                    settings = {}
                    settings["volume_capacity"] = volume["volume_capacity"]
                    volume_service.add_service_volume(
                        tenant, service, volume["volume_path"], volume["volume_type"], volume_name, None, settings)
        return 200, "success"

    def wrap_service_check_info(self, service, data):
        rt_info = dict()
        rt_info["check_status"] = data["check_status"]
        rt_info["error_infos"] = data["error_infos"]
        if data["service_info"] and len(data["service_info"]) > 1:
            rt_info["is_multi"] = True
        else:
            rt_info["is_multi"] = False
        service_info_list = data["service_info"]
        service_list = []
        if service_info_list:
            service_info = service_info_list[0]
            service_list = self.wrap_check_info(service, service_info)

            # service_middle_ware_bean = {}
            # sub_bean_list.append(service_middle_ware_bean)
            # service_list.append(sub_bean_list)

        rt_info["service_info"] = service_list
        return rt_info

    def wrap_check_info(self, service, service_info):
        service_attr_list = []
        if service_info["ports"]:
            service_port_bean = {
                "type": "ports",
                "key": "端口信息",
                "value": [str(port["container_port"]) + "(" + port["protocol"] + ")" for port in service_info["ports"]]
            }
            service_attr_list.append(service_port_bean)
        if service_info["volumes"]:
            service_volume_bean = {"type": "volumes", "key": "持久化目录", "value": [
                volume["volume_path"] + "(" + volume["volume_type"] + ")" for volume in service_info["volumes"]]}
            service_attr_list.append(service_volume_bean)
        service_code_from = {}
        service_language = {}
        if service.service_source == AppConstants.SOURCE_CODE:
            service_code_from = {
                "type": "source_from",
                "key": "源码信息",
                "value": "{0}  branch: {1}".format(service.git_url, service.code_version)
            }
            service_language = {"type": "language", "key": "代码语言", "value": service_info["language"]}
        elif service.service_source == AppConstants.DOCKER_RUN or service.service_source == AppConstants.DOCKER_IMAGE:
            service_code_from = {"type": "source_from", "key": "镜像名称", "value": service.image}
            if service.cmd:
                service_attr_list.append({"type": "source_from", "key": "镜像启动命令", "value": service.cmd})
        if service_language:
            service_attr_list.append(service_language)
        if service_code_from:
            service_attr_list.append(service_code_from)
        return service_attr_list


app_check_service = AppCheckService()

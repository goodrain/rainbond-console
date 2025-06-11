# -*- coding: utf8 -*-
"""
  Created on 18/1/24.
"""
import datetime
import json
import logging

from console.cloud.services import check_account_quota
from console.constants import AppConstants
from console.enum.component_enum import ComponentType, is_singleton, is_state
from console.exception.main import AbortRequest, ServiceHandleException
from console.models.main import ServiceShareRecordEvent
from console.repositories.app import (delete_service_repo, recycle_bin_repo, relation_recycle_bin_repo, service_repo,
                                      service_source_repo)

from console.repositories.app_config import (auth_repo, dep_relation_repo, domain_repo, env_var_repo,
                                             extend_repo, mnt_repo, port_repo, tcp_domain, volume_repo, compile_env_repo)
from console.repositories.app_config_group import app_config_group_service_repo
from console.repositories.compose_repo import compose_relation_repo
from console.repositories.event_repo import event_repo
from console.repositories.group import (group_service_relation_repo, tenant_service_group_repo, group_repo)
from console.repositories.label_repo import service_label_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.oauth_repo import oauth_repo, oauth_user_repo
from console.repositories.plugin import app_plugin_relation_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.region_app import region_app_repo
from console.repositories.region_repo import region_repo
from console.repositories.service_backup_repo import service_backup_repo
from console.repositories.share_repo import share_repo
from console.repositories.team_repo import team_repo
from console.repositories.virtual_machine import vm_repo
from console.services.app import app_market_service, app_service
from console.services.app_actions.app_log import AppEventService
from console.services.app_actions.exception import ErrVersionAlreadyExists
from console.services.app_config import (AppEnvVarService, AppMntService, AppPortService, AppServiceRelationService,
                                         AppVolumeService)
from console.services.app_config.component_graph import component_graph_service
from console.services.app_config.service_monitor import service_monitor_repo
from console.services.exception import ErrChangeServiceType
from console.services.group_service import group_service
from console.services.service_services import base_service
from console.utils import slug_util
from console.utils.oauth.base.exception import NoAccessKeyErr
from console.utils.oauth.oauth_types import (NoSupportOAuthType, get_oauth_instance)
from django.conf import settings
from django.db import transaction
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroupRelation
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid

event_service = AppEventService()
region_api = RegionInvokeApi()
logger = logging.getLogger("default")
baseService = BaseTenantService()
relation_service = AppServiceRelationService()
env_var_service = AppEnvVarService()
port_service = AppPortService()
volume_service = AppVolumeService()
app_service_relation = AppServiceRelationService()
mnt_service = AppMntService()


class AppManageBase(object):
    def __init__(self):
        self.MODULES = settings.MODULES
        self.START = "restart"
        self.STOP = "stop"
        self.RESTART = "reboot"
        self.DELETE = "delete"
        self.DEPLOY = "deploy"
        self.UPGRADE = "upgrade"
        self.ROLLBACK = "callback"
        self.VERTICAL_UPGRADE = "VerticalUpgrade"
        self.HORIZONTAL_UPGRADE = "HorizontalUpgrade"
        self.TRUNCATE = "truncate"
        self.ResourceOperationStart = "start"
        self.ResourceOperationReStart = "restart"
        self.ResourceOperationDeploy = "deploy"
        self.ResourceOperationUPGRADE = "upgrade"
        self.ResourceOperationROLLBACK = "rollback"
        self.ResourceOperationVerticalUpgrade = "vertical-upgrade"
        self.ResourceOperationHorizontalUpgrade = "horizontal-upgrade"

    def cur_service_memory(self, tenant, cur_service):
        """查询当前组件占用的内存"""
        memory = 0
        try:
            body = region_api.check_service_status(cur_service.service_region, tenant.tenant_name, cur_service.service_alias,
                                                   tenant.enterprise_id)
            status = body["bean"]["cur_status"]
            # 占用内存的状态
            occupy_memory_status = (
                "starting",
                "running",
            )
            if status not in occupy_memory_status:
                memory = cur_service.min_node * cur_service.min_memory
        except Exception:
            pass
        return memory




class AppManageService(AppManageBase):
    def start(self, tenant, service, user, oauth_instance):
        if service.service_source != "third_party" and not check_account_quota(tenant.creater, service.service_region,
                                                                               self.ResourceOperationStart):
            raise ServiceHandleException(error_code=20002, msg="not enough quota")
        if service.create_status == "complete":
            body = dict()
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.start_service(service.service_region, tenant.tenant_name, service.service_alias, body)
                logger.debug("user {0} start app !".format(user.nick_name))
            except region_api.CallApiError as e:
                logger.exception(e)
                return 507, "组件异常"
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, "操作过于频繁，请稍后再试"
        return 200, "操作成功"

    def pause(self, tenant, service, user):
        if service.create_status == "complete":
            body = dict()
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.pause_service(service.service_region, tenant.tenant_name, service.service_alias, body)
                logger.debug("user {0} start app !".format(user.nick_name))
            except region_api.CallApiError as e:
                logger.exception(e)
                return 507, "组件异常"
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, "操作过于频繁，请稍后再试"
        return 200, "操作成功"

    def un_pause(self, tenant, service, user):
        if service.create_status == "complete":
            body = dict()
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.un_pause_service(service.service_region, tenant.tenant_name, service.service_alias, body)
                logger.debug("user {0} start app !".format(user.nick_name))
            except region_api.CallApiError as e:
                logger.exception(e)
                return 507, "组件异常"
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, "操作过于频繁，请稍后再试"
        return 200, "操作成功"

    def stop(self, tenant, service, user):
        if service.create_status == "complete":
            body = dict()
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.stop_service(service.service_region, tenant.tenant_name, service.service_alias, body)
                logger.debug("user {0} stop app !".format(user.nick_name))
            except region_api.CallApiError as e:
                logger.exception(e)
                raise ServiceHandleException(msg_show="从集群关闭组件受阻，请稍后重试", msg="check console log", status_code=500)
            except region_api.CallApiFrequentError:
                raise ServiceHandleException(msg_show="操作过于频繁，请稍后重试", msg="wait a moment please", status_code=409)

    def restart(self, tenant, service, user, oauth_instance):
        if service.create_status == "complete":
            if service.service_source != "third_party" and not check_account_quota(tenant.creater, service.service_region, self.ResourceOperationReStart):
                raise ServiceHandleException(error_code=20002, msg="not enough quota")
            body = dict()
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.restart_service(service.service_region, tenant.tenant_name, service.service_alias, body)
                logger.debug("user {0} retart app !".format(user.nick_name))
            except region_api.CallApiError as e:
                logger.exception(e)
                return 507, "组件异常"
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, "操作过于频繁，请稍后再试"
        return 200, "操作成功"

    def deploy(self, tenant, service, user, oauth_instance=None, service_copy_path=None):
        res, body = region_api.get_cluster_nodes_arch(service.service_region)
        chaos_arch = list(set(body.get("list")))
        service.arch = service.arch if service.arch else "amd64"
        if service.arch not in chaos_arch:
            raise AbortRequest("app arch does not match build node arch", "应用架构与构建节点架构不匹配", status_code=404, error_code=404)
        if service.service_source != "third_party" and not check_account_quota(tenant.creater, service.service_region, self.ResourceOperationDeploy):
            raise ServiceHandleException(msg="not enough quota", error_code=20002)
        body = dict()
        # 默认更新升级
        body["action"] = "deploy"
        if service.build_upgrade:
            body["action"] = "upgrade"
        body["envs"] = env_var_repo.get_build_envs(tenant.tenant_id, service.service_id)
        kind = self.__get_service_kind(service)
        body["kind"] = kind
        body["arch"] = service.arch
        body["operator"] = str(user.nick_name)
        body["configs"] = {}
        if service_copy_path != {}:
            body["configs"] = service_copy_path
        body["service_id"] = service.service_id
        # source type parameter
        if kind == "build_from_source_code" or kind == "source":
            if service.oauth_service_id:
                try:
                    oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service.oauth_service_id)
                    oauth_user = oauth_user_repo.get_user_oauth_by_user_id(
                        service_id=service.oauth_service_id, user_id=user.user_id)
                except Exception as e:
                    logger.exception(e)
                    return 400, "该组件构建源基于Oauth对接的代码仓库，Oauth服务可能已被删除，请在构建源中重新配置", ""
                try:
                    instance = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
                except NoSupportOAuthType as e:
                    logger.debug(e)
                    return 400, "该组件构建源代码仓库类型已不支持", ""
                if not instance.is_git_oauth():
                    return 400, "该组件构建源代码仓库类型不正确", ""
                try:
                    git_url = instance.get_clone_url(service.git_url)
                except NoAccessKeyErr:
                    return 400, "该组件代码仓库认证信息已过期，请重新认证", ""
                body["code_info"] = {
                    "repo_url": git_url,
                    "branch": service.code_version,
                    "server_type": service.server_type,
                    "lang": service.language,
                    "cmd": service.cmd,
                }
            else:
                body["code_info"] = {
                    "repo_url": service.git_url,
                    "branch": service.code_version,
                    "server_type": service.server_type,
                    "lang": service.language,
                    "cmd": service.cmd,
                }
        if kind == "build_from_image" or kind == "build_from_market_image" or kind == "build_from_vm":
            body["image_info"] = {
                "image_url": service.image,
                "cmd": service.cmd,
                "vm_image_source": service.git_url,
            }
        service_source = service_source_repo.get_service_source(service.tenant_id, service.service_id)
        if service_source and (service_source.user_name or service_source.password):
            if body.get("code_info", None):
                body["code_info"]["user"] = service_source.user_name
                body["code_info"]["password"] = service_source.password
            if body.get("image_info", None):
                body["image_info"]["user"] = service_source.user_name
                body["image_info"]["password"] = service_source.password
        if service_source and service_source.extend_info and kind == "build_from_market_image":
            extend_info = json.loads(service_source.extend_info)
            if service.is_slug():  # abandoned
                body["slug_info"] = extend_info
            else:
                hub_user = extend_info.get("hub_user", None)
                hub_password = extend_info.get("hub_password", None)
                if hub_user or hub_password:
                    if body.get("image_info", None):
                        body["image_info"]["user"] = hub_user
                        body["image_info"]["password"] = hub_password
        else:
            logger.warning("service_source is not exist for service {0}".format(service.service_id))
        try:
            body['operator'] = user.nick_name
            re = region_api.build_service(service.service_region, tenant.tenant_name, service.service_alias, body)
            if re and re.get("bean") and re.get("bean").get("status") != "success":
                logger.error("deploy component failure {}".format(re))
                return 507, "构建异常", ""
            event_id = re["bean"].get("event_id", "")
        except region_api.CallApiError as e:
            if e.status == 400:
                logger.warning("failed to deploy service: {}".format(e))
                raise ErrVersionAlreadyExists()
            logger.exception(e)
            return 507, "构建异常", ""
        except region_api.CallApiFrequentError as e:
            logger.exception(e)
            return 409, "操作过于频繁，请稍后再试", ""
        return 200, "操作成功", event_id

    def __delete_envs(self, tenant, service):
        service_envs = env_var_repo.get_service_env(tenant.tenant_id, service.service_id)
        if service_envs:
            for env in service_envs:
                env_var_service.delete_env_by_attr_name(tenant, service, env.attr_name)
        return 200, "success"

    def __delete_volume(self, tenant, service):
        service_volumes = volume_repo.get_service_volumes(service.service_id)
        if service_volumes:
            for volume in service_volumes:
                code, msg, volume = volume_service.delete_service_volume_by_id(tenant, service, int(volume.ID))
                if code != 200:
                    return 400, msg
        return 200, "success"

    def __save_extend_info(self, service, extend_info):
        if not extend_info:
            return 200, "success"
        params = {
            "service_key": service.service_key,
            "app_version": service.version,
            "min_node": extend_info["min_node"],
            "max_node": extend_info["max_node"],
            "step_node": extend_info["step_node"],
            "min_memory": extend_info["min_memory"],
            "max_memory": extend_info["max_memory"],
            "step_memory": extend_info["step_memory"],
            "is_restart": extend_info["is_restart"]
        }
        extend_repo.create_extend_method(**params)

    def __save_volume(self, tenant, service, volumes):
        if volumes:
            for volume in volumes:
                service_volume = volume_repo.get_service_volume_by_name(service.service_id, volume["volume_name"])
                if service_volume:
                    continue
                service_volume = volume_repo.get_service_volume_by_path(service.service_id, volume["volume_path"])
                if service_volume:
                    continue
                file_content = volume.get("file_content", None)
                settings = {}
                settings["volume_capacity"] = volume["volume_capacity"]
                volume_service.add_service_volume(
                    tenant,
                    service,
                    volume["volume_path"],
                    volume_type=volume["volume_type"],
                    volume_name=volume["volume_name"],
                    file_content=file_content,
                    settings=settings)

    def __save_env(self, tenant, service, inner_envs, outer_envs):
        if not inner_envs and not outer_envs:
            return 200, "success"
        for env in inner_envs:
            exist = env_var_repo.get_by_attr_name_and_scope(
                tenant_id=tenant.tenant_id, service_id=service.service_id, attr_name=env["attr_name"], scope="inner")
            if exist:
                continue
            code, msg, env_data = env_var_service. \
                add_service_env_var(tenant, service, 0, env["name"], env["attr_name"],
                                    env.get("attr_value"), env["is_change"], scope="inner")
            if code != 200:
                logger.error("save market app env error {0}".format(msg))
                return code, msg
        for env in outer_envs:
            exist = env_var_repo.get_by_attr_name_and_scope(
                tenant_id=tenant.tenant_id, service_id=service.service_id, attr_name=env["attr_name"], scope="outer")
            if exist:
                continue
            container_port = env.get("container_port", 0)
            if container_port == 0:
                if env.get("attr_value") == "**None**":
                    env["attr_value"] = service.service_id[:8]
                code, msg, env_data = env_var_service. \
                    add_service_env_var(tenant, service, container_port,
                                        env["name"], env["attr_name"],
                                        env.get("attr_value"), env["is_change"], "outer")
                if code != 200:
                    logger.error("save market app env error {0}".format(msg))
                    return code, msg
        return 200, "success"

    def __save_port(self, tenant, service, ports):
        if not ports:
            return 200, "success"
        for port in ports:
            mapping_port = int(port["container_port"])
            env_prefix = port["port_alias"].upper() if bool(port["port_alias"]) else service.service_key.upper()
            service_port = port_repo.get_service_port_by_port(tenant.tenant_id, service.service_id, int(port["container_port"]))
            if service_port:
                if port["is_inner_service"]:
                    code, msg, data = env_var_service.add_service_env_var(
                        tenant,
                        service,
                        int(port["container_port"]),
                        "连接地址",
                        env_prefix + "_HOST",
                        "127.0.0.1",
                        False,
                        scope="outer")
                    if code != 200 and code != 412:
                        return code, msg
                    code, msg, data = env_var_service.add_service_env_var(
                        tenant,
                        service,
                        int(port["container_port"]),
                        "端口",
                        env_prefix + "_PORT",
                        mapping_port,
                        False,
                        scope="outer")
                    if code != 200 and code != 412:
                        return code, msg
                continue

            code, msg, port_data = port_service.add_service_port(tenant, service, int(port["container_port"]), port["protocol"],
                                                                 port["port_alias"], port["is_inner_service"],
                                                                 port["is_outer_service"])
            if code != 200:
                logger.error("save market app port error: {}".format(msg))
                return code, msg
        return 200, "success"

    def upgrade(self, tenant, service, user, committer_name=None, oauth_instance=None):
        if service.service_source != "third_party" and not check_account_quota(tenant.creater, service.service_region, self.ResourceOperationUPGRADE):
            raise ServiceHandleException(error_code=20002, msg="not enough quota")
        body = dict()
        body["service_id"] = service.service_id
        body["operator"] = str(user.nick_name)
        try:
            body = region_api.upgrade_service(service.service_region, tenant.tenant_name, service.service_alias, body)
            event_id = body["bean"].get("event_id", "")
            return 200, "操作成功", event_id
        except region_api.CallApiError as e:
            logger.exception(e)
            return 507, "更新异常", ""
        except region_api.CallApiFrequentError as e:
            logger.exception(e)
            return 409, "操作过于频繁，请稍后再试", ""

    def __get_service_kind(self, service):
        """获取组件种类，兼容老的逻辑"""
        if service.service_source:
            if service.service_source == AppConstants.SOURCE_CODE \
                    or service.service_source == AppConstants.PACKAGE_BUILD:
                return "build_from_source_code"
            elif service.service_source == AppConstants.DOCKER_RUN \
                    or service.service_source == AppConstants.DOCKER_COMPOSE \
                    or service.service_source == AppConstants.DOCKER_IMAGE:
                return "build_from_image"
            elif service.service_source == AppConstants.MARKET:
                if slug_util.is_slug(service.image, service.language):
                    return "build_from_market_slug"
                else:
                    return "build_from_market_image"
            elif service.service_source == AppConstants.VM_RUN:
                return "build_from_vm"
        else:
            kind = "build_from_image"
            if service.category == "application":
                kind = "build_from_source_code"
            if service.category == "app_publish":
                kind = "build_from_market_image"
                if slug_util.is_slug(service.image, service.language):
                    kind = "build_from_market_slug"
                if service.service_key == "0000":
                    kind = "build_from_image"
            return kind

    def roll_back(self, tenant, service, user, deploy_version, upgrade_or_rollback):
        if service.create_status == "complete":
            res, data = region_api.get_service_build_version_by_id(service.service_region, tenant.tenant_name,
                                                                   service.service_alias, deploy_version)
            is_version_exist = data['bean']['status']
            if not is_version_exist:
                return 404, "当前版本可能已被系统清理或删除"
            body = dict()
            body["operator"] = str(user.nick_name)
            body["upgrade_version"] = deploy_version
            body["service_id"] = service.service_id
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.rollback(service.service_region, tenant.tenant_name, service.service_alias, body)
            except region_api.CallApiError as e:
                logger.exception(e)
                return 507, "组件异常"
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, "操作过于频繁，请稍后再试"
        return 200, "操作成功"

    @transaction.atomic()
    def batch_action(self, region_name, tenant, user, action, service_ids, move_group_id, oauth_instance):
        services = service_repo.get_services_by_service_ids(service_ids)
        code = 500
        msg = "系统异常"
        fail_service_name = []
        for service in services:
            try:
                if action == "start":
                    self.start(tenant, service, user, oauth_instance=oauth_instance)
                elif action == "stop":
                    self.stop(tenant, service, user)
                elif action == "restart" and service.service_source != "third_party":
                    self.restart(tenant, service, user, oauth_instance=oauth_instance)
                elif action == "move":
                    group_service.sync_app_services(tenant, region_name, move_group_id)
                    self.move(service, move_group_id)
                elif action == "deploy" and service.service_source != "third_party" and service.service_source != "vm_run":
                    res, body = region_api.get_cluster_nodes_arch(region_name)
                    chaos_arch = list(set(body.get("list")))
                    service.arch = service.arch if service.arch else "amd64"
                    if service.arch not in chaos_arch:
                        raise AbortRequest(
                            "app arch does not match build node arch", "应用架构与构建节点架构不匹配", status_code=404, error_code=404)
                    self.deploy(tenant, service, user, oauth_instance=oauth_instance)
                elif action == "upgrade" and service.service_source != "third_party" and service.service_source != "vm_run":
                    self.upgrade(tenant, service, user, oauth_instance=oauth_instance)
                code = 200
                msg = "success"
                service.update_time = datetime.datetime.now()
                service.save()
            except ServiceHandleException as e:
                raise e
            except Exception as e:
                fail_service_name.append(service.service_cname)
                logger.exception(e)
        logger.debug("fail service names {0}".format(fail_service_name))
        return code, msg, services

    # 5.1新版批量操作（启动，关闭，构建）
    def batch_operations(self, tenant, region_name, user, action, service_ids, oauth_instance=None):
        services = service_repo.get_services_by_service_ids(service_ids)
        if not services:
            return
        # 获取所有组件信息
        body = dict()
        data = ''
        code = 200
        if action == "start":
            code, data = self.start_services_info(body, services, tenant, user, oauth_instance, region_name=region_name)
        elif action == "stop":
            code, data = self.stop_services_info(body, services, tenant, user)
        elif action == "upgrade":
            code, data = self.upgrade_services_info(body, services, tenant, user, oauth_instance, region_name=region_name)
        elif action == "deploy":
            code, data = self.deploy_services_info(body, services, tenant, user, oauth_instance, region_name=region_name)
        if code != 200:
            raise AbortRequest(415, "failed to get component", "组件信息获取失败")
        # 获取数据中心信息
        data['operator'] = user.nick_name
        try:
            _, body = region_api.batch_operation_service(region_name, tenant.tenant_name, data)
            events = body["bean"]["batch_result"]
            return events
        except region_api.CallApiError as e:
            logger.exception(e)
            raise AbortRequest(500, "failed to request region api", "数据中心操作失败")

    def start_services_info(self, body, services, tenant, user, oauth_instance, region_name):
        body["operation"] = "start"
        start_infos_list = []
        body["start_infos"] = start_infos_list
        # request_memory = base_service.get_not_run_services_request_memory(tenant, services)
        if not check_account_quota(tenant.creater, region_name, self.ResourceOperationStart):
            raise ServiceHandleException(error_code=20002, msg="not enough quota")
        for service in services:
            if service.service_source == "":
                continue
            service_dict = dict()
            if service.create_status == "complete":
                service_dict["service_id"] = service.service_id
                start_infos_list.append(service_dict)
        return 200, body

    def stop_services_info(self, body, services, tenant, user):
        body["operation"] = "stop"
        stop_infos_list = []
        body["stop_infos"] = stop_infos_list
        for service in services:
            service_dict = dict()
            if service.create_status == "complete":
                service_dict["service_id"] = service.service_id
                stop_infos_list.append(service_dict)
        return 200, body

    def upgrade_services_info(self, body, services, tenant, user, oauth_instance, region_name):
        body["operation"] = "upgrade"
        upgrade_infos_list = []
        body["upgrade_infos"] = upgrade_infos_list
        # request_memory = base_service.get_not_run_services_request_memory(tenant, services)
        if not check_account_quota(tenant.creater, region_name, self.ResourceOperationUPGRADE):
            raise ServiceHandleException(error_code=20002, msg="not enough quota")
        for service in services:
            service_dict = dict()
            if service.create_status == "complete":
                service_dict["service_id"] = service.service_id
                upgrade_infos_list.append(service_dict)
        return 200, body

    def deploy_services_info(self, body, services, tenant, user, oauth_instance, template_apps=None, upgrade=True, region_name=None):
        body["operation"] = "build"
        deploy_infos_list = []
        body["build_infos"] = deploy_infos_list
        # request_memory = base_service.get_not_run_services_request_memory(tenant, services)
        if not check_account_quota(tenant.creater, region_name, self.ResourceOperationDeploy):
            raise ServiceHandleException(error_code=20002, msg="not enough quota")
        app_version_cache = {}
        for service in services:
            service_dict = dict()
            service_dict["service_id"] = service.service_id
            service_dict["action"] = 'deploy'
            if service.build_upgrade:
                service_dict["action"] = 'upgrade'
            envs = env_var_repo.get_build_envs(tenant.tenant_id, service.service_id)
            service_dict["envs"] = envs
            kind = self.__get_service_kind(service)
            service_dict["kind"] = kind
            service_source = service_source_repo.get_service_source(service.tenant_id, service.service_id)
            clone_url = service.git_url
            service_dict["arch"] = service.arch
            # 源码
            if kind == "build_from_source_code" or kind == "source":
                source_code = dict()
                service_dict["code_info"] = source_code
                source_code["repo_url"] = clone_url
                source_code["branch"] = service.code_version
                source_code["server_type"] = service.server_type
                source_code["lang"] = service.language
                source_code["cmd"] = service.cmd
                if service.oauth_service_id:
                    try:
                        oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service.oauth_service_id)
                        oauth_user = oauth_user_repo.get_user_oauth_by_user_id(
                            service_id=service.oauth_service_id, user_id=user.user_id)
                    except Exception as e:
                        logger.debug(e)
                        continue
                    try:
                        instance = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
                    except Exception as e:
                        logger.debug(e)
                        continue
                    if not instance.is_git_oauth():
                        continue
                    try:
                        git_url = instance.get_clone_url(service.git_url)
                    except NoAccessKeyErr as e:
                        logger.exception(e)
                        git_url = service.git_url
                    source_code["repo_url"] = git_url
                elif service_source and (service_source.user_name or service_source.password):
                    source_code["user"] = service_source.user_name
                    source_code["password"] = service_source.password
            # 镜像
            elif kind == "build_from_image":
                source_image = dict()
                source_image["image_url"] = service.image
                source_image["cmd"] = service.cmd
                if service_source and (service_source.user_name or service_source.password):
                    source_image["user"] = service_source.user_name
                    source_image["password"] = service_source.password
                service_dict["image_info"] = source_image

            # local registry or rainstore
            elif service.service_source == "market":
                try:
                    if service_source:
                        apps_template = template_apps
                        if not apps_template:
                            old_extent_info = json.loads(service_source.extend_info)
                            app_version = None
                            # install from cloud
                            install_from_cloud = service_source.is_install_from_cloud()
                            if app_version_cache.get(service_source.group_key + service_source.version):
                                apps_template = app_version_cache.get(service_source.group_key + service_source.version)
                            else:
                                if install_from_cloud:
                                    # TODO:Skip the subcontract structure to avoid loop introduction
                                    market_name = old_extent_info.get("market_name")
                                    market = app_market_service.get_app_market_by_name(
                                        tenant.enterprise_id, market_name, raise_exception=True)
                                    _, app_version = app_market_service.cloud_app_model_to_db_model(
                                        market, service_source.group_key, service_source.version)
                                # install from local cloud
                                else:
                                    _, app_version = rainbond_app_repo.get_rainbond_app_and_version(
                                        tenant.enterprise_id, service_source.group_key, service_source.version)
                                if app_version:
                                    apps_template = json.loads(app_version.app_template)
                                    app_version_cache[service_source.group_key + service_source.version] = apps_template
                                else:
                                    raise ServiceHandleException(msg="version can not found", msg_show="应用版本不存在，无法构建")
                        if not apps_template:
                            raise ServiceHandleException(msg="version template can not found", msg_show="应用版本不存在，无法构建")
                        apps_list = apps_template.get("apps")
                        if service_source.extend_info:
                            extend_info = json.loads(service_source.extend_info)
                            template_app = None
                            for app in apps_list:
                                if "service_share_uuid" in app and app["service_share_uuid"] == extend_info[
                                        "source_service_share_uuid"]:
                                    template_app = app
                                    break
                                if "service_share_uuid" not in app and "service_key" in app and app[
                                        "service_key"] == extend_info["source_service_share_uuid"]:
                                    template_app = app
                                    break
                            if template_app:
                                share_image = template_app.get("share_image", None)
                                share_slug_path = template_app.get("share_slug_path", None)
                                new_extend_info = {}
                                if share_image and template_app.get("service_image", None):
                                    source_image = dict()
                                    service_dict["image_info"] = source_image
                                    source_image["image_url"] = share_image
                                    source_image["user"] = template_app.get("service_image").get("hub_user")
                                    source_image["password"] = template_app.get("service_image").get("hub_password")
                                    source_image["cmd"] = service.cmd
                                    new_extend_info = template_app["service_image"]
                                if share_slug_path:
                                    slug_info = template_app.get("service_slug")
                                    slug_info["slug_path"] = share_slug_path
                                    new_extend_info = slug_info
                                    service_dict["slug_info"] = new_extend_info
                                # This should not be an upgrade, code should be analyzed and improved.
                                if upgrade:
                                    new_extend_info["source_deploy_version"] = template_app.get("deploy_version")
                                    new_extend_info["source_service_share_uuid"] \
                                        = template_app.get("service_share_uuid") \
                                        if template_app.get("service_share_uuid", None) \
                                        else template_app.get("service_key", "")
                                    new_extend_info["update_time"] = apps_template.update_time.strftime('%Y-%m-%d %H:%M:%S')
                                    if install_from_cloud:
                                        new_extend_info["install_from_cloud"] = True
                                        new_extend_info["market"] = "default"
                                        new_extend_info["market_name"] = old_extent_info.get("market_name")
                                    service_source.extend_info = json.dumps(new_extend_info)
                                    service_source.save()
                                    code, msg = self.__save_env(tenant, service, app["service_env_map_list"],
                                                                app["service_connect_info_map_list"])
                                    if code != 200:
                                        raise Exception(msg)
                                    self.__save_volume(tenant, service, app["service_volume_map_list"])
                                    code, msg = self.__save_port(tenant, service, app["port_map_list"])
                                    if code != 200:
                                        raise Exception(msg)
                                    self.__save_extend_info(service, app["extend_method_map"])
                except ServiceHandleException as e:
                    if e.msg != "no found app market":
                        logger.exception(e)
                        raise e
                except Exception as e:
                    logger.exception(e)
                    if service_source:
                        extend_info = json.loads(service_source.extend_info)
                        if service.is_slug():
                            service_dict["slug_info"] = extend_info
            deploy_infos_list.append(service_dict)
        return 200, body

    def vertical_upgrade(self, tenant, service, user, new_memory, oauth_instance, new_gpu=None, new_cpu=None):
        """组件垂直升级"""
        new_memory = int(new_memory)
        if new_memory > 65536 or new_memory < 0:
            return 400, "内存范围在0M到64G之间"
        if new_memory > service.min_memory and not check_account_quota(tenant.creater, service.service_region, self.ResourceOperationVerticalUpgrade):
            raise ServiceHandleException(error_code=20002, msg="not enough quota")
        if service.create_status == "complete":
            body = dict()
            body["container_memory"] = new_memory
            if new_cpu is None or type(new_cpu) != int:
                new_cpu = baseService.calculate_service_cpu(service.service_region, new_memory)
            body["container_cpu"] = new_cpu
            if new_gpu is not None and type(new_gpu) == int:
                body["container_gpu"] = new_gpu
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.vertical_upgrade(service.service_region, tenant.tenant_name, service.service_alias, body)
                service.min_cpu = new_cpu
                service.min_memory = new_memory
                service.container_gpu = new_gpu
                service.save()
            except region_api.CallApiError as e:
                logger.exception(e)
                return 507, "组件异常"
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, "操作过于频繁，请稍后再试"
        return 200, "操作成功"

    def horizontal_upgrade(self, tenant, service, user, new_node, oauth_instance):
        """组件水平升级"""
        new_node = int(new_node)
        if new_node > 100 or new_node < 0:
            raise ServiceHandleException(status_code=409, msg="node replicas must between 1 and 100", msg_show="节点数量需在1到100之间")

        if new_node > 1 and is_singleton(service.extend_method):
            raise ServiceHandleException(status_code=409, msg="singleton component, do not allow", msg_show="组件为单实例组件，不可使用多节点")

        if new_node > service.min_node:
            if not check_account_quota(tenant.creater, service.service_region, self.ResourceOperationHorizontalUpgrade):
                raise ServiceHandleException(status_code=20002, msg="not enough quota")

        if service.create_status == "complete":
            body = dict()
            body["node_num"] = new_node
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.horizontal_upgrade(service.service_region, tenant.tenant_name, service.service_alias, body)
                service.min_node = new_node
                service.save()
            except ServiceHandleException as e:
                logger.exception(e)
                if e.error_code == 10104:
                    e.msg_show = "节点没有变化，无需升级"
                raise e
            except region_api.CallApiError as e:
                logger.exception(e)
                raise ServiceHandleException(status_code=507, msg="component error", msg_show="组件异常")
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                raise ServiceHandleException(status_code=409, msg="just wait a moment", msg_show="操作过于频繁，请稍后再试")

    def delete(self, user, tenant, service, is_force):
        # 判断组件是否是运行状态
        if self.__is_service_running(tenant, service) and service.service_source != "third_party":
            msg = "组件可能处于运行状态,请先关闭组件"
            return 409, msg
        # 判断组件是否被依赖
        is_related, msg = self.__is_service_related(tenant, service)
        if is_related:
            return 412, "组件被{0}依赖，不可删除".format(msg)
        # 判断组件是否被其他组件挂载
        is_mounted, msg = self.__is_service_mnt_related(tenant, service)
        if is_mounted:
            return 412, "当前组件有存储被{0}组件挂载, 不可删除".format(msg)
        # 组件在哪个应用下
        app = self.get_app_by_service(service)
        if not is_force:
            # 如果不是真删除，将数据备份,删除tenant_service表中的数据
            self.move_service_into_recycle_bin(service)
            # 组件关系移除
            self.move_service_relation_info_recycle_bin(tenant, service)
            return 200, "success"
        else:
            try:
                code, msg = self.truncate_service(tenant, service, user, app)
                if code != 200:
                    return code, msg
                else:
                    return code, "success"
            except Exception as e:
                logger.exception(e)
                return 507, "删除异常"

    def get_app_by_service(self, service):
        relation = group_service_relation_repo.get_group_by_service_id(service.service_id)
        group = group_repo.get_group_by_id(relation.group_id)
        return group

    def delete_components(self, tenant, components, user=None):
        # Batch delete considers that the preconditions have been met,
        # and no longer judge the preconditions
        for cpt in components:
            self.truncate_service(tenant, cpt, user)

    def get_etcd_keys(self, tenant, service):
        logger.debug("ready delete etcd data while delete service")
        keys = []
        # 删除代码检测的etcd数据
        keys.append(service.check_uuid)
        # 删除分享应用的etcd数据
        events = ServiceShareRecordEvent.objects.filter(service_id=service.service_id)
        if events and events[0].region_share_id:
            logger.debug("ready for delete etcd service share data")
            for event in events:
                keys.append(event.region_share_id)
        return keys

    def _truncate_service(self, tenant, service, user=None, app=None):
        data = {}
        if service.create_status == "complete":
            data = service.toJSON()
            data.pop("ID")
            data.pop("service_name")
            data.pop("build_upgrade")
            data.pop("oauth_service_id")
            data.pop("is_upgrate")
            data.pop("secret")
            data.pop("open_webhooks")
            data.pop("server_type")
            data.pop("git_full_name")
            data.pop("arch")
        if app:
            data["app_name"] = app.group_name
            data["app_id"] = app.ID
        if user:
            data["exec_user"] = user.nick_name
        try:
            with transaction.atomic():
                delete_service_repo.create_delete_service(**data)
        except Exception as e:
            logger.exception(e)
            pass
        if service.create_status != "complete":
            vm_repo.delete_vm_image_by_image_url(service.image)
        env_var_repo.delete_service_env(tenant.tenant_id, service.service_id)
        auth_repo.delete_service_auth(service.service_id)
        domain_repo.delete_service_domain(service.service_id)
        tcp_domain.delete_service_tcp_domain(service.service_id)
        dep_relation_repo.delete_service_relation(tenant.tenant_id, service.service_id)
        mnt_repo.delete_mnt(service.service_id)
        port_repo.delete_service_port(tenant.tenant_id, service.service_id)
        volume_repo.delete_service_volumes(service.service_id)
        group_service_relation_repo.delete_relation_by_service_id(service.service_id)
        event_service.delete_service_events(service)
        probe_repo.delete_service_probe(service.service_id)
        service_source_repo.delete_service_source(tenant.tenant_id, service.service_id)
        compose_relation_repo.delete_relation_by_service_id(service.service_id)
        service_label_repo.delete_service_all_labels(service.service_id)
        service_backup_repo.del_by_sid(service.tenant_id, service.service_id)
        component_graph_service.delete_by_component_id(service.service_id)
        app_config_group_service_repo.delete_effective_service(service.service_id)
        service_monitor_repo.delete_by_service_id(service.service_id)
        compile_env_repo.delete_service_compile_env(service.service_id)
        self.__create_service_delete_event(tenant, service, user)
        service.delete()

    @transaction.atomic
    def truncate_service(self, tenant, service, user=None, app=None):
        """彻底删除组件"""
        try:
            data = {}
            data["etcd_keys"] = self.get_etcd_keys(tenant, service)
            region_api.delete_service(service.service_region, tenant.tenant_name, service.service_alias, tenant.enterprise_id,
                                      data)
        except region_api.CallApiError as e:
            if int(e.status) != 404:
                logger.exception(e)
                return 500, "删除组件失败 {0}".format(e.message)

        self._truncate_service(tenant, service, user, app)

        # 如果这个组件属于应用, 则删除应用最后一个组件后同时删除应用
        # 如果这个组件属于模型安装应用, 则删除最后一个组件后同时删除安装应用关系。
        if service.tenant_service_group_id > 0:
            count = service_repo.get_services_by_service_group_id(service.tenant_service_group_id).count()
            if not count:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(service.tenant_service_group_id)

        return 200, "success"

    def delete_compose_app(self, tenant, region_name, k8s_app=None):
        try:
            region_api.delete_compose_app_by_k8s_app(region_name, tenant.tenant_name, k8s_app)
        except Exception as e:
            logger.exception(e)
            raise e

    def __create_service_delete_event(self, tenant, service, user):
        if not user:
            return None
        try:
            event_info = {
                "event_id": make_uuid(),
                "service_id": service.service_id,
                "tenant_id": tenant.tenant_id,
                "type": "truncate",
                "old_deploy_version": "",
                "user_name": user.nick_name,
                "start_time": datetime.datetime.now(),
                "message": service.service_cname,
                "final_status": "complete",
                "status": "success",
                "region": service.service_region
            }
            return event_repo.create_event(**event_info)
        except Exception as e:
            logger.exception(e)
            return None

    def move_service_into_recycle_bin(self, service):
        """将组件移入回收站"""
        data = service.toJSON()
        data.pop("ID")
        trash_service = recycle_bin_repo.create_trash_service(**data)

        # 如果这个组件属于模型安装应用, 则删除最后一个组件后同时删除安装应用关系。
        if service.tenant_service_group_id > 0:
            count = service_repo.get_services_by_service_group_id(service.tenant_service_group_id).count()
            if count <= 1:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(service.tenant_service_group_id)

        service.delete()
        return trash_service

    def move_service_relation_info_recycle_bin(self, tenant, service):
        # 1.如果组件依赖其他组件，将组件对应的关系放入回收站
        relations = dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id)
        if relations:
            for r in relations:
                r_data = r.to_dict()
                r_data.pop("ID")
                relation_recycle_bin_repo.create_trash_service_relation(**r_data)
                r.delete()
        # 如果组件被其他应用下的组件依赖，将组件对应的关系删除
        relations = dep_relation_repo.get_dependency_by_dep_id(tenant.tenant_id, service.service_id)
        if relations:
            relations.delete()
        # 如果组件关系回收站有被此组件依赖的组件，将信息及其对应的数据中心的依赖关系删除
        recycle_relations = relation_recycle_bin_repo.get_by_dep_service_id(service.service_id)
        if recycle_relations:
            for recycle_relation in recycle_relations:
                task = dict()
                task["dep_service_id"] = recycle_relation.dep_service_id
                task["tenant_id"] = tenant.tenant_id
                task["dep_service_type"] = "v"
                task["enterprise_id"] = tenant.enterprise_id
                try:
                    region_api.delete_service_dependency(service.service_region, tenant.tenant_name, service.service_alias,
                                                         task)
                except Exception as e:
                    logger.exception(e)
                recycle_relation.delete()

    def __is_service_bind_domain(self, service):
        domains = domain_repo.get_service_domains(service.service_id)
        if not domains:
            return False

        for domain in domains:
            if domain.type == 1:
                return True
        return False

    def __is_service_mnt_related(self, tenant, service):
        sms = mnt_repo.get_mount_current_service(tenant.tenant_id, service.service_id)
        if sms:
            sids = [sm.service_id for sm in sms]
            services = service_repo.get_services_by_service_ids(sids).values_list("service_cname", flat=True)
            mnt_service_names = ",".join(list(services))
            return True, mnt_service_names
        return False, ""

    def __is_service_related(self, tenant, service):
        tsrs = dep_relation_repo.get_dependency_by_dep_id(tenant.tenant_id, service.service_id)
        if tsrs:
            sids = [tsr.service_id for tsr in tsrs]
            services = service_repo.get_services_by_service_ids(sids).values_list("service_cname", flat=True)
            if not services:
                return False, ""
            dep_service_names = ",".join(list(services))
            return True, dep_service_names
        return False, ""

    def __is_service_related_by_other_app_service(self, tenant, service):
        tsrs = dep_relation_repo.get_dependency_by_dep_id(tenant.tenant_id, service.service_id)
        if tsrs:
            sids = list(set([tsr.service_id for tsr in tsrs]))
            service_group = ServiceGroupRelation.objects.get(service_id=service.service_id, tenant_id=tenant.tenant_id)
            groups = ServiceGroupRelation.objects.filter(service_id__in=sids, tenant_id=tenant.tenant_id)
            group_ids = set([group.group_id for group in groups])
            if group_ids and service_group.group_id in group_ids:
                group_ids.remove(service_group.group_id)
            if not group_ids:
                return False
            return True
        return False

    def __is_service_running(self, tenant, service):
        try:
            if service.create_status != "complete":
                return False
            status_info = region_api.check_service_status(service.service_region, tenant.tenant_name, service.service_alias,
                                                          tenant.enterprise_id)
            status = status_info["bean"]["cur_status"]
            if status in ("running", "starting", "stopping", "failure", "unKnow", "unusual", "abnormal", "some_abnormal"):
                return True
        except region_api.CallApiError as e:
            if int(e.status) == 404:
                return False
        return False

    def __is_service_has_plugins(self, service):
        service_plugin_relations = app_plugin_relation_repo.get_service_plugin_relation_by_service_id(service.service_id)
        if service_plugin_relations:
            return True
        return False

    def delete_region_service(self, tenant, service):
        try:
            data = {}
            logger.debug("delete service {0} for team {1}".format(service.service_cname, tenant.tenant_name))
            data["etcd_keys"] = self.get_etcd_keys(tenant, service)
            region_api.delete_service(service.service_region, tenant.tenant_name, service.service_alias, tenant.enterprise_id,
                                      data)
            return 200, "success"
        except region_api.CallApiError as e:
            if e.status != 404:
                logger.exception(e)
                return 500, "数据中心删除失败"
            return 200, "success"

    # 变更应用分组
    @transaction.atomic
    def move(self, service, move_group_id):
        # 先删除分组应用关系表中该组件数据
        group_service_relation_repo.delete_relation_by_service_id(service_id=service.service_id)
        # 再新建该组件新的关联数据
        group_service_relation_repo.add_service_group_relation(move_group_id, service.service_id, service.tenant_id,
                                                               service.service_region)
        team = team_repo.get_team_by_team_id(service.tenant_id)
        tenant_name = team.tenant_name
        region_app_id = region_app_repo.get_region_app_id(service.service_region, move_group_id)
        update_body = {"service_name": service.service_name, "app_id": region_app_id}
        region_api.update_service_app_id(service.service_region, tenant_name, service.service_alias, update_body)

    # 批量删除组件
    def batch_delete(self, user, tenant, service, is_force, is_del_app=True):
        if not is_del_app:
            # 判断组件是否是运行状态
            if self.__is_service_running(tenant, service) and service.service_source != "third_party":
                msg = "当前组件处于运行状态,请先关闭组件"
                code = 409
                return code, msg
            # 判断组件是否被其他组件挂载
            is_mounted, msg = self.__is_service_mnt_related(tenant, service)
            if is_mounted:
                code = 412
                msg = "当前组件被其他组件挂载, 您确定要删除吗？"
                return code, msg
            # 判断组件是否绑定了域名
            is_bind_domain = self.__is_service_bind_domain(service)
            if is_bind_domain:
                code = 412
                msg = "当前组件绑定了域名， 您确定要删除吗？"
                return code, msg
            # 判断是否有插件
            if self.__is_service_has_plugins(service):
                code = 412
                msg = "当前组件安装了插件， 您确定要删除吗？"
                return code, msg
            # 判断是否被其他应用下的组件依赖
            if self.__is_service_related_by_other_app_service(tenant, service):
                code = 412
                msg = "当前组件被其他应用下的组件依赖了，您确定要删除吗？"
                return code, msg
        # 组件在哪个应用下
        app = self.get_app_by_service(service)
        if not is_force:
            # 如果不是真删除，将数据备份,删除tenant_service表中的数据
            self.move_service_into_recycle_bin(service)
            # 组件关系移除
            self.move_service_relation_info_recycle_bin(tenant, service)
            code = 200
            msg = "success"
            return code, msg
        else:
            try:
                code, msg = self.truncate_service(tenant, service, user, app)
                if code != 200:
                    return code, msg
                else:
                    msg = "success"
                    return code, msg
            except Exception as e:
                logger.exception(e)
                code = 507
                msg = "删除异常"
                return code, msg

    @transaction.atomic
    def delete_again(self, user, tenant, service, is_force):
        # 组件在哪个应用下
        app = self.get_app_by_service(service)
        if not is_force:
            # 如果不是真删除，将数据备份,删除tenant_service表中的数据
            self.move_service_into_recycle_bin(service)
            # 组件关系移除
            self.move_service_relation_info_recycle_bin(tenant, service)
        else:
            try:
                self.really_delete_service(tenant, service, user, app=app)
            except ServiceHandleException as e:
                raise e
            except Exception as e:
                logger.exception(e)
                raise ServiceHandleException(msg="delete component {} failure".format(service.service_alias), msg_show="组件删除失败")

    def really_delete_service(self,
                              tenant,
                              service,
                              user=None,
                              ignore_cluster_result=False,
                              not_delete_from_cluster=False,
                              app=None):
        """组件真实删除方法，调用端必须进行事务控制"""
        ignore_delete_from_cluster = not_delete_from_cluster
        data = {}
        if not not_delete_from_cluster:
            try:
                data["etcd_keys"] = self.get_etcd_keys(tenant, service)
                region_api.delete_service(service.service_region, tenant.tenant_name, service.service_alias,
                                          tenant.enterprise_id, data)
            except region_api.CallApiError as e:
                if (not ignore_cluster_result) and int(e.status) != 404:
                    logger.error("delete component form cluster failure {}".format(e.body))
                    raise ServiceHandleException(msg="delete component from cluster failure", msg_show="组件从集群删除失败")
            except Exception as e:
                logger.exception(e)
                if (not ignore_cluster_result):
                    raise ServiceHandleException(msg="delete component from cluster failure", msg_show="组件从集群删除失败")
                else:
                    ignore_delete_from_cluster = True
        if service.create_status == "complete":
            data = service.toJSON()
            data.pop("ID")
            data.pop("service_name")
            data.pop("build_upgrade")
            data.pop("oauth_service_id")
            data.pop("is_upgrate")
            data.pop("secret")
            data.pop("open_webhooks")
            data.pop("server_type")
            data.pop("git_full_name")
            data.pop("arch")
        if app:
            data["app_name"] = app.group_name
            data["app_id"] = app.ID
        if user:
            data["exec_user"] = user.nick_name
        try:
            with transaction.atomic():
                delete_service_repo.create_delete_service(**data)
        except Exception as e:
            logger.exception(e)
            pass
        env_var_repo.delete_service_env(tenant.tenant_id, service.service_id)
        auth_repo.delete_service_auth(service.service_id)
        domain_repo.delete_service_domain(service.service_id)
        tcp_domain.delete_service_tcp_domain(service.service_id)
        dep_relation_repo.delete_service_relation(tenant.tenant_id, service.service_id)
        relations = dep_relation_repo.get_dependency_by_dep_id(tenant.tenant_id, service.service_id)
        if relations:
            relations.delete()
        mnt_repo.delete_mnt(service.service_id)
        port_repo.delete_service_port(tenant.tenant_id, service.service_id)
        volume_repo.delete_service_volumes(service.service_id)
        group_service_relation_repo.delete_relation_by_service_id(service.service_id)
        event_service.delete_service_events(service)
        probe_repo.delete_service_probe(service.service_id)
        service_source_repo.delete_service_source(tenant.tenant_id, service.service_id)
        compose_relation_repo.delete_relation_by_service_id(service.service_id)
        service_label_repo.delete_service_all_labels(service.service_id)
        share_repo.delete_tenant_service_plugin_relation(service.service_id)
        service_monitor_repo.delete_by_service_id(service.service_id)
        component_graph_service.delete_by_component_id(service.service_id)
        app_config_group_service_repo.delete_effective_service(service.service_id)
        if service.tenant_service_group_id > 0:
            count = service_repo.get_services_by_service_group_id(service.tenant_service_group_id).count()
            if count <= 1:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(service.tenant_service_group_id)
        self.__create_service_delete_event(tenant, service, user)
        service.delete()
        return ignore_delete_from_cluster

    def get_extend_method_name(self, extend_method):
        if extend_method == "state_singleton":
            return "有状态单实例"
        elif extend_method == "state_multiple":
            return "有状态多实例"
        elif extend_method == "stateless_singleton":
            return "无状态单实例"
        elif extend_method == "stateless_multiple":
            return "无状态多实例"
        else:
            return None

    def change_service_type(self, tenant, service, extend_method, user_name=''):
        # 存储限制
        tenant_service_volumes = volume_service.get_service_volumes(tenant, service)
        if tenant_service_volumes:
            old_extend_method = service.extend_method
            for tenant_service_volume in tenant_service_volumes:
                if tenant_service_volume["volume_type"] == "share-file" or tenant_service_volume["volume_type"] == "memoryfs":
                    continue
                if tenant_service_volume["volume_type"] == "local":
                    if old_extend_method == ComponentType.state_singleton.value:
                        raise ServiceHandleException(
                            msg="local storage only support state_singleton", msg_show="本地存储仅支持有状态单实例组件")
                if tenant_service_volume.get("access_mode", "") == "RWO":
                    if not is_state(extend_method):
                        raise ServiceHandleException(msg="storage access mode do not support", msg_show="存储读写属性限制,不可修改为无状态组件")
        # 实例个数限制
        if is_singleton(extend_method) and service.min_node > 1:
            raise ServiceHandleException(
                msg="singleton service limit", msg_show="组件实例数为{0}，不可修改为单实例组件类型".format(service.min_node))

        if service.create_status != "complete":
            service.extend_method = extend_method
            service.save()
            return

        data = dict()
        data["extend_method"] = extend_method
        data["operator"] = user_name
        try:
            region_api.update_service(service.service_region, tenant.tenant_name, service.service_alias, data)
            service.extend_method = extend_method
            service.save()
        except region_api.CallApiError as e:
            logger.exception(e)
            raise ErrChangeServiceType

    def close_all_component_in_team(self, tenant, user):
        # close all component in define team
        tenant_regions = region_repo.list_by_tenant_id(tenant.tenant_id)
        tenant_regions = tenant_regions if tenant_regions else []
        for region in tenant_regions:
            self.close_all_component_in_tenant(tenant, region.region_name, user)

    def close_all_component_in_tenant(self, tenant, region_name, user):
        try:
            # list components
            components = service_repo.get_services_by_team_and_region(tenant.tenant_id, region_name)
            component_ids = [cpt.service_id for cpt in components]
            self.batch_operations(tenant, region_name, user, "stop", component_ids)
        except Exception as e:
            logger.exception(e)

    def change_lang_and_package_tool(self, tenant, service, lang, package_tool, dist):
        serivce_params = {"language": lang}
        try:
            service_repo.update(tenant.tenant_id, service.service_id, **serivce_params)
            env_var_repo.update_or_create_env_var(tenant.tenant_id, service.service_id, "BUILD_PACKAGE_TOOL", package_tool)
            if dist and lang == "NodeJSStatic":
                tenantServiceEnvVar = {}
                tenantServiceEnvVar["tenant_id"] = service.tenant_id
                tenantServiceEnvVar["service_id"] = service.service_id
                tenantServiceEnvVar['container_port'] = 0
                tenantServiceEnvVar["name"] = "set_dist"
                tenantServiceEnvVar["attr_name"] = "BUILD_DIST_DIR"
                tenantServiceEnvVar["attr_value"] = dist
                tenantServiceEnvVar["is_change"] = True
                tenantServiceEnvVar["scope"] = "scope"
                env_var_repo.add_service_env(**tenantServiceEnvVar)
        except Exception as e:
            logger.exception(e)
            return 507, "failed"
        return 200, "success"

    def change_image_tool(self, tenant, service, image_name):
        tag = image_name.split(":")[-1]
        service_params = {"version": tag, "image": image_name, "docker_cmd": image_name}
        try:
            service_repo.update(tenant.tenant_id, service.service_id, **service_params)
        except Exception as e:
            logger.exception(e)
            return 507, "failed"
        return 200, "success"

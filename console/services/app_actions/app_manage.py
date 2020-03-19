# -*- coding: utf8 -*-
"""
  Created on 18/1/24.
"""
import datetime
import json
import logging

from django.conf import settings

from console.constants import AppConstants
from console.enum.component_enum import ComponentType
from console.enum.component_enum import is_singleton
from console.enum.component_enum import is_state
from console.exception.main import ServiceHandleException
from console.models.main import ServiceShareRecordEvent
from console.repositories.app import delete_service_repo
from console.repositories.app import recycle_bin_repo
from console.repositories.app import relation_recycle_bin_repo
from console.repositories.app import service_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import auth_repo
from console.repositories.app_config import create_step_repo
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import domain_repo
from console.repositories.app_config import env_var_repo
from console.repositories.app_config import extend_repo
from console.repositories.app_config import mnt_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import service_attach_repo
from console.repositories.app_config import service_payment_repo
from console.repositories.app_config import tcp_domain
from console.repositories.app_config import volume_repo
from console.repositories.compose_repo import compose_relation_repo
from console.repositories.event_repo import event_repo
from console.repositories.group import group_service_relation_repo
from console.repositories.group import tenant_service_group_repo
from console.repositories.label_repo import service_label_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.migration_repo import migrate_repo
from console.repositories.oauth_repo import oauth_repo
from console.repositories.oauth_repo import oauth_user_repo
from console.repositories.perm_repo import service_perm_repo
from console.repositories.plugin import app_plugin_relation_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.service_backup_repo import service_backup_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo
from console.repositories.share_repo import share_repo
from console.services.app_actions.app_log import AppEventService
from console.services.app_actions.exception import ErrVersionAlreadyExists
from console.services.app_config import AppEnvVarService
from console.services.app_config import AppMntService
from console.services.app_config import AppPortService
from console.services.app_config import AppServiceRelationService
from console.services.app_config import AppVolumeService
from console.services.exception import ErrChangeServiceType
from console.utils import slug_util
from console.utils.oauth.oauth_types import get_oauth_instance
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroupRelation
from www.tenantservice.baseservice import BaseTenantService
from www.tenantservice.baseservice import TenantUsedResource
from www.utils.crypt import make_uuid

tenantUsedResource = TenantUsedResource()
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

    def isOwnedMoney(self, tenant):
        if self.MODULES["Owned_Fee"]:
            if tenant.balance < 0 and tenant.pay_type == "payed":
                return True
        return False

    def isExpired(self, tenant, service):
        if service.expired_time is not None:
            if tenant.pay_type == "free" and service.expired_time < datetime.datetime.now():
                if self.MODULES["Owned_Fee"]:
                    return True
        else:
            # 将原有免费用户的组件设置为7天后
            service.expired_time = datetime.datetime.now() + datetime.timedelta(days=7)
        return False

    def is_over_resource(self, tenant, service):
        tenant_cur_used_resource = tenantUsedResource.calculate_real_used_resource(tenant)
        if tenant.pay_type == "free":
            # 免费用户使用上限
            new_add_memory = service.min_node * service.min_memory
            if new_add_memory + tenant_cur_used_resource > tenant.limit_memory:
                return True
        return False

    def cur_service_memory(self, tenant, cur_service):
        """查询当前组件占用的内存"""
        memory = 0
        try:
            body = region_api.check_service_status(
                cur_service.service_region, tenant.tenant_name, cur_service.service_alias, tenant.enterprise_id)
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

    def is_operate_over_resource(self, tenant, service, new_add_memory, is_check_status):
        """

        :param tenant: 租户
        :param service: 组件
        :param new_add_memory: 新添加的内存
        :param is_check_status: 是否检测当前组件状态
        :return:
        """
        if self.MODULES["Memory_Limit"]:
            if is_check_status:
                new_add_memory = new_add_memory + \
                    self.cur_service_memory(tenant, service)
            if tenant.pay_type == "free":
                tm = tenantUsedResource.calculate_real_used_resource(tenant) + new_add_memory
                logger.debug(tenant.tenant_id + " used memory " + str(tm))
                if tm > tenant.limit_memory:
                    return True

        return False

    def check_resource(self, tenant, service, new_add_memory=0, is_check_status=False):
        # if self.isOwnedMoney(tenant):
        #     return 400, u"余额不足请及时充值"
        if self.isExpired(tenant, service):
            return 400, u"该应用试用已到期"
        # if self.is_over_resource(tenant, service):
        if self.is_operate_over_resource(tenant, service, new_add_memory, is_check_status):
            return 400, u"资源已达上限，您最多使用{0}G内存".format(tenant.limit_memory / 1024)
        return 200, "pass"


class AppManageService(AppManageBase):
    def start(self, tenant, service, user):
        if service.create_status == "complete":
            body = dict()
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.start_service(service.service_region, tenant.tenant_name, service.service_alias, body)
                logger.debug("user {0} start app !".format(user.nick_name))
            except region_api.CallApiError as e:
                logger.exception(e)
                return 507, u"组件异常"
            except region_api.ResourceNotEnoughError as e:
                logger.exception(e)
                return 412, e.msg
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, u"操作过于频繁，请稍后再试"
        return 200, u"操作成功"

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
                return 507, u"组件异常"
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, u"操作过于频繁，请稍后再试"
        return 200, u"操作成功"

    def restart(self, tenant, service, user):
        if service.create_status == "complete":
            body = dict()
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.restart_service(service.service_region, tenant.tenant_name, service.service_alias, body)
                logger.debug("user {0} retart app !".format(user.nick_name))
            except region_api.CallApiError as e:
                logger.exception(e)
                return 507, u"组件异常"
            except region_api.ResourceNotEnoughError as e:
                logger.exception(e)
                return 412, e.msg
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, u"操作过于频繁，请稍后再试"
        return 200, u"操作成功"

    def deploy(self, tenant, service, user, group_version, committer_name=None):
        body = dict()
        # 默认更新升级
        body["action"] = "deploy"
        if service.build_upgrade:
            body["action"] = "upgrade"
        body["envs"] = env_var_repo.get_build_envs(tenant.tenant_id, service.service_id)
        kind = self.__get_service_kind(service)
        body["kind"] = kind
        body["operator"] = str(user.nick_name)
        body["configs"] = {}
        body["service_id"] = service.service_id
        # source type parameter
        if kind == "build_from_source_code" or kind == "source":
            if service.oauth_service_id:
                try:
                    oauth_service = oauth_repo.get_oauth_services_by_service_id(
                        service_id=service.oauth_service_id)
                    oauth_user = oauth_user_repo.get_user_oauth_by_user_id(
                        service_id=service.oauth_service_id, user_id=user.user_id)
                except Exception as e:
                    logger.debug(e)
                    return 507, "构建异常", ""
                try:
                    instance = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
                except Exception as e:
                    logger.debug(e)
                    return 507, "构建异常", ""
                if not instance.is_git_oauth():
                    return 507, "构建异常", ""
                git_url = instance.get_clone_url(service.git_url)
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
        if kind == "build_from_image" or kind == "build_from_market_image":
            body["image_info"] = {
                "image_url": service.image,
                "cmd": service.cmd,
            }
        service_source = service_source_repo.get_service_source(service.tenant_id, service.service_id)
        if service_source and (service_source.user_name or service_source.password):
            if body.get("code_info", None):
                body["code_info"]["user"] = service_source.user_name
                body["code_info"]["password"] = service_source.password
            if body.get("image_info", None):
                body["image_info"]["user"] = service_source.user_name
                body["image_info"]["password"] = service_source.password
        if service_source and service_source.extend_info:
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
            re = region_api.build_service(service.service_region, tenant.tenant_name, service.service_alias, body)
            if re and re.get("bean") and re.get("bean").get("status") != "success":
                return 507, "构建异常", ""
            event_id = re["bean"].get("event_id", "")
        except region_api.CallApiError as e:
            if e.status == 400:
                logger.warning("failed to deploy service: {}".format(e))
                raise ErrVersionAlreadyExists()
            logger.exception(e)
            return 507, "构建异常", ""
        except region_api.ResourceNotEnoughError as e:
            logger.exception(e)
            return 412, e.msg, ""
        except region_api.CallApiFrequentError as e:
            logger.exception(e)
            return 409, u"操作过于频繁，请稍后再试", ""
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
        if not volumes:
            return 200, "success"
        for volume in volumes:
            service_volume = volume_repo.get_service_volume_by_name(service.service_id, volume["volume_name"])
            if service_volume:
                continue
            file_content = volume.get("file_content", None)
            settings = {}
            settings["volume_capacity"] = volume["volume_capacity"]
            volume_service.add_service_volume(
                tenant, service, volume["volume_path"], volume_type=volume["volume_type"], volume_name=volume["volume_name"],
                file_content=file_content, settings=settings)
        return 200, "success"

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
                                    env["attr_value"], env["is_change"], scope="inner")
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
                if env["attr_value"] == "**None**":
                    env["attr_value"] = service.service_id[:8]
                code, msg, env_data = env_var_service. \
                    add_service_env_var(tenant, service, container_port,
                                        env["name"], env["attr_name"],
                                        env["attr_value"], env["is_change"], "outer")
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
            service_port = port_repo.get_service_port_by_port(
                tenant.tenant_id, service.service_id, int(port["container_port"]))
            if service_port:
                if port["is_inner_service"]:
                    code, msg, data = env_var_service.add_service_env_var(
                        tenant,
                        service,
                        int(port["container_port"]),
                        u"连接地址",
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
                        u"端口",
                        env_prefix + "_PORT",
                        mapping_port,
                        False,
                        scope="outer")
                    if code != 200 and code != 412:
                        return code, msg
                continue

            code, msg, port_data = port_service.add_service_port(
                tenant, service, int(port["container_port"]),
                port["protocol"],
                port["port_alias"],
                port["is_inner_service"],
                port["is_outer_service"])
            if code != 200:
                logger.error("save market app port error: {}".format(msg))
                return code, msg
        return 200, "success"

    def upgrade(self, tenant, service, user, committer_name=None):
        body = dict()
        body["service_id"] = service.service_id
        try:
            body = region_api.upgrade_service(service.service_region, tenant.tenant_name, service.service_alias, body)
            event_id = body["bean"].get("event_id", "")
            return 200, "操作成功", event_id
        except region_api.CallApiError as e:
            logger.exception(e)
            return 507, "更新异常", ""
        except region_api.ResourceNotEnoughError as e:
            logger.exception(e)
            return 412, e.msg, ""
        except region_api.CallApiFrequentError as e:
            logger.exception(e)
            return 409, u"操作过于频繁，请稍后再试", ""

    def __get_service_kind(self, service):
        """获取组件种类，兼容老的逻辑"""
        if service.service_source:
            if service.service_source == AppConstants.SOURCE_CODE:
                # return "source"
                return "build_from_source_code"
            elif service.service_source == AppConstants.DOCKER_RUN \
                    or service.service_source == AppConstants.DOCKER_COMPOSE \
                    or service.service_source == AppConstants.DOCKER_IMAGE:
                # return "image"
                return "build_from_image"
            elif service.service_source == AppConstants.MARKET:
                if slug_util.is_slug(service.image, service.language):
                    return "build_from_market_slug"
                else:
                    return "build_from_market_image"
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
                return 404, u"当前版本可能已被系统清理或删除"
            body = dict()
            body["operator"] = str(user.nick_name)
            body["upgrade_version"] = deploy_version
            body["service_id"] = service.service_id
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.rollback(service.service_region, tenant.tenant_name, service.service_alias, body)
            except region_api.CallApiError as e:
                logger.exception(e)
                return 507, u"组件异常"
            except region_api.ResourceNotEnoughError as e:
                logger.exception(e)
                return 412, e.msg
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, u"操作过于频繁，请稍后再试"
        return 200, u"操作成功"

    def batch_action(self, tenant, user, action, service_ids, move_group_id):
        services = service_repo.get_services_by_service_ids(service_ids)
        code = 500
        msg = "系统异常"
        fail_service_name = []
        for service in services:
            try:
                # 第三方组件不具备启动，停止，重启操作
                if action == "start" and service.service_source != "third_party":
                    self.start(tenant, service, user)
                elif action == "stop" and service.service_source != "third_party":
                    self.stop(tenant, service, user)
                elif action == "restart" and service.service_source != "third_party":
                    self.restart(tenant, service, user)
                elif action == "move":
                    self.move(service, move_group_id)
                elif action == "deploy" and service.service_source != "third_party":
                    self.deploy(tenant, service, user, group_version=None)
                code = 200
                msg = "success"
            except Exception as e:
                fail_service_name.append(service.service_cname)
                logger.exception(e)
        logger.debug("fail service names {0}".format(fail_service_name))
        return code, msg

    # 5.1新版批量操作（启动，关闭，构建）
    def batch_operations(self, tenant, user, action, service_ids):
        services = service_repo.get_services_by_service_ids(service_ids)
        # 获取所有组件信息
        body = dict()
        code = 200
        data = ''
        if action == "start":
            code, data = self.start_services_info(body, services, tenant, user)
        elif action == "stop":
            code, data = self.stop_services_info(body, services, tenant, user)
        elif action == "upgrade":
            code, data = self.upgrade_services_info(body, services, tenant, user)
        elif action == "deploy":
            code, data = self.deploy_services_info(body, services, tenant, user)
        if code != 200:
            return 415, "组件信息获取失败"
        # 获取数据中心信息
        one_service = services[0]
        region_name = one_service.service_region
        try:
            region_api.batch_operation_service(region_name, tenant.tenant_name, data)
            return 200, "操作成功"
        except region_api.CallApiError as e:
            logger.exception(e)
            return 500, "数据中心操作失败"

    def start_services_info(self, body, services, tenant, user):
        body["operation"] = "start"
        start_infos_list = []
        body["start_infos"] = start_infos_list
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

    def upgrade_services_info(self, body, services, tenant, user):
        body["operation"] = "upgrade"
        upgrade_infos_list = []
        body["upgrade_infos"] = upgrade_infos_list
        for service in services:
            service_dict = dict()
            if service.create_status == "complete":
                service_dict["service_id"] = service.service_id
                upgrade_infos_list.append(service_dict)
        return 200, body

    def deploy_services_info(self, body, services, tenant, user):
        body["operation"] = "build"
        deploy_infos_list = []
        body["build_infos"] = deploy_infos_list
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

            # 源码
            if kind == "build_from_source_code" or kind == "source":
                source_code = dict()
                service_dict["code_info"] = source_code
                source_code["repo_url"] = clone_url
                source_code["branch"] = service.code_version
                source_code["server_type"] = service.server_type
                source_code["lang"] = service.language
                source_code["cmd"] = service.cmd
                if service_source:
                    if service_source.user_name or service_source.password:
                        source_code["user"] = service_source.user_name
                        source_code["password"] = service_source.password
            # 镜像
            elif kind == "build_from_image":
                source_image = dict()
                source_image["image_url"] = service.image
                source_image["cmd"] = service.cmd
                if service_source:
                    if service_source.user_name or service_source.password:
                        source_image["user"] = service_source.user_name
                        source_image["password"] = service_source.password
                service_dict["image_info"] = source_image

            # 云市
            elif service.service_source == "market":
                try:
                    if service_source:
                        old_extent_info = json.loads(service_source.extend_info)
                        app_version = None
                        # install from cloud
                        install_from_cloud = False
                        if old_extent_info.get("install_from_cloud", False):
                            install_from_cloud = True
                            # TODO:Skip the subcontract structure to avoid loop introduction
                            from console.services.market_app_service import market_app_service
                            _, app_version = market_app_service.get_app_from_cloud(
                                tenant, service_source.group_key, service_source.version)
                        # install from local cloud
                        else:
                            _, app_version = rainbond_app_repo.get_rainbond_app_and_version(
                                tenant.enterprise_id, service_source.group_key, service_source.version)
                        if app_version:
                            # 解析app_template的json数据
                            apps_template = json.loads(app_version.app_template)
                            apps_list = apps_template.get("apps")
                            if service_source.extend_info:
                                extend_info = json.loads(service_source.extend_info)
                                template_app = None
                                for app in apps_list:
                                    if "service_share_uuid" in app:
                                        if app["service_share_uuid"] == extend_info["source_service_share_uuid"]:
                                            template_app = app
                                            break
                                    if "service_share_uuid" not in app and "service_key" in app:
                                        if app["service_key"] == extend_info["source_service_share_uuid"]:
                                            template_app = app
                                            break
                                if template_app:
                                    share_image = template_app.get("share_image", None)
                                    share_slug_path = template_app.get("share_slug_path", None)
                                    new_extend_info = {}
                                    if share_image:
                                        if template_app.get("service_image", None):
                                            source_image = dict()
                                            service_dict["image_info"] = source_image
                                            source_image["image_url"] = share_image
                                            source_image["user"] = template_app.get("service_image").get("hub_user")
                                            source_image["password"] = template_app.get(
                                                "service_image").get("hub_password")
                                            source_image["cmd"] = service.cmd
                                            new_extend_info = template_app["service_image"]
                                    if share_slug_path:
                                        slug_info = template_app.get("service_slug")
                                        slug_info["slug_path"] = share_slug_path
                                        new_extend_info = slug_info
                                        service_dict["slug_info"] = new_extend_info
                                    new_extend_info["source_deploy_version"] = template_app.get("deploy_version")
                                    new_extend_info["source_service_share_uuid"] \
                                        = template_app.get("service_share_uuid") \
                                        if template_app.get("service_share_uuid", None) \
                                        else template_app.get("service_key", "")
                                    if install_from_cloud:
                                        new_extend_info["install_from_cloud"] = True
                                        new_extend_info["market"] = "default"
                                    service_source.extend_info = json.dumps(new_extend_info)
                                    service_source.save()
                                    code, msg = self.__save_env(tenant, service, app["service_env_map_list"],
                                                                app["service_connect_info_map_list"])
                                    if code != 200:
                                        raise Exception(msg)
                                    code, msg = self.__save_volume(tenant, service, app["service_volume_map_list"])
                                    if code != 200:
                                        raise Exception(msg)
                                    logger.debug('-------222---->{0}'.format(app["port_map_list"]))
                                    code, msg = self.__save_port(tenant, service, app["port_map_list"])
                                    if code != 200:
                                        raise Exception(msg)
                                    self.__save_extend_info(service, app["extend_method_map"])
                except Exception as e:
                    logger.exception(e)
                    if service_source:
                        extend_info = json.loads(service_source.extend_info)
                        if service.is_slug():
                            service_dict["slug_info"] = extend_info
            deploy_infos_list.append(service_dict)
        return 200, body

    def vertical_upgrade(self, tenant, service, user, new_memory):
        """组件水平升级"""
        new_memory = int(new_memory)
        if new_memory == service.min_memory:
            return 409, "内存没有变化，无需升级"
        if new_memory > 65536 or new_memory < 64:
            return 400, "内存范围在64M到64G之间"
        if new_memory % 32 != 0:
            return 400, "内存必须为32的倍数"

        new_cpu = baseService.calculate_service_cpu(service.service_region, new_memory)
        if service.create_status == "complete":
            body = dict()
            body["container_memory"] = new_memory
            body["container_cpu"] = new_cpu
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.vertical_upgrade(service.service_region, tenant.tenant_name, service.service_alias, body)
                service.min_cpu = new_cpu
                service.min_memory = new_memory
                service.save()
            except region_api.CallApiError as e:
                logger.exception(e)
                return 507, u"组件异常"
            except region_api.ResourceNotEnoughError as e:
                logger.exception(e)
                return 412, e.msg
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                return 409, u"操作过于频繁，请稍后再试"
        return 200, u"操作成功"

    def horizontal_upgrade(self, tenant, service, user, new_node):
        """组件水平升级"""
        new_node = int(new_node)
        if new_node > 100 or new_node < 0:
            raise ServiceHandleException(
                status_code=409, msg="node replicas must between 1 and 100", msg_show="节点数量需在1到100之间")
        if new_node == service.min_node:
            raise ServiceHandleException(status_code=409, msg="no change, no update", msg_show="节点没有变化，无需升级")

        if new_node > 1 and is_singleton(service.extend_method):
            raise ServiceHandleException(
                status_code=409, msg="singleton component, do not allow", msg_show="组件为单实例组件，不可使用多节点")

        if service.create_status == "complete":
            body = dict()
            body["node_num"] = new_node
            body["operator"] = str(user.nick_name)
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.horizontal_upgrade(service.service_region, tenant.tenant_name, service.service_alias, body)
                service.min_node = new_node
                service.save()
            except region_api.CallApiError as e:
                logger.exception(e)
                raise ServiceHandleException(status_code=507, msg="component error", msg_show="组件异常")
            except region_api.ResourceNotEnoughError as e:
                logger.exception(e)
                raise ServiceHandleException(status_code=412, msg="resource not enough", msg_show=e.msg)
            except region_api.CallApiFrequentError as e:
                logger.exception(e)
                raise ServiceHandleException(status_code=409, msg="just wait a moment", msg_show="操作过于频繁，请稍后再试")

    def delete(self, user, tenant, service, is_force):
        # 判断组件是否是运行状态
        if self.__is_service_running(tenant, service) and service.service_source != "third_party":
            msg = u"组件可能处于运行状态,请先关闭组件"
            return 409, msg
        # 判断组件是否被依赖
        is_related, msg = self.__is_service_related(tenant, service)
        if is_related:
            return 412, "组件被{0}依赖，不可删除".format(msg)
        # 判断组件是否被其他组件挂载
        is_mounted, msg = self.__is_service_mnt_related(tenant, service)
        if is_mounted:
            return 412, "当前组件被{0}挂载, 不可删除".format(msg)
        # 判断组件是否绑定了域名
        is_bind_domain = self.__is_service_bind_domain(service)
        if is_bind_domain:
            return 412, "请先解绑组件绑定的域名"
        # 判断是否有插件
        if self.__is_service_has_plugins(service):
            return 412, "请先卸载组件安装的插件"

        if not is_force:
            # 如果不是真删除，将数据备份,删除tenant_service表中的数据
            self.move_service_into_recycle_bin(service)
            # 组件关系移除
            self.move_service_relation_info_recycle_bin(tenant, service)
            return 200, "success"
        else:
            try:
                code, msg = self.truncate_service(tenant, service, user)
                if code != 200:
                    return code, msg
                else:
                    return code, "success"
            except Exception as e:
                logger.exception(e)
                return 507, u"删除异常"

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
        # 删除恢复迁移的etcd数据
        group_id = service_group_relation_repo.get_group_id_by_service(service)
        if group_id:
            migrate_record = migrate_repo.get_by_original_group_id(group_id)
            if migrate_record:
                for record in migrate_record:
                    keys.append(record.restore_id)
        return keys

    def truncate_service(self, tenant, service, user=None):
        """彻底删除组件"""

        try:
            data = {}
            data["etcd_keys"] = self.get_etcd_keys(tenant, service)
            region_api.delete_service(service.service_region, tenant.tenant_name,
                                      service.service_alias, tenant.enterprise_id, data)
        except region_api.CallApiError as e:
            if int(e.status) != 404:
                logger.exception(e)
                return 500, "删除组件失败 {0}".format(e.message)
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
            delete_service_repo.create_delete_service(**data)

        env_var_repo.delete_service_env(tenant.tenant_id, service.service_id)
        auth_repo.delete_service_auth(service.service_id)
        domain_repo.delete_service_domain(service.service_id)
        tcp_domain.delete_service_tcp_domain(service.service_id)
        dep_relation_repo.delete_service_relation(tenant.tenant_id, service.service_id)
        mnt_repo.delete_mnt(service.service_id)
        port_repo.delete_service_port(tenant.tenant_id, service.service_id)
        volume_repo.delete_service_volumes(service.service_id)
        group_service_relation_repo.delete_relation_by_service_id(service.service_id)
        service_attach_repo.delete_service_attach(service.service_id)
        create_step_repo.delete_create_step(service.service_id)
        event_service.delete_service_events(service)
        probe_repo.delete_service_probe(service.service_id)
        service_payment_repo.delete_service_payment(service.service_id)
        service_source_repo.delete_service_source(tenant.tenant_id, service.service_id)
        service_perm_repo.delete_service_perm(service.ID)
        compose_relation_repo.delete_relation_by_service_id(service.service_id)
        service_label_repo.delete_service_all_labels(service.service_id)
        service_backup_repo.del_by_sid(service.tenant_id, service.service_id)
        # 如果这个组件属于应用, 则删除应用最后一个组件后同时删除应用
        if service.tenant_service_group_id > 0:
            count = service_repo.get_services_by_service_group_id(service.tenant_service_group_id).count()
            if count <= 1:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(service.tenant_service_group_id)
        self.__create_service_delete_event(tenant, service, user)
        service.delete()
        return 200, "success"

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

        # 如果这个组件属于应用, 则删除应用最后一个组件后同时删除应用
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
                    region_api.delete_service_dependency(
                        service.service_region, tenant.tenant_name, service.service_alias, task)
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
        group_ids = []
        if tsrs:
            sids = list(set([tsr.service_id for tsr in tsrs]))
            service_group = ServiceGroupRelation.objects.get(
                service_id=service.service_id, tenant_id=tenant.tenant_id)
            groups = ServiceGroupRelation.objects.filter(service_id__in=sids, tenant_id=tenant.tenant_id)
            for group in groups:
                group_ids.append(group.group_id)
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
            status_info = region_api.check_service_status(
                service.service_region, tenant.tenant_name, service.service_alias, tenant.enterprise_id)
            status = status_info["bean"]["cur_status"]
            if status in ("running", "starting", "stopping", "failure",
                          "unKnow", "unusual", "abnormal", "some_abnormal"):
                return True
        except region_api.CallApiError as e:
            if int(e.status) == 404:
                return False
        return False

    def __is_service_has_plugins(self, service):
        service_plugin_relations = app_plugin_relation_repo.get_service_plugin_relation_by_service_id(
            service.service_id)
        if service_plugin_relations:
            return True
        return False

    def delete_region_service(self, tenant, service):
        try:
            logger.debug("delete service {0} for team {1}".format(service.service_cname, tenant.tenant_name))
            region_api.delete_service(service.service_region, tenant.tenant_name,
                                      service.service_alias, tenant.enterprise_id)
            return 200, "success"
        except region_api.CallApiError as e:
            if e.status != 404:
                logger.exception(e)
                return 500, "数据中心删除失败"
            return 200, "success"

    # 变更应用分组
    def move(self, service, move_group_id):
        # 先删除分组应用关系表中该组件数据
        group_service_relation_repo.delete_relation_by_service_id(service_id=service.service_id)
        # 再新建该组件新的关联数据
        group_service_relation_repo.add_service_group_relation(move_group_id, service.service_id, service.tenant_id,
                                                               service.service_region)

    # 批量删除组件
    def batch_delete(self, user, tenant, service, is_force):
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
                code, msg = self.truncate_service(tenant, service, user)
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

    def delete_again(self, user, tenant, service, is_force):
        if not is_force:
            # 如果不是真删除，将数据备份,删除tenant_service表中的数据
            self.move_service_into_recycle_bin(service)
            # 组件关系移除
            self.move_service_relation_info_recycle_bin(tenant, service)
            return 200, "success"
        else:
            try:
                code, msg = self.again_delete_service(tenant, service, user)
                if code != 200:
                    return code, msg
                else:
                    return code, "success"
            except Exception as e:
                logger.exception(e)
                return 507, u"删除异常"

    def again_delete_service(self, tenant, service, user=None):
        """二次删除组件"""

        try:
            data = {}
            data["etcd_keys"] = self.get_etcd_keys(tenant, service)
            region_api.delete_service(service.service_region, tenant.tenant_name,
                                      service.service_alias, tenant.enterprise_id, data)
        except region_api.CallApiError as e:
            if int(e.status) != 404:
                logger.exception(e)
                return 500, "删除组件失败 {0}".format(e.message)
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
            delete_service_repo.create_delete_service(**data)

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
        service_attach_repo.delete_service_attach(service.service_id)
        create_step_repo.delete_create_step(service.service_id)
        event_service.delete_service_events(service)
        probe_repo.delete_service_probe(service.service_id)
        service_payment_repo.delete_service_payment(service.service_id)
        service_source_repo.delete_service_source(tenant.tenant_id, service.service_id)
        service_perm_repo.delete_service_perm(service.ID)
        compose_relation_repo.delete_relation_by_service_id(service.service_id)
        service_label_repo.delete_service_all_labels(service.service_id)
        # 删除组件和插件的关系
        share_repo.delete_tenant_service_plugin_relation(service.service_id)
        # 如果这个组件属于应用, 则删除应用最后一个组件后同时删除应用
        if service.tenant_service_group_id > 0:
            count = service_repo.get_services_by_service_group_id(service.tenant_service_group_id).count()
            if count <= 1:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(service.tenant_service_group_id)
        self.__create_service_delete_event(tenant, service, user)
        service.delete()
        return 200, "success"

    def change_service_type(self, tenant, service, extend_method):
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
                            msg="local storage only support state_singleton", msg_show="本地存储仅支持有状态组件")
                if tenant_service_volume.get("access_mode", "") == "RWO":
                    if not is_state(extend_method):
                        raise ServiceHandleException(msg="storage access mode do not support",
                                                     msg_show="存储读写属性限制,不可修改为无状态组件")
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
        try:
            region_api.update_service(service.service_region, tenant.tenant_name, service.service_alias, data)
            service.extend_method = extend_method
            service.save()
        except region_api.CallApiError as e:
            logger.exception(e)
            raise ErrChangeServiceType

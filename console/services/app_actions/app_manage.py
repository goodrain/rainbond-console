# -*- coding: utf8 -*-
"""
  Created on 18/1/24.
"""
from django.conf import settings
import datetime
import json

from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.share_repo import share_repo
from console.services.app_actions import AppEventService
from console.services.app_config import AppServiceRelationService, AppEnvVarService, AppVolumeService, AppPortService
from www.apiclient.regionapi import RegionInvokeApi
from www.tenantservice.baseservice import TenantUsedResource, BaseTenantService
import logging
from console.repositories.app_config import env_var_repo, mnt_repo, volume_repo, port_repo, \
    auth_repo, domain_repo, dep_relation_repo, service_attach_repo, create_step_repo, service_payment_repo, extend_repo
from console.repositories.app import service_repo, recycle_bin_repo, service_source_repo, delete_service_repo, \
    relation_recycle_bin_repo
from console.constants import AppConstants
from console.repositories.group import group_service_relation_repo, tenant_service_group_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.plugin import app_plugin_relation_repo
from console.repositories.perm_repo import service_perm_repo
from console.repositories.compose_repo import compose_relation_repo
from console.repositories.label_repo import service_label_repo
from www.utils.crypt import make_uuid
from console.repositories.event_repo import event_repo
from console.repositories.app_config import tcp_domain


tenantUsedResource = TenantUsedResource()
event_service = AppEventService()
region_api = RegionInvokeApi()
logger = logging.getLogger("default")
baseService = BaseTenantService()
relation_service = AppServiceRelationService()
env_var_service = AppEnvVarService()
port_service = AppPortService()
volume_service = AppVolumeService()


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
            # 将原有免费用户的服务设置为7天后
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
        """查询当前应用占用的内存"""
        memory = 0
        try:
            body = region_api.check_service_status(cur_service.service_region, tenant.tenant_name,
                                                   cur_service.service_alias, tenant.enterprise_id)
            status = body["bean"]["cur_status"]
            # 占用内存的状态
            occupy_memory_status = ("starting", "running",)
            if status not in occupy_memory_status:
                memory = cur_service.min_node * cur_service.min_memory
        except Exception:
            pass
        return memory

    def is_operate_over_resource(self, tenant, service, new_add_memory, is_check_status):
        """

        :param tenant: 租户
        :param service: 服务
        :param new_add_memory: 新添加的内存
        :param is_check_status: 是否检测当前服务状态
        :return:
        """
        if self.MODULES["Memory_Limit"]:
            if is_check_status:
                new_add_memory = new_add_memory + self.cur_service_memory(tenant, service)
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
        from console.services.app import app_service
        new_add_memory = service.min_memory * service.min_node
        allow_start, tips = app_service.verify_source(tenant, service.service_region, new_add_memory,
                                                      "start_app")
        if not allow_start:
            return 412, "资源不足，无法启动应用", None

        code, msg, event = event_service.create_event(tenant, service, user, self.START)
        if code != 200:
            return code, msg, event

        if service.create_status == "complete":
            body = dict()
            body["deploy_version"] = service.deploy_version
            body["operator"] = str(user.nick_name)
            body["event_id"] = event.event_id
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.start_service(service.service_region, tenant.tenant_name, service.service_alias,
                                         body)
                logger.debug("user {0} start app !".format(user.nick_name))
            except region_api.CallApiError as e:
                logger.exception(e)
                if event:
                    event.message = u"启动应用失败".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                return 507, u"服务异常", event
        else:
            event = event_service.update_event(event, "应用未在数据中心创建", "failure")
        return 200, u"操作成功", event

    def stop(self, tenant, service, user):
        code, msg, event = event_service.create_event(tenant, service, user, self.STOP)
        if code != 200:
            return code, msg, event

        if service.create_status == "complete":
            body = dict()
            body["operator"] = str(user.nick_name)
            body["event_id"] = event.event_id
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.stop_service(service.service_region,
                                        tenant.tenant_name,
                                        service.service_alias,
                                        body)
                logger.debug("user {0} stop app !".format(user.nick_name))
            except region_api.CallApiError as e:
                logger.exception(e)
                if event:
                    event.message = u"启动停止失败{0}".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                return 507, u"服务异常", event
        else:
            event = event_service.update_event(event, "应用未在数据中心创建", "failure")

        return 200, u"操作成功", event

    def restart(self, tenant, service, user):
        code, msg, event = event_service.create_event(tenant, service, user, self.RESTART)
        if code != 200:
            return code, msg, event

        if service.create_status == "complete":
            body = dict()
            body["operator"] = str(user.nick_name)
            body["event_id"] = event.event_id
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.restart_service(service.service_region,
                                           tenant.tenant_name,
                                           service.service_alias,
                                           body)
                logger.debug("user {0} retart app !".format(user.nick_name))
            except region_api.CallApiError as e:
                logger.exception(e)
                if event:
                    event.message = u"启动重启失败".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                return 507, u"服务异常", event
        else:
            event = event_service.update_event(event, "应用未在数据中心创建", "failure")

        return 200, u"操作成功", event

    def deploy(self, tenant, service, user, is_upgrade, group_version, committer_name=None):
        code, msg, event = event_service.create_event(tenant, service, user, self.DEPLOY, committer_name)
        if code != 200:
            return code, msg, event

        body = dict()
        # 默认更新升级
        body["action"] = "deploy"
        service.build_upgrade = False
        if is_upgrade:
            body["action"] = "upgrade"
            service.build_upgrade = True
        service.deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        service.save()
        event.deploy_version = service.deploy_version
        event.save()

        clone_url = service.git_url

        body["deploy_version"] = service.deploy_version
        body["operator"] = str(user.nick_name)
        body["event_id"] = event.event_id
        body["service_id"] = service.service_id
        envs = env_var_repo.get_build_envs(tenant.tenant_id, service.service_id)
        body["envs"] = envs

        kind = self.__get_service_kind(service)
        service_source = service_source_repo.get_service_source(service.tenant_id, service.service_id)
        if kind == "build_from_source_code" or kind == "source":
            body["repo_url"] = clone_url
            body["branch"] = service.code_version
            body["server_type"] = service.server_type

        if service.service_source == "market":
            try:
                # 获取组对象
                group_obj = tenant_service_group_repo.get_group_by_service_group_id(service.tenant_service_group_id)
                if group_obj:
                    # 获取内部市场对象
                    if group_version:
                        rain_app = rainbond_app_repo.get_enterpirse_app_by_key_and_version(tenant.enterprise_id, group_obj.group_key,
                                                                                         group_version)
                    else:
                        rain_app = rainbond_app_repo.get_enterpirse_app_by_key_and_version(tenant.enterprise_id, group_obj.group_key,
                                                                                         group_obj.group_version)
                    if rain_app:
                        # 解析app_template的json数据
                        apps_template = json.loads(rain_app.app_template)
                        apps_list = apps_template.get("apps")
                        if service_source and service_source.extend_info:
                            extend_info = json.loads(service_source.extend_info)
                            for app in apps_list:
                                if app["service_share_uuid"] == extend_info["source_service_share_uuid"]:
                                    # 如果是slug包，获取内部市场最新的数据保存（如果是最新，就获取最新，不是最新就获取之前的）
                                    share_image = app.get("share_image", None)
                                    share_slug_path = app.get("share_slug_path", None)
                                    new_extend_info = {}
                                    if share_image:
                                        if app.get("service_image", None):
                                            body["image_url"] = share_image
                                            body["user"] = app.get("service_image").get("hub_user")
                                            body["password"] = app.get("service_image").get("hub_password")
                                            new_extend_info = app["service_image"]
                                    if share_slug_path:
                                        slug_info = app.get("service_slug")
                                        slug_info["slug_path"] = share_slug_path
                                        new_extend_info = slug_info
                                        body["slug_info"] = new_extend_info
                                    # 如果是image，获取内部市场最新镜像版本保存（如果是最新，就获取最新，不是最新就获取之前的， 不会报错）
                                    service.cmd = app.get("cmd", "")
                                    service.version = app["version"]
                                    service.is_upgrate = False
                                    service.save()
                                    new_extend_info["source_deploy_version"] = app.get("deploy_version")
                                    new_extend_info["source_service_share_uuid"] = app.get("service_share_uuid")  \
                                        if app.get("service_share_uuid", None)\
                                        else app.get("service_key", "")
                                    service_source.extend_info = json.dumps(new_extend_info)
                                    service_source.save()

                                    # 删除服务原有端口，环境变量，pod
                                    code, msg = self.__delete_envs(tenant, service)
                                    if code != 200:
                                        raise Exception(msg)
                                    code, msg = self.__delete_volume(tenant, service)
                                    if code != 200:
                                        raise Exception(msg)

                                    # 先保存env,再保存端口，因为端口需要处理env
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

                                    # 保存应用探针信息
                                    self.__save_extend_info(service, app["extend_method_map"])

                        group_obj.group_version = rain_app.version
                        group_obj.save()
            except Exception as e:
                logger.exception('===========000============>'.format(e))
                body["image_url"] = service.image
                if service_source:
                    extend_info = json.loads(service_source.extend_info)
                    if service.is_slug():
                        body["slug_info"] = extend_info
        else:
            body["image_url"] = service.image
        body["kind"] = kind
        body["service_alias"] = service.service_alias
        body["service_name"] = service.service_name
        body["tenant_name"] = tenant.tenant_name
        body["enterprise_id"] = tenant.enterprise_id
        body["lang"] = service.language
        body["cmd"] = service.cmd
        if service_source:
            if service_source.user_name or service_source.password:
                body["user"] = service_source.user_name
                body["password"] = service_source.password
            if service_source.extend_info:
                extend_info = json.loads(service_source.extend_info)
                if not service.is_slug():
                    hub_user = extend_info.get("hub_user", None)
                    hub_password = extend_info.get("hub_password", None)
                    if hub_user or hub_password:
                        body["user"] = hub_user
                        body["password"] = hub_password
        logger.debug('-------------deploy-----body-------------------->{0}'.format(json.dumps(body)))
        try:
            region_api.build_service(service.service_region, tenant.tenant_name, service.service_alias, body)
        except region_api.CallApiError as e:
            logger.exception(e)
            if event:
                event.message = u"应用构建失败".format(e.message)
                event.final_status = "complete"
                event.status = "failure"
                event.save()
            return 507, "构建异常", event

        return 200, "操作成功", event

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
            if volume.has_key("file_content"):
                code, msg, volume_data = volume_service.add_service_volume(tenant, service, volume["volume_path"],
                                                                           volume["volume_type"], volume["volume_name"],
                                                                           volume["file_content"])
                if code != 200:
                    logger.error("save market app volume error".format(msg))
                    return code, msg
            else:
                code, msg, volume_data = volume_service.add_service_volume(tenant, service, volume["volume_path"],
                                                                           volume["volume_type"], volume["volume_name"])
                if code != 200:
                    logger.error("save market app volume error".format(msg))
                    return code, msg
        return 200, "success"

    def __save_env(self, tenant, service, inner_envs, outer_envs):
        if not inner_envs and not outer_envs:
            return 200, "success"
        for env in inner_envs:
            code, msg, env_data = env_var_service.add_service_env_var(tenant, service, 0, env["name"], env["attr_name"],
                                                                      env["attr_value"], env["is_change"],
                                                                      "inner")
            if code != 200:
                logger.error("save market app env error {0}".format(msg))
                return code, msg
        for env in outer_envs:
            container_port = env.get("container_port", 0)
            if container_port == 0:
                if env["attr_value"] == "**None**":
                    env["attr_value"] = service.service_id[:8]
                code, msg, env_data = env_var_service.add_service_env_var(tenant, service, container_port,
                                                                          env["name"], env["attr_name"],
                                                                          env["attr_value"], env["is_change"],
                                                                          "outer")
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
                    code, msg, data = env_var_service.add_service_env_var(tenant, service, int(port["container_port"]), u"连接地址",
                                                                          env_prefix + "_HOST", "127.0.0.1", False,
                                                                          scope="outer")
                    if code != 200:
                        return code, msg, None
                    code, msg, data = env_var_service.add_service_env_var(tenant, service, int(port["container_port"]), u"端口",
                                                                          env_prefix + "_PORT", mapping_port, False,
                                                                          scope="outer")
                    if code != 200:
                        return code, msg, None

                continue
            code, msg, port_data = port_service.add_service_port(tenant, service,
                                                                 int(port["container_port"]),
                                                                 port["protocol"],
                                                                 port["port_alias"],
                                                                 port["is_inner_service"],
                                                                 port["is_outer_service"])
            if code != 200:
                logger.error("save market app port error".format(msg))
                return code, msg
        return 200, "success"

    def upgrade(self, tenant, service, user, committer_name=None):
        code, msg, event = event_service.create_event(tenant, service, user, self.UPGRADE, committer_name)
        if code != 200:
            return code, msg, event

        body = dict()

        event.deploy_version = service.deploy_version
        event.save()

        body["deploy_version"] = service.deploy_version
        body["service_name"] = service.service_name
        body["event_id"] = event.event_id
        try:
            region_api.upgrade_service(service.service_region, tenant.tenant_name, service.service_alias, body)
        except region_api.CallApiError as e:
            logger.exception(e)
            if event:
                event.message = u"应用更新失败".format(e.message)
                event.final_status = "complete"
                event.status = "failure"
                event.save()
            return 507, "更新异常", event

        return 200, "操作成功", event

    def __get_service_kind(self, service):
        """获取应用种类，兼容老的逻辑"""
        if service.service_source:
            if service.service_source == AppConstants.SOURCE_CODE:
                # return "source"
                return "build_from_source_code"
            elif service.service_source == AppConstants.DOCKER_RUN or service.service_source == AppConstants.DOCKER_COMPOSE or service.service_source == AppConstants.DOCKER_IMAGE:
                # return "image"
                return "build_from_image"
            elif service.service_source == AppConstants.MARKET:
                if service.image.startswith('goodrain.me/runner') and service.language not in ("dockerfile", "docker"):
                    return "build_from_market_slug"
                else:
                    return "build_from_market_image"
        else:
            kind = "build_from_image"
            if service.category == "application":
                kind = "build_from_source_code"
            if service.category == "app_publish":
                kind = "build_from_market_image"
                if service.image.startswith('goodrain.me/runner') and service.language not in ("dockerfile", "docker"):
                    kind = "build_from_market_slug"
                if service.service_key == "0000":
                    kind = "build_from_image"
            return kind

    def roll_back(self, tenant, service, user, deploy_version, upgrade_or_rollback):
        if int(upgrade_or_rollback) == 1:
            code, msg, event = event_service.create_event(tenant, service, user, self.UPGRADE)
        else:
            code, msg, event = event_service.create_event(tenant, service, user, self.ROLLBACK)
        if code != 200:
            return code, msg, event
        if service.create_status == "complete":
            if deploy_version == service.deploy_version:
                event.delete()
                return 409, u"当前版本与所需回滚版本一致，无需回滚", None

            res, data = region_api.get_service_build_version_by_id(service.service_region, tenant.tenant_name,
                                                                   service.service_alias, deploy_version)
            is_version_exist = data['bean']['status']
            if not is_version_exist:
                event.delete()
                return 404, u"当前版本可能已被系统清理或删除", event

            body = dict()
            body["event_id"] = event.event_id
            body["operator"] = str(user.nick_name)
            body["deploy_version"] = deploy_version
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.rollback(service.service_region, tenant.tenant_name, service.service_alias,
                                    body)
                service.deploy_version = deploy_version
                service.save()
                event.deploy_version = deploy_version
                event.save()
            except region_api.CallApiError as e:
                logger.exception(e)
                if event:
                    event.message = u"启动回滚失败".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                return 507, u"服务异常", event
        else:
            event = event_service.update_event(event, "应用未在数据中心创建", "failure")
        return 200, u"操作成功", event

    def batch_action(self, tenant, user, action, service_ids, move_group_id):
        services = service_repo.get_services_by_service_ids(*service_ids)
        code = 500
        msg = "系统异常"
        fail_service_name = []
        for service in services:
            try:
                # 三方服务不具备启动，停止，重启操作
                if action == "start" and service.service_source != "third_party":
                    self.start(tenant, service, user)
                elif action == "stop" and service.service_source != "third_party":
                    self.stop(tenant, service, user)
                elif action == "restart" and service.service_source != "third_party":
                    self.restart(tenant, service, user)
                elif action == "move":
                    self.move(service, move_group_id)
                elif action == "deploy" and service.service_source != "third_party":
                    self.deploy(tenant, service, user, is_upgrade=True, group_version=None)
                code = 200
                msg = "success"
            except Exception as e:
                fail_service_name.append(service.service_cname)
                logger.exception(e)
        logger.debug("fail service names {0}".format(fail_service_name))
        return code, msg

    # 5.1新版批量操作（启动，关闭，构建）
    def batch_operations(self, tenant, user, action, service_ids):
        services = service_repo.get_services_by_service_ids(*service_ids)
        try:
            # 获取所有服务信息
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
            logger.debug('-===================---bodybody----------->{0}'.format(json.dumps(data)))
            if code != 200:
                return 415, "服务信息获取失败"
            # 获取数据中心信息
            one_service = services[0]
            region_name = one_service.service_region
            try:
                logger.debug('--------12222222222----___>{0}'.format(json.dumps(data)))
                region_api.batch_operation_service(region_name, tenant.tenant_name, data)
                return 200, "操作成功"
            except region_api.CallApiError as e:
                logger.exception(e)
                return 500, "数据中心操作失败"
        except Exception as e:
            logger.exception(e)
            return 500, "系统异常"

    def start_services_info(self, body, services, tenant, user):
        body["operation"] = "start"
        start_infos_list = []
        body["start_infos"] = start_infos_list
        for service in services:
            from console.services.app import app_service
            if service.service_source == "":
                continue
            service_dict = dict()
            new_add_memory = service.min_memory * service.min_node
            allow_start, tips = app_service.verify_source(tenant, service.service_region, new_add_memory,
                                                          "start_app")
            if not allow_start:
                continue
            code, msg, event = event_service.create_event(tenant, service, user, self.START)
            if code != 200:
                continue

            if service.create_status == "complete":
                service_dict["event_id"] = event.event_id
                service_dict["service_id"] = service.service_id

                start_infos_list.append(service_dict)
            else:
                event = event_service.update_event(event, "应用未在数据中心创建", "failure")
                continue
        return 200, body

    def stop_services_info(self, body, services, tenant, user):
        logger.debug('--------------__>{0}'.format(body))
        body["operation"] = "stop"
        stop_infos_list = []
        body["stop_infos"] = stop_infos_list
        for service in services:
            service_dict = dict()
            code, msg, event = event_service.create_event(tenant, service, user, self.STOP)
            if code != 200:
                continue
            if service.create_status == "complete":
                service_dict["event_id"] = event.event_id
                service_dict["service_id"] = service.service_id
                stop_infos_list.append(service_dict)
            else:
                event = event_service.update_event(event, "应用未在数据中心创建", "failure")
                continue
        return 200, body

    def upgrade_services_info(self, body, services, tenant, user):
        body["operation"] = "upgrade"
        upgrade_infos_list = []
        body["upgrade_infos"] = upgrade_infos_list
        for service in services:
            service_dict = dict()
            code, msg, event = event_service.create_event(tenant, service, user, self.UPGRADE)
            if code != 200:
                continue
            if service.create_status == "complete":
                service_dict["event_id"] = event.event_id
                service_dict["service_id"] = service.service_id
                service_dict["upgrade_version"] = service.deploy_version

                upgrade_infos_list.append(service_dict)
            else:
                event = event_service.update_event(event, "应用未在数据中心创建", "failure")
                continue
        return 200, body

    def deploy_services_info(self, body, services, tenant, user):
        body["operation"] = "build"
        deploy_infos_list = []
        body["build_infos"] = deploy_infos_list
        for service in services:
            service_dict = dict()
            code, msg, event = event_service.create_event(tenant, service, user, self.DEPLOY)
            if code != 200:
                continue
            service.deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            service.save()
            event.deploy_version = service.deploy_version
            event.save()

            service_dict["event_id"] = event.event_id
            service_dict["service_id"] = service.service_id
            service_dict["deploy_version"] = service.deploy_version

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
                if service_source:
                    if service_source.user_name or service_source.password:
                        source_code["user"] = service_source.user_name
                        source_code["password"] = service_source.password
                    if service_source.extend_info:
                        extend_info = json.loads(service_source.extend_info)
                        if not service.is_slug():
                            hub_user = extend_info.get("hub_user", None)
                            hub_password = extend_info.get("hub_password", None)
                            if hub_user or hub_password:
                                source_code["user"] = hub_user
                                source_code["password"] = hub_password
            # 镜像
            elif kind == "build_from_image":
                source_image = dict()
                service_dict["image_info"] = source_image
                source_image["image_url"] = service.image
                source_image["cmd"] = service.cmd
                if service_source:
                    if service_source.user_name or service_source.password:
                        source_image["user"] = service_source.user_name
                        source_image["password"] = service_source.password
                    if service_source.extend_info:
                        extend_info = json.loads(service_source.extend_info)
                        if not service.is_slug():
                            hub_user = extend_info.get("hub_user", None)
                            hub_password = extend_info.get("hub_password", None)
                            if hub_user or hub_password:
                                source_image["user"] = hub_user
                                source_image["password"] = hub_password

            # 云市
            elif service.service_source == "market":
                try:
                    # 获取组对象
                    group_obj = tenant_service_group_repo.get_group_by_service_group_id(service.tenant_service_group_id)
                    if group_obj:
                        # 获取内部市场对象
                        rain_app = rainbond_app_repo.get_rainbond_app_by_key_and_version(group_obj.group_key,
                                                                                         group_obj.group_version)
                        if rain_app:
                            # 解析app_template的json数据
                            apps_template = json.loads(rain_app.app_template)
                            apps_list = apps_template.get("apps")
                            if service_source and service_source.extend_info:
                                extend_info = json.loads(service_source.extend_info)
                                for app in apps_list:
                                    if app.has_key("service_share_uuid"):
                                        if app["service_share_uuid"] == extend_info["source_service_share_uuid"]:
                                            # 如果是slug包，获取内部市场最新的数据保存（如果是最新，就获取最新，不是最新就获取之前的）
                                            share_image = app.get("share_image", None)
                                            share_slug_path = app.get("share_slug_path", None)
                                            new_extend_info = {}
                                            if share_image:
                                                if app.get("service_image", None):
                                                    source_image = dict()
                                                    service_dict["image_info"] = source_image
                                                    source_image["image_url"] = share_image
                                                    source_image["user"] = app.get("service_image").get("hub_user")
                                                    source_image["password"] = app.get("service_image").get("hub_password")
                                                    source_image["cmd"] = service.cmd
                                                    new_extend_info = app["service_image"]
                                            if share_slug_path:
                                                slug_info = app.get("service_slug")
                                                slug_info["slug_path"] = share_slug_path
                                                new_extend_info = slug_info
                                                service_dict["slug_info"] = new_extend_info
                                            # 如果是image，获取内部市场最新镜像版本保存（如果是最新，就获取最新，不是最新就获取之前的， 不会报错）
                                            service.is_upgrate = False
                                            service.save()
                                            new_extend_info["source_deploy_version"] = app.get("deploy_version")
                                            new_extend_info["source_service_share_uuid"] = app.get("service_share_uuid") \
                                                if app.get("service_share_uuid", None) \
                                                else app.get("service_key", "")
                                            service_source.extend_info = json.dumps(new_extend_info)
                                            service_source.save()

                                            # 删除服务原有端口，环境变量，pod
                                            code, msg = self.__delete_envs(tenant, service)
                                            if code != 200:
                                                raise Exception(msg)
                                            code, msg = self.__delete_volume(tenant, service)
                                            if code != 200:
                                                raise Exception(msg)

                                            # 先保存env,再保存端口，因为端口需要处理env
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

                                            # 保存应用探针信息
                                            self.__save_extend_info(service, app["extend_method_map"])

                                    if not app.has_key("service_share_uuid") and app.has_key("service_key"):
                                        if app["service_key"] == extend_info["source_service_share_uuid"]:
                                            # 如果是slug包，获取内部市场最新的数据保存（如果是最新，就获取最新，不是最新就获取之前的）
                                            share_image = app.get("share_image", None)
                                            share_slug_path = app.get("share_slug_path", None)
                                            new_extend_info = {}
                                            if share_image:
                                                if app.get("service_image", None):
                                                    source_image = dict()
                                                    service_dict["image_info"] = source_image
                                                    source_image["image_url"] = share_image
                                                    source_image["user"] = app.get("service_image").get("hub_user")
                                                    source_image["password"] = app.get("service_image").get(
                                                        "hub_password")
                                                    source_image["cmd"] = service.cmd
                                                    new_extend_info = app["service_image"]
                                            if share_slug_path:
                                                slug_info = app.get("service_slug")
                                                slug_info["slug_path"] = share_slug_path
                                                new_extend_info = slug_info
                                                service_dict["slug_info"] = new_extend_info
                                            # 如果是image，获取内部市场最新镜像版本保存（如果是最新，就获取最新，不是最新就获取之前的， 不会报错）
                                            service.is_upgrate = False
                                            service.save()
                                            new_extend_info["source_deploy_version"] = app.get("deploy_version")
                                            new_extend_info["source_service_share_uuid"] = app.get("service_share_uuid") \
                                                if app.get("service_share_uuid", None) \
                                                else app.get("service_key", "")
                                            service_source.extend_info = json.dumps(new_extend_info)
                                            service_source.save()

                                            # 删除服务原有端口，环境变量，pod
                                            code, msg = self.__delete_envs(tenant, service)
                                            if code != 200:
                                                raise Exception(msg)
                                            code, msg = self.__delete_volume(tenant, service)
                                            if code != 200:
                                                raise Exception(msg)

                                            # 先保存env,再保存端口，因为端口需要处理env
                                            code, msg = self.__save_env(tenant, service, app["service_env_map_list"],
                                                                        app["service_connect_info_map_list"])
                                            if code != 200:
                                                raise Exception(msg)
                                            code, msg = self.__save_volume(tenant, service,
                                                                           app["service_volume_map_list"])
                                            if code != 200:
                                                raise Exception(msg)
                                            logger.debug('-------222---->{0}'.format(app["port_map_list"]))

                                            code, msg = self.__save_port(tenant, service, app["port_map_list"])
                                            if code != 200:
                                                raise Exception(msg)

                                            # 保存应用探针信息
                                            self.__save_extend_info(service, app["extend_method_map"])

                            group_obj.group_version = rain_app.version
                            group_obj.save()
                except Exception as e:
                    logger.exception('===========000============>'.format(e))
                    if service_source:
                        extend_info = json.loads(service_source.extend_info)
                        if service.is_slug():
                            service_dict["slug_info"] = extend_info

            deploy_infos_list.append(service_dict)
        return 200, body

    def vertical_upgrade(self, tenant, service, user, new_memory):
        """服务水平升级"""
        new_memory = int(new_memory)
        if new_memory > 16384 or new_memory < 128:
            return 400, "内存范围在128M到16G之间", None
        if new_memory % 128 != 0:
            return 400, "内存必须为128的倍数", None
        if new_memory == service.min_memory:
            return 409, "内存没有变化，无需升级", None

        code, msg, event = event_service.create_event(tenant, service, user, self.VERTICAL_UPGRADE)
        if code != 200:
            return code, msg, event
        new_cpu = baseService.calculate_service_cpu(service.service_region, new_memory)
        if service.create_status == "complete":
            body = dict()
            body["container_memory"] = new_memory
            body["deploy_version"] = service.deploy_version
            body["container_cpu"] = new_cpu
            body["operator"] = str(user.nick_name)
            body["event_id"] = event.event_id
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.vertical_upgrade(service.service_region,
                                            tenant.tenant_name,
                                            service.service_alias,
                                            body)
                service.min_cpu = new_cpu
                service.min_memory = new_memory
                service.save()
            except region_api.CallApiError as e:
                logger.exception(e)
                if event:
                    event.message = u"应用垂直升级失败".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                return 507, u"服务异常", event
        else:
            event = event_service.update_event(event, "应用未在数据中心创建", "failure")

        return 200, u"操作成功", event

    def horizontal_upgrade(self, tenant, service, user, new_node):
        """服务水平升级"""
        new_node = int(new_node)
        if new_node > 20 or new_node < 0:
            return 400, "节点数量需在1到20之间"
        if new_node == service.min_node:
            return 409, "节点没有变化，无需升级", None

        code, msg, event = event_service.create_event(tenant, service, user, self.HORIZONTAL_UPGRADE)
        if code != 200:
            return code, msg, event
        if service.create_status == "complete":
            body = dict()
            body["node_num"] = new_node
            body["deploy_version"] = service.deploy_version
            body["operator"] = str(user.nick_name)
            body["event_id"] = event.event_id
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.horizontal_upgrade(service.service_region, tenant.tenant_name,
                                              service.service_alias, body)
                service.min_node = new_node
                service.save()
            except region_api.CallApiError as e:
                logger.exception(e)
                if event:
                    event.message = u"应用水平升级失败".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                return 507, u"服务异常", event
        else:
            event = event_service.update_event(event, "应用未在数据中心创建", "failure")

        return 200, u"操作成功", event

    def delete(self, user, tenant, service, is_force):
        code, msg, event = event_service.create_event(tenant, service, user, self.DELETE)
        if code != 200:
            return code, msg, event
        # 判断服务是否是运行状态
        if self.__is_service_running(tenant, service) and service.service_source != "third_party":
            msg = u"应用可能处于运行状态,请先关闭应用"
            event = event_service.update_event(event, msg, "failure")
            return 409, msg, event
        # 判断服务是否被依赖
        is_related, msg = self.__is_service_related(tenant, service)
        if is_related:
            event = event_service.update_event(event, "被依赖, 不可删除", "failure")
            return 412, "服务被{0}依赖，不可删除".format(msg), event
        # 判断服务是否被其他应用挂载
        is_mounted, msg = self.__is_service_mnt_related(tenant, service)
        if is_mounted:
            event = event_service.update_event(event, "当前应用被其他应用挂载, 不可删除", "failure")
            return 412, "当前应用被{0}挂载, 不可删除".format(msg), event
        # 判断服务是否绑定了域名
        is_bind_domain = self.__is_service_bind_domain(service)
        if is_bind_domain:
            event = event_service.update_event(event, "当前应用已绑定域名,请先解绑", "failure")
            return 412, "请先解绑应用绑定的域名", event
        # 判断是否有插件
        if self.__is_service_has_plugins(service):
            event = event_service.update_event(event, "当前应用已安装插件,请先卸载相关插件", "failure")
            return 412, "请先卸载应用安装的插件", event

        if not is_force:
            # 如果不是真删除，将数据备份,删除tenant_service表中的数据
            self.move_service_into_recycle_bin(service)
            # 服务关系移除
            self.move_service_relation_info_recycle_bin(tenant, service)

            return 200, "success", event
        else:
            try:
                code, msg = self.truncate_service(tenant, service, user)
                if code != 200:
                    event = event_service.update_event(event, msg, "failure")
                    return code, msg, event
                else:
                    return code, "success", event
            except Exception as e:
                logger.exception(e)
                if event:
                    event.message = u"应用删除".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                return 507, u"删除异常", event

    def truncate_service(self, tenant, service, user=None):
        """彻底删除应用"""

        try:
            region_api.delete_service(service.service_region, tenant.tenant_name, service.service_alias,
                                      tenant.enterprise_id)
        except region_api.CallApiError as e:
            if int(e.status) != 404:
                logger.exception(e)
                return 500, "删除应用失败 {0}".format(e.message)
        if service.create_status == "complete":
            data = service.toJSON()
            data.pop("ID")
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
        # 如果这个应用属于应用组, 则删除应用组最后一个应用后同时删除应用组
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
                "deploy_version": service.deploy_version,
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
        """将服务移入回收站"""
        data = service.toJSON()
        data.pop("ID")
        trash_service = recycle_bin_repo.create_trash_service(**data)

        # 如果这个应用属于应用组, 则删除应用组最后一个应用后同时删除应用组
        if service.tenant_service_group_id > 0:
            count = service_repo.get_services_by_service_group_id(service.tenant_service_group_id).count()
            if count <= 1:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(service.tenant_service_group_id)

        service.delete()
        return trash_service

    def move_service_relation_info_recycle_bin(self, tenant, service):
        # 1.如果服务依赖其他服务，将服务对应的关系放入回收站
        relations = dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id)
        if relations:
            for r in relations:
                r_data = r.to_dict()
                r_data.pop("ID")
                relation_recycle_bin_repo.create_trash_service_relation(**r_data)
                r.delete()
        # 如果服务关系回收站有被此服务依赖的服务，将信息及其对应的数据中心的依赖关系删除
        recycle_relations = relation_recycle_bin_repo.get_by_dep_service_id(service.service_id)
        if recycle_relations:
            for recycle_relation in recycle_relations:
                task = dict()
                task["dep_service_id"] = recycle_relation.dep_service_id
                task["tenant_id"] = tenant.tenant_id
                task["dep_service_type"] = "v"
                task["enterprise_id"] = tenant.enterprise_id
                try:
                    region_api.delete_service_dependency(service.service_region, tenant.tenant_name,
                                                         service.service_alias,
                                                         task)
                except Exception as e:
                    logger.exception(e)
                recycle_relation.delete()

    def __is_service_bind_domain(self, service):
        domains = domain_repo.get_service_domains(service.service_id)
        if not domains:
            return False
        elif len(domains) == 1:
            for domain in domains:
                if domain.type == 0:
                    return False
                else:
                    return True
        return True

    def __is_service_mnt_related(self, tenant, service):
        sms = mnt_repo.get_mount_current_service(tenant.tenant_id, service.service_id)
        if sms:
            sids = [sm.service_id for sm in sms]
            services = service_repo.get_services_by_service_ids(*sids).values_list("service_cname", flat=True)
            mnt_service_names = ",".join(list(services))
            return True, mnt_service_names
        return False, ""

    def __is_service_related(self, tenant, service):
        tsrs = dep_relation_repo.get_dependency_by_dep_id(tenant.tenant_id, service.service_id)
        if tsrs:
            sids = [tsr.service_id for tsr in tsrs]
            services = service_repo.get_services_by_service_ids(*sids).values_list("service_cname", flat=True)
            if not services:
                return False, ""
            dep_service_names = ",".join(list(services))
            return True, dep_service_names
        return False, ""

    def __is_service_running(self, tenant, service):
        try:
            if service.create_status != "complete":
                return False
            status_info = region_api.check_service_status(service.service_region, tenant.tenant_name,
                                                          service.service_alias, tenant.enterprise_id)
            status = status_info["bean"]["cur_status"]
            if status in ("running", "starting", "stopping", "failure", "unKnow", "unusual", "abnormal", "some_abnormal"):
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
            region_api.delete_service(service.service_region, tenant.tenant_name, service.service_alias,
                                      tenant.enterprise_id)
            return 200, "success"
        except region_api.CallApiError as e:
            if e.status != 404:
                logger.exception(e)
                return 500, "数据中心删除失败"
            return 200, "success"

    # 变更应用分组
    def move(self, service, move_group_id):
        # 先删除分组应用关系表中该应用数据
        group_service_relation_repo.delete_relation_by_service_id(service_id=service.service_id)
        # 再新建该应用新的关联数据
        group_service_relation_repo.add_service_group_relation(move_group_id, service.service_id, service.tenant_id,
                                                               service.service_region)

    # 批量删除应用
    def batch_delete(self, user, tenant, service, is_force):
        code, msg, event = event_service.create_event(tenant, service, user, self.DELETE)
        if code != 200:
            return code, msg, event
        # 判断服务是否是运行状态
        if self.__is_service_running(tenant, service) and service.service_source != "third_party":
            msg = "当前应用处于运行状态,请先关闭应用"
            event = event_service.update_event(event, msg, "failure")
            code = 409
            return code, msg, event
        # 判断服务是否被其他应用挂载
        is_mounted, msg = self.__is_service_mnt_related(tenant, service)
        if is_mounted:
            event = event_service.update_event(event, "当前应用被其他应用挂载", "failure")
            code = 412
            msg = "当前应用被其他应用挂载, 您确定要删除吗？"
            return code, msg, event
        # 判断服务是否绑定了域名
        is_bind_domain = self.__is_service_bind_domain(service)
        if is_bind_domain:
            event = event_service.update_event(event, "当前应用已绑定域名", "failure")
            code = 412
            msg = "当前应用绑定了域名， 您确定要删除吗？"
            return code, msg, event
        # 判断是否有插件
        if self.__is_service_has_plugins(service):
            event = event_service.update_event(event, "当前应用已安装插件", "failure")
            code = 412
            msg = "当前应用安装了插件， 您确定要删除吗？"
            return code, msg, event

        if not is_force:
            # 如果不是真删除，将数据备份,删除tenant_service表中的数据
            self.move_service_into_recycle_bin(service)
            # 服务关系移除
            self.move_service_relation_info_recycle_bin(tenant, service)
            code = 200
            msg = "success"
            return code, msg, event
        else:
            try:
                code, msg = self.truncate_service(tenant, service, user)
                if code != 200:
                    event = event_service.update_event(event, msg, "failure")
                    return code, msg, event
                else:
                    msg = "success"
                    return code, msg, event
            except Exception as e:
                logger.exception(e)
                if event:
                    event.message = u"应用删除".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                code = 507
                msg = "删除异常"
                return code, msg, event

    def delete_again(self, user, tenant, service, is_force):
        code, msg, event = event_service.create_event(tenant, service, user, self.DELETE)
        if code != 200:
            return code, msg, event
        if not is_force:
            # 如果不是真删除，将数据备份,删除tenant_service表中的数据
            self.move_service_into_recycle_bin(service)
            # 服务关系移除
            self.move_service_relation_info_recycle_bin(tenant, service)
            return 200, "success", event
        else:
            try:
                code, msg = self.again_delete_service(tenant, service, user)
                if code != 200:
                    event = event_service.update_event(event, msg, "failure")
                    return code, msg, event
                else:
                    return code, "success", event
            except Exception as e:
                logger.exception(e)
                if event:
                    event.message = u"应用删除".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                return 507, u"删除异常", event

    def again_delete_service(self, tenant, service, user=None):
        """二次删除应用"""

        try:
            region_api.delete_service(service.service_region, tenant.tenant_name, service.service_alias,
                                      tenant.enterprise_id)
        except region_api.CallApiError as e:
            if int(e.status) != 404:
                logger.exception(e)
                return 500, "删除应用失败 {0}".format(e.message)
        if service.create_status == "complete":
            data = service.toJSON()
            data.pop("ID")
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
        # 删除应用和插件的关系
        share_repo.delete_tenant_service_plugin_relation(service.service_id)
        # 如果这个应用属于应用组, 则删除应用组最后一个应用后同时删除应用组
        if service.tenant_service_group_id > 0:
            count = service_repo.get_services_by_service_group_id(service.tenant_service_group_id).count()
            if count <= 1:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(service.tenant_service_group_id)
        self.__create_service_delete_event(tenant, service, user)
        service.delete()
        return 200, "success"

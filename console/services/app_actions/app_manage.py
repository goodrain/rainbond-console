# -*- coding: utf8 -*-
"""
  Created on 18/1/24.
"""
from django.conf import settings
import datetime
import json
from console.services.app_actions import AppEventService
from console.services.app_config import AppServiceRelationService
from www.apiclient.regionapi import RegionInvokeApi
from www.tenantservice.baseservice import TenantUsedResource, BaseTenantService
import logging
from console.repositories.app_config import env_var_repo, mnt_repo, volume_repo, port_repo, \
    auth_repo, domain_repo, dep_relation_repo, service_attach_repo, create_step_repo, service_payment_repo
from console.repositories.app import service_repo, recycle_bin_repo, service_source_repo, delete_service_repo, relation_recycle_bin_repo
from console.constants import AppConstants
from console.repositories.group import group_service_relation_repo, tenant_service_group_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.plugin import app_plugin_relation_repo

tenantUsedResource = TenantUsedResource()
event_service = AppEventService()
region_api = RegionInvokeApi()
logger = logging.getLogger("default")
baseService = BaseTenantService()
relation_service = AppServiceRelationService()


class AppManageBase(object):
    def __init__(self):
        self.MODULES = settings.MODULES
        self.START = "restart"
        self.STOP = "stop"
        self.RESTART = "reboot"
        self.DELETE = "delete"
        self.DEPLOY = "deploy"
        self.ROLLBACK = "callback"
        self.VERTICAL_UPGRADE = "VerticalUpgrade"
        self.HORIZONTAL_UPGRADE = "HorizontalUpgrade"

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
                                                       "启动应用")
        if not allow_start:
            return 412, "资源不足，无法启动应用", None

        code, msg, event = event_service.create_event(tenant, service, user, self.START)
        if code != 200:
            return code, msg, event

        if service.create_status == "complete":
            body = {}
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
            body = {}
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
            body = {}
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

    def deploy(self, tenant, service, user):
        code, msg, event = event_service.create_event(tenant, service, user, self.DEPLOY)
        if code != 200:
            return code, msg, event

        body = {}
        if not service.deploy_version:
            body["action"] = "deploy"
        else:
            body["action"] = "upgrade"

        service.deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        service.save()
        event.deploy_version = service.deploy_version
        event.save()

        clone_url = service.git_url
        if service.code_from == "github":
            code_user = clone_url.split("/")[3]
            code_project_name = clone_url.split("/")[4].split(".")[0]
            clone_url = "https://" + user.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"

        body["deploy_version"] = service.deploy_version
        body["operator"] = str(user.nick_name)
        body["event_id"] = event.event_id
        body["service_id"] = service.service_id
        envs = env_var_repo.get_build_envs(tenant.tenant_id, service.service_id)
        body["envs"] = envs

        kind = self.__get_service_kind(service)
        if kind == "build_from_source_code" or kind == "source":
            body["repo_url"] = clone_url
            body["branch"] = service.code_version
        body["kind"] = kind
        body["service_alias"] = service.service_alias
        body["tenant_name"] = tenant.tenant_name
        body["enterprise_id"] = tenant.enterprise_id
        body["lang"] = service.language
        body["image_url"] = service.image
        service_source = service_source_repo.get_service_source(service.tenant_id, service.service_id)
        if service_source:
            if service_source.user_name or service_source.password:
                body["user"] = service_source.user_name
                body["password"] = service_source.password
            if service_source.extend_info:
                extend_info = json.loads(service_source.extend_info)
                if service.is_slug():
                    body["slug_info"] = extend_info
                else:
                    hub_user = extend_info.get("hub_user", None)
                    hub_password = extend_info.get("hub_password", None)
                    if hub_user or hub_password:
                        body["user"] = hub_user
                        body["password"] = hub_password

        try:
            region_api.build_service(service.service_region, tenant.tenant_name, service.service_alias, body)
        except region_api.CallApiError as e:
            logger.exception(e)
            if event:
                event.message = u"应用部署失败".format(e.message)
                event.final_status = "complete"
                event.status = "failure"
                event.save()
            return 507, "部署异常", event

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
                if service.image .startswith('goodrain.me/runner') and service.language not in ("dockerfile", "docker"):
                    return "build_from_market_slug"
                else:
                    return "build_from_market_image"
        else:
            kind = "build_from_image"
            if service.category == "application":
                kind = "build_from_source_code"
            if service.category == "app_publish":
                kind = "build_from_market_image"
                if service.image .startswith('goodrain.me/runner') and service.language not in ("dockerfile", "docker"):
                    kind = "build_from_market_slug"
                if service.service_key == "0000":
                    kind = "build_from_image"
            return kind

    def roll_back(self, tenant, service, user, deploy_version):
        code, msg, event = event_service.create_event(tenant, service, user, self.ROLLBACK)
        if code != 200:
            return code, msg, event
        if service.create_status == "complete":
            if deploy_version == service.deploy_version:
                return 409, u"当前版本与所需回滚版本一致，无需回滚", event
            body = {}
            body["event_id"] = event.event_id
            body["operator"] = str(user.nick_name)
            body["deploy_version"] = deploy_version
            body["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.rollback(service.service_region, tenant.tenant_name, service.service_alias,
                                    body)
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

    def batch_action(self, tenant, user, action, service_ids):
        services = service_repo.get_services_by_service_ids(*service_ids)
        code = 500
        msg = "系统异常"
        fail_service_name = []
        for service in services:
            try:
                if action == "start":
                    self.start(tenant, service, user)
                elif action == "stop":
                    self.stop(tenant, service, user)
                elif action == "restart":
                    self.restart(tenant, service, user)
                code = 200
                msg = "success"
            except Exception as e:
                fail_service_name.append(service.service_cname)
                logger.exception(e)
        logger.debug("fail service names {0}".format(fail_service_name))
        return code, msg

    def vertical_upgrade(self, tenant, service, user, new_memory):
        """服务水平升级"""
        new_memory = int(new_memory)
        if new_memory > 16384 or new_memory < 128:
            return 400, "内存范围在128M到16G之间", None
        if new_memory % 128 != 0:
            return 400, "内存必须为128的倍数", None
        if new_memory == service.min_memory:
            return 409, "内存没有变化，无需升级", None
        new_add_memory = new_memory * service.min_node - service.min_memory * service.min_node

        code, msg, event = event_service.create_event(tenant, service, user, self.VERTICAL_UPGRADE)
        if code != 200:
            return code, msg, event
        new_cpu = baseService.calculate_service_cpu(service.service_region, new_memory)
        if service.create_status == "complete":
            body = {}
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
            body = {}
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
        if self.__is_service_running(tenant, service):
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
            self.move_service_relation_info_recycle_bin(tenant,service)

            return 200, "success", event
        else:
            try:
                code, msg = self.truncate_service(tenant, service)
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

    def truncate_service(self, tenant, service):
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
            delete_service_repo.create_delete_service(**data)

        env_var_repo.delete_service_env(tenant.tenant_id, service.service_id)
        auth_repo.delete_service_auth(service.service_id)
        domain_repo.delete_service_domain(service.service_id)
        dep_relation_repo.delete_service_relation(tenant.tenant_id, service.service_id)
        env_var_repo.delete_service_env(tenant.tenant_id, service.service_id)
        mnt_repo.delete_mnt(service.service_id)
        port_repo.delete_service_port(tenant.tenant_id, service.service_id)
        volume_repo.delete_service_volumes(service.service_id)
        group_service_relation_repo.delete_relation_by_service_id(service.service_id)
        service_attach_repo.delete_service_attach(service.service_id)
        create_step_repo.delete_create_step(service.service_id)
        event_service.delete_service_events(service)
        probe_repo.delete_service_probe(service.service_id)
        service_payment_repo.delete_service_payment(service.service_id)
        # 如果这个应用属于应用组, 则删除应用组最后一个应用后同时删除应用组
        if service.tenant_service_group_id > 0:
            count = service_repo.get_services_by_service_group_id(service.tenant_service_group_id).count()
            if count <= 1:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(service.tenant_service_group_id)

        service.delete()
        return 200, "success"

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
                task = {}
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
        if domains:
            return True
        return False

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
            if status in ("running", "starting", "stopping", "failure", "unKnow"):
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

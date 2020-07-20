# -*- coding: utf8 -*-
import logging

from django.db import transaction
from console.services.app_check_service import app_check_service
from console.services.app_actions import app_manage_service
from console.services.app import app_service
from console.services.group_service import group_service
from console.repositories.app import service_repo, service_source_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo

logger = logging.getLogger("default")


class MultiAppService(object):
    def list_services(self, region_name, tenant, check_uuid):
        # get detection information from data center(region)
        # first result(code) is always 200
        code, msg, data = app_check_service.get_service_check_info(tenant, region_name, check_uuid)
        if code != 200:
            return 11006, "error listing service check info", msg, None
        if not data["check_status"] or data["check_status"].lower() != "success":
            return 11001, "not finished", "检测尚未完成", None

        if data["service_info"] and len(data["service_info"]) < 2:
            return 11002, "not multiple services", "不是多组件项目", None

        bean = data["service_info"]

        return 200, "success", "", bean

    def create_services(self, region_name, tenant, user, service_alias, service_infos):
        # get temporary service
        temporary_service = service_repo.get_service_by_tenant_and_alias(tenant.tenant_id, service_alias)
        if not temporary_service:
            return 11005, "service not found", "组件不存在", -1

        group_id = service_group_relation_repo.get_group_id_by_service(temporary_service)

        # save services
        code, msg = self.save_multi_services(
            region_name=region_name,
            tenant=tenant,
            group_id=group_id,
            service=temporary_service,
            user=user,
            service_infos=service_infos)
        if code != 200:
            return code, msg, "创建多组件应用失败", -1

        code, msg = app_manage_service.delete(user, tenant, temporary_service, True)
        if code != 200:
            return code, "Service id: " + temporary_service.service_id + ";error \
                deleting temporary service", msg, -1

        return 200, "successfully create the multi-services", "成功创建多组件应用", group_id

    def save_multi_services(self, region_name, tenant, group_id, service, user, service_infos):
        service_source = service_source_repo.get_service_source(tenant.tenant_id, service.service_id)
        tx = transaction.savepoint()
        for service_info in service_infos:
            code, msg_show, new_service = app_service \
                .create_source_code_app(region_name, tenant, user,
                                        service.code_from,
                                        service_info["cname"],
                                        service.clone_url,
                                        service.git_project_id,
                                        service.code_version,
                                        service.server_type,
                                        oauth_service_id=service.oauth_service_id,
                                        git_full_name=service.git_full_name)
            if code != 200:
                logger.error("Multiple services; Service alias: {}; error creating service".format(service.service_alias))
                transaction.savepoint_rollback(tx)
                return code, msg_show
            # add username and password
            if service_source:
                git_password = service_source.password
                git_user_name = service_source.user_name
                if git_password or git_user_name:
                    app_service.create_service_source_info(tenant, new_service, git_user_name, git_password)
            #  add group
            code, msg_show = group_service.add_service_to_group(tenant, region_name, group_id, new_service.service_id)
            if code != 200:
                logger.debug("Group ID: {0}; Service ID: {1}; error adding service to group".format(
                    group_id, new_service.service_id))
                transaction.savepoint_rollback(tx)
                return code, msg_show
            # save service info, such as envs, ports, etc
            code, msg = app_check_service.save_service_info(tenant, new_service, service_info)
            if code != 200:
                logger.debug("Group ID: {0}; Service ID: {1}; error saving services".format(group_id, new_service.service_id))
                transaction.savepoint_rollback(tx)
                return code, msg
            new_service = app_service.create_region_service(tenant, new_service, user.nick_name)
            new_service.create_status = "complete"
            new_service.save()

        transaction.savepoint_commit(tx)

        return 200, "success"


multi_app_service = MultiAppService()

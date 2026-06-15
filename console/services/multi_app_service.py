# -*- coding: utf8 -*-
import logging
from typing import Any, List, Tuple

from django.db import transaction

from console.exception.main import AbortRequest
from console.services.app_check_service import app_check_service
from console.services.app_actions import app_manage_service
from console.services.app import app_service
from console.services.group_service import group_service
from console.repositories.app import service_repo, service_source_repo, service_webhooks_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo
from console.repositories.oauth_repo import oauth_repo, oauth_user_repo
from console.utils.oauth.oauth_types import get_oauth_instance
from www.models.main import TenantServiceInfo, Tenants

logger = logging.getLogger("default")


class MultiAppService(object):
    def list_services(self, region_name: str, tenant: Tenants, check_uuid: str) -> Any:
        # get detection information from data center(region)
        # first result(code) is always 200
        code, msg, data = app_check_service.get_service_check_info(tenant, region_name, check_uuid)
        if code != 200:
            raise AbortRequest("error listing service check info", msg, status_code=400, error_code=11006)
        if not data["check_status"] or data["check_status"].lower() != "success":
            raise AbortRequest("not finished", "检测尚未完成", status_code=400, error_code=11001)
        if data["service_info"] and len(data["service_info"]) < 2:
            raise AbortRequest("not multiple services", "不是多组件项目", status_code=400, error_code=11002)

        return data["service_info"]

    def create_services(self, region_name: str, tenant: Tenants, user: Any, service_alias: str,
                        service_infos: Any, host: str) -> Tuple[Any, List[str]]:
        # get temporary service
        temporary_service = service_repo.get_service_by_tenant_and_alias(tenant.tenant_id, service_alias)
        if not temporary_service:
            raise AbortRequest("service not found", "组件不存在", status_code=404, error_code=11005)

        group_id = service_group_relation_repo.get_group_id_by_service(temporary_service)

        # save services
        service_ids = self.save_multi_services(
            region_name=region_name,
            tenant=tenant,
            group_id=group_id,
            service=temporary_service,
            user=user,
            service_infos=service_infos,
            host=host)

        code, msg = app_manage_service.delete(user, tenant, temporary_service, True)
        if code != 200:
            raise AbortRequest(
                "Service id: " + temporary_service.service_id + "; error deleting temporary service",
                msg,
                status_code=400,
                error_code=code)

        return group_id, service_ids  # type: ignore[return-value]

    @transaction.atomic
    def save_multi_services(self, region_name: str, tenant: Tenants, group_id: Any,
                            service: TenantServiceInfo, user: Any, service_infos: Any,
                            host: str) -> Any:
        service_source = service_source_repo.get_service_source(tenant.tenant_id, service.service_id)
        service_ids: List[str] = []

        git_service = None
        if service.oauth_service_id:
            try:
                oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service.oauth_service_id)  # type: ignore[arg-type]
                oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service.oauth_service_id, user_id=user.pk)  # type: ignore[arg-type]
            except Exception as e:
                logger.debug(e)
                rst = {"data": {"bean": None}, "status": 400, "msg_show": "未找到OAuth服务, 请检查该服务是否存在且属于开启状态"}
                return 400, rst, None
            try:
                git_service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)  # type: ignore[union-attr]
            except Exception as e:
                logger.debug(e)
                rst = {"data": {"bean": None}, "status": 400, "msg_show": "未找到OAuth服务"}
                return 400, rst, None
            if not git_service.is_git_oauth():
                rst = {"data": {"bean": None}, "status": 400, "msg_show": "该OAuth服务不是代码仓库类型"}
                return 400, rst, None

        for service_info in service_infos:
            code, msg_show, new_service = app_service \
                .create_source_code_app(region_name, tenant, user,
                                        service.code_from,  # type: ignore[arg-type]
                                        service_info["cname"],
                                        service.clone_url,  # type: ignore[arg-type]
                                        service.git_project_id,  # type: ignore[arg-type]
                                        service.code_version,  # type: ignore[arg-type]
                                        service.server_type,
                                        oauth_service_id=service.oauth_service_id,  # type: ignore[arg-type]
                                        git_full_name=service.git_full_name,
                                        arch=service_info.get("arch", "amd64"))
            if code != 200:
                raise AbortRequest("Multiple services; Service alias: {}; error creating service".format(service.service_alias),
                                   "创建多组件应用失败")

            # 添加hook
            if service.open_webhooks:
                service_webhook = service_webhooks_repo.create_service_webhooks(new_service.service_id, "code_webhooks")  # type: ignore[union-attr]
                service_webhook.state = True
                service_webhook.deploy_keyword = "deploy"
                service_webhook.save()
                try:
                    git_service.create_hook(host, service.git_full_name, endpoint='console/webhooks/' + new_service.service_id)  # type: ignore[union-attr]
                    new_service.open_webhooks = True  # type: ignore[union-attr]
                except Exception as e:
                    logger.exception(e)
                    new_service.open_webhooks = False  # type: ignore[union-attr]

            # add username and password
            if service_source:
                git_password = service_source.password
                git_user_name = service_source.user_name
                if git_password or git_user_name:
                    app_service.create_service_source_info(tenant, new_service, git_user_name, git_password)  # type: ignore[arg-type]
            #  add group
            code, msg_show = group_service.add_service_to_group(tenant, region_name, group_id, new_service.service_id)  # type: ignore[arg-type, union-attr]
            if code != 200:
                logger.debug("Group ID: {0}; Service ID: {1}; error adding service to group".format(
                    group_id, new_service.service_id))  # type: ignore[union-attr]
                raise AbortRequest("app not found", "创建多组件应用失败", 404, 404)
            # save service info, such as envs, ports, etc
            app_check_service.save_service_info(tenant, new_service, service_info)  # type: ignore[arg-type]
            new_service = app_service.create_region_service(tenant, new_service, user.nick_name)  # type: ignore[arg-type]
            new_service.create_status = "complete"
            new_service.save()
            service_ids.append(new_service.service_id)

        return service_ids


multi_app_service = MultiAppService()

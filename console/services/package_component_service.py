# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict, List, Optional

from console.exception.main import ServiceHandleException
from console.repositories.deploy_repo import deploy_repo
from console.services.app import app_service as console_app_service, package_upload_service
from console.services.app_actions import app_manage_service
from console.services.app_check_service import app_check_service
from console.services.app_config.arch_service import arch_service
from console.services.enterprise_first_deploy_service import enterprise_first_deploy_service
from console.services.group_service import group_service
from console.services.source_component_service import source_component_service
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants, ServiceGroup

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class PackageComponentService(object):
    def auto_create_component(
            self,
            team: Tenants,
            app: ServiceGroup,
            user: Any,
            event_id: str,
            service_cname: str,
            k8s_component_name: str = "",
            arch: str = "amd64",
            is_deploy: bool = True,
            max_check_retries: Optional[int] = None,
            check_poll_interval: Optional[int] = None) -> Dict[str, Any]:
        if k8s_component_name and console_app_service.is_k8s_component_name_duplicate(app.ID, k8s_component_name):  # type: ignore[arg-type]  # NOTE: app.ID is int (PK), callee expects str; runtime coercion via Django ORM lookup works
            raise ServiceHandleException(msg="component name exists", msg_show="组件英文名称已存在", status_code=400)

        upload_record = package_upload_service.get_upload_record(team.tenant_name, app.region_name, event_id)
        if not upload_record:
            raise ServiceHandleException(msg="upload record not found", msg_show="未找到软件包上传记录", status_code=404)

        packages = self._get_uploaded_packages(app.region_name, team.tenant_name, event_id)
        if not packages:
            raise ServiceHandleException(msg="package not uploaded", msg_show="软件包未上传完成", status_code=400)

        component = console_app_service.create_package_upload_info(
            app.region_name,
            team,
            user,
            service_cname,
            k8s_component_name,
            event_id,
            upload_record.create_time,  # type: ignore[arg-type]  # NOTE: create_time is datetime | None (nullable model field); callee expects str — runtime formats it implicitly
            arch,
        )
        package_upload_service.update_upload_record(
            team.tenant_name,
            event_id,
            status="finished",
            component_id=component.service_id,
            source_dir=packages,
        )

        code, msg_show = group_service.add_service_to_group(team, app.region_name, app.ID, component.service_id)
        if code != 200:
            raise ServiceHandleException(msg="add service to app failure", msg_show=msg_show, status_code=code)

        code, msg, check_info = app_check_service.check_service(team, component, False, event_id, user)
        if code != 200:
            raise ServiceHandleException(msg="check service error", msg_show=msg, status_code=code)

        check_uuid = check_info.get("check_uuid") or component.check_uuid  # type: ignore[union-attr]  # NOTE: check_info is Optional[dict]; only reached after code==200 so always non-None at runtime
        bean = source_component_service._wait_for_check_result(
            app.region_name,
            team,
            check_uuid,
            max_retries=max_check_retries or source_component_service.MAX_CHECK_RETRIES,
            poll_interval=check_poll_interval or source_component_service.CHECK_POLL_INTERVAL,
        )

        service_info_list = bean.get("service_info") or []
        if len(service_info_list) > 1:
            raise ServiceHandleException(
                msg="multiple services detected",
                msg_show="检测到多组件软件包，请使用多组件创建流程",
                status_code=400,
            )
        if service_info_list:
            app_check_service.save_service_check_info(team, app.ID, component, bean)  # type: ignore[arg-type]  # NOTE: app.ID is int (PK), callee expects str; Django ORM coerces at runtime
            source_component_service.apply_default_build_config(team, component, service_info_list[0])

        region_component = console_app_service.create_region_service(team, component, source_component_service._get_username(user))
        deploy_event_id = None
        if is_deploy:
            service_alias = getattr(region_component, "service_alias", "") or getattr(component, "service_alias", "")
            source_language = ""
            if service_info_list:
                source_language = service_info_list[0].get("language") or ""
            tracker = enterprise_first_deploy_service.safe_begin_tracking(
                enterprise_id=team.enterprise_id,
                tenant_name=team.tenant_name,
                region_name=app.region_name,
                deploy_type=enterprise_first_deploy_service.get_deploy_type(
                    getattr(region_component, "service_source", "") or getattr(component, "service_source", "")),
                operator=getattr(user, "nick_name", ""),
                source_language=source_language or getattr(component, "language", "") or "",
                service_id=region_component.service_id,
                service_alias=service_alias,
                service=region_component,
                trigger="package_auto_create",
                app_context=enterprise_first_deploy_service.build_service_app_context(app))
            try:
                arch_service.update_affinity_by_arch(region_component.arch, team, app.region_name, region_component)
                code, msg, deploy_event_id = app_manage_service.deploy(team, region_component, user)
                if code != 200:
                    raise ServiceHandleException(msg="deploy failed", msg_show=msg, status_code=code)
            except Exception as exc:
                enterprise_first_deploy_service.safe_mark_failure(
                    tracker,
                    reason=getattr(exc, "msg_show", str(exc)))
                raise
            enterprise_first_deploy_service.safe_bind_events(
                tracker,
                [deploy_event_id],
                service_ids=[region_component.service_id],
                service_alias=service_alias)
            deploy_repo.create_deploy_relation_by_service_id(service_id=region_component.service_id)

        return {
            "service_id": region_component.service_id,
            "service_alias": getattr(component, "service_alias", ""),
            "service_cname": getattr(component, "service_cname", service_cname),
            "app_id": app.ID,
            "app_name": getattr(app, "group_name", ""),
            "event_id": deploy_event_id,
            "upload_event_id": event_id,
            "uploaded_packages": packages,
            "check_uuid": check_uuid,
            "check_status": bean.get("check_status"),
            "create_status": getattr(region_component, "create_status", getattr(component, "create_status", "")),
            "is_deploy": bool(is_deploy),
            "built": True,
        }

    @staticmethod
    def _get_uploaded_packages(region_name: str, team_name: str, event_id: str) -> List[Any]:
        try:
            _, body = region_api.get_upload_file_dir(region_name, team_name, event_id)
        except region_api.CallApiError:
            return []
        return body.get("bean", {}).get("packages", []) or []  # type: ignore[union-attr]  # NOTE: body is Optional[dict]; on 2xx the region client always returns a non-None body; CallApiError raised otherwise


package_component_service = PackageComponentService()

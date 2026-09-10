# -*- coding: utf-8 -*-
import ast
import logging
import re
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
    PACKAGE_EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

    @staticmethod
    def _package_git_url(service_id: str, event_id: str) -> str:
        return "/grdata/package_build/components/{0}/events/{1}".format(service_id, event_id)

    @staticmethod
    def get_package_event_id(git_url: str) -> str:
        normalized = (git_url or "").rstrip("/")
        return normalized.rsplit("/", 1)[-1] if normalized else ""

    @staticmethod
    def _record_packages(upload_record: Any) -> List[Any]:
        source_dir = getattr(upload_record, "source_dir", []) or []
        if isinstance(source_dir, list):
            return source_dir
        if not isinstance(source_dir, str):
            return []
        try:
            parsed = ast.literal_eval(source_dir)
        except (SyntaxError, ValueError):
            return []
        return parsed if isinstance(parsed, list) else []

    def replace_component(self,
                          team: Tenants,
                          app: ServiceGroup,
                          service: Any,
                          user: Any,
                          event_id: str,
                          expected_current_event_id: str = "",
                          is_deploy: bool = True) -> Dict[str, Any]:
        if (getattr(service, "service_source", "") != "package_build" or getattr(service, "server_type", "") != "pkg"):
            raise ServiceHandleException(
                msg="component is not package based",
                msg_show="目标组件不是软件包构建组件",
                status_code=400,
            )
        if getattr(service, "create_status", "") not in ("checked", "complete"):
            raise ServiceHandleException(
                msg="component is not ready for package replacement",
                msg_show="组件未完成创建，禁止替换软件包",
                status_code=400,
            )
        if not self.PACKAGE_EVENT_ID_PATTERN.match(event_id or ""):
            raise ServiceHandleException(
                msg="invalid package upload event",
                msg_show="软件包上传事件ID无效",
                status_code=400,
            )

        old_git_url = getattr(service, "git_url", "") or ""
        old_code_version = getattr(service, "code_version", "") or ""
        old_event_id = self.get_package_event_id(old_git_url)
        if expected_current_event_id and expected_current_event_id != old_event_id:
            raise ServiceHandleException(
                msg="package source changed concurrently",
                msg_show="组件软件包构建源已变化，请重新查询后再更新",
                status_code=409,
            )

        upload_record = package_upload_service.get_upload_record(team.tenant_name, app.region_name, event_id)
        if not upload_record:
            raise ServiceHandleException(
                msg="upload record not found",
                msg_show="未找到软件包上传记录",
                status_code=404,
            )
        upload_component_id = getattr(upload_record, "component_id", "") or ""
        if upload_component_id and upload_component_id != service.service_id:
            raise ServiceHandleException(
                msg="upload belongs to another component",
                msg_show="软件包上传事件已关联到其他组件",
                status_code=409,
            )

        if event_id == old_event_id:
            return {
                "service_id": service.service_id,
                "service_alias": getattr(service, "service_alias", ""),
                "app_id": app.ID,
                "upload_event_id": event_id,
                "previous_upload_event_id": old_event_id,
                "uploaded_packages": self._record_packages(upload_record),
                "event_id": None,
                "replaced": False,
                "build_triggered": False,
                "is_deploy": bool(is_deploy),
                "next_action": "rainbond_build_component" if is_deploy else None,
            }

        packages = self._get_uploaded_packages(app.region_name, team.tenant_name, event_id)
        if not packages:
            raise ServiceHandleException(
                msg="package not uploaded",
                msg_show="软件包未上传完成",
                status_code=400,
            )

        new_git_url = self._package_git_url(service.service_id, event_id)
        pkg_create_time = str(getattr(upload_record, "create_time", "") or "")
        updated = console_app_service.change_package_upload_info(
            service.service_id,
            event_id,
            pkg_create_time,
            tenant_id=team.tenant_id,
            expected_git_url=old_git_url,
        )
        if updated != 1:
            raise ServiceHandleException(
                msg="package source changed concurrently",
                msg_show="组件软件包构建源已变化，请重新查询后再更新",
                status_code=409,
            )

        upload_updated = package_upload_service.update_upload_record(
            team.tenant_name,
            event_id,
            status="finished",
            component_id=service.service_id,
            source_dir=packages,
        )
        if upload_updated != 1:
            console_app_service.restore_package_upload_info(service.service_id, team.tenant_id, new_git_url, old_git_url,
                                                            old_code_version)
            raise ServiceHandleException(
                msg="update upload record failed",
                msg_show="更新软件包上传记录失败",
                status_code=409,
            )

        service.git_url = new_git_url
        service.code_version = pkg_create_time
        build_event_id = None
        if is_deploy:
            try:
                code, msg, build_event_id = app_manage_service.deploy(team, service, user)
                if code != 200:
                    raise ServiceHandleException(msg="package build failed", msg_show=msg, status_code=code)
            except Exception:
                restored = console_app_service.restore_package_upload_info(
                    service.service_id,
                    team.tenant_id,
                    new_git_url,
                    old_git_url,
                    old_code_version,
                )
                if restored != 1:
                    logger.error("restore package source failed after build dispatch error: service_id=%s", service.service_id)
                package_upload_service.update_upload_record(
                    team.tenant_name,
                    event_id,
                    status="unfinished",
                    component_id=service.service_id,
                    source_dir=packages,
                )
                service.git_url = old_git_url
                service.code_version = old_code_version
                raise
            try:
                deploy_repo.create_deploy_relation_by_service_id(service_id=service.service_id)
            except Exception as exc:
                logger.warning("create deploy relation after package replacement failed: service_id=%s error=%s",
                               service.service_id, exc)

        return {
            "service_id": service.service_id,
            "service_alias": getattr(service, "service_alias", ""),
            "app_id": app.ID,
            "upload_event_id": event_id,
            "previous_upload_event_id": old_event_id,
            "uploaded_packages": packages,
            "event_id": build_event_id,
            "replaced": True,
            "build_triggered": bool(is_deploy),
            "is_deploy": bool(is_deploy),
            "next_action": "rainbond_wait_for_build_completion" if build_event_id else None,
        }

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
            tracker = enterprise_first_deploy_service.safe_begin_deploy_tracking(
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

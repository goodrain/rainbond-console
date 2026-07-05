# -*- coding: utf-8 -*-
import json
import logging
import time
from typing import Any, Optional

from console.constants import SourceCodeType
from console.exception.main import ServiceHandleException
from console.repositories.app import service_source_repo
from console.repositories.deploy_repo import deploy_repo
from console.services.app import app_service as console_app_service
from console.services.app_actions import app_manage_service
from console.services.app_check_service import app_check_service
from console.services.app_config.arch_service import arch_service
from console.services.enterprise_first_deploy_service import enterprise_first_deploy_service
from console.services.group_service import group_service
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroup, TenantServiceInfo, Tenants, Users
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class SourceComponentService(object):
    MAX_CHECK_RETRIES = 30
    CHECK_POLL_INTERVAL = 2
    VALID_SERVER_TYPES = ("git", "svn", "oss")
    DOCKERFILE_PREFERENCE_KEY = "prefer_dockerfile_when_detected"

    def persist_dockerfile_preference(self, team: Tenants, service: TenantServiceInfo) -> None:
        """Persist the Dockerfile build preference in service_source.extend_info.

        Called when detection has not finished inside the create call (the
        timeout/pending path), so the follow-up check-result call can re-apply
        the preference without the caller re-passing the flag. Persistence
        failures must never break component creation, so errors are swallowed
        after logging.
        """
        try:
            extend_info = self._load_source_extend_info(team, service)
            extend_info[self.DOCKERFILE_PREFERENCE_KEY] = True
            service_source_repo.update_or_create_service_source(
                team_id=team.tenant_id,
                service_id=service.service_id,
                extend_info=json.dumps(extend_info, ensure_ascii=False),
            )
        except Exception:
            logger.warning(
                "persist dockerfile preference failed, service_id=%s", service.service_id, exc_info=True)

    def load_dockerfile_preference(self, team: Tenants, service: TenantServiceInfo) -> bool:
        """Read back the persisted Dockerfile build preference (default False)."""
        try:
            return bool(self._load_source_extend_info(team, service).get(self.DOCKERFILE_PREFERENCE_KEY, False))
        except Exception:
            logger.warning(
                "load dockerfile preference failed, service_id=%s", service.service_id, exc_info=True)
            return False

    @staticmethod
    def _load_source_extend_info(team: Tenants, service: TenantServiceInfo) -> dict:
        source = service_source_repo.get_service_source(team.tenant_id, service.service_id)
        if not source or not source.extend_info:
            return {}
        try:
            extend_info = json.loads(source.extend_info)
        except ValueError:
            return {}
        return extend_info if isinstance(extend_info, dict) else {}

    @classmethod
    def build_unapplied_preference_note(cls, selected_language: Optional[str]) -> str:
        return (
            "已请求 Dockerfile 构建（prefer_dockerfile_when_detected=true），但代码检测未在构建目录根路径发现 Dockerfile，"
            "已回退为 {} 语言构建。如需 Dockerfile 构建，请通过 subdirectories 指向包含 Dockerfile 的目录，"
            "或改用镜像方式部署。".format(selected_language or "检测到的")
        )

    def _report_source_check_failure(
            self,
            team: Tenants,
            app: ServiceGroup,
            user: Users,
            component: TenantServiceInfo,
            git_url: str,
            code_version: str,
            server_type: str,
            check_uuid: str,
            reason: str) -> None:
        enterprise_first_deploy_service.safe_report_source_check_failure(
            enterprise_id=team.enterprise_id,
            tenant_name=team.tenant_name,
            region_name=app.region_name,
            reason=reason,
            service=component,
            operator=getattr(user, "nick_name", ""),
            app_context=enterprise_first_deploy_service.build_service_app_context(app),
            source_context={
                "git_url": git_url,
                "code_version": code_version,
                "server_type": server_type,
                "check_uuid": check_uuid,
            },
        )

    def auto_create_component(
            self,
            team: Tenants,
            app: ServiceGroup,
            user: Users,
            service_cname: str,
            code_from: str,
            git_url: str,
            git_project_id: Any = None,
            code_version: str = "master",
            server_type: Optional[str] = None,
            version_type: Optional[str] = None,
            subdirectories: Optional[str] = None,
            username: str = "",
            password: str = "",
            check_uuid: Optional[str] = None,
            event_id: Optional[str] = None,
            oauth_service_id: Any = None,
            full_name: Optional[str] = None,
            k8s_component_name: str = "",
            arch: str = "amd64",
            is_deploy: bool = True,
            prefer_dockerfile_when_detected: bool = False,
            max_check_retries: Optional[int] = None,
            check_poll_interval: Optional[int] = None) -> dict:
        git_url = self.normalize_git_url(git_url, subdirectories)
        server_type = self.infer_server_type(git_url, server_type)
        code_from = self.normalize_code_from(code_from, git_url)
        code_version = self.normalize_code_version(code_version, version_type, server_type)

        # NOTE: app.ID is the Django int PK; is_k8s_component_name_duplicate types app_id
        # as str. The ORM coerces int->str in the lookup, so behavior is unchanged.
        if k8s_component_name and console_app_service.is_k8s_component_name_duplicate(
                app.ID, k8s_component_name):  # type: ignore[arg-type]
            raise ServiceHandleException(msg="component name exists", msg_show="组件英文名称已存在", status_code=400)

        code, msg_show, component = console_app_service.create_source_code_app(
            app.region_name,
            team,
            user,
            code_from,
            service_cname,
            git_url,
            git_project_id,
            code_version,
            server_type,
            check_uuid,
            event_id or make_uuid(),
            oauth_service_id,
            full_name,
            k8s_component_name=k8s_component_name,
            arch=arch,
        )
        if code != 200:
            raise ServiceHandleException(msg="service create fail", msg_show=msg_show, status_code=code)
        # NOTE: create_source_code_app returns Optional[TenantServiceInfo]; it is None only
        # when code != 200, which is excluded by the guard above. So on this path component is
        # always non-None (invariant), and the [arg-type]/[union-attr] ignores below are safe.

        if username or password:
            console_app_service.create_service_source_info(
                team, component, username, password)  # type: ignore[arg-type]

        code, msg_show = group_service.add_service_to_group(
            team, app.region_name, app.ID, component.service_id)  # type: ignore[union-attr]
        if code != 200:
            raise ServiceHandleException(msg="add service to app failure", msg_show=msg_show, status_code=code)

        # component is Optional[TenantServiceInfo] but non-None on this path (code==200 guard above)
        code, msg, check_info = app_check_service.check_service(team, component, False, "", user)  # type: ignore[arg-type]
        if code != 200:
            raise ServiceHandleException(msg="check service error", msg_show=msg, status_code=code)

        check_uuid = check_info.get("check_uuid") or component.check_uuid  # type: ignore[union-attr]
        effective_poll_interval = check_poll_interval or self.CHECK_POLL_INTERVAL
        try:
            bean = self._wait_for_check_result(
                app.region_name,
                team,
                check_uuid,  # type: ignore[arg-type]
                max_retries=max_check_retries or self.MAX_CHECK_RETRIES,
                poll_interval=effective_poll_interval,
            )
        except ServiceHandleException as exc:
            self._report_source_check_failure(
                team,
                app,
                user,
                component,  # type: ignore[arg-type]
                git_url,
                code_version,
                server_type,
                check_uuid,  # type: ignore[arg-type]
                exc.msg_show)
            if getattr(exc, "msg", "") == "check timeout":
                build_mode_note = None
                if prefer_dockerfile_when_detected:
                    # Detection outlived the synchronous wait window (large
                    # repos take minutes to clone), so persist the preference;
                    # get_component_check_result reads it back and applies it
                    # before persisting the detection result.
                    self.persist_dockerfile_preference(team, component)  # type: ignore[arg-type]
                    build_mode_note = (
                        "Dockerfile 构建偏好已持久化，检测完成后调用 rainbond_get_component_check_result 会自动应用，"
                        "无需重新传递 prefer_dockerfile_when_detected。"
                    )
                return {
                    "prefer_dockerfile_when_detected": bool(prefer_dockerfile_when_detected),
                    "build_mode_note": build_mode_note,
                    "service_id": component.service_id,  # type: ignore[union-attr]
                    "service_alias": getattr(component, "service_alias", ""),
                    "service_cname": getattr(component, "service_cname", service_cname),
                    "app_id": app.ID,
                    "app_name": getattr(app, "group_name", ""),
                    "git_url": git_url,
                    "code_version": code_version,
                    "server_type": server_type,
                    "check_uuid": check_uuid,
                    "check_status": "checking",
                    "create_status": getattr(component, "create_status", "checking"),
                    "event_id": None,
                    "is_deploy": False,
                    "built": False,
                    "workflow_stage": "checking",
                    "next_action": "rainbond_get_component_check_result",
                    "next_poll_after_seconds": effective_poll_interval,
                    "message": exc.msg_show,
                }
            raise

        service_info_list = bean.get("service_info") or []
        if len(service_info_list) > 1:
            raise ServiceHandleException(
                msg="multiple services detected",
                msg_show="检测到多组件源码，请使用多组件创建流程",
                status_code=400,
            )
        selected_language = None
        detected_language_raw = None
        dockerfile_preference_applied = None
        build_mode_note = None
        if service_info_list:
            selected_service_info = self._select_service_info(service_info_list[0], prefer_dockerfile_when_detected)
            detected_language_raw = service_info_list[0].get("language")
            selected_language = selected_service_info.get("language")
            service_info_list[0] = selected_service_info
            if prefer_dockerfile_when_detected:
                dockerfile_preference_applied = selected_language == "dockerfile"
                if not dockerfile_preference_applied:
                    build_mode_note = self.build_unapplied_preference_note(selected_language)
            # app.ID is int (AutoField used as str id) and component is Optional but non-None here
            app_check_service.save_service_check_info(team, app.ID, component, bean)  # type: ignore[arg-type]
            self.apply_default_build_config(team, component, selected_service_info)  # type: ignore[arg-type]

        region_component = console_app_service.create_region_service(
            team, component, self._get_username(user))  # type: ignore[arg-type]
        deploy_event_id = None
        if is_deploy:
            service_alias = getattr(region_component, "service_alias", "") or getattr(component, "service_alias", "")
            tracker = enterprise_first_deploy_service.safe_begin_deploy_tracking(
                enterprise_id=team.enterprise_id,
                tenant_name=team.tenant_name,
                region_name=app.region_name,
                deploy_type=enterprise_first_deploy_service.get_deploy_type(
                    getattr(region_component, "service_source", "") or getattr(component, "service_source", "")),
                operator=getattr(user, "nick_name", ""),
                source_language=selected_language or getattr(component, "language", "") or "",
                service_id=region_component.service_id,
                service_alias=service_alias,
                service=region_component,
                trigger="source_auto_create",
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
            "git_url": git_url,
            "code_version": code_version,
            "server_type": server_type,
            "check_uuid": check_uuid,
            "check_status": bean.get("check_status"),
            "create_status": getattr(region_component, "create_status", getattr(component, "create_status", "")),
            "event_id": deploy_event_id,
            "is_deploy": bool(is_deploy),
            "detected_language_raw": detected_language_raw,
            "selected_language": selected_language or getattr(component, "language", ""),
            "dockerfile_preference_applied": dockerfile_preference_applied,
            "build_mode_note": build_mode_note,
            "built": True,
        }

    @staticmethod
    def _select_service_info(service_info: Optional[dict], prefer_dockerfile_when_detected: bool = False) -> dict:
        normalized = dict(service_info or {})
        if not prefer_dockerfile_when_detected:
            return normalized

        language = (normalized.get("language") or "").strip()
        dockerfiles = normalized.get("dockerfiles") or []
        lowered_parts = [part.strip().lower() for part in language.split(",") if part.strip()]
        if dockerfiles and lowered_parts != ["dockerfile"]:
            normalized["language"] = "dockerfile"
        return normalized

    def _wait_for_check_result(self, region_name: str, team: Tenants, check_uuid: str, max_retries: int,
                               poll_interval: int) -> dict:
        retry_count = 0
        while retry_count < max_retries:
            try:
                _, body = region_api.get_service_check_info(region_name, team.tenant_name, check_uuid)
                # NOTE: body is Optional[Dict]; the region client returns a body only on a 2xx
                # response and raises CallApiError otherwise (caught below), so on this line
                # body is non-None (invariant).
                bean = body["bean"]  # type: ignore[index]
                if not bean.get("check_status"):
                    bean["check_status"] = "checking"
                bean["check_status"] = bean["check_status"].lower()
                if bean["check_status"] == "checking":
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(poll_interval)
                    continue
                if bean["check_status"] == "success":
                    return bean
                raise ServiceHandleException(
                    msg="check failed",
                    msg_show=self._format_check_failure(bean),
                    status_code=500,
                )
            except region_api.CallApiError:
                retry_count += 1
                if retry_count >= max_retries:
                    break
                time.sleep(poll_interval)
        raise ServiceHandleException(msg="check timeout", msg_show="代码检测超时", status_code=500)

    @staticmethod
    def _format_check_failure(bean: dict) -> str:
        error_infos = bean.get("error_infos") or []
        if error_infos:
            first_error = error_infos[0]
            return first_error.get("error_info") or first_error.get("solve_advice") or "代码检测失败"
        return "代码检测失败"

    def apply_default_build_config(self, team: Tenants, component: TenantServiceInfo, service_info: dict) -> None:
        language = (service_info.get("language") or getattr(component, "language", "") or "").strip()
        normalized_language = self.normalize_build_language(language)
        if normalized_language not in ("Node.js", "static"):
            return

        runtime_info = service_info.get("runtime_info") or {}
        build_config = runtime_info.get("build_config") or {}
        package_manager = runtime_info.get("package_manager") or {}
        framework = runtime_info.get("framework") or {}
        config_files = runtime_info.get("config_files") or {}

        package_tool = package_manager.get("name", "") or ""
        cnb_framework = framework.get("name", "") or ""
        cnb_build_script = build_config.get("build_command", "") or ""
        cnb_output_dir = build_config.get("output_dir", "") or ""
        cnb_node_version = runtime_info.get("language_version", "") or ""
        cnb_start_script = build_config.get("start_command", "") or ""
        has_npmrc = "true" if config_files.get("has_npmrc") else ""
        has_yarnrc = "true" if config_files.get("has_yarnrc") else ""
        cnb_mirror_source = "project" if (has_npmrc or has_yarnrc) else "global"

        code, msg = app_manage_service.change_lang_and_package_tool(
            team,
            component,
            normalized_language,
            package_tool,
            cnb_output_dir,
            cnb_framework=cnb_framework,
            cnb_build_script=cnb_build_script,
            cnb_output_dir=cnb_output_dir,
            cnb_node_version=cnb_node_version,
            cnb_node_env="production",
            cnb_mirror_source=cnb_mirror_source,
            has_npmrc=has_npmrc,
            has_yarnrc=has_yarnrc,
            cnb_start_script=cnb_start_script,
        )
        if code != 200:
            raise ServiceHandleException(msg="save build config failed", msg_show=msg, status_code=500)
        component.language = normalized_language

    @staticmethod
    def normalize_build_language(language: Optional[str]) -> str:
        lowered = (language or "").strip().lower()
        if lowered == "static":
            return "static"
        if "node" in lowered:
            return "Node.js"
        # NOTE: language is Optional[str]; returning it as-is preserves the original
        # passthrough behavior. The sole caller (apply_default_build_config) already
        # coerces it to a non-None stripped string, so this returns a str in practice.
        return language  # type: ignore[return-value]

    def infer_server_type(self, git_url: str, server_type: Optional[str] = None) -> str:
        server_type = (server_type or "").strip().lower()
        if server_type:
            if server_type not in self.VALID_SERVER_TYPES:
                raise ServiceHandleException(msg="invalid server_type", msg_show="参数server_type无效", status_code=400)
            return server_type
        git_url = (git_url or "").strip().lower()
        if git_url.startswith("svn://") or git_url.startswith("svn+ssh://"):
            return "svn"
        if git_url.startswith(("oss://", "s3://", "cos://", "obs://", "gs://")):
            return "oss"
        if any(domain in git_url for domain in (".aliyuncs.com/", ".myqcloud.com/", ".amazonaws.com/", ".obs.")):
            return "oss"
        return "git"

    def normalize_git_url(self, git_url: str, subdirectories: Optional[str] = None) -> str:
        git_url = (git_url or "").strip()
        subdirectories = (subdirectories or "").strip()
        if not subdirectories or "dir=" in git_url:
            return git_url
        separator = "&" if "?" in git_url else "?"
        return "{}{}dir={}".format(git_url, separator, subdirectories)

    def normalize_code_version(self, code_version: Optional[str], version_type: Optional[str] = None,
                               server_type: Optional[str] = None) -> str:
        if server_type == "oss":
            return ""
        code_version = (code_version or "master").strip()
        if (version_type or "").strip() == "tag" and not code_version.startswith("tag:"):
            return "tag:{}".format(code_version)
        return code_version

    def normalize_code_from(self, code_from: Optional[str], git_url: Optional[str]) -> str:
        code_from = (code_from or "").strip()
        git_url = (git_url or "").strip().lower()
        if not code_from:
            return SourceCodeType.GITLAB_MANUAL
        if self.is_github_proxy_url(git_url):
            return SourceCodeType.GITLAB_MANUAL
        if code_from in (
                SourceCodeType.GITLAB_MANUAL,
                SourceCodeType.GITLAB_SELF,
                SourceCodeType.GITLAB_NEW,
                SourceCodeType.GITLAB_EXIT,
                SourceCodeType.GITHUB,
                SourceCodeType.GITLAB_DEMO):
            return code_from
        if code_from.startswith("oauth_"):
            return code_from

        lowered = code_from.lower()
        if lowered in ("git", "svn", "oss", "gitee", "gitea", "gitlab"):
            if "github.com/" in git_url:
                return SourceCodeType.GITHUB
            return SourceCodeType.GITLAB_MANUAL
        if lowered == "github":
            return SourceCodeType.GITHUB
        return SourceCodeType.GITLAB_MANUAL

    @staticmethod
    def is_github_proxy_url(git_url: Optional[str]) -> bool:
        git_url = (git_url or "").strip().lower()
        return git_url.startswith((
            "https://ghfast.top/https://github.com/",
            "https://gh.rainbond.cc/https://github.com/",
        ))

    @staticmethod
    def _get_username(user: Users) -> str:
        if hasattr(user, "get_username") and callable(user.get_username):
            return user.get_username()
        return getattr(user, "nick_name", "")


source_component_service = SourceComponentService()

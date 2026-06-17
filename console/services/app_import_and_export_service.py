# -*- coding: utf8 -*-
"""
  Created on 18/5/15.
"""
import base64
import hashlib
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from console.appstore.appstore import app_store
from console.exception.main import (ExportAppError, RbdAppNotFound, RecordNotFound, RegionNotFound)
from console.models.main import (RainbondCenterApp, RainbondCenterAppVersion, RegionConfig)
from console.repositories.market_app_repo import (app_export_record_repo, app_import_record_repo, rainbond_app_repo)
from console.repositories.region_repo import region_repo
from console.services.app_config.app_relation_service import \
    AppServiceRelationService
from console.services.region_services import region_services
from goodrain_web import settings
from www.apiclient.regionapi import RegionInvokeApi
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
baseService = BaseTenantService()
app_relation_service = AppServiceRelationService()
region_api = RegionInvokeApi()

EXTEND_METHOD_FIELDS = (
    "min_node",
    "max_node",
    "step_node",
    "min_memory",
    "init_memory",
    "max_memory",
    "step_memory",
    "is_restart",
    "container_cpu",
)


class AppExportService(object):
    def select_handle_region(self, eid: str) -> RegionConfig:
        # NOTE: get_enterprise_regions declares status: str / check_status: str, but
        # callers pass int/bool literals. Pre-existing arg-type mismatch; behavior
        # unchanged. type: ignore keeps the value as-is.
        data = region_services.get_enterprise_regions(
            eid, level="safe", status=1, check_status=True)  # type: ignore[arg-type]
        if data:
            for region in data:
                if region["rbd_version"] != "":
                    return region_services.get_region_by_region_id(data[0]["region_id"])
        raise RegionNotFound("暂无可用的集群，应用导出功能不可用")

    def export_app(self, eid: str, app_id: str, version: str, export_format: str,
                   helm_chart_parameter: dict) -> Any:
        app, app_version = rainbond_app_repo.get_rainbond_app_and_version(eid, app_id, version)
        if not app or not app_version:
            raise RbdAppNotFound("未找到该应用")

        # get region TODO: get region by app publish meta info
        region = self.select_handle_region(eid)
        region_name = region.region_name
        export_record = app_export_record_repo.get_export_record(eid, app_id, version, export_format)
        if export_record:
            if export_record.status == "success":
                # NOTE: ExportAppError.__init__ has no "mes_show" param (correct
                # name is "msg_show") and does NOT accept **kwargs, so this line
                # raises TypeError at runtime when a "success" export record exists.
                # Real latent bug — left as-is (behavior change out of scope).
                raise ExportAppError(
                    msg="exported", mes_show="已存在该导出记录", status_code=409)  # type: ignore[call-arg]
            if export_record.status == "exporting":
                logger.debug("export record exists: event_id :{0}".format(export_record.event_id))
                return export_record
        # did not export, make a new export record
        # make export data
        event_id = make_uuid()
        data = {
            "event_id": event_id,
            "group_key": app.app_id,
            "version": app_version.version,
            "format": export_format,
            "group_metadata": self.__get_app_metata(app, app_version, helm_chart_parameter)
        }

        try:
            region_api.export_app(region_name, eid, data)
        except region_api.CallApiError as e:
            logger.exception(e)
            raise ExportAppError()

        params = {
            "event_id": event_id,
            "group_key": app_id,
            "version": version,
            "format": export_format,
            "status": "exporting",
            "enterprise_id": eid,
            "region_name": region.region_name
        }

        return app_export_record_repo.create_app_export_record(**params)

    def __get_app_metata(self, app: RainbondCenterApp, app_version: RainbondCenterAppVersion,
                         helm_chart_parameter: dict) -> str:
        picture_path = app.pic
        suffix = picture_path.split('.')[-1] if picture_path else ""
        describe = app.describe
        try:
            image_base64_string = self.encode_image(picture_path) or ""
        except IOError as e:
            logger.warning("path: {}; error encoding image: {}".format(picture_path, e))
            image_base64_string = ""

        app_template = self.__normalize_export_template(json.loads(app_version.app_template))
        for ingress_http_route in app_template.get("ingress_http_routes", []):
            ingress_http_route["proxy_header"] = ingress_http_route.get("proxy_header", {})
            if isinstance(ingress_http_route["proxy_header"], list):
                ingress_http_route["proxy_header"] = {
                    header["item_key"]: header["item_value"]
                    for header in ingress_http_route["proxy_header"]
                }

        app_template["annotations"] = {
            "suffix": suffix,
            "describe": describe,
            "image_base64_string": image_base64_string,
            "version_info": app_version.app_version_info,
            "version_alias": app_version.version_alias,
        }
        app_template["helm_chart"] = {
            "image_handle": helm_chart_parameter["image_handle"],
        }
        return json.dumps(app_template, cls=MyEncoder)

    @staticmethod
    def __is_vm_template_component(component: Any) -> bool:
        return bool(
            isinstance(component, dict) and (
                component.get("vm")
                or component.get("extend_method") == "vm"
                or component.get("service_source") == "vm_run"
            )
        )

    def __normalize_export_item(self, item: Optional[dict]) -> dict:
        export_item = dict(item or {})
        is_vm_component = self.__is_vm_template_component(export_item)
        if is_vm_component:
            export_item["service_type"] = "vm"
        elif export_item.get("service_type") == "vm":
            export_item["service_type"] = "application"
        if not export_item.get("share_image") and export_item.get("image"):
            export_item["share_image"] = export_item["image"]
        vm_payload = export_item.get("vm")
        disk_layout: list = []
        if isinstance(vm_payload, dict):
            disk_layout = vm_payload.get("disk_layout") or []
        if isinstance(vm_payload, dict) and isinstance(disk_layout, list):
            root_image = export_item.get("share_image") or export_item.get("image") or ""
            normalized_layout = []
            for disk in disk_layout:
                if not isinstance(disk, dict):
                    continue
                item_disk = dict(disk)
                if str(item_disk.get("disk_role", "")).lower() == "root":
                    item_disk["image"] = item_disk.get("image") or root_image
                    item_disk["source_type"] = item_disk.get("source_type") or "registry"
                normalized_layout.append(item_disk)
            if normalized_layout:
                vm_payload["disk_layout"] = normalized_layout
                export_item["vm"] = vm_payload
        extend_method_map = dict(export_item.get("extend_method_map") or {})
        if export_item.get("cpu") is None and extend_method_map.get("container_cpu") is not None:
            export_item["cpu"] = extend_method_map["container_cpu"]
        if export_item.get("memory") is None and extend_method_map.get("init_memory") is not None:
            export_item["memory"] = extend_method_map["init_memory"]
        if export_item.get("memory") is not None and extend_method_map.get("init_memory") is None:
            extend_method_map["init_memory"] = export_item["memory"]
        if extend_method_map:
            export_item["extend_method_map"] = extend_method_map
        return export_item

    @classmethod
    def __resolve_export_template_version(cls, template: dict) -> str:
        for component in template.get("apps", []):
            if cls.__is_vm_template_component(component):
                return "v3"
        return "v2"

    def __normalize_export_template(self, app_template: Optional[dict]) -> dict:
        template = dict(app_template or {})
        template["apps"] = [
            self.__normalize_export_item(component)
            for component in template.get("apps", [])
        ]
        template["plugins"] = [
            self.__normalize_export_item(plugin)
            for plugin in template.get("plugins", [])
        ]
        template["template_version"] = self.__resolve_export_template_version(template)
        return template

    def encode_image(self, image_url: Optional[str]) -> Optional[str]:
        if not image_url:
            return None
        if image_url.startswith("http"):
            response = urllib.request.urlopen(image_url)
        else:
            image_url = "{}/media/uploads/{}".format(settings.DATA_DIR, image_url.split('/')[-1])
            response = open(image_url, mode='rb')
        image_base64_string = base64.encodebytes(response.read()).decode('utf-8')
        response.close()
        return image_base64_string

    def get_export_status(self, enterprise_id: str, app: RainbondCenterApp,
                          app_version: RainbondCenterAppVersion) -> dict:
        app_export_records = app_export_record_repo.get_enter_export_record_by_key_and_version(
            enterprise_id, app.app_id, app_version.version)
        rainbond_app_init_data: Dict[str, Any] = {
            "is_export_before": False,
        }
        docker_compose_init_data: Dict[str, Any] = {
            "is_export_before": False,
        }
        slug_init_data: Dict[str, Any] = {
            "is_export_before": False,
        }
        helm_chart_init_data: Dict[str, Any] = {
            "is_export_before": False,
        }

        if app_export_records:
            for export_record in app_export_records:
                if not export_record.region_name:
                    continue
                region = region_services.get_enterprise_region_by_region_name(enterprise_id, export_record.region_name)
                if not region:
                    continue
                if export_record.event_id and export_record.status == "exporting":
                    try:
                        res, body = region_api.get_app_export_status(export_record.region_name, enterprise_id,
                                                                     export_record.event_id)
                        # NOTE: region_api returns body as Optional[dict]; deref is
                        # guarded only by the surrounding try/except. type: ignore for
                        # the Optional index — behavior unchanged.
                        result_bean = body["bean"]  # type: ignore[index]
                        if result_bean["status"] in ("failed", "success"):
                            export_record.status = result_bean["status"]
                        export_record.file_path = result_bean["tar_file_href"]
                        export_record.save()
                    except Exception as e:
                        logger.exception(e)

                # NOTE: export_record.file_path is a nullable model field; .replace
                # below (here and in the docker-compose/slug/helm-chart blocks) is
                # unguarded. If file_path is None this raises AttributeError at
                # runtime — potential latent None-bug. Behavior unchanged.
                if export_record.format == "rainbond-app":
                    rainbond_app_init_data.update({
                        "is_export_before":
                        True,
                        "status":
                        export_record.status,
                        "file_path":
                        self._wrapper_director_download_url(
                            export_record.region_name,
                            export_record.file_path.replace("/v2", ""))  # type: ignore[union-attr]
                    })
                if export_record.format == "docker-compose":
                    docker_compose_init_data.update({
                        "is_export_before":
                        True,
                        "status":
                        export_record.status,
                        "file_path":
                        self._wrapper_director_download_url(
                            export_record.region_name,
                            export_record.file_path.replace("/v2", ""))  # type: ignore[union-attr]
                    })
                if export_record.format == "slug":
                    slug_init_data.update({
                        "is_export_before":
                        True,
                        "status":
                        export_record.status,
                        "file_path":
                        self._wrapper_director_download_url(
                            export_record.region_name,
                            export_record.file_path.replace("/v2", ""))  # type: ignore[union-attr]
                    })
                if export_record.format == "helm-chart":
                    helm_chart_init_data.update({
                        "is_export_before":
                        True,
                        "status":
                        export_record.status,
                        "file_path":
                        self._wrapper_director_download_url(
                            export_record.region_name,
                            export_record.file_path.replace("/v2", ""))  # type: ignore[union-attr]
                    })
        result = {
            "rainbond_app": rainbond_app_init_data,
            "docker_compose": docker_compose_init_data,
        }
        tmpl = json.loads(app_version.app_template)
        if tmpl.get("governance_mode", "") == "KUBERNETES_NATIVE_SERVICE":
            result["helm_chart"] = helm_chart_init_data
        if not tmpl.get("apps"):
            return {"no_export": "true"}
        for component in tmpl.get("apps"):
            if component.get("service_source") == "source_code":
                result["slug"] = slug_init_data
                break
        return result

    def __get_down_url(self, region_name: str, raw_url: str) -> str:
        region = region_repo.get_region_by_region_name(region_name)
        if region:
            return region.url + raw_url
        else:
            return raw_url

    def _wrapper_director_download_url(self, region_name: str, raw_url: str) -> Optional[str]:
        region = region_repo.get_region_by_region_name(region_name)
        if region:
            splits_texts = region.wsurl.split("://")
            if splits_texts[0] == "wss":
                return "https://" + splits_texts[1] + raw_url
            else:
                return "http://" + splits_texts[1] + raw_url
        return None

    def get_export_record(self, export_format: str, app: Any) -> Any:
        return app_export_record_repo.get_export_record_by_unique_key(app.group_key, app.version, export_format)

    def get_export_record_status(self, enterprise_id: str, group_key: str, version: str) -> str:
        records = app_export_record_repo.get_enter_export_record_by_key_and_version(enterprise_id, group_key, version)
        # 有一个成功即成功，全部失败为失败，全部为导出中则显示导出中
        if not records:
            return "unexported"
        failed = True

        for record in records:
            if record.status == "success":
                return "success"
            if record.status != "failed":
                failed = False
        if failed:
            return "failed"
        else:
            return "exporting"


class AppImportService(object):
    def select_handle_region(self, eid: str) -> RegionConfig:
        # NOTE: see AppExportService.select_handle_region — same pre-existing
        # status/check_status arg-type mismatch. Behavior unchanged.
        data = region_services.get_enterprise_regions(
            eid, level="safe", status=1, check_status=True)  # type: ignore[arg-type]
        if data:
            for region in data:
                if region["rbd_version"] != "":
                    return region_services.get_region_by_region_id(data[0]["region_id"])
        raise RegionNotFound("暂无可用的集群、应用导入功能不可用")

    def start_import_apps(self, scope: str, event_id: str, file_names: Any, team_name: Optional[str] = None,
                          enterprise_id: Optional[str] = None) -> None:
        import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
        if not import_record:
            raise RecordNotFound("import_record not found")
        import_record.scope = scope
        if team_name:
            import_record.team_name = team_name

        service_image = app_store.get_app_hub_info(enterprise_id=enterprise_id)
        data = {"service_image": service_image, "event_id": event_id, "apps": file_names}
        # NOTE: import_record.region / .enterprise_id and team_name are nullable
        # (Optional[str]); region_api requires str. Pre-existing Optional-flow,
        # behavior unchanged.
        if scope == "enterprise":
            region_api.import_app_2_enterprise(
                import_record.region, import_record.enterprise_id, data)  # type: ignore[arg-type]
        else:
            res, body = region_api.import_app(import_record.region, team_name, data)  # type: ignore[arg-type]
        import_record.status = "importing"
        import_record.save()

    def openapi_deploy_import_apps(self, region: str, scope: str, event_id: str, file_names: Any,
                                   team_name: Optional[str] = None, enterprise_id: Optional[str] = None) -> None:
        service_image = app_store.get_app_hub_info(enterprise_id=enterprise_id)
        data = {"service_image": service_image, "event_id": event_id, "apps": file_names}
        # NOTE: enterprise_id / team_name are Optional[str]; region_api requires str.
        # Pre-existing Optional-flow, behavior unchanged.
        if scope == "enterprise":
            region_api.import_app_2_enterprise(region, enterprise_id, data)  # type: ignore[arg-type]
        else:
            region_api.import_app(region, team_name, data)  # type: ignore[arg-type]

    def get_helm_yaml_info(self,
                           region_name: str,
                           tenant: Any,
                           event_id: str,
                           file_name: str,
                           region_app_id: str,
                           name: str,
                           version: str,
                           enterprise_id: Optional[str] = None,
                           region_id: Optional[str] = None) -> Any:
        data = {
            "event_id": event_id,
            "file_name": file_name,
            "namespace": tenant.namespace,
            "name": name,
            "version": version,
        }
        # NOTE: enterprise_id / region_id are Optional[str] but region_api requires
        # str; body is Optional[dict] and dereferenced unguarded. Pre-existing
        # Optional-flow, behavior unchanged.
        res, body = region_api.get_yaml_by_chart(region_name, enterprise_id, data)  # type: ignore[arg-type]
        yaml_resource_detailed_data = {
            "event_id": "",
            "region_app_id": region_app_id,
            "tenant_id": tenant.tenant_id,
            "namespace": tenant.namespace,
            "yaml": body["bean"]["yaml"]  # type: ignore[index]
        }
        _, body = region_api.yaml_resource_detailed(
            enterprise_id, region_id, yaml_resource_detailed_data)  # type: ignore[arg-type]
        return body["bean"]  # type: ignore[index]

    def __get_next_import_record_status(self, current_status: Optional[str], status: str,
                                        apps_status: list) -> Optional[str]:
        next_status = None
        if current_status != "success":
            next_status = status

        failed_num = 0
        success_num = 0
        for item in apps_status:
            if item.get("status") == "success":
                success_num += 1
            elif item.get("status") == "failed":
                failed_num += 1

        if success_num == len(apps_status):
            next_status = "success"
        elif failed_num == len(apps_status):
            next_status = "failed"
        elif success_num > 0:
            next_status = "partial_success"
        if status == "uploading":
            next_status = status
        return next_status

    def __save_import_record_status(self, import_record: Any, status: Optional[str]) -> None:
        if status and import_record.status != status:
            import_record.status = status
            import_record.save()

    def get_and_update_import_by_event_id(self, event_id: str, arch: str) -> Tuple[Any, list]:
        import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
        if not import_record:
            raise RecordNotFound("import_record not found")
        # get import status from region
        # NOTE: import_record.region / .enterprise_id are Optional[str] (region_api
        # requires str) and body is Optional[dict] dereferenced unguarded.
        # Pre-existing Optional-flow, behavior unchanged.
        res, body = region_api.get_enterprise_app_import_status(
            import_record.region, import_record.enterprise_id, event_id)  # type: ignore[arg-type]
        status = body["bean"]["status"]  # type: ignore[index]
        if import_record.status != "success":
            if status == "success":
                logger.debug("app import success !")
                self.__save_enterprise_import_info(import_record, body["bean"]["metadata"], arch)  # type: ignore[index]
                import_record.source_dir = body["bean"]["source_dir"]  # type: ignore[index]
                import_record.format = body["bean"]["format"]  # type: ignore[index]
                import_record.status = "success"
                import_record.save()
                # 成功以后删除数据中心目录数据
                try:
                    region_api.delete_enterprise_import_file_dir(
                        import_record.region, import_record.enterprise_id, event_id)  # type: ignore[arg-type]
                except Exception as e:
                    logger.exception(e)
        apps_status = self.__wrapp_app_import_status(body["bean"]["apps"])  # type: ignore[index]

        next_status = self.__get_next_import_record_status(import_record.status, status, apps_status)
        self.__save_import_record_status(import_record, next_status)

        return import_record, apps_status

    def openapi_deploy_app_get_import_by_event_id(self, event_id: str) -> Tuple[Any, list]:
        import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
        if not import_record:
            raise RecordNotFound("import_record not found")
        # get import status from region
        # NOTE: import_record.region / .enterprise_id are Optional[str] (region_api
        # requires str) and body is Optional[dict] dereferenced unguarded.
        # Pre-existing Optional-flow, behavior unchanged.
        res, body = region_api.get_enterprise_app_import_status(
            import_record.region, import_record.enterprise_id, event_id)  # type: ignore[arg-type]
        metadata = []
        status = body["bean"]["status"]  # type: ignore[index]
        if import_record.status != "success":
            if status == "success":
                logger.debug("app import success !")
                import_record.scope = "enterprise"
                self.__save_enterprise_import_info(import_record, body["bean"]["metadata"], "")  # type: ignore[index]
                import_record.source_dir = body["bean"]["source_dir"]  # type: ignore[index]
                import_record.format = body["bean"]["format"]  # type: ignore[index]
                import_record.status = "success"
                import_record.save()
                metadata = json.loads(body["bean"]["metadata"])  # type: ignore[index]
                # 成功以后删除数据中心目录数据
                try:
                    region_api.delete_enterprise_import_file_dir(
                        import_record.region, import_record.enterprise_id, event_id)  # type: ignore[arg-type]
                except Exception as e:
                    logger.exception(e)
            else:
                self.__save_import_record_status(import_record, status)
        return import_record, metadata

    def get_and_update_import_status(self, tenant: Any, region: str, event_id: str) -> Tuple[Any, list]:
        """获取并更新导入状态"""
        import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
        if not import_record:
            raise RecordNotFound("import_record not found")
        # 去数据中心请求导入状态
        # NOTE: body is Optional[dict] (region_api) dereferenced unguarded, and
        # import_record.scope is a nullable model field passed where str is
        # expected. Pre-existing Optional-flow, behavior unchanged.
        res, body = region_api.get_app_import_status(region, tenant.tenant_name, event_id)
        status = body["bean"]["status"]  # type: ignore[index]
        if import_record.status != "success":
            if status == "success":
                logger.debug("app import success !")
                self.__save_import_info(
                    tenant, import_record.scope, body["bean"]["metadata"])  # type: ignore[arg-type,index]
                import_record.source_dir = body["bean"]["source_dir"]  # type: ignore[index]
                import_record.format = body["bean"]["format"]  # type: ignore[index]
                import_record.status = "success"
                import_record.save()
                # 成功以后删除数据中心目录数据
                try:
                    region_api.delete_import_file_dir(region, tenant.tenant_name, event_id)
                except Exception as e:
                    logger.exception(e)
        apps_status = self.__wrapp_app_import_status(body["bean"]["apps"])  # type: ignore[index]

        next_status = self.__get_next_import_record_status(import_record.status, status, apps_status)
        self.__save_import_record_status(import_record, next_status)

        return import_record, apps_status

    def __wrapp_app_import_status(self, app_status: Optional[str]) -> List[Dict[str, Any]]:
        """
        wrapper struct "app1:success,app2:failed" to
        [{"file_name":"app1","status":"success"},{"file_name":"app2","status":"failed"} ]
        """
        status_list: List[Dict[str, Any]] = []
        if not app_status:
            return status_list
        k_v_map_list = app_status.split(",")
        for value in k_v_map_list:
            kv_map_list = value.split(":")
            status_list.append({"file_name": kv_map_list[0], "status": kv_map_list[1]})
        return status_list

    def __normalize_import_app_template(self, app_template: dict) -> dict:
        apps = []
        for component in app_template.get("apps", []) or []:
            apps.append(self.__normalize_import_component_template(component))
        app_template["apps"] = apps
        return app_template

    @staticmethod
    def __normalize_import_component_template(component: dict) -> dict:
        service_extend_method = component.get("service_extend_method") or {}
        extend_method_map = dict(component.get("extend_method_map") or {})
        for field in EXTEND_METHOD_FIELDS:
            if extend_method_map.get(field) is None and service_extend_method.get(field) is not None:
                extend_method_map[field] = service_extend_method[field]
        if extend_method_map.get("container_cpu") is None and component.get("cpu") is not None:
            extend_method_map["container_cpu"] = component["cpu"]
        if not extend_method_map.get("init_memory") and component.get("memory") is not None:
            extend_method_map["init_memory"] = component["memory"]
        if extend_method_map.get("init_memory") is None and extend_method_map.get("min_memory") is not None:
            extend_method_map["init_memory"] = extend_method_map["min_memory"]
        if extend_method_map:
            component["extend_method_map"] = extend_method_map
        return component

    def get_import_app_dir(self, event_id: str) -> Any:
        """获取应用目录下的包"""
        import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
        if not import_record:
            raise RecordNotFound("import_record not found")
        # NOTE: import_record.region / .enterprise_id are Optional[str] (region_api
        # requires str); body is Optional[dict] dereferenced unguarded.
        # Pre-existing Optional-flow, behavior unchanged.
        res, body = region_api.get_enterprise_import_file_dir(
            import_record.region, import_record.enterprise_id, event_id)  # type: ignore[arg-type]
        app_tars = body["bean"]["apps"]  # type: ignore[index]
        return app_tars

    def create_import_app_dir(self, tenant: Any, user: Any, region: str) -> Any:
        """创建一个应用包"""
        event_id = make_uuid()
        res, body = region_api.create_import_file_dir(region, tenant.tenant_name, event_id)
        # NOTE: body is Optional[dict] (region_api) dereferenced unguarded.
        path = body["bean"]["path"]  # type: ignore[index]
        import_record_params = {
            "event_id": event_id,
            "status": "created_dir",
            "source_dir": path,
            "team_name": tenant.tenant_name,
            "region": region,
            "user_name": user.get_name()
        }
        import_record = app_import_record_repo.create_app_import_record(**import_record_params)
        return import_record

    def delete_import_app_dir_by_event_id(self, event_id: str) -> None:
        try:
            import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
            # NOTE: import_record may be None (no record for event_id); the attribute
            # access below would raise AttributeError, but it is caught by the broad
            # except. Behavior preserved — potential latent None-bug.
            region_api.delete_enterprise_import(
                import_record.region, import_record.enterprise_id, event_id)  # type: ignore[union-attr,arg-type]
        except Exception as e:
            logger.exception(e)

        app_import_record_repo.delete_by_event_id(event_id)

    def delete_import_app_dir(self, tenant: Any, region: str, event_id: str) -> None:
        try:
            region_api.delete_import(region, tenant.tenant_name, event_id)
        except Exception as e:
            logger.exception(e)

        app_import_record_repo.delete_by_event_id(event_id)

    @staticmethod
    def __normalize_import_identity_name(name: Any) -> str:
        return (name or "").strip()

    @classmethod
    def __same_import_app_identity(cls, app: Any, app_template: dict) -> bool:
        if not app:
            return False
        existing_name = cls.__normalize_import_identity_name(
            getattr(app, "app_name", "") or getattr(app, "group_name", "")
        )
        imported_name = cls.__normalize_import_identity_name(app_template.get("group_name", ""))
        return bool(getattr(app, "source", None) == "import" and existing_name == imported_name)

    @staticmethod
    def __canonical_import_template_for_fingerprint(app_template: dict) -> dict:
        template = json.loads(json.dumps(app_template, sort_keys=True))
        template.pop("group_key", None)
        return template

    @classmethod
    def __build_import_template_fingerprint(cls, app_template: dict) -> str:
        template = cls.__canonical_import_template_for_fingerprint(app_template)
        return hashlib.md5(json.dumps(template, sort_keys=True).encode("utf-8")).hexdigest()

    @classmethod
    def __is_same_import_version_content(cls, app_version: Any, app_template: dict) -> bool:
        if not app_version:
            return True
        try:
            existing_template = json.loads(app_version.app_template)
        except Exception:
            return False
        return cls.__build_import_template_fingerprint(existing_template) == cls.__build_import_template_fingerprint(
            app_template
        )

    @staticmethod
    def __build_import_collision_app_id(group_key: Any, group_name: str, fingerprint: str = "",
                                        index: int = 0) -> str:
        seed = "import:{0}:{1}".format(group_key, group_name)
        if fingerprint:
            seed = "{0}:{1}".format(seed, fingerprint)
        if index:
            seed = "{0}:{1}".format(seed, index)
        return hashlib.md5(seed.encode("utf-8")).hexdigest()

    def __resolve_import_app(self, app_template: dict) -> Tuple[Any, Any]:
        group_key = app_template["group_key"]
        group_name = self.__normalize_import_identity_name(app_template.get("group_name", ""))
        fingerprint = self.__build_import_template_fingerprint(app_template)
        candidate_ids = [
            group_key,
            self.__build_import_collision_app_id(group_key, group_name),
            self.__build_import_collision_app_id(group_key, group_name, fingerprint),
        ]

        for candidate_id in candidate_ids:
            app = rainbond_app_repo.get_rainbond_app_by_app_id(candidate_id)
            if not app:
                return candidate_id, None
            if not self.__same_import_app_identity(app, app_template):
                continue
            app_version = rainbond_app_repo.get_rainbond_app_version_by_app_id_and_version(
                candidate_id, app_template["group_version"]
            )
            if self.__is_same_import_version_content(app_version, app_template):
                return candidate_id, app

        for index in range(1, 100):
            candidate_id = self.__build_import_collision_app_id(group_key, group_name, fingerprint, index)
            app = rainbond_app_repo.get_rainbond_app_by_app_id(candidate_id)
            if not app:
                return candidate_id, None
            if not self.__same_import_app_identity(app, app_template):
                continue
            app_version = rainbond_app_repo.get_rainbond_app_version_by_app_id_and_version(
                candidate_id, app_template["group_version"]
            )
            if self.__is_same_import_version_content(app_version, app_template):
                return candidate_id, app
        # NOTE: `mes_show` is a typo for `msg_show` (latent bug carried from main, backlog).
        raise ExportAppError(msg="import app id collision", mes_show="导入应用模板 ID 冲突", status_code=500)  # type: ignore[call-arg]

    def __save_enterprise_import_info(self, import_record: Any, metadata: str, arch: str) -> None:
        rainbond_apps = []
        rainbond_app_versions = []
        metadata = json.loads(metadata)
        key_and_version_list = []
        if not metadata:
            return
        for app_template in metadata:
            app_template = self.__normalize_import_app_template(app_template)
            annotations = app_template.get("annotations", {})
            app_describe = app_template.pop("describe", "")
            apps = app_template.get("apps")
            if annotations.get("describe", ""):
                app_describe = annotations.pop("describe", "")
            resolved_app_id, app = self.__resolve_import_app(app_template)
            app_template["group_key"] = resolved_app_id
            if not arch:
                # NOTE: app_template.get("apps") may be None; iterating it unguarded
                # would raise TypeError. Potential latent None-bug (reached only when
                # arch is empty and the template omits "apps"). Behavior unchanged.
                arch_map = {a.get("arch", "amd64"): 1 for a in apps}  # type: ignore[union-attr]
                arch = "&".join(list(arch_map.keys()))
            # if app exists, update it
            if app:
                app.scope = import_record.scope
                app.describe = app_describe
                app.arch = app.arch if arch in app.arch.split(",") else app.arch + "," + arch
                app.save()
                app_version = rainbond_app_repo.get_rainbond_app_version_by_app_id_and_version(
                    app.app_id, app_template["group_version"])
                if app_version:
                    version_info = annotations.get("version_info")
                    version_alias = annotations.get("version_alias")
                    if not version_info:
                        version_info = app_version.app_version_info
                    if not version_alias:
                        version_alias = app_version.version_alias
                    # update version if exists
                    app_version.scope = import_record.scope
                    app_version.app_template = json.dumps(app_template)
                    app_version.template_version = app_template["template_version"]
                    # NOTE: trailing comma makes these tuple assignments
                    # (version_info, ) / (version_alias, ) instead of scalars — a real
                    # latent bug; the field is persisted as a 1-tuple. Left as-is
                    # (behavior change out of scope).
                    app_version.app_version_info = version_info,  # type: ignore[assignment]
                    app_version.version_alias = version_alias,  # type: ignore[assignment]
                    app_version.arch = arch
                    app_version.save()
                else:
                    # create a new version
                    rainbond_app_versions.append(self.create_app_version(app, import_record, app_template, arch))
            else:
                image_base64_string = app_template.pop("image_base64_string", "")
                if annotations.get("image_base64_string"):
                    image_base64_string = annotations.pop("image_base64_string", "")
                pic_url = ""
                if image_base64_string:
                    suffix = app_template.pop("suffix", "jpg")
                    if annotations.get("suffix"):
                        suffix = annotations.pop("suffix", "jpg")
                    pic_url = self.decode_image(image_base64_string, suffix)
                key_and_version = "{0}:{1}".format(app_template["group_key"], app_template['group_version'])
                if key_and_version in key_and_version_list:
                    continue
                key_and_version_list.append(key_and_version)
                rainbond_app = RainbondCenterApp(
                    enterprise_id=import_record.enterprise_id,
                    app_id=app_template["group_key"],
                    app_name=app_template["group_name"],
                    source="import",
                    create_team=import_record.team_name,
                    scope=import_record.scope,
                    describe=app_describe,
                    pic=pic_url,
                    arch=arch,
                    is_version=True,
                )
                rainbond_apps.append(rainbond_app)
                # create a new app version
                rainbond_app_versions.append(self.create_app_version(rainbond_app, import_record, app_template, arch))
        rainbond_app_repo.bulk_create_rainbond_app_versions(rainbond_app_versions)
        rainbond_app_repo.bulk_create_rainbond_apps(rainbond_apps)

    @staticmethod
    def create_app_version(app: RainbondCenterApp, import_record: Any, app_template: dict,
                           arch: str) -> RainbondCenterAppVersion:
        version = RainbondCenterAppVersion(
            scope=import_record.scope,
            enterprise_id=import_record.enterprise_id,
            app_id=app.app_id,
            app_template=json.dumps(app_template),
            version=app_template["group_version"],
            template_version=app_template["template_version"],
            record_id=import_record.ID,
            share_user=0,
            is_complete=True,
            app_version_info=app_template.get("annotations", {}).get("version_info", ""),
            version_alias=app_template.get("annotations", {}).get("version_alias", ""),
            arch=arch,
        )
        if app_store.is_no_multiple_region_hub(import_record.enterprise_id):
            version.region_name = import_record.region
        return version

    def __save_import_info(self, tenant: Any, scope: str, metadata: str) -> None:
        # NOTE: this method reads/writes RainbondCenterApp fields that no longer
        # exist on the current model (share_team, app_template, template_version,
        # is_complete, group_key, group_name, version, share_user, record_id). It is
        # legacy "v1" import code that would raise at runtime if reached. type: ignore
        # below preserves the existing (broken) behavior; real latent bug.
        rainbond_apps = []
        metadata = json.loads(metadata)
        key_and_version_list = []
        for app_template in metadata:
            app_template = self.__normalize_import_app_template(app_template)
            resolved_app_id, app = self.__resolve_import_app(app_template)
            app_template["group_key"] = resolved_app_id
            if app:
                # 覆盖原有应用数据
                app.share_team = tenant.tenant_name  # type: ignore[attr-defined]
                app.scope = scope
                app.describe = app_template.pop("describe", "")
                app.app_template = json.dumps(app_template)  # type: ignore[attr-defined]
                app.template_version = app_template.get("template_version", "")  # type: ignore[attr-defined]
                app.is_complete = True  # type: ignore[attr-defined]
                app.save()
                continue
            image_base64_string = app_template.pop("image_base64_string", "")
            pic_url = ""
            if image_base64_string:
                pic_url = self.decode_image(image_base64_string, app_template.pop("suffix", "jpg"))

            key_and_version = "{0}:{1}".format(app_template["group_key"], app_template['group_version'])
            if key_and_version in key_and_version_list:
                continue
            key_and_version_list.append(key_and_version)
            rainbond_app = RainbondCenterApp(  # type: ignore[misc]
                enterprise_id=tenant.enterprise_id,
                group_key=app_template["group_key"],
                group_name=app_template["group_name"],
                version=app_template['group_version'],
                share_user=0,
                record_id=0,
                share_team=tenant.tenant_name,
                source="import",
                scope=scope,
                describe=app_template.pop("describe", ""),
                pic=pic_url,
                app_template=json.dumps(app_template),
                is_complete=True,
                is_version=True,
                template_version=app_template.get("template_version", ""))
            rainbond_apps.append(rainbond_app)
        rainbond_app_repo.bulk_create_rainbond_apps(rainbond_apps)

    def decode_image(self, image_base64_string: str, suffix: str) -> str:
        if not image_base64_string:
            return ""
        try:
            filename = 'uploads/{0}.{1}'.format(make_uuid(), suffix)
            savefilename = os.path.join(settings.MEDIA_ROOT, filename)
            queryfilename = os.path.join(settings.MEDIA_URL, filename)
            with open(savefilename, "wb") as f:
                f.write(base64.decodebytes(image_base64_string.encode('utf-8')))
            return queryfilename
        except Exception as e:
            logger.exception(e)
        return ""

    def get_importing_apps(self, tenant: Any, user: Any, region: str) -> list:
        importing_records = app_import_record_repo.get_importing_record(tenant.tenant_name, user.nick_name)
        importing_list = []
        for importing_record in importing_records:
            # NOTE: importing_record.event_id is a nullable model field; the callee
            # requires str. Pre-existing Optional-flow, behavior unchanged.
            import_record, apps_status = self.get_and_update_import_status(
                tenant, region, importing_record.event_id)  # type: ignore[arg-type]
            if import_record.status not in ("success", "failed"):
                importing_list.append(apps_status)
        return importing_list

    def get_user_not_finish_import_record_in_enterprise(self, eid: str, user: Any) -> Any:
        return app_import_record_repo.get_user_not_finished_import_record_in_enterprise(eid, user.nick_name)

    def get_user_unfinished_import_record(self, tenant: Any, user: Any) -> Any:
        return app_import_record_repo.get_user_unfinished_import_record(tenant.tenant_name, user.nick_name)

    def create_app_import_record(self, team_name: str, user_name: str, region: str) -> Any:
        event_id = make_uuid()
        import_record_params = {
            "event_id": event_id,
            "status": "uploading",
            "team_name": team_name,
            "region": region,
            "user_name": user_name
        }
        return app_import_record_repo.create_app_import_record(**import_record_params)

    def create_app_import_record_2_enterprise(self, eid: str, user_name: str) -> Any:
        event_id = make_uuid()
        region = self.select_handle_region(eid)
        import_record_params = {
            "event_id": event_id,
            "status": "uploading",
            "enterprise_id": eid,
            "region": region.region_name,
            "user_name": user_name
        }
        return app_import_record_repo.create_app_import_record(**import_record_params)

    def get_upload_url(self, region: str, event_id: str) -> str:
        region = region_repo.get_region_by_region_name(region)
        raw_url = "/app/upload"
        upload_url = ""
        if region:
            splits_texts = region.wsurl.split("://")
            if splits_texts[0] == "wss":
                upload_url = "https://" + splits_texts[1] + raw_url
            else:
                upload_url = "http://" + splits_texts[1] + raw_url
        return upload_url + "/" + event_id

    def get_upload_package_url(self, region: str, event_id: str) -> str:
        region = region_repo.get_region_by_region_name(region)
        raw_url = "/package_build/component/events"
        get_upload_package_url = ""
        if region:
            splits_texts = region.wsurl.split("://")
            if splits_texts[0] == "wss":
                get_upload_package_url = "https://" + splits_texts[1] + raw_url
            else:
                get_upload_package_url = "http://" + splits_texts[1] + raw_url
        return get_upload_package_url + "/" + event_id


class MyEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


export_service = AppExportService()
import_service = AppImportService()

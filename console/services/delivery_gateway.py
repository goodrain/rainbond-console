"""Adapters for existing artifact, installer and export executors; no snapshot source."""
import copy
import json
import uuid
from types import SimpleNamespace
from urllib.parse import urlsplit
from django.utils import timezone
from console.services.delivery_manifest import DeliveryError, public_manifest


class DeliveryGateway:
    @staticmethod
    def region_api():
        from www.apiclient.regionapi import RegionInvokeApi
        return RegionInvokeApi()

    def source(self, scope):
        from www.models.main import Tenants, ServiceGroup, ServiceGroupRelation
        from console.services.share_services import share_service
        tenant = Tenants.objects.get(tenant_name=scope["team_name"], enterprise_id=scope["enterprise_id"])
        app = ServiceGroup.objects.filter(ID=scope["app_id"], tenant_id=tenant.tenant_id,
                                          region_name=scope["region_name"]).first()
        if not app:
            raise DeliveryError("源应用不存在", 404)
        services = share_service.query_share_service_info(tenant, app.ID, include_unbuilt=True)
        component_ids = list(ServiceGroupRelation.objects.filter(group_id=app.ID).values_list("service_id", flat=True))
        versions = {}
        if component_ids:
            _, response = self.region_api().get_team_services_deploy_version(scope["region_name"], tenant.tenant_name,
                                                                             {"service_ids": component_ids})
            if not response or not isinstance(response.get("list"), list):
                raise DeliveryError("无法获取组件构建信息，请稍后重试", 502)
            versions = {item["service_id"]: item for item in response["list"] if item}
        for component in services:
            version = versions.get(component["service_id"], {})
            component["delivery_available"] = version.get("final_status") == "success"
            if not component["delivery_available"]:
                continue
            component["deploy_version"] = version["build_version"]
            component["build_version"] = version["build_version"]
            component["delivered_type"] = version["delivered_type"]
            component["delivered_path"] = version.get("delivered_path", "")
            component["code_branch"] = version.get("code_branch", "")
            component["code_version"] = version.get("code_version", "")
        plugins = share_service.get_group_services_used_plugins(app.ID)
        shared_plugins = share_service.get_plugins_group_items(plugins) if plugins else []
        for plugin in shared_plugins:
            build = self.region_api().get_build_status(scope["region_name"], tenant.tenant_name, plugin["plugin_id"],
                                                       plugin["build_version"])
            info = (build or {}).get("bean", {})
            plugin["built_image"] = info.get("build_local_image", "")
            plugin["delivery_available"] = info.get("status") == "success" and bool(plugin["built_image"])
        for component in services:
            component["service_related_plugin_config"] = share_service.wrapper_service_plugin_config(
                component.get("service_related_plugin_config", []), shared_plugins)
        keys = {c["service_id"]: c["service_key"] for c in services}
        source = {
            "template_version": "v3" if any(c.get("vm") for c in services) else "v2",
            "apps": services,
            "plugins": shared_plugins,
            "governance_mode": app.governance_mode,
            "k8s_resources": list(share_service.get_k8s_resources(app.ID)),
            "app_config_groups": share_service.config_groups(scope["region_name"], keys),
            "ingress_http_routes": share_service._list_http_ingresses(tenant, keys),
            "application": {
                "name": app.group_name,
                "logo": getattr(app, "logo", "") or "",
                "description": getattr(app, "note", "") or ""
            },
            "arch": "&".join(sorted({c.get("arch", "amd64")
                                     for c in services}))
        }
        from console.services.app_import_and_export_service import MyEncoder
        return json.loads(json.dumps(source, cls=MyEncoder)), app.group_name

    def dispatch(self, task, item):
        from console.appstore.appstore import app_store
        from console.services.share_services import share_service
        api, template = self.region_api(), task.template
        if task.kind == "catalog_publish":
            return self.dispatch_catalog_artifact(task, item)
        component = copy.deepcopy(item.component)
        image = app_store.get_app_hub_info(None, template.id.hex, template.enterprise_id)
        if item.key.startswith("plugin:"):
            _, body = api.share_plugin(
                template.region_name, template.team_name, component["plugin_id"], {
                    "event_id": uuid.uuid4().hex,
                    "plugin_key": component["plugin_key"],
                    "plugin_version": component["build_version"],
                    "image_info": image
                })
        else:
            if component.get("vm"):
                from console.services.service_services import base_service
                states = base_service.status_multi_service(region=template.region_name,
                                                           tenant_name=template.team_name,
                                                           service_ids=[item.key],
                                                           enterprise_id=template.enterprise_id)
                if not any(
                        row.get("service_id") == item.key and row.get("status") in share_service.VM_PUBLISH_CLOSED_STATUSES
                        for row in states):
                    raise DeliveryError("虚拟机发布前请先关机")
                source, token = share_service._prepare_vm_publish_image_source(template.region_name,
                                                                               template.team_name,
                                                                               component,
                                                                               SimpleNamespace(
                                                                                   service_alias=component["service_alias"],
                                                                                   service_id=item.key),
                                                                               force_export=True)
                image.update(vm_image_source=source, vm_image_token=token)
            body = {
                "service_key": component["service_key"],
                "app_version": str(task.id).replace("-", ""),
                "deploy_version": component["deploy_version"],
                "arch": component.get("arch", "amd64"),
                "share_user": task.actor_name,
                "share_scope": "team",
                "image_info": image,
                "slug_info": app_store.get_slug_hub_info(None, template.id.hex, template.enterprise_id)
            }
            _, body = api.share_service(template.region_name, template.team_name, component["service_alias"], body)
        bean = (body or {}).get("bean")
        if not bean or not bean.get("share_id"):
            raise DeliveryError("数据中心未受理同步任务", 502)
        # Persist only execution identifiers and immutable output references.
        return {key: value for key, value in bean.items() if key in ("share_id", "event_id", "image_name", "slug_path")}

    def status(self, task, item):
        template = task.template
        if task.kind == "catalog_publish":
            _, body = self.region_api().delivery_artifact_status(template.region_name, template.enterprise_id, item.remote_id)
            return (body or {}).get("bean", {})
        if item.key.startswith("plugin:"):
            _, body = self.region_api().share_plugin_result(template.region_name, template.team_name,
                                                            item.component["plugin_id"], item.remote_id)
        else:
            _, body = self.region_api().share_service_result(template.region_name, template.team_name,
                                                             item.component["service_alias"], item.remote_id)
        return (body or {}).get("bean", {})

    def logs(self, task, item):
        template = task.template
        _, body = self.region_api().get_events_log(template.team_name, template.region_name, item.event_id)
        # Event logs are a dedicated authorized endpoint, never task result metadata.
        rows = (body or {}).get("list", [])
        return {
            "lines": [
                str(row.get("message") or row.get("Message") or row.get("msg") or "") if isinstance(row, dict) else str(row)
                for row in rows
            ]
        }

    def export(self, task):
        from console.services.app_import_and_export_service import export_service
        manifest = self.version_manifest(task.version)
        manifest = export_service._AppExportService__normalize_export_template(manifest)
        manifest.setdefault("annotations", {}).update(version_info=task.version.description)
        manifest["helm_chart"] = {"image_handle": task.payload.get("image_handle", "image_save")}
        from console.appstore.appstore import app_store
        image_auth = app_store.get_app_hub_info(None, task.template_id.hex, task.template.enterprise_id)
        for component in manifest["apps"]:
            component["service_image"] = self.auth_for_image(component.get("share_image", ""), image_auth)
        for plugin in manifest.get("plugins", []):
            plugin["plugin_image"] = self.auth_for_image(plugin.get("share_image", ""), image_auth)
        logo = manifest.get("annotations", {}).get("logo", "")
        logo_path = urlsplit(logo).path
        if "/uploads/" in logo_path and logo_path.startswith("/"):
            try:
                encoded = export_service.encode_image(logo_path)
            except OSError:
                encoded = ""
            if encoded:
                manifest["annotations"].update(image_base64_string=encoded, suffix=logo_path.rsplit(".", 1)[-1])
        event_id = uuid.uuid4().hex
        self.region_api().export_app(
            task.template.region_name, task.template.enterprise_id, {
                "event_id": event_id,
                "group_key": task.template_id.hex,
                "version": task.version.version,
                "format": task.payload.get("format", "rainbond-app"),
                "group_metadata": json.dumps(manifest)
            })
        return {"event_id": event_id}

    def export_status(self, task):
        _, body = self.region_api().get_app_export_status(task.template.region_name, task.template.enterprise_id,
                                                          task.result["event_id"])
        bean = (body or {}).get("bean", {})
        return {"status": bean.get("status", "exporting"), "download_path": bean.get("tar_file_href", "")}

    def install(self, task):
        from www.models.main import Tenants, ServiceGroup, Users
        from console.models.main import RegionConfig
        from console.services.group_service import group_service
        from console.services.market_app_service import market_app_service
        from console.services.market_app.app_upgrade import AppUpgrade
        from console.services.market_app_preflight_service import market_install_preflight_service
        target = task.payload["target"]
        manifest, market_name = self.installation_manifest(task)
        tenant = Tenants.objects.get(tenant_name=target["team_name"], enterprise_id=task.template.enterprise_id)
        region = RegionConfig.objects.get(region_name=target["region_name"], enterprise_id=tenant.enterprise_id)
        user = Users.objects.get(user_id=task.actor_id)
        plugin = manifest.get("platform_plugin")
        if plugin:
            from console.models.main import EnterpriseUserPerm
            if not EnterpriseUserPerm.objects.filter(enterprise_id=tenant.enterprise_id, user_id=user.user_id).exists():
                raise DeliveryError("平台插件仅允许平台管理员安装")
            if task.kind == "test":
                manifest.pop("platform_plugin")
            elif not task.version.listings.filter(publication_status="published").exists():
                raise DeliveryError("平台插件审核上架后才可安装，审核前可部署测试")
        for component in manifest["apps"]:
            from console.services.delivery_credentials import open_environment
            environment = open_environment(task.payload.get("encrypted_environment", ""))
            values = environment.get(component["service_id"], {})
            for env in component.get("service_env_map_list", []) + component.get("service_connect_info_map_list", []):
                if env["attr_name"] in values:
                    env["attr_value"] = str(values[env["attr_name"]])
        from console.appstore.appstore import app_store
        template_key = manifest.get("group_key") or task.template_id.hex
        market = None
        if market_name:
            from console.services.app import app_market_service
            market = app_market_service.get_app_market_by_name(task.template.enterprise_id,
                                                               market_name,
                                                               user_id=str(task.actor_id),
                                                               raise_exception=True)
        image_auth = app_store.get_app_hub_info(market, template_key, task.template.enterprise_id)
        for component in manifest["apps"]:
            component["service_image"] = self.auth_for_image(component.get("share_image", ""), image_auth)
        for plugin_info in manifest.get("plugins", []):
            plugin_info["plugin_image"] = self.auth_for_image(plugin_info.get("share_image", ""), image_auth)
        market_app_service._ensure_vm_template_allowed(tenant, region.region_name, manifest)
        preflight = market_install_preflight_service.run(tenant, region, manifest, check_images=False)
        if preflight.get("should_block"):
            raise DeliveryError("目标环境资源或能力不足")
        # Stable target name allows recovery after an interrupted install without creating another application.
        k8s_app = "delivery-" + task.id.hex[:20]
        app = ServiceGroup.objects.filter(tenant_id=tenant.tenant_id, region_name=region.region_name, k8s_app=k8s_app).first()
        if not app:
            result = group_service.create_app(tenant,
                                              region.region_name,
                                              target["app_name"],
                                              note=manifest.get("annotations", {}).get("describe", ""),
                                              logo=manifest.get("annotations", {}).get("logo", ""),
                                              username=task.actor_name,
                                              eid=tenant.enterprise_id,
                                              k8s_app=k8s_app)
            app = ServiceGroup.objects.get(ID=result["group_id"])
        from www.models.main import TenantServiceGroup
        group = TenantServiceGroup.objects.filter(service_group_id=app.ID,
                                                  group_key=template_key,
                                                  group_version=task.version.version).first()
        group = group or market_app_service._create_tenant_service_group(region.region_name,
                                                                         tenant.tenant_id,
                                                                         app.ID,
                                                                         template_key,
                                                                         task.version.version,
                                                                         task.template.name,
                                                                         external_template=manifest)
        installer = AppUpgrade(tenant.enterprise_id,
                               tenant,
                               region,
                               user,
                               app,
                               task.version.version,
                               group,
                               manifest,
                               bool(market_name),
                               market_name,
                               is_deploy=True)
        events = installer.install()
        if manifest.get("platform_plugin"):
            market_app_service._create_rbdplugin_if_needed(tenant, region, manifest, app.ID)
        return {
            "app_id": str(app.ID),
            "app_model_id": template_key,
            "upgrade_group_id": str(group.ID),
            "region_name": region.region_name,
            "event_ids": market_app_service._extract_event_ids(events),
            "service_ids": [component.component.component_id for component in installer.new_app.components()]
        }

    def upgrade_info(self, task, user, admin=False):
        if task.kind != "delivery" or task.status != "succeeded" or not task.result.get("app_id"):
            return {"available": False}
        from www.models.main import ServiceGroup, TenantServiceGroup, TenantServiceInfo
        from console.services.delivery_access import team_access
        from console.services.market_app_service import market_app_service
        from console.utils.version import sorted_versions
        target = task.payload["target"]
        app_id = str(task.result["app_id"])
        tenant = team_access(user, target["team_name"], 330003, app_id, admin)
        if not ServiceGroup.objects.filter(ID=app_id, tenant_id=tenant.tenant_id,
                                           region_name=target["region_name"]).exists():
            return {"available": False}
        # New tasks retain the installed source. Existing tasks resolve it from their real component IDs.
        if task.result.get("upgrade_group_id"):
            filters = {"ID": task.result["upgrade_group_id"], "group_key": task.result["app_model_id"]}
        else:
            ids = TenantServiceInfo.objects.filter(
                tenant_id=tenant.tenant_id, service_region=target["region_name"],
                service_id__in=task.result.get("service_ids", [])).values_list("tenant_service_group_id", flat=True)
            filters = {"ID__in": ids}
        groups = list(TenantServiceGroup.objects.filter(tenant_id=tenant.tenant_id,
                                                        service_group_id=app_id, region_name=target["region_name"],
                                                        **filters))
        if len(groups) != 1:
            return {"available": False}
        group = groups[0]
        from console.models.main import AppUpgradeRecord, UpgradeStatus
        last = AppUpgradeRecord.objects.filter(tenant_id=tenant.tenant_id, group_id=app_id,
                                               upgrade_group_id=group.ID, group_key=group.group_key,
                                               record_type="upgrade").order_by("-ID").first()
        resume = last if last and last.version and last.status in (
            UpgradeStatus.UPGRADING.value, UpgradeStatus.PARTIAL_UPGRADED.value,
            UpgradeStatus.UPGRADE_FAILED.value, UpgradeStatus.DEPLOY_FAILED.value) else None
        versions = [] if resume else market_app_service.get_models_upgradeable_version(
            task.template.enterprise_id, group.group_key, app_id, str(group.ID)) or []
        if not versions and not resume:
            return {"available": False}
        return {
            "available": True,
            "current_version": group.group_version,
            "latest_version": resume.version if resume else sorted_versions(list(versions))[0],
            **({"resume_record_id": str(resume.ID)} if resume else {}),
            "upgrade_group_id": str(group.ID),
            "app_model_id": group.group_key,
            "target": {"team_name": target["team_name"], "region_name": target["region_name"], "app_id": app_id}
        }

    def installation_status(self, task):
        target, events = task.payload["target"], task.result.get("event_ids", [])
        if not events:
            from console.services.service_services import base_service
            ids = task.result.get("service_ids", [])
            states = base_service.status_multi_service(region=target["region_name"],
                                                       tenant_name=target["team_name"],
                                                       service_ids=ids,
                                                       enterprise_id=task.template.enterprise_id) if ids else []
            return "succeeded" if len(states) == len(ids) and ids and all(row.get("status") == "running"
                                                                          for row in states) else "running"
        body = self.region_api().get_tenant_events(target["region_name"], target["team_name"], events)
        rows = (body or {}).get("list", [])
        states = {str(row.get("EventID") or row.get("event_id")): row.get("Status") or row.get("status") for row in rows}
        if any(states.get(key) in ("failure", "failed", "timeout") for key in events):
            return "failed"
        return "succeeded" if all(states.get(key) == "success" for key in events) else "running"

    def validate_market(self, enterprise_id, market_id, actor_id):
        from console.services.app import app_market_service
        from console.utils.offline import is_cloud_market_disabled
        if is_cloud_market_disabled():
            raise DeliveryError("当前环境未启用在线应用市场", 403)
        info, market = app_market_service.get_app_market(
            enterprise_id, market_id, user_id=str(actor_id), extend="true", raise_exception=True)
        if not market.access_key or info.get("status") != 1 or "Write" not in info.get("access_actions", []):
            raise DeliveryError("该应用市场没有发布权限，请使用具有写入权限的市场授权", 403)
        return market

    def prepare_catalog(self, task):
        from console.appstore.appstore import app_store
        from console.models.delivery_template import DeliveryTask
        destination = task.payload["destination"]
        if destination["type"] == "local":
            return
        market = self.validate_market(task.template.enterprise_id, destination["market_id"], task.actor_id)
        if task.result.get("market_app_id"):
            return
        remote_id = None
        for previous in DeliveryTask.objects.filter(template=task.template, kind="catalog_publish").exclude(id=task.id):
            if previous.payload.get("destination") == destination and previous.result.get("market_app_id"):
                remote_id = previous.result["market_app_id"]
                break
        if not remote_id:
            remote = app_store.create_app(
                market, {
                    "name": task.version.manifest["group_name"],
                    "desc": task.version.manifest.get("annotations", {}).get("describe", ""),
                    "introduction": task.version.manifest.get("annotations", {}).get("details", ""),
                    "logo": task.version.manifest.get("annotations", {}).get("logo", ""),
                    "publish_type": "private",
                    "tags": []
                })
            data = remote.to_dict() if hasattr(remote, "to_dict") else remote
            remote_id = data.get("app_key_id") or data.get("app_id") if isinstance(data, dict) else None
            if not remote_id:
                raise DeliveryError("商店未返回应用标识，暂不能上架", 502)
        task.result["market_app_id"] = remote_id

    def dispatch_catalog_artifact(self, task, item):
        from console.appstore.appstore import app_store
        from console.services.app import app_market_service
        destination = task.payload["destination"]
        remote_id = task.result.get("market_app_id", task.template_id.hex)
        market = None
        if destination["type"] == "market":
            market = app_market_service.get_app_market_by_name(task.template.enterprise_id,
                                                               destination["market_id"],
                                                               user_id=str(task.actor_id),
                                                               raise_exception=True)
        source = app_store.get_app_hub_info(None, task.template_id.hex, task.template.enterprise_id)
        source_auth = self.auth_for_image(item.component.get("share_image", ""), source)
        data = {
            "service_key": task.template_id.hex + "-" + str(item.id).replace("-", "")[:16],
            "version": task.version.version,
            "event_id": uuid.uuid4().hex,
            "actor": task.actor_name,
            "source_image": item.component.get("share_image", ""),
            "source_slug": item.component.get("share_slug_path", ""),
            "source_auth": {
                "user": source_auth.get("hub_user", ""),
                "password": source_auth.get("hub_password", "")
            },
            "image_info": app_store.get_app_hub_info(market, remote_id, task.template.enterprise_id),
            "slug_info": app_store.get_slug_hub_info(market, remote_id, task.template.enterprise_id)
        }
        _, body = self.region_api().share_delivery_artifact(task.template.region_name, task.template.enterprise_id, data)
        bean = (body or {}).get("bean", {})
        if not bean.get("share_id"):
            raise DeliveryError("商店产物同步未受理", 502)
        return {key: value for key, value in bean.items() if key in ("share_id", "event_id", "image_name", "slug_path")}

    def publish_catalog(self, task):
        from console.models.main import RainbondCenterApp, RainbondCenterAppVersion
        from console.services.app import app_market_service
        manifest = self.version_manifest(task.version)
        destination = task.payload["destination"]
        results = {item.key: item.result for item in task.items.all()}
        for component in manifest["apps"]:
            self.apply_artifact_result(component, results[component["service_id"]])
        for plugin in manifest.get("plugins", []):
            self.apply_artifact_result(plugin, results["plugin:" + plugin["plugin_id"]])
        if destination["type"] == "market":
            remote_id = task.result["market_app_id"]
            manifest["group_key"] = remote_id
            market = app_market_service.get_app_market_by_name(task.template.enterprise_id,
                                                               destination["market_id"],
                                                               user_id=str(task.actor_id),
                                                               raise_exception=True)
            app_market_service.create_market_app_model_version(
                market, remote_id, {
                    "version": task.version.version,
                    "description": task.version.description,
                    "template": manifest,
                    "template_type": "application_template",
                    "arch": manifest.get("arch", "amd64"),
                    "is_plugin": bool(manifest.get("platform_plugin")),
                    "version_alias": ""
                })
        else:
            # Only reviewed copies enter the existing enterprise catalog. Private versions never enter it.
            RainbondCenterApp.objects.update_or_create(app_id=task.template_id.hex,
                                                       defaults={
                                                           "app_name": manifest["group_name"],
                                                           "enterprise_id": task.template.enterprise_id,
                                                           "scope": "enterprise",
                                                           "describe": manifest.get("annotations", {}).get("describe", ""),
                                                           "details": manifest.get("annotations", {}).get("details", ""),
                                                           "pic": manifest.get("annotations", {}).get("logo", ""),
                                                           "create_user": task.actor_id,
                                                           "create_team": task.template.team_name,
                                                           "arch": manifest.get("arch", "amd64"),
                                                           "is_version": True
                                                       })
            RainbondCenterAppVersion.objects.update_or_create(app_id=task.template_id.hex,
                                                              version=task.version.version,
                                                              defaults={
                                                                  "enterprise_id": task.template.enterprise_id,
                                                                  "scope": "enterprise",
                                                                  "source": "local",
                                                                  "app_template": json.dumps(manifest),
                                                                  "app_version_info": task.version.description,
                                                                  "record_id": 0,
                                                                  "share_user": str(task.actor_id),
                                                                  "share_team": task.template.team_name,
                                                                  "template_type": "application_template",
                                                                  "is_complete": True,
                                                                  "update_time": timezone.now(),
                                                                  "template_version": manifest.get("template_version", "v2"),
                                                                  "arch": manifest.get("arch", "amd64")
                                                              })
        return {**task.result, "catalog_id": task.template_id.hex, "destination": destination, "published_manifest": manifest}

    @staticmethod
    def apply_artifact_result(component, result):
        if result.get("image_name"):
            component["share_image"] = result["image_name"]
            for disk in (component.get("vm") or {}).get("disk_layout", []):
                if str(disk.get("disk_role", "")).lower() == "root":
                    disk.update(image=result["image_name"], source_type="http-artifact")
                    disk.pop("source_uri", None)
        if result.get("slug_path"):
            component["share_slug_path"] = result["slug_path"]

    @staticmethod
    def auth_for_image(image, registry):
        host = urlsplit("//" + str(registry.get("hub_url") or "").split("://")[-1]).netloc
        return registry if host and image.startswith(host + "/") else {}

    def installation_manifest(self, task):
        target = task.payload["target"]
        if target["team_name"] != task.template.team_name or target["region_name"] != task.template.region_name:
            published = list(task.version.listings.filter(publication_status="published").select_related("publication_task"))
            published.sort(key=lambda row: row.destination.get("type") != "local")
            for row in published:
                if row.publication_task and row.publication_task.result.get("published_manifest"):
                    return self.version_manifest(task.version,
                                                 row.publication_task.result["published_manifest"]), row.destination.get(
                                                     "market_id", "")
        return self.version_manifest(task.version), ""

    def upgrade_manifest(self, version, published=None):
        from console.appstore.appstore import app_store
        manifest = self.version_manifest(version, published)
        registry = app_store.get_app_hub_info(None, version.template_id.hex, version.template.enterprise_id)
        for component in manifest["apps"]:
            component["service_image"] = self.auth_for_image(component.get("share_image", ""), registry)
        for plugin in manifest.get("plugins", []):
            plugin["plugin_image"] = self.auth_for_image(plugin.get("plugin_image", plugin.get("share_image", "")), registry)
        manifest["update_time"] = version.created_at
        return manifest

    def version_manifest(self, version, published=None):
        from console.services.delivery_credentials import open_environment
        saved = version.manifest
        environment = open_environment(saved.get("encrypted_environment", ""))
        legacy = [(component["service_id"], env["attr_name"]) for component in saved.get("apps", [])
                  for env in component.get("service_env_map_list", []) + component.get("service_connect_info_map_list", [])
                  if env.get("required_on_install")]
        if legacy and not saved.get("encrypted_environment"):
            scope = {key: getattr(version.template, key) for key in ("enterprise_id", "team_name", "region_name", "app_id")}
            source, _ = self.source(scope)
            for component in source.get("apps", []):
                for env in component.get("service_env_map_list", []) + component.get("service_connect_info_map_list", []):
                    if (component["service_id"], env["attr_name"]) in legacy:
                        environment.setdefault(component["service_id"], {})[env["attr_name"]] = env.get("attr_value", "")
            if any(name not in environment.get(service_id, {}) for service_id, name in legacy):
                raise DeliveryError("旧版本环境配置已丢失，请重新创建模板版本")
        manifest = public_manifest(published if published is not None else saved)
        for component in manifest.get("apps", []):
            values = environment.get(component["service_id"], {})
            for env in component.get("service_env_map_list", []) + component.get("service_connect_info_map_list", []):
                env.pop("required_on_install", None)
                if env["attr_name"] in values:
                    env["attr_value"] = values[env["attr_name"]]
        return manifest

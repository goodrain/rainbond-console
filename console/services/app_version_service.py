# -*- coding: utf-8 -*-
import copy
import hashlib
import json
import time

from console.enum.app import GovernanceModeEnum
from console.models.main import RainbondCenterApp, RainbondCenterAppVersion, AppUpgradeSnapshot, AppUpgradeRecord, UpgradeStatus, AppUpgradeRecordType
from console.exception.main import ServiceHandleException
from console.repositories.app_snapshot import app_snapshot_repo
from console.repositories.app_version_repo import app_version_template_relation_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.share_repo import share_repo
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.backup_service import groupapp_backup_service
from console.services.market_app.app_restore import AppRestore
from console.services.share_services import share_service
from django.db import transaction
from www.models.main import make_uuid, TenantServiceGroup


class AppVersionRollbackRestore(AppRestore):
    def __init__(self, tenant, region, user, app, component_group, app_upgrade_record, current_version, target_version):
        self.current_snapshot_version = current_version
        self.target_snapshot_version = target_version
        super(AppVersionRollbackRestore, self).__init__(tenant, region, user, app, component_group, app_upgrade_record)

    def create_rollback_record(self):
        rollback_record = self.upgrade_record.to_dict()
        rollback_record.pop("ID")
        rollback_record.pop("can_rollback", None)
        rollback_record.pop("is_finished", None)
        rollback_record["status"] = UpgradeStatus.ROLLING.value
        rollback_record["record_type"] = AppUpgradeRecordType.ROLLBACK.value
        rollback_record["parent_id"] = 0
        rollback_record["version"] = self.target_snapshot_version
        rollback_record["old_version"] = self.current_snapshot_version
        self.rollback_record = AppUpgradeRecord.objects.create(**rollback_record)


class AppVersionService(object):
    HIDDEN_TEMPLATE_SOURCE = "app_version"
    HIDDEN_TEMPLATE_SCOPE = "team"

    @staticmethod
    def _build_hidden_template_name(app):
        return app.group_name

    @staticmethod
    def _build_hidden_template_id_by_app_id(app_id):
        return hashlib.md5("app-version:{0}".format(app_id).encode("utf-8")).hexdigest()

    @classmethod
    def _build_hidden_template_id(cls, app):
        return cls._build_hidden_template_id_by_app_id(app.ID)

    @staticmethod
    def _split_version(version):
        if not version:
            return [1, 0, 0]
        parts = str(version).split(".")
        if len(parts) != 3 or any(not p.isdigit() for p in parts):
            return [1, 0, 0]
        return [int(p) for p in parts]

    def _next_version(self, latest_version):
        major, minor, patch = self._split_version(latest_version)
        return "{0}.{1}.{2}".format(major, minor, patch + 1)

    def get_relation(self, app_id):
        return app_version_template_relation_repo.get_by_group_id(app_id)

    def get_hidden_template(self, app_id):
        relation = self.get_relation(app_id)
        if not relation:
            return None, None
        return relation, rainbond_app_repo.get_rainbond_app_by_app_id(relation.app_model_id)

    def get_or_create_hidden_template(self, tenant, user, app):
        relation, hidden_app = self.get_hidden_template(app.ID)
        if relation and hidden_app:
            return relation, hidden_app

        hidden_app_id = self._build_hidden_template_id(app)
        hidden_app_name = self._build_hidden_template_name(app)

        hidden_app = rainbond_app_repo.get_rainbond_app_by_app_id(hidden_app_id)
        if not hidden_app:
            hidden_app = rainbond_app_repo.add_basic_app_info(
                app_id=hidden_app_id,
                app_name=hidden_app_name,
                create_user=user.user_id,
                create_team=tenant.tenant_name,
                source=self.HIDDEN_TEMPLATE_SOURCE,
                dev_status="",
                scope=self.HIDDEN_TEMPLATE_SCOPE,
                describe="App version hidden template for app {0}".format(app.ID),
                is_ingerit=False,
                enterprise_id=tenant.enterprise_id,
                install_number=0,
                is_official=False,
                details="",
                arch="amd64",
                is_version=True,
            )
        elif hidden_app.app_name != hidden_app_name:
            hidden_app.app_name = hidden_app_name
            hidden_app.save()

        relation = app_version_template_relation_repo.get_or_create(
            app.ID,
            defaults={
                "tenant_id": tenant.tenant_id,
                "app_model_id": hidden_app_id,
                "app_model_name": hidden_app_name,
                "template_type": "application_version",
            },
        )
        return relation, hidden_app

    @transaction.atomic
    def delete_hidden_template(self, app_id):
        relation, _ = self.get_hidden_template(app_id)
        hidden_app_id = relation.app_model_id if relation else self._build_hidden_template_id_by_app_id(app_id)
        rainbond_app_repo.delete_app_version_by_id(hidden_app_id)
        rainbond_app_repo.delete_app_by_id(hidden_app_id)
        if relation:
            app_version_template_relation_repo.delete_by_group_id(app_id)

    def _build_app_template(self, tenant, region, user, app, hidden_app_id, version):
        services = share_service.query_share_service_info(team=tenant, group_id=app.ID, scope="team")
        plugins = share_service.get_group_services_used_plugins(group_id=app.ID)
        plugins = share_service.get_plugins_group_items(plugins) if plugins else []
        return self._assemble_app_template(tenant, region, app, hidden_app_id, version, services, plugins, list(share_service.get_k8s_resources(app.ID)))

    def _build_app_template_from_share_info(self, tenant, region, user, app, hidden_app_id, version, share_info):
        services = share_info.get("share_service_list") or share_service.query_share_service_info(team=tenant, group_id=app.ID, scope="team")
        plugins = share_info.get("share_plugin_list") or share_service.get_group_services_used_plugins(group_id=app.ID)
        plugins = share_service.get_plugins_group_items(plugins) if plugins else []
        k8s_resources = share_info.get("share_k8s_resources")
        if k8s_resources is None:
            k8s_resources = list(share_service.get_k8s_resources(app.ID))
        return self._assemble_app_template(tenant, region, app, hidden_app_id, version, services, plugins, k8s_resources)

    def _assemble_app_template(self, tenant, region, app, hidden_app_id, version, services, plugins, k8s_resources):
        service_ids_keys_map = {svc["service_id"]: svc["service_key"] for svc in services}
        app_template = {
            "template_version": "v2",
            "group_key": hidden_app_id,
            "group_name": app.group_name,
            "group_version": version,
            "group_dev_status": "",
            "governance_mode": app.governance_mode if app.governance_mode else GovernanceModeEnum.BUILD_IN_SERVICE_MESH.name,
            "k8s_resources": k8s_resources,
            "app_config_groups": share_service.config_groups(region.region_name, service_ids_keys_map),
            "ingress_http_routes": share_service._list_http_ingresses(tenant, service_ids_keys_map),
            "plugins": plugins,
            "apps": services,
        }
        app_arch = [svc.get("arch", "amd64") for svc in services if svc.get("arch")]
        app_arch = sorted(list(set(app_arch))) if app_arch else ["amd64"]
        app_template["arch"] = "&".join(app_arch)
        return app_template

    @classmethod
    def _strip_runtime_fields(cls, value):
        ignored = {"ID", "create_time", "update_time", "upgrade_time"}
        if isinstance(value, dict):
            data = {}
            for key, item in value.items():
                if key in ignored:
                    continue
                data[key] = cls._strip_runtime_fields(item)
            return data
        if isinstance(value, list):
            stripped = [cls._strip_runtime_fields(item) for item in value]
            return sorted(stripped, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
        return value

    def _normalize_template(self, app_template):
        normalized = copy.deepcopy(app_template)
        normalized.pop("group_version", None)
        normalized.pop("update_time", None)
        normalized.pop("snapshot_id", None)
        return self._strip_runtime_fields(normalized)

    def _content_hash(self, app_template):
        normalized = self._normalize_template(app_template)
        payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _component_map(self, app_template):
        apps = app_template.get("apps", [])
        result = {}
        for app in apps:
            identity = app.get("service_alias") or app.get("service_cname") or app.get("service_id")
            if not identity:
                continue
            result[identity] = self._strip_runtime_fields(copy.deepcopy(app))
        return result

    def _summarize_diff(self, current_template, target_template):
        current_map = self._component_map(current_template)
        target_map = self._component_map(target_template)
        added = [name for name in current_map.keys() if name not in target_map]
        removed = [name for name in target_map.keys() if name not in current_map]
        updated = [
            name for name in current_map.keys()
            if name in target_map and current_map[name] != target_map[name]
        ]
        return {
            "has_changes": bool(added or removed or updated),
            "added_count": len(added),
            "removed_count": len(removed),
            "updated_count": len(updated),
            "added_components": added,
            "removed_components": removed,
            "updated_components": updated,
        }

    def _serialize_version(self, version_obj, previous_version=None):
        app_template = json.loads(version_obj.app_template)
        diff_summary = None
        if previous_version:
            previous_template = json.loads(previous_version.app_template)
            diff_summary = self._summarize_diff(app_template, previous_template)
        return {
            "version_id": version_obj.ID,
            "version": version_obj.version,
            "version_alias": version_obj.version_alias,
            "app_version_info": version_obj.app_version_info,
            "create_time": version_obj.create_time.strftime('%Y-%m-%d %H:%M:%S') if version_obj.create_time else None,
            "update_time": version_obj.update_time.strftime('%Y-%m-%d %H:%M:%S') if version_obj.update_time else None,
            "group_id": version_obj.group_id,
            "app_model_id": version_obj.app_id,
            "template_type": version_obj.template_type,
            "arch": version_obj.arch,
            "diff_summary": diff_summary or {
                "has_changes": False,
                "added_count": 0,
                "removed_count": 0,
                "updated_count": 0,
                "added_components": [],
                "removed_components": [],
                "updated_components": [],
            },
        }

    def list_snapshot_versions(self, app_id):
        relation, _ = self.get_hidden_template(app_id)
        if not relation:
            return []
        versions = rainbond_app_repo.get_rainbond_app_versions(relation.app_model_id).filter(
            source=self.HIDDEN_TEMPLATE_SOURCE
        ).order_by("-create_time")
        versions = list(versions)
        result = []
        for index, version in enumerate(versions):
            previous_version = versions[index + 1] if index + 1 < len(versions) else None
            result.append(self._serialize_version(version, previous_version))
        return result

    def get_overview(self, tenant, region, user, app):
        relation, hidden_app = self.get_hidden_template(app.ID)
        latest_publish = share_repo.get_last_shared_app_version_by_group_id(app.ID, tenant.tenant_name)
        upgradeable_sources = []
        try:
            apps = market_app_service.get_market_apps_in_app(region, tenant, app)
            for source in apps:
                current_version = source.get("current_version")
                versions = source.get("upgrade_versions", []) or []
                latest_version = versions[0] if versions else None
                if source.get("can_upgrade") or (latest_version and str(latest_version) != str(current_version)):
                    upgradeable_sources.append({
                        "group_key": source.get("group_key"),
                        "upgrade_group_id": source.get("upgrade_group_id"),
                        "template_name": source.get("group_name") or source.get("app_model_name"),
                        "current_version": current_version,
                        "latest_version": latest_version,
                    })
        except Exception:
            upgradeable_sources = []

        if not relation or not hidden_app:
            return {
                "has_template": False,
                "template_id": None,
                "current_version": None,
                "latest_publish_time": latest_publish.create_time.strftime('%Y-%m-%d %H:%M:%S') if latest_publish else None,
                "snapshot_count": 0,
                "source_template_count": len(upgradeable_sources),
                "upgradeable_sources": upgradeable_sources,
                "has_changes": False,
                "change_summary": {
                    "has_changes": False,
                    "added_count": 0,
                    "removed_count": 0,
                    "updated_count": 0,
                    "added_components": [],
                    "removed_components": [],
                    "updated_components": [],
                },
            }

        versions = rainbond_app_repo.get_rainbond_app_versions(relation.app_model_id).filter(
            source=self.HIDDEN_TEMPLATE_SOURCE
        ).order_by("-create_time")
        latest_version = versions.first()
        if not latest_version:
            return {
                "has_template": True,
                "template_id": relation.app_model_id,
                "current_version": None,
                "latest_publish_time": latest_publish.create_time.strftime('%Y-%m-%d %H:%M:%S') if latest_publish else None,
                "snapshot_count": 0,
                "source_template_count": len(upgradeable_sources),
                "upgradeable_sources": upgradeable_sources,
                "has_changes": False,
                "change_summary": {
                    "has_changes": False,
                    "added_count": 0,
                    "removed_count": 0,
                    "updated_count": 0,
                    "added_components": [],
                    "removed_components": [],
                    "updated_components": [],
                },
            }

        current_template = self._build_app_template(tenant, region, user, app, relation.app_model_id, latest_version.version)
        snapshot_template = json.loads(latest_version.app_template)
        change_summary = self._summarize_diff(current_template, snapshot_template)
        return {
            "has_template": True,
            "template_id": relation.app_model_id,
            "current_version": latest_version.version,
            "latest_publish_time": latest_publish.create_time.strftime('%Y-%m-%d %H:%M:%S') if latest_publish else None,
            "snapshot_count": versions.count(),
            "source_template_count": len(upgradeable_sources),
            "upgradeable_sources": upgradeable_sources,
            "has_changes": change_summary["has_changes"],
            "change_summary": change_summary,
        }

    def create_snapshot(self, tenant, region, user, app, version="", version_alias="", app_version_info="", share_info=None):
        relation, hidden_app = self.get_or_create_hidden_template(tenant, user, app)
        latest_version = rainbond_app_repo.get_rainbond_app_versions(relation.app_model_id).filter(
            source=self.HIDDEN_TEMPLATE_SOURCE
        ).order_by("-create_time").first()
        next_version = version or self._next_version(latest_version.version if latest_version else None)
        if rainbond_app_repo.get_app_version(relation.app_model_id, next_version):
            raise ServiceHandleException(msg="snapshot version exists", msg_show="版本号已存在", status_code=400)
        share_info = share_info or {}
        if share_info.get("share_service_list") or share_info.get("share_plugin_list") or share_info.get("share_k8s_resources"):
            app_template = self._build_app_template_from_share_info(
                tenant, region, user, app, relation.app_model_id, next_version, share_info
            )
        else:
            app_template = self._build_app_template(tenant, region, user, app, relation.app_model_id, next_version)
        if latest_version:
            latest_template = json.loads(latest_version.app_template)
            change_summary = self._summarize_diff(app_template, latest_template)
            if not change_summary["has_changes"]:
                result = self._serialize_version(latest_version)
                result["created"] = False
                result["change_summary"] = change_summary
                return result
        snapshot = self._take_restore_snapshot(tenant, app, next_version)
        app_template["snapshot_id"] = snapshot.snapshot_id if snapshot else None
        version = RainbondCenterAppVersion.objects.create(
            enterprise_id=tenant.enterprise_id,
            app_id=relation.app_model_id,
            version=next_version,
            version_alias=version_alias or "",
            app_version_info=app_version_info or "",
            record_id=0,
            share_user=user.user_id,
            share_team=tenant.tenant_name,
            group_id=app.ID,
            dev_status="",
            source=self.HIDDEN_TEMPLATE_SOURCE,
            scope=self.HIDDEN_TEMPLATE_SCOPE,
            app_template=json.dumps(app_template),
            template_version="v2",
            upgrade_time=str(time.time()),
            install_number=0,
            is_official=False,
            is_ingerit=False,
            is_complete=True,
            template_type="application_version",
            release_user_id=None,
            region_name=region.region_name,
            is_plugin=False,
            arch=app_template["arch"],
        )
        hidden_app.is_version = True
        hidden_app.arch = app_template["arch"]
        hidden_app.update_time = version.update_time
        hidden_app.save()
        result = self._serialize_version(version)
        result["created"] = True
        return result

    def _take_restore_snapshot(self, tenant, app, version):
        services = group_service.get_group_services(app.ID)
        components = []
        for service in services:
            if service.create_status != "complete":
                continue
            service_snapshot, _ = groupapp_backup_service.get_service_details(tenant, service)
            service_snapshot["action_type"] = "nothing"
            components.append(service_snapshot)
        if not components:
            return None
        snapshot = app_snapshot_repo.create(
            AppUpgradeSnapshot(
                tenant_id=tenant.tenant_id,
                upgrade_group_id=0,
                snapshot_id=make_uuid(),
                snapshot=json.dumps({
                    "components": components,
                    "component_group": {
                        "group_version": version,
                    },
                }),
            )
        )
        return snapshot

    def get_snapshot_detail(self, app_id, version_id):
        relation, _ = self.get_hidden_template(app_id)
        if not relation:
            return None
        version = RainbondCenterAppVersion.objects.filter(
            ID=version_id, app_id=relation.app_model_id, source=self.HIDDEN_TEMPLATE_SOURCE
        ).first()
        if not version:
            return None
        app_template = json.loads(version.app_template)
        return {
            "version_id": version.ID,
            "version": version.version,
            "version_alias": version.version_alias,
            "app_version_info": version.app_version_info,
            "create_time": version.create_time.strftime('%Y-%m-%d %H:%M:%S') if version.create_time else None,
            "template": app_template,
            "content_hash": self._content_hash(app_template),
            "snapshot_id": app_template.get("snapshot_id"),
        }

    def delete_snapshot(self, app_id, version_id):
        relation, _ = self.get_hidden_template(app_id)
        if not relation:
            raise ServiceHandleException("snapshot not found", "快照不存在", status_code=404)

        versions = rainbond_app_repo.get_rainbond_app_versions(relation.app_model_id).filter(
            source=self.HIDDEN_TEMPLATE_SOURCE
        )
        target_version = versions.filter(ID=version_id).first()
        if not target_version:
            raise ServiceHandleException("snapshot not found", "快照不存在", status_code=404)

        latest_version = versions.order_by("-create_time").first()
        if latest_version and str(target_version.ID) == str(latest_version.ID):
            raise ServiceHandleException(
                "current snapshot can not delete", "当前版本不允许删除", status_code=400
            )

        target_version.delete()
        return True

    def rollback_snapshot(self, tenant, region, user, app, version_id):
        relation, _ = self.get_hidden_template(app.ID)
        if not relation:
            return None
        target_version = RainbondCenterAppVersion.objects.filter(
            ID=version_id, app_id=relation.app_model_id, source=self.HIDDEN_TEMPLATE_SOURCE
        ).first()
        if not target_version:
            return None
        target_template = json.loads(target_version.app_template)
        snapshot_id = target_template.get("snapshot_id")
        if not snapshot_id:
            return None

        latest_version = rainbond_app_repo.get_rainbond_app_versions(relation.app_model_id).filter(
            source=self.HIDDEN_TEMPLATE_SOURCE
        ).order_by("-create_time").first()
        current_version = latest_version.version if latest_version else ""

        record = AppUpgradeRecord(
            tenant_id=tenant.tenant_id,
            group_id=app.ID,
            group_key=relation.app_model_id,
            group_name=app.group_name,
            version=target_version.version,
            old_version=current_version,
            status=UpgradeStatus.UPGRADED.value,
            market_name="",
            is_from_cloud=False,
            upgrade_group_id=0,
            snapshot_id=snapshot_id,
            record_type=AppUpgradeRecordType.UPGRADE.value,
            parent_id=0,
        )
        pseudo_component_group = TenantServiceGroup(
            tenant_id=tenant.tenant_id,
            group_name=app.group_name,
            group_alias=app.group_name,
            group_key=relation.app_model_id,
            group_version=target_version.version,
            region_name=region.region_name,
            service_group_id=app.ID,
        )
        app_restore = AppVersionRollbackRestore(
            tenant, region, user, app, pseudo_component_group, record, current_version, target_version.version
        )
        rollback_record, _ = app_restore.restore()
        return rollback_record.to_dict()


app_version_service = AppVersionService()

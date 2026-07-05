# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import logging
import time
from typing import Any, List, Optional, Tuple

from console.models.main import (AppExportRecord, AppImportRecord, RainbondCenterApp, RainbondCenterAppTagsRelation,
                                 RainbondCenterAppVersion, AppHelmOverrides)
from django.db.models import Q, QuerySet

logger = logging.getLogger("default")


class RainbondCenterAppRepository(object):
    HIDDEN_APP_VERSION_SOURCE = "app_version"

    def base_filter_rainbond_app_by_app_id(self, app_id: str) -> QuerySet:
        return RainbondCenterApp.objects.filter(app_id=app_id)

    def get_rainbond_app_by_app_id(self, app_id: str) -> Optional[RainbondCenterApp]:
        return self.base_filter_rainbond_app_by_app_id(app_id).first()

    def get_rainbond_app_by_app_id_team(self, app_ids: List[str]) -> QuerySet:
        return RainbondCenterApp.objects.filter(app_id__in=app_ids, scope="team").exclude(
            source=self.HIDDEN_APP_VERSION_SOURCE
        )

    def get_enterprise_team_apps(self, enterprise_id: str, team_name: str, scope: Optional[str] = None,
                                 visible_team_names: Optional[List[str]] = None) -> QuerySet:
        apps = RainbondCenterApp.objects.filter(source="local").exclude(source=self.HIDDEN_APP_VERSION_SOURCE)
        if scope == "enterprise":
            if visible_team_names:
                apps = apps.filter(scope=scope, create_team__in=visible_team_names)
            else:
                apps = apps.filter(scope=scope)
        else:
            apps = apps.filter(create_team=team_name)
            if scope:
                apps = apps.filter(scope=scope)
        return apps.order_by("-create_time")

    def delete_helm_shared_apps(self, source: str) -> Tuple[int, dict]:
        return RainbondCenterApp.objects.filter(source=source).delete()

    def delete_app_by_id(self, app_id: str) -> None:
        self.base_filter_rainbond_app_by_app_id(app_id=app_id).delete()

    def bulk_create_rainbond_apps(self, rainbond_apps: List[RainbondCenterApp]) -> None:
        RainbondCenterApp.objects.bulk_create(rainbond_apps)

    def get_rainbond_app_versions(self, app_id: str) -> QuerySet:
        return RainbondCenterAppVersion.objects.filter(app_id=app_id)

    def filter_rainbond_app_version_by_app_id_and_version(self, app_id: str,
                                                          version: str) -> QuerySet:
        return self.get_rainbond_app_versions(app_id=app_id).filter(version=version)

    def delete_app_version_by_id(self, app_id: str, version: str = "") -> Tuple[int, dict]:
        ver = self.get_rainbond_app_versions(app_id)
        if version:
            ver = self.filter_rainbond_app_version_by_app_id_and_version(app_id, version)
        return ver.delete()

    def bulk_create_rainbond_app_versions(self, rainbond_app_versions: List[RainbondCenterAppVersion]) -> None:
        RainbondCenterAppVersion.objects.bulk_create(rainbond_app_versions)

    def get_app_versions_by_app_id(self, app_id: str, is_complete: bool) -> QuerySet:
        return self.get_rainbond_app_versions(app_id=app_id).filter(is_complete=is_complete)

    def add_basic_app_info(self, **kwargs: Any) -> RainbondCenterApp:
        app = RainbondCenterApp(**kwargs)
        app.save()
        return app


    def get_rainbond_app_version_by_app_id_and_version(self, app_id: str,
                                                       version: str) -> Optional[RainbondCenterAppVersion]:
        return self.get_rainbond_app_versions(app_id).filter(version=version).first()

    def get_app_version(self, app_id: str, version: str) -> Optional[RainbondCenterAppVersion]:
        return self.filter_rainbond_app_version_by_app_id_and_version(app_id, version).order_by("-create_time").first()

    def get_rainbond_app_version_by_app_ids(self, app_ids: List[str],
                                            is_complete: Optional[bool] = None) -> QuerySet:
        q = Q(app_id__in=app_ids)
        if is_complete:
            q = q & Q(is_complete=is_complete)
        return RainbondCenterAppVersion.objects.filter(q)

    def get_rainbond_app_version_by_record_id(self, record_id: str) -> Optional[RainbondCenterAppVersion]:
        return RainbondCenterAppVersion.objects.filter(record_id=record_id).last()

    def get_rainbond_app_version_by_id(self, eid: str, group_id: str) -> QuerySet:
        return RainbondCenterAppVersion.objects.filter(group_id=group_id, scope="team")


    def get_rainbond_ceneter_app_by(self,
                                    scope: str,
                                    app_name: str,
                                    teams: Optional[List[str]] = None,
                                    page: int = 1,
                                    page_size: int = 10,
                                    need_install: str = "",
                                    arch: str = "",
                                    is_plugin: Optional[str] = None
                                    ) -> Tuple[QuerySet, int]:
        if scope:
            app = RainbondCenterApp.objects.filter(scope=scope)
            if scope == "team" and teams:
                app = app.filter(create_team__in=teams)
        else:
            app = RainbondCenterApp.objects.filter(Q(scope="enterprise") | Q(scope="team", create_team__in=teams))
        app = app.exclude(source=self.HIDDEN_APP_VERSION_SOURCE)
        if need_install:
            app = app.filter(is_version=True)
        if arch:
            app = app.filter(arch=arch)
        if app_name:
            app = app.filter(app_name__icontains=app_name)
        if is_plugin is not None:
            # Filter by is_plugin field in RainbondCenterAppVersion
            is_plugin_bool = is_plugin.lower() in ['true', '1', 'yes']
            # Get app_ids that have at least one version with matching is_plugin value
            app_ids_with_plugin = RainbondCenterAppVersion.objects.filter(
                is_plugin=is_plugin_bool
            ).values_list('app_id', flat=True).distinct()
            app = app.filter(app_id__in=app_ids_with_plugin)
        start_row = (page - 1) * page_size
        end_row = page * page_size
        apps = app.order_by('-update_time')[start_row:end_row]
        return apps, app.count()

    def get_rainbond_app_and_version(self, enterprise_id: str, app_id: str, app_version: str) -> Tuple[Any, Any]:
        app = self.get_rainbond_app_by_app_id(app_id)
        if not app_version:
            return app, None
        app_version = self.filter_rainbond_app_version_by_app_id_and_version(app_id, app_version
                                                                             ).order_by("-update_time").first()
        return app, app_version

    def get_app_helm_overrides(self, app_id: str, app_model_id: str) -> QuerySet:
        return AppHelmOverrides.objects.filter(app_id=app_id, app_model_id=app_model_id)

    def get_rainbond_app_by_key_version(self, group_key: str, version: str) -> Optional[RainbondCenterAppVersion]:
        """使用group_key 和 version 获取一个云市应用"""
        # pre-existing: called with 2 args though signature declares 3 (enterprise_id)
        app, app_version = self.get_rainbond_app_and_version(group_key, version)  # type: ignore[call-arg]
        if app and app_version:
            app_version.app_name = app.app_name
        return app_version

    def get_enterpirse_app_by_key_and_version(self, enterprise_id: str, group_key: str,
                                              group_version: str) -> Optional[RainbondCenterAppVersion]:
        app = self.get_rainbond_app_by_app_id(group_key)
        rcapps = self.filter_rainbond_app_version_by_app_id_and_version(group_key, group_version).order_by("-update_time")
        if rcapps and app:
            rcapp = rcapps.filter(enterprise_id=enterprise_id)
            # 优先获取企业下的应用
            if rcapp:
                # dynamic attrs attached for serialization; not declared on the model
                rcapp[0].pic = app.pic  # type: ignore[attr-defined]
                rcapp[0].group_name = app.app_name  # type: ignore[attr-defined]
                rcapp[0].describe = app.describe  # type: ignore[attr-defined]

                return rcapp[0]
            else:
                rcapps[0].pic = app.pic  # type: ignore[attr-defined]
                rcapps[0].describe = app.describe  # type: ignore[attr-defined]
                rcapps[0].group_name = app.app_name  # type: ignore[attr-defined]
            return rcapps[0]
        logger.warning("Enterprise ID: {0}; Group Key: {1}; Version: {2}".format(enterprise_id, group_key, group_version))
        return None

    def get_app_tag_by_id(self, enterprise_id: str, app_id: str) -> QuerySet:
        return RainbondCenterAppTagsRelation.objects.filter(enterprise_id=enterprise_id, app_id=app_id)

    def delete_app_tag_by_id(self, enterprise_id: str, app_id: str) -> None:
        RainbondCenterAppTagsRelation.objects.filter(enterprise_id=enterprise_id, app_id=app_id).delete()

    def update_app_version(self, app_id: str, version: str, **data: Any) -> Optional[RainbondCenterAppVersion]:
        version = self.filter_rainbond_app_version_by_app_id_and_version(app_id, version).last()
        if version is not None:
            if data["version_alias"] is not None:
                version.version_alias = data["version_alias"]
            if data["app_version_info"] is not None:
                version.app_version_info = data["app_version_info"]
            if data["dev_status"] == "release":
                version.release_user_id = data["release_user_id"]
            version.dev_status = data["dev_status"]
            version.update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            version.save()
            return version
        return None



class AppExportRepository(object):
    def get_export_record_by_unique_key(self, group_key: str, version: str,
                                        export_format: str) -> Optional[AppExportRecord]:
        return AppExportRecord.objects.filter(group_key=group_key, version=version, format=export_format).first()

    def get_export_record(self, eid: str, app_id: str, app_version: str,
                          export_format: str) -> Optional[AppExportRecord]:
        records = AppExportRecord.objects.filter(
            group_key=app_id, version=app_version, format=export_format, enterprise_id__in=[eid, "public"], status="exporting")
        if not records:
            return None
        return records[0]

    def get_enter_export_record_by_unique_key(self, enterprise_id: str, group_key: str, version: str,
                                              export_format: str) -> Optional[AppExportRecord]:
        app_records = AppExportRecord.objects.filter(
            group_key=group_key, version=version, format=export_format, enterprise_id__in=[enterprise_id, "public"])
        if app_records:
            current_enter_records = app_records.filter(enterprise_id=enterprise_id)
            if current_enter_records:
                return current_enter_records[0]
            return app_records[0]
        return None

    def create_app_export_record(self, **params: Any) -> AppExportRecord:
        return AppExportRecord.objects.create(**params)

    def delete_by_key_and_version(self, group_key: str, version: str) -> None:
        AppExportRecord.objects.filter(group_key=group_key, version=version).delete()

    def get_by_key_and_version(self, group_key: str, version: str) -> QuerySet:
        return AppExportRecord.objects.filter(group_key=group_key, version=version)

    def get_enter_export_record_by_key_and_version(self, enterprise_id: str, group_key: str,
                                                   version: str) -> QuerySet:
        return AppExportRecord.objects.filter(group_key=group_key, version=version, enterprise_id__in=["public", enterprise_id])


class AppImportRepository(object):
    def get_import_record(self, id: str) -> Optional[AppImportRecord]:
        records = AppImportRecord.objects.filter(ID=id)
        if not records:
            return None
        return records[0]

    def get_import_record_by_event_id(self, event_id: str) -> Optional[AppImportRecord]:
        return AppImportRecord.objects.filter(event_id=event_id).first()

    def delete_by_event_id(self, event_id: str) -> None:
        AppImportRecord.objects.filter(event_id=event_id).delete()

    def create_app_import_record(self, **params: Any) -> AppImportRecord:
        return AppImportRecord.objects.create(**params)

    def get_importing_record(self, user_name: str, team_name: str) -> QuerySet:
        return AppImportRecord.objects.filter(user_name=user_name, team_name=team_name, status="importing")

    def get_user_unfinished_import_record(self, team_name: str, user_name: str) -> QuerySet:
        return AppImportRecord.objects.filter(
            user_name=user_name, team_name=team_name).exclude(status__in=["success", "failed"])

    def get_user_not_finished_import_record_in_enterprise(self, eid: str,
                                                          user_name: str) -> QuerySet:
        return AppImportRecord.objects.filter(user_name=user_name, enterprise_id=eid).exclude(status__in=["success", "failed"])


rainbond_app_repo = RainbondCenterAppRepository()
app_export_record_repo = AppExportRepository()
app_import_record_repo = AppImportRepository()

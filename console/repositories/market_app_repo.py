# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import logging

from console.models.main import AppExportRecord
from console.models.main import AppImportRecord
from console.models.main import RainbondCenterApp
from console.utils.shortcuts import get_object_or_404

logger = logging.getLogger("default")


class RainbondCenterAppRepository(object):
    def get_rainbond_app_by_id(self, id):
        rain_bond_apps = RainbondCenterApp.objects.filter(ID=id)
        if rain_bond_apps:
            return rain_bond_apps[0]
        return None

    def get_all_rainbond_apps(self):
        return RainbondCenterApp.objects.all()

    def get_complete_rainbond_apps(self):
        return RainbondCenterApp.objects.filter(is_complete=True)

    def get_current_enter_visable_apps(self, enterprise_id):
        return RainbondCenterApp.objects.filter(is_complete=True, enterprise_id__in=["public", enterprise_id])

    def get_rainbond_app_by_key_and_version(self, group_key, group_version):
        rcapps = RainbondCenterApp.objects.filter(group_key=group_key, version=group_version)
        if rcapps:
            return rcapps[0]
        return None

    def get_rainbond_app_by_key(self, group_key):
        rcapps = RainbondCenterApp.objects.filter(group_key=group_key).all()
        if rcapps:
            return rcapps
        return None

    def list_by_key_time(self, group_key, time):
        rcapps = RainbondCenterApp.objects.filter(group_key=group_key, update_time__gte=time, is_complete=True).all()
        if rcapps:
            return rcapps
        return None

    def get_rainbond_app_qs_by_key(self, eid, group_key):
        """使用group_key获取一个云市应用的所有版本查询集合"""
        return RainbondCenterApp.objects.filter(enterprise_id=eid, group_key=group_key)

    def get_rainbond_app_by_key_version(self, group_key, version):
        """使用group_key 和 version 获取一个云市应用"""
        return get_object_or_404(RainbondCenterApp, msg='rainbond center app not found', group_key=group_key, version=version)

    def get_enterpirse_app_by_key_and_version(self, enterprise_id, group_key, group_version):
        rcapps = RainbondCenterApp.objects.filter(
            group_key=group_key, version=group_version, enterprise_id__in=["public", enterprise_id])
        if rcapps:
            rcapp = rcapps.filter(enterprise_id=enterprise_id)
            # 优先获取企业下的应用
            if rcapp:
                return rcapp[0]
            else:
                return rcapps[0]
        logger.warning("Enterprise ID: {0}; Group Key: {1}; Version: {2}".format(enterprise_id, group_key, group_version))
        return None

    def bulk_create_rainbond_apps(self, rainbond_apps):
        RainbondCenterApp.objects.bulk_create(rainbond_apps)

    def get_rainbond_app_by_record_id(self, record_id):
        rcapps = RainbondCenterApp.objects.filter(record_id=record_id)
        if rcapps:
            return rcapps[0]
        return None


class AppExportRepository(object):
    def get_export_record_by_unique_key(self, group_key, version, export_format):
        return AppExportRecord.objects.filter(group_key=group_key, version=version, format=export_format).first()

    def get_enter_export_record_by_unique_key(self, enterprise_id, group_key, version, export_format):
        app_records = AppExportRecord.objects.filter(
            group_key=group_key, version=version, format=export_format, enterprise_id__in=[enterprise_id, "public"])
        if app_records:
            current_enter_records = app_records.filter(enterprise_id=enterprise_id)
            if current_enter_records:
                return current_enter_records[0]
            return app_records[0]
        return None

    def create_app_export_record(self, **params):
        return AppExportRecord.objects.create(**params)

    def delete_by_key_and_version(self, group_key, version):
        AppExportRecord.objects.filter(group_key=group_key, version=version).delete()

    def get_by_key_and_version(self, group_key, version):
        return AppExportRecord.objects.filter(group_key=group_key, version=version)

    def get_enter_export_record_by_key_and_version(self, enterprise_id, group_key, version):
        return AppExportRecord.objects.filter(group_key=group_key, version=version, enterprise_id__in=["public", enterprise_id])


class AppImportRepository(object):
    def get_import_record_by_event_id(self, event_id):
        return AppImportRecord.objects.filter(event_id=event_id).first()

    def delete_by_event_id(self, event_id):
        AppImportRecord.objects.filter(event_id=event_id).delete()

    def create_app_import_record(self, **params):
        return AppImportRecord.objects.create(**params)

    def get_importing_record(self, user_name, team_name):
        return AppImportRecord.objects.filter(user_name=user_name, team_name=team_name, status="importing")

    def get_user_unfinished_import_record(self, team_name, user_name):
        return AppImportRecord.objects.filter(
            user_name=user_name, team_name=team_name).exclude(status__in=["success", "failed"])


rainbond_app_repo = RainbondCenterAppRepository()
app_export_record_repo = AppExportRepository()
app_import_record_repo = AppImportRepository()

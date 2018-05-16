# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
from console.models.main import RainbondCenterApp,AppExportRecord


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

    def get_rainbond_app_by_key_and_version(self, group_key, group_version):
        rcapps = RainbondCenterApp.objects.filter(group_key=group_key, version=group_version)
        if rcapps:
            return rcapps[0]
        return None

    def bulk_create_rainbond_apps(self, rainbond_apps):
        RainbondCenterApp.objects.bulk_create(rainbond_apps)

    def get_rainbond_app_by_record_id(self,record_id):
        rcapps = RainbondCenterApp.objects.filter(record_id=record_id)
        if rcapps:
            return rcapps[0]
        return None


class AppExportRepository(object):
    def get_export_record_by_unique_key(self, group_key, version, export_format):
        return AppExportRecord.objects.filter(group_key=group_key, version=version, format=export_format).first()

    def create_app_export_record(self, **params):
        return AppExportRecord.objects.create(**params)

    def delete_by_key_and_version(self, group_key, version):
        AppExportRecord.objects.filter(group_key=group_key, version=version).delete()

    def get_by_key_and_version(self, group_key, version):
        return AppExportRecord.objects.filter(group_key=group_key, version=version)

rainbond_app_repo = RainbondCenterAppRepository()
app_export_record_repo = AppExportRepository()
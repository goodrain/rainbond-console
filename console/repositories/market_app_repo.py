# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import logging
import time

from console.models.main import (AppExportRecord, AppImportRecord, RainbondCenterApp, RainbondCenterAppTagsRelation,
                                 RainbondCenterAppVersion, AppHelmOverrides)
from django.db.models import Q
from www.db.base import BaseConnection

logger = logging.getLogger("default")


class RainbondCenterAppRepository(object):
    def base_filter_rainbond_app_by_app_id(self, app_id):
        return RainbondCenterApp.objects.filter(app_id=app_id)

    def get_rainbond_app_by_app_id(self, app_id):
        return self.base_filter_rainbond_app_by_app_id(app_id).first()

    def get_rainbond_app_by_app_id_team(self, app_ids):
        return RainbondCenterApp.objects.filter(app_id__in=app_ids)

    def get_enterprise_team_apps(self, enterprise_id, team_name):
        return RainbondCenterApp.objects.filter(create_team=team_name, source="local").order_by("-create_time")

    def delete_helm_shared_apps(self, source):
        return RainbondCenterApp.objects.filter(source=source).delete()

    def delete_app_by_id(self, app_id):
        self.base_filter_rainbond_app_by_app_id(app_id=app_id).delete()

    def bulk_create_rainbond_apps(self, rainbond_apps):
        RainbondCenterApp.objects.bulk_create(rainbond_apps)

    def get_rainbond_app_versions(self, eid, app_id):
        return RainbondCenterAppVersion.objects.filter(app_id=app_id)

    def filter_rainbond_app_version_by_app_id_and_version(self, app_id, version):
        return self.get_rainbond_app_versions(app_id=app_id).filter(version=version)

    def delete_app_version_by_id(self, app_id, version=""):
        ver = self.get_rainbond_app_versions(app_id)
        if version:
            ver = self.filter_rainbond_app_version_by_app_id_and_version(app_id, version)
        return ver.delete()

    def bulk_create_rainbond_app_versions(self, rainbond_app_versions):
        RainbondCenterAppVersion.objects.bulk_create(rainbond_app_versions)

    def get_app_versions_by_app_id(self, app_id, is_complete):
        return self.get_rainbond_app_versions(app_id=app_id).filter(is_complete=is_complete)

    def add_basic_app_info(self, **kwargs):
        app = RainbondCenterApp(**kwargs)
        app.save()
        return app


    def get_rainbond_app_version_by_app_id_and_version(self, app_id, version):
        return self.get_rainbond_app_versions(app_id).filter(version=version).first()

    def get_app_version(self, app_id, version):
        return self.filter_rainbond_app_version_by_app_id_and_version(app_id, version).order_by("-create_time").first()

    def get_rainbond_app_version_by_app_ids(self, app_ids, is_complete=None):
        q = Q(app_id__in=app_ids)
        if is_complete:
            q = q & Q(is_complete=is_complete)
        return RainbondCenterAppVersion.objects.filter(q)

    def get_rainbond_app_version_by_record_id(self, record_id):
        return RainbondCenterAppVersion.objects.filter(record_id=record_id).first()

    def get_rainbond_app_version_by_id(self, eid, group_id):
        return RainbondCenterAppVersion.objects.filter(group_id=group_id, scope="team")


    def get_rainbond_app_in_enterprise_by_query(self,
                                                eid,
                                                scope,
                                                app_name,
                                                tag_names=None,
                                                page=1,
                                                page_size=10,
                                                need_install="false",
                                                is_plugin="false",
                                                arch=""):
        sql = self._prepare_get_rainbond_app_by_query_sql(eid, scope, app_name, None, tag_names, page, page_size, need_install,
                                                          is_plugin, arch)
        conn = BaseConnection()
        apps = conn.query(sql)
        return apps

    def _prepare_get_rainbond_app_by_query_sql(self,
                                               eid,
                                               scope,
                                               app_name,
                                               teams=None,
                                               tag_names=None,
                                               page=1,
                                               page_size=10,
                                               need_install="false",
                                               is_plugin="false",
                                               arch=""):
        extend_where = ""
        join_version = ""
        if tag_names:
            extend_where += " and tag.name in ({0})".format(",".join("'{0}'".format(tag_name) for tag_name in tag_names))
        if app_name:
            extend_where += " and app.app_name like '%{0}%'".format(app_name)
        if arch:
            extend_where += " and app.arch like '%{0}%'".format(arch)
        # When installing components from the component library, you need to display the versioned application template
        if need_install == "true":
            join_version += " left join rainbond_center_app_version apv on app.app_id = apv.app_id" \
                            " and app.enterprise_id = apv.enterprise_id"
            extend_where += " and apv.`version` <> '' and apv.is_complete"
        if is_plugin == "true":
            extend_where += " and apv.is_plugin = 1"
        # if teams is None, create_team scope is ('')
        if scope == "team":
            team_sql = ""
            if teams:
                team_sql = " and app.create_team in({0})".format(",".join("'{0}'".format(team) for team in teams))
            team_sql += " and app.scope='" + scope + "'"
            extend_where += team_sql
        if scope == "enterprise":
            extend_where += " and app.scope='" + scope + "'"
        sql = """
            select
                distinct app.*
            from
                rainbond_center_app app
            left join rainbond_center_app_tag_relation apr on
                app.app_id = apr.app_id
                and app.enterprise_id = apr.enterprise_id
            left join rainbond_center_app_tag tag on
                apr.tag_id = tag.ID
                and tag.enterprise_id = app.enterprise_id
            {join_version}
            where
                app.enterprise_id = '{eid}'
                {extend_where}
            order by app.update_time desc
            limit {offset}, {rows}
            """.format(
            eid=eid, extend_where=extend_where, offset=(page - 1) * page_size, rows=page_size, join_version=join_version)
        return sql

    def get_rainbond_app_in_teams_by_querey(self,
                                            eid,
                                            scope,
                                            teams,
                                            app_name,
                                            tag_names=None,
                                            page=1,
                                            page_size=10,
                                            need_install="false",
                                            is_plugin="false",
                                            arch=""):
        sql = self._prepare_get_rainbond_app_by_query_sql(eid, scope, app_name, teams, tag_names, page, page_size, need_install,
                                                          is_plugin, arch)
        conn = BaseConnection()
        apps = conn.query(sql)
        return apps

    def get_rainbond_app_total_count(self, eid, scope, teams, app_name, tag_names, need_install="false", is_plugin="false"):
        extend_where = ""
        join_version = ""
        if tag_names:
            extend_where += " and tag.name in ({0})".format(",".join("'{0}'".format(tag_name) for tag_name in tag_names))
        if app_name:
            extend_where += " and app.app_name like '%{0}%'".format(app_name)
        if need_install == "true":
            join_version += " left join rainbond_center_app_version apv on app.app_id = apv.app_id" \
                            " and app.enterprise_id = apv.enterprise_id"
            extend_where += " and apv.`version` <> '' and apv.is_complete"
        if is_plugin == "true":
            extend_where += " and apv.is_plugin = 1"
        # if teams is None, create_team scope is ('')
        if scope == "team":
            team_sql = ""
            if teams:
                team_sql = " and app.create_team in({0})".format(",".join("'{0}'".format(team) for team in teams))
            team_sql += " and app.scope='" + scope + "'"
            extend_where += team_sql
        if scope == "enterprise":
            extend_where += " and app.scope='" + scope + "'"
        sql = """
            select
                count(distinct app.app_id) as total
            from
                rainbond_center_app app
            left join (
                select
                    app_id,
                    tag.name
                from
                    rainbond_center_app_tag_relation rcatr
                join rainbond_center_app_tag tag on
                    rcatr.tag_id = tag.iD) tag on app.app_id = tag.app_id
            {join_version}
            where
                app.enterprise_id = '{eid}'
                {extend_where}
            """.format(
            eid=eid, extend_where=extend_where, join_version=join_version)
        conn = BaseConnection()
        count = conn.query(sql)
        return count

    def get_rainbond_app_and_version(self, enterprise_id, app_id, app_version):
        app = self.get_rainbond_app_by_app_id(app_id)
        if not app_version:
            return app, None
        app_version = self.filter_rainbond_app_version_by_app_id_and_version(app_id, app_version
                                                                             ).order_by("-upgrade_time").first()
        return app, app_version

    def get_app_helm_overrides(self, app_id, app_model_id):
        return AppHelmOverrides.objects.filter(app_id=app_id, app_model_id=app_model_id)

    def get_rainbond_app_by_key_version(self, group_key, version):
        """使用group_key 和 version 获取一个云市应用"""
        app, app_version = self.get_rainbond_app_and_version(group_key, version)
        if app and app_version:
            app_version.app_name = app.app_name
        return app_version

    def get_enterpirse_app_by_key_and_version(self, enterprise_id, group_key, group_version):
        app = self.get_rainbond_app_by_app_id(group_key)
        rcapps = self.filter_rainbond_app_version_by_app_id_and_version(group_key, group_version).order_by("-update_time")
        if rcapps and app:
            rcapp = rcapps.filter(enterprise_id=enterprise_id)
            # 优先获取企业下的应用
            if rcapp:
                rcapp[0].pic = app.pic
                rcapp[0].group_name = app.app_name
                rcapp[0].describe = app.describe

                return rcapp[0]
            else:
                rcapps[0].pic = app.pic
                rcapps[0].describe = app.describe
                rcapps[0].group_name = app.app_name
            return rcapps[0]
        logger.warning("Enterprise ID: {0}; Group Key: {1}; Version: {2}".format(enterprise_id, group_key, group_version))
        return None

    def get_app_tag_by_id(self, enterprise_id, app_id):
        return RainbondCenterAppTagsRelation.objects.filter(enterprise_id=enterprise_id, app_id=app_id)

    def delete_app_tag_by_id(self, enterprise_id, app_id):
        RainbondCenterAppTagsRelation.objects.filter(enterprise_id=enterprise_id, app_id=app_id).delete()

    def update_app_version(self, app_id, version, **data):
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
    def get_export_record_by_unique_key(self, group_key, version, export_format):
        return AppExportRecord.objects.filter(group_key=group_key, version=version, format=export_format).first()

    def get_export_record(self, eid, app_id, app_version, export_format):
        records = AppExportRecord.objects.filter(
            group_key=app_id, version=app_version, format=export_format, enterprise_id__in=[eid, "public"], status="exporting")
        if not records:
            return None
        return records[0]

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
    def get_import_record(self, id):
        records = AppImportRecord.objects.filter(ID=id)
        if not records:
            return None
        return records[0]

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

    def get_user_not_finished_import_record_in_enterprise(self, eid, user_name):
        return AppImportRecord.objects.filter(user_name=user_name, enterprise_id=eid).exclude(status__in=["success", "failed"])


rainbond_app_repo = RainbondCenterAppRepository()
app_export_record_repo = AppExportRepository()
app_import_record_repo = AppImportRepository()

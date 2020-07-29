# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import logging

from django.db.models import Q

from console.models.main import AppExportRecord
from console.models.main import AppImportRecord
from console.models.main import RainbondCenterApp
from console.models.main import RainbondCenterAppTagsRelation
from console.models.main import RainbondCenterAppVersion
from www.db.base import BaseConnection

logger = logging.getLogger("default")


class RainbondCenterAppRepository(object):
    # def get_rainbond_app_by_id(self, id):
    #     rain_bond_apps = RainbondCenterApp.objects.filter(ID=id)
    #     if rain_bond_apps:
    #         return rain_bond_apps[0]
    #     return None

    def get_all_rainbond_apps(self):
        return RainbondCenterApp.objects.all()

    def get_rainbond_app_by_id(self, id):
        return RainbondCenterApp.objects.filter(ID=id)

    def get_rainbond_app_by_key_and_version_eid(self, eid, app_id, dev_status):
        rcapps = RainbondCenterApp.objects.filter(enterprise_id=eid, app_id=app_id, dev_status=dev_status)
        if rcapps:
            return rcapps[0]
        rcapps = RainbondCenterApp.objects.filter(enterprise_id=eid, app_id=app_id, dev_status=dev_status)
        if rcapps:
            return rcapps[0]
        return None

    def get_rainbond_app_in_enterprise_by_query(self, eid, scope, app_name, tag_names=None, page=1, page_size=10):
        sql = self._prepare_get_rainbond_app_by_query_sql(eid, scope, app_name, None, tag_names, page, page_size)
        conn = BaseConnection()
        apps = conn.query(sql)
        return apps

    def _prepare_get_rainbond_app_by_query_sql(self, eid, scope, app_name, teams=None, tag_names=None, page=1, page_size=10):
        extend_where = ""
        if tag_names:
            extend_where += " and tag.name in ({0})".format(",".join("'{0}'".format(tag_name) for tag_name in tag_names))
        if app_name:
            extend_where += " and app.app_name like '%{0}%'".format(app_name)
        # if teams is None, create_team scope is ('')
        if scope == "team":
            team_sql = " and app.create_team in ('')"
            if teams:
                team_sql = " and app.create_team in({0})".format(",".join("'{0}'".format(team) for team in teams))
            team_sql += " and scope='" + scope + "'"
            extend_where += team_sql
        if scope == "enterprise":
            extend_where += " and scope='" + scope + "'"
        sql = """
            select
                distinct app.*
            from
                console.rainbond_center_app app
            left join console.rainbond_center_app_tag_relation apr on
                app.app_id = apr.app_id
                and app.enterprise_id = apr.enterprise_id
            left join console.rainbond_center_app_tag tag on
                apr.tag_id = tag.ID
                and tag.enterprise_id = app.enterprise_id
            where
                app.enterprise_id = '{eid}'
                {extend_where}
            limit {offset}, {rows}
            """.format(
            eid=eid, extend_where=extend_where, offset=(page - 1) * page_size, rows=page_size)
        return sql

    def get_rainbond_app_in_teams_by_querey(self, eid, teams, app_name, tag_names=None, page=1, page_size=10):
        sql = self._prepare_get_rainbond_app_by_query_sql(eid, "team", app_name, teams, tag_names, page, page_size)
        conn = BaseConnection()
        apps = conn.query(sql)
        return apps

    def get_rainbond_app_total_count(self, eid, scope, teams, app_name, tag_names):
        extend_where = ""
        if tag_names:
            extend_where += " and tag.name in ({0})".format(",".join("'{0}'".format(tag_name) for tag_name in tag_names))
        if app_name:
            extend_where += " and app.app_name like '%{0}%'".format(app_name)
        # if teams is None, create_team scope is ('')
        if scope == "team":
            team_sql = " and app.create_team in ('')"
            if teams:
                team_sql = " and app.create_team in({0})".format(",".join("'{0}'".format(team) for team in teams))
            team_sql += " and scope='" + scope + "'"
            extend_where += team_sql
        if scope == "enterprise":
            extend_where += " and scope='" + scope + "'"
        sql = """
            select
                count(distinct app.app_id) as total
            from
                console.rainbond_center_app app
            left join (
                select
                    app_id,
                    tag.name
                from
                    console.rainbond_center_app_tag_relation rcatr
                join console.rainbond_center_app_tag tag on
                    rcatr.tag_id = tag.iD) tag on app.app_id = tag.app_id
            where
                app.enterprise_id = '{eid}'
                {extend_where}
            """.format(
            eid=eid, extend_where=extend_where)
        conn = BaseConnection()
        count = conn.query(sql)
        return count

    def get_rainbond_app_version_by_app_ids(self, eid, app_ids, is_complete=None):
        q = Q(enterprise_id=eid, app_id__in=app_ids)
        if is_complete:
            q = q & Q(is_complete=is_complete)
        return RainbondCenterAppVersion.objects.filter(q)

    def get_rainbond_app_by_app_id(self, eid, app_id):
        return RainbondCenterApp.objects.filter(app_id=app_id, enterprise_id=eid).first()

    def get_rainbond_app_by_eid(self, eid):
        return RainbondCenterApp.objects.filter(enterprise_id=eid)

    def get_rainbond_app_version_by_record_id(self, record_id):
        return RainbondCenterAppVersion.objects.filter(record_id=record_id).first()

    def get_rainbond_app_version_by_id(self, eid, app_id):
        return RainbondCenterAppVersion.objects.filter(enterprise_id=eid, app_id=app_id)

    def get_rainbond_apps_versions_by_eid(self,
                                          eid,
                                          name=None,
                                          tags=None,
                                          scope=None,
                                          team_names=None,
                                          is_complete=None,
                                          page=1,
                                          page_size=10):
        page = (page - 1) * page_size
        limit = "LIMIT {page}, {page_size}".format(page=page, page_size=page_size)
        where = 'WHERE BB.enterprise_id="{eid}" '.format(eid=eid)
        group = """GROUP BY BB.enterprise_id, BB.app_id {}) CC
        LEFT JOIN rainbond_center_app_tag_relation D
        ON D.app_id=CC.app_id AND D.enterprise_id=CC.enterprise_id
        LEFT JOIN rainbond_center_app_tag E
        ON D.tag_id=E.ID """.format(limit)
        if name:
            where += 'AND BB.app_name LIKE"{}%" '.format(name)
        if scope:
            where += 'AND BB.scope="{}" '.format(scope)
        if team_names:
            team_names_count = len(team_names)
            if team_names_count == 1:
                where += 'AND (BB.create_team="{}" OR BB.create_team is NULL) '.format(team_names[0])
            else:
                where += 'AND (BB.create_team="{}" '.format(team_names[0])
                for team_name in team_names[1]:
                    where += 'OR BB.create_team="{}" '.format(team_name)
                where += 'OR BB.create_team is NULL") '
        if is_complete:
            where += 'AND C.is_complete={} '.format(is_complete)
        if tags:
            group += 'WHERE E.name="{}" '.format(tags[0])
            for tag in tags[1:]:
                group += 'OR E.name="{}" '.format(tag)
        order_by = "GROUP BY CC.enterprise_id, CC.app_id ORDER BY CC.install_number DESC, CC.update_time DESC;"
        # sql1 = """SET GLOBAL group_concat_max_len = 40960000;"""
        # sql2 = """SET SESSION group_concat_max_len = 40960000;"""
        sql = """
                SELECT CC.*,
                CONCAT('[',
                    GROUP_CONCAT(
                        CONCAT('{"tag_id":"',E.ID,'"'),',',
                        CONCAT('"name":"',E.name),'"}')
                        ,']') as tags
                FROM
                (SELECT
                    BB.ID,
                    BB.app_id,
                    BB.app_name,
                    BB.create_user,
                    BB.create_team,
                    BB.pic,
                    BB.dev_status,
                    BB.describe,
                    BB.details,
                    BB.enterprise_id,
                    BB.create_time,
                    BB.update_time,
                    BB.is_ingerit,
                    BB.is_official,
                    BB.install_number,
                    BB.source,
                    BB.scope,
                    CONCAT('[',
                    GROUP_CONCAT(
                        CONCAT('"',C.version,'"'))
                    ,']') as versions,
                    CONCAT('[',
                    GROUP_CONCAT(
                        CONCAT('{"version":"',C.version,'"'),',',
                        CONCAT('"is_complete":',C.is_complete),',',
                        CONCAT('"version_alas":"',C.version_alias),'"}')
                    ,']') as versions_info
                FROM (SELECT A.enterprise_id, A.app_id, A.version, MAX(A.update_time) update_time
                      FROM rainbond_center_app_version A GROUP BY A.enterprise_id, A.app_id, A.version) B
                LEFT JOIN rainbond_center_app_version C
                ON C.enterprise_id=B.enterprise_id AND C.app_id=B.app_id AND
                C.version=B.version AND C.update_time=B.update_time
                RIGHT JOIN (SELECT * FROM rainbond_center_app RCA GROUP BY RCA.enterprise_id, RCA.app_id) BB
                ON C.enterprise_id=BB.enterprise_id AND C.app_id=BB.app_id
            """
        sql += where
        sql += group
        sql += order_by
        conn = BaseConnection()
        # conn.query(sql1)
        # conn.query(sql2)
        result = conn.query(sql)
        return result

    def get_rainbond_apps_versions_with_template_by_eid(self, eid, name=None, tags=None, scope=None, page=1, page_size=10):
        page = (page - 1) * page_size
        limit = "LIMIT {page}, {page_size}".format(page=page, page_size=page_size)
        where = 'WHERE BB.enterprise_id="{eid}" '.format(eid=eid)
        group = """GROUP BY BB.enterprise_id, BB.app_id {}) CC
        LEFT JOIN rainbond_center_app_tag_relation D
        ON D.app_id=CC.app_id AND D.enterprise_id=CC.enterprise_id
        LEFT JOIN rainbond_center_app_tag E
        ON D.tag_id=E.ID """.format(limit)
        if name:
            where += 'AND BB.app_name LIKE"{}%" '.format(name)
        if scope:
            where += 'AND BB.scope="{}" '.format(scope)
        if tags:
            group += 'WHERE E.name="{}" '.format(tags[0])
            for tag in tags[1:]:
                group += 'OR E.name="{}" '.format(tag)
        order_by = "GROUP BY CC.enterprise_id, CC.app_id ORDER BY CC.install_number DESC, CC.update_time DESC;"
        sql1 = """SET GLOBAL group_concat_max_len = 40960000;"""
        sql2 = """SET SESSION group_concat_max_len = 40960000;"""
        sql = """
                SELECT CC.*,
                CONCAT('[',
                    GROUP_CONCAT(
                        CONCAT('{"tag_id":"',E.ID,'"'),',',
                        CONCAT('"name":"',E.name),'"}')
                        ,']') as tags
                FROM
                (SELECT
                    BB.ID,
                    BB.app_id,
                    BB.app_name,
                    BB.create_user,
                    BB.create_team,
                    BB.pic,
                    BB.dev_status,
                    BB.describe,
                    BB.details,
                    BB.enterprise_id,
                    BB.create_time,
                    BB.update_time,
                    BB.is_ingerit,
                    BB.is_official,
                    BB.install_number,
                    BB.source,
                    BB.scope,
                    CONCAT('[',
                    GROUP_CONCAT(
                        CONCAT('"',C.version,'"'))
                    ,']') as versions,
                    CONCAT('[',
                    GROUP_CONCAT(
                        CONCAT('{"version":"',C.version,'"'),',',
                        CONCAT('"is_complete":',C.is_complete),',',
                        CONCAT('"version_alias":"',C.version_alias),'",',
                        CONCAT('"app_template":',C.app_template),'}')
                    ,']') as versions_info
                FROM (SELECT A.enterprise_id, A.app_id, A.version, MAX(A.update_time) update_time
                      FROM rainbond_center_app_version A GROUP BY A.enterprise_id, A.app_id, A.version) B
                LEFT JOIN rainbond_center_app_version C
                ON C.enterprise_id=B.enterprise_id AND C.app_id=B.app_id AND
                C.version=B.version AND C.update_time=B.update_time
                RIGHT JOIN (SELECT * FROM rainbond_center_app RCA GROUP BY RCA.enterprise_id, RCA.app_id) BB
                ON C.enterprise_id=BB.enterprise_id AND C.app_id=BB.app_id
            """
        sql += where
        sql += group
        sql += order_by
        conn = BaseConnection()
        conn.query(sql1)
        conn.query(sql2)
        result = conn.query(sql)
        return result

    def get_rainbond_app_versions_by_id(self, eid, app_id):
        where = 'WHERE (BB.enterprise_id="{eid}" OR BB.enterprise_id="public") AND BB.app_id="{app_id}";'.format(
            eid=eid, app_id=app_id)
        sql = """
                SELECT
                    BB.ID,
                    BB.app_id,
                    BB.app_name,
                    BB.create_user,
                    BB.create_team,
                    BB.pic,
                    BB.dev_status,
                    BB.describe,
                    BB.details,
                    BB.enterprise_id,
                    BB.create_time,
                    BB.update_time,
                    BB.is_ingerit,
                    BB.is_official,
                    BB.install_number,
                    BB.source,
                    BB.scope,
                    C.app_template,
                    C.version,
                    C.is_complete,
                    C.version_alias,
                    C.update_time,
                    C.create_time
                FROM (SELECT A.enterprise_id, A.app_id, A.version, MAX(A.update_time) update_time
                      FROM rainbond_center_app_version A GROUP BY A.enterprise_id, A.app_id, A.version) B
                LEFT JOIN rainbond_center_app_version C
                ON C.enterprise_id=B.enterprise_id AND C.app_id=B.app_id AND
                C.version=B.version AND C.update_time=B.update_time
                RIGHT JOIN (SELECT * FROM rainbond_center_app RCA GROUP BY RCA.enterprise_id, RCA.app_id) BB
                ON C.enterprise_id=BB.enterprise_id AND C.app_id=BB.app_id
            """
        sql += where
        conn = BaseConnection()
        result = conn.query(sql)
        return result

    def get_rainbond_app_version_by_app_id(self, eid, app_id, version):
        where = """
            WHERE (BB.enterprise_id="{eid}" OR BB.enterprise_id="public") AND
             BB.app_id="{app_id}" AND C.version="{version}";
            """.format(
            eid=eid, app_id=app_id, version=version)
        sql = """
                SELECT
                    BB.ID,
                    BB.app_id,
                    BB.app_name,
                    BB.create_user,
                    BB.create_team,
                    BB.pic,
                    BB.dev_status,
                    BB.describe,
                    BB.details,
                    BB.enterprise_id,
                    BB.create_time,
                    BB.update_time,
                    BB.is_ingerit,
                    BB.is_official,
                    BB.install_number,
                    BB.source,
                    BB.scope,
                    C.app_template,
                    C.version,
                    C.is_complete,
                    C.version_alias,
                    C.update_time,
                    C.create_time
                FROM (SELECT A.enterprise_id, A.app_id, A.version, MAX(A.update_time) update_time
                      FROM rainbond_center_app_version A GROUP BY A.enterprise_id, A.app_id, A.version) B
                LEFT JOIN rainbond_center_app_version C
                ON C.enterprise_id=B.enterprise_id AND C.app_id=B.app_id AND
                C.version=B.version AND C.update_time=B.update_time
                RIGHT JOIN (SELECT * FROM rainbond_center_app RCA GROUP BY RCA.enterprise_id, RCA.app_id) BB
                ON C.enterprise_id=BB.enterprise_id AND C.app_id=BB.app_id
            """
        sql += where
        conn = BaseConnection()
        result = conn.query(sql)
        return result

    def get_rainbond_app_by_key(self, group_key):
        rcapps = RainbondCenterApp.objects.filter(group_key=group_key).all()
        if rcapps:
            return rcapps
        return None

    def add_rainbond_install_num(self, enterprise_id, app_id, app_version):
        app = RainbondCenterApp.objects.get(enterprise_id=enterprise_id, app_id=app_id)
        app.install_number += 1
        app.save()

        app_version = RainbondCenterAppVersion.objects.filter(
            enterprise_id=enterprise_id, app_id=app_id, version=app_version).order_by("-upgrade_time").first()
        app_version.install_number += 1
        app_version.save()

    def get_rainbond_app_and_version(self, enterprise_id, app_id, app_version):
        app = RainbondCenterApp.objects.filter(enterprise_id=enterprise_id, app_id=app_id).first()
        app_version = RainbondCenterAppVersion.objects.filter(
            enterprise_id=enterprise_id,
            app_id=app_id,
            version=app_version,
            scope__in=["gooodrain", "team", "enterprise"],
        ).order_by("-upgrade_time").first()
        if app_version and app:
            return app, app_version
        app_version = RainbondCenterAppVersion.objects.filter(
            enterprise_id="public",
            app_id=app_id,
            version=app_version,
            scope__in=["gooodrain", "team", "enterprise"],
        ).order_by("-upgrade_time").first()
        if app_version and app:
            return app, app_version
        return None, None

    def list_by_key_time(self, group_key, time):
        rcapps = RainbondCenterAppVersion.objects.filter(app_id=group_key, update_time__gte=time, is_complete=True).all()
        if rcapps:
            return rcapps
        return None

    def get_rainbond_app_qs_by_key(self, eid, app_id):
        """使用group_key获取一个云市应用的所有版本查询集合"""
        return RainbondCenterApp.objects.filter(enterprise_id=eid, app_id=app_id)

    def get_rainbond_app_by_key_version(self, group_key, version):
        """使用group_key 和 version 获取一个云市应用"""
        app = RainbondCenterApp.objects.filter(app_id=group_key).first()
        app_version = RainbondCenterAppVersion.objects.filter(
            app_id=group_key, version=version, scope__in=["team", "enterprise", "goodrain"]).order_by("-upgrade_time").first()
        if app and app_version:
            app_version.app_name = app.app_name
        return app_version

    def get_enterpirse_app_by_key_and_version(self, enterprise_id, group_key, group_version):
        app = RainbondCenterApp.objects.filter(enterprise_id=enterprise_id, app_id=group_key).first()
        rcapps = RainbondCenterAppVersion.objects.filter(
            app_id=group_key, version=group_version, enterprise_id__in=["public", enterprise_id]).order_by("-update_time")
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

    def get_enterpirse_app_by_key(self, enterprise_id, group_key):
        rcapps = RainbondCenterApp.objects.filter(app_id=group_key, enterprise_id__in=["public", enterprise_id])
        if rcapps:
            rcapp = rcapps.filter(enterprise_id=enterprise_id)
            # 优先获取企业下的应用
            if rcapp:
                return rcapp[0]
            else:
                return rcapps[0]
        logger.warning("Enterprise ID: {0}; Group Key: {1};".format(enterprise_id, group_key))
        return None

    def bulk_create_rainbond_apps(self, rainbond_apps):
        RainbondCenterApp.objects.bulk_create(rainbond_apps)

    def bulk_create_rainbond_app_versions(self, rainbond_app_versions):
        RainbondCenterAppVersion.objects.bulk_create(rainbond_app_versions)

    def get_rainbond_app_version_by_app_id_and_version(self, app_id, version):
        return RainbondCenterAppVersion.objects.filter(app_id=app_id, version=version).first()

    def get_rainbond_app_versions(self, eid, app_id):
        return RainbondCenterAppVersion.objects.filter(enterprise_id=eid, app_id=app_id)

    def get_rainbond_app_by_record_id(self, record_id):
        rcapps = RainbondCenterApp.objects.filter(record_id=record_id)
        if rcapps:
            return rcapps[0]
        return None

    def delete_app_tag_by_id(self, enterprise_id, app_id):
        RainbondCenterAppTagsRelation.objects.filter(enterprise_id=enterprise_id, app_id=app_id).delete()

    def delete_app_version_by_id(self, enterprise_id, app_id):
        RainbondCenterAppVersion.objects.filter(enterprise_id=enterprise_id, app_id=app_id).delete()

    def delete_app_by_id(self, enterprise_id, app_id):
        RainbondCenterApp.objects.filter(enterprise_id=enterprise_id, app_id=app_id).delete()


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

# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import logging

from console.models.main import AppExportRecord
from console.models.main import AppImportRecord
from console.models.main import RainbondCenterApp
from console.models.main import RainbondCenterAppVersion
from console.utils.shortcuts import get_object_or_404
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

    def get_rainbond_app_by_app_id(self, eid, app_id):
        return RainbondCenterApp.objects.filter(app_id=app_id, enterprise_id=eid).first()

    def get_rainbond_app_by_eid(self, eid):
        return RainbondCenterApp.objects.filter(enterprise_id=eid)

    def get_rainbond_app_version_by_record_id(self, record_id):
        return RainbondCenterAppVersion.objects.filter(record_id=record_id).first()

    def get_rainbond_app_version_by_id(self, eid, app_id):
        return RainbondCenterAppVersion.objects.filter(enterprise_id=eid, app_id=app_id)

    def get_rainbond_apps_versions_by_eid(self, eid, name=None, tags=None, scope=None,
                                          is_complete=None, page=1, page_size=10):
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

    def get_rainbond_apps_versions_with_template_by_eid(self, eid, name=None, tags=None,
                                                        scope=None, page=1, page_size=10):
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

    def get_rainbond_app_by_key_and_version(self, enterprise_id, group_key, group_version):
        app = RainbondCenterApp.objects.filter(enterprise_id=enterprise_id, app_id=group_key).first()
        rcapps = RainbondCenterAppVersion.objects.filter(
            enterprise_id=enterprise_id, app_id=group_key,
            version=group_version,
            scope__in=["gooodrain", "team", "enterprise"]).order_by("-update_time")
        if rcapps and app:
            rcapps[0].pic = app.pic
            rcapps[0].group_name = app.app_name
            rcapps[0].describe = app.describe
            return rcapps[0]
        rcapps = RainbondCenterAppVersion.objects.filter(
            enterprise_id="public", app_id=group_key,
            version=group_version,
            scope__in=["gooodrain", "team", "enterprise"]).order_by("-update_time")
        if rcapps and app:
            rcapps[0].pic = app.pic
            rcapps[0].group_name = app.app_name
            rcapps[0].describe = app.describe
            return rcapps[0]
        return None

    def list_by_key_time(self, group_key, time):
        rcapps = RainbondCenterAppVersion.objects.filter(
            app_id=group_key, update_time__gte=time, is_complete=True).all()
        if rcapps:
            return rcapps
        return None

    def get_rainbond_app_qs_by_key(self, eid, app_id):
        """使用group_key获取一个云市应用的所有版本查询集合"""
        rbca = RainbondCenterAppVersion.objects.filter(
            enterprise_id=eid, app_id=app_id, scope__in=["team", "enterprise", "goodrain"]
        ).values().annotate("update_time")
        if not rbca:
            # 兼容旧数据
            rbca = RainbondCenterAppVersion.objects.filter(enterprise_id="public", app_id=app_id)
        return rbca

    def get_rainbond_app_by_key_version(self, group_key, version):
        """使用group_key 和 version 获取一个云市应用"""
        return get_object_or_404(RainbondCenterApp, msg='rainbond center app not found', group_key=group_key,
                                 version=version, scope__in=["team", "enterprise", "goodrain"])

    def get_enterpirse_app_by_key_and_version(self, enterprise_id, group_key, group_version):
        app = RainbondCenterApp.objects.filter(enterprise_id=enterprise_id, app_id=group_key).first()
        rcapps = RainbondCenterAppVersion.objects.filter(
            app_id=group_key, version=group_version,
            enterprise_id__in=["public", enterprise_id]).order_by("-update_time")
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
        rcapps = RainbondCenterApp.objects.filter(
            app_id=group_key, enterprise_id__in=["public", enterprise_id])
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

    def get_user_not_finished_import_record_in_enterprise(self, eid, user_name):
        return AppImportRecord.objects.filter(
            user_name=user_name, enterprise_id=eid).exclude(status__in=["success", "failed"])


rainbond_app_repo = RainbondCenterAppRepository()
app_export_record_repo = AppExportRepository()
app_import_record_repo = AppImportRepository()

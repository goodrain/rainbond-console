# -*- coding: utf-8 -*-
import logging

from www.apiclient.regionapi import RegionInvokeApi
from www.db.base import BaseConnection

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class BaseService(object):
    def get_services_list(self, team_id, region_name):
        dsn = BaseConnection()
        query_sql = '''
            SELECT
                t.service_id,
                t.service_alias,
                t.service_cname,
                t.service_type,
                t.deploy_version,
                t.version,
                t.update_time,
                r.group_id,
                g.group_name,
                h.tenant_name,
                i.region_id
            FROM
                tenant_service t
                LEFT JOIN service_group_relation r ON t.service_id = r.service_id
                LEFT JOIN service_group g ON r.group_id = g.ID
                LEFT JOIN tenant_info h ON t.tenant_id = h.tenant_id
                LEFT JOIN region_info i ON t.service_region = i.region_name

            WHERE
                t.tenant_id = "{team_id}"
                AND t.service_region = "{region_name}"
            ORDER BY
                t.update_time DESC;
        '''.format(
            team_id=team_id, region_name=region_name)
        services = dsn.query(query_sql)
        return services

    def get_group_services_list(self, team_id, region_name, group_id):
        dsn = BaseConnection()
        query_sql = '''
            SELECT
                t.service_id,
                t.service_alias,
                t.create_status,
                t.service_cname,
                t.service_type,
                t.deploy_version,
                t.version,
                t.update_time,
                t.min_memory * t.min_node AS min_memory,
                g.group_name
            FROM
                tenant_service t
                LEFT JOIN service_group_relation r ON t.service_id = r.service_id
                LEFT JOIN service_group g ON r.group_id = g.ID
            WHERE
                t.tenant_id = "{team_id}"
                AND t.service_region = "{region_name}"
                AND r.group_id = "{group_id}"
            ORDER BY
                t.update_time DESC;
        '''.format(
            team_id=team_id, region_name=region_name, group_id=group_id)
        services = dsn.query(query_sql)
        return services

    def get_no_group_services_list(self, team_id, region_name):
        dsn = BaseConnection()
        query_sql = '''
            SELECT
                t.service_id,
                t.service_alias,
                t.service_cname,
                t.service_type,
                t.create_status,
                t.deploy_version,
                t.version,
                t.update_time,
                t.min_memory * t.min_node AS min_memory,
                g.group_name
            FROM
                tenant_service t
                LEFT JOIN service_group_relation r ON t.service_id = r.service_id
                LEFT JOIN service_group g ON r.group_id = g.ID
            WHERE
                t.tenant_id = "{team_id}"
                AND t.service_region = "{region_name}"
                AND r.group_id IS NULL
            ORDER BY
                t.update_time DESC;
        '''.format(
            team_id=team_id, region_name=region_name)
        services = dsn.query(query_sql)
        return services

    def get_fuzzy_services_list(self, team_id, region_name, query_key, fields, order):
        if fields != "update_time" and fields != "ID":
            fields = "ID"
        if order != "desc" and order != "asc":
            order = "desc"
        dsn = BaseConnection()
        query_sql = '''
            SELECT
                t.create_status,
                t.service_id,
                t.service_cname,
                t.min_memory * t.min_node AS min_memory,
                t.service_alias,
                t.service_type,
                t.deploy_version,
                t.version,
                t.update_time,
                r.group_id,
                g.group_name
            FROM
                tenant_service t
                LEFT JOIN service_group_relation r ON t.service_id = r.service_id
                LEFT JOIN service_group g ON r.group_id = g.ID
            WHERE
                t.tenant_id = "{team_id}"
                AND t.service_region = "{region_name}"
                AND t.service_cname LIKE "%{query_key}%"
            ORDER BY
                t.{fields} {order};
        '''.format(
            team_id=team_id, region_name=region_name, query_key=query_key, fields=fields, order=order)
        services = dsn.query(query_sql)
        return services

    def status_multi_service(self, region, tenant_name, service_ids, enterprise_id):
        try:
            body = region_api.service_status(region, tenant_name, {"service_ids": service_ids, "enterprise_id": enterprise_id})
            return body["list"]
        except Exception as e:
            logger.exception(e)
            return None

    def get_apps_deploy_versions(self, region, tenant_name, service_ids):
        data = {"service_ids": service_ids}
        try:
            res, body = region_api.get_team_services_deploy_version(region, tenant_name, data)
            return body["list"]
        except Exception as e:
            logger.exception(e)
            return None

    def get_app_deploy_version(self, region, tenant_name, service_alias):
        try:
            res, body = region_api.get_service_deploy_version(region, tenant_name, service_alias)
            return body["bean"]
        except Exception as e:
            logger.exception(e)
            return None


base_service = BaseService()

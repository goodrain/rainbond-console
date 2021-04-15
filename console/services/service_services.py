# -*- coding: utf-8 -*-
import json
import logging
from re import split as re_split

from console.exception.main import RbdAppNotFound, ServiceHandleException
from console.repositories.app import service_source_repo
from console.utils.oauth.oauth_types import support_oauth_type
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

    def get_group_services_list(self, team_id, region_name, group_id, query=""):
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
                AND t.service_cname like "%{service_cname}%"
            ORDER BY
                t.update_time DESC;
        '''.format(
            team_id=team_id, region_name=region_name, group_id=group_id, service_cname=query)
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
            return []

    def get_apps_deploy_versions(self, region, tenant_name, service_ids):
        data = {"service_ids": service_ids}
        try:
            res, body = region_api.get_team_services_deploy_version(region, tenant_name, data)
            return body["list"]
        except Exception as e:
            logger.exception(e)
            return []

    def get_app_deploy_version(self, region, tenant_name, service_alias):
        try:
            res, body = region_api.get_service_deploy_version(region, tenant_name, service_alias)
            return body["bean"]
        except Exception as e:
            logger.exception(e)
            return None

    def get_enterprise_group_services(self, enterprise_id):
        where = 'WHERE group_id IN (SELECT ID FROM service_group WHERE tenant_id IN (SELECT tenant_id FROM ' \
                'tenant_info WHERE enterprise_id="{enterprise_id}")) '.format(enterprise_id=enterprise_id)
        group_by = "GROUP BY group_id"
        sql = """
            SELECT
                group_id,
                CONCAT('[', GROUP_CONCAT(CONCAT('"', service_id, '"')), ']') as service_ids
            FROM service_group_relation
        """
        sql += where
        sql += group_by
        conn = BaseConnection()
        result = conn.query(sql)
        return result

    def get_build_info(self, tenant, service):
        service_source = service_source_repo.get_service_source(team_id=service.tenant_id, service_id=service.service_id)

        code_from = service.code_from
        oauth_type = list(support_oauth_type.keys())
        if code_from in oauth_type:
            result_url = re_split("[:,@]", service.git_url)
            service.git_url = result_url[0] + '//' + result_url[-1]
        bean = {
            "user_name": "",
            "password": "",
            "service_source": service.service_source,
            "image": service.image,
            "cmd": service.cmd,
            "code_from": service.code_from,
            "version": service.version,
            "docker_cmd": service.docker_cmd,
            "create_time": service.create_time,
            "git_url": service.git_url,
            "code_version": service.code_version,
            "server_type": service.server_type,
            "language": service.language,
            "oauth_service_id": service.oauth_service_id,
            "full_name": service.git_full_name
        }
        if service_source:
            bean["user"] = service_source.user_name
            bean["password"] = service_source.password
        if service.service_source == 'market':
            from console.services.app import app_market_service
            from console.services.market_app_service import market_app_service
            if service_source:
                # get from cloud
                app = None
                app_version = None
                if service_source.extend_info:
                    extend_info = json.loads(service_source.extend_info)
                    if extend_info and extend_info.get("install_from_cloud", False):
                        market_name = extend_info.get("market_name")
                        bean["install_from_cloud"] = True
                        try:
                            market = app_market_service.get_app_market_by_name(
                                tenant.enterprise_id, market_name, raise_exception=True)
                            app, app_version = app_market_service.cloud_app_model_to_db_model(
                                market, service_source.group_key, service_source.version)
                            bean["market_error_code"] = 200
                            bean["market_status"] = 1
                        except ServiceHandleException as e:
                            logger.debug(e)
                            bean["market_status"] = 0
                            bean["market_error_code"] = e.error_code
                            return bean
                        bean["install_from_cloud"] = True
                        bean["app_detail_url"] = app.describe
                if not app:
                    try:
                        app, app_version = market_app_service.get_rainbond_app_and_version(
                            tenant.enterprise_id, service_source.group_key, service_source.version)
                    except RbdAppNotFound:
                        logger.warning("not found app {0} version {1} in local market".format(
                            service_source.group_key, service_source.version))
                if app:
                    bean["rain_app_name"] = app.app_name
                    bean["details"] = app.details
                    bean["group_key"] = app.app_id
                    bean["app_version"] = service_source.version
                    bean["version"] = service_source.version
        return bean

    def get_not_run_services_request_memory(self, tenant, services):
        not_run_service_ids = []
        memory = 0
        service_ids = [service.service_id for service in services]
        service_status_list = self.status_multi_service(tenant.region, tenant.tenant_name, service_ids, tenant.enterprise_id)
        if service_status_list:
            for status_map in service_status_list:
                if status_map.get("status") in ["undeploy", "closed"]:
                    not_run_service_ids.append(status_map.get("service_id"))
            if not_run_service_ids:
                for service in services:
                    if service.service_id in not_run_service_ids:
                        memory += int(service.min_memory) * int(service.min_node)
        return memory


base_service = BaseService()

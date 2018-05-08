# -*- coding: utf-8 -*-
import logging

from www.apiclient.regionapi import RegionInvokeApi
from www.db import BaseConnection

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class BaseService(object):
    def get_services_list(self, team_id, region_name):
        dsn = BaseConnection()
        query_sql = '''
            SELECT t.service_id,t.service_alias,t.service_cname,t.service_type,t.deploy_version,t.version,t.update_time,r.group_id,g.group_name FROM tenant_service t left join service_group_relation r on t.service_id=r.service_id LEFT join service_group g on r.group_id=g.ID where t.tenant_id="{team_id}" and t.service_region="{region_name}" ORDER by t.update_time DESC ;
        '''.format(team_id=team_id, region_name=region_name)
        services = dsn.query(query_sql)
        return services

    def get_group_services_list(self, team_id, region_name, group_id):
        dsn = BaseConnection()
        query_sql = '''
            SELECT t.service_id,t.service_alias,t.service_cname,t.service_type,t.deploy_version,t.version,t.update_time,t.min_memory*t.min_node as min_memory,g.group_name FROM tenant_service t left join service_group_relation r on t.service_id=r.service_id LEFT join service_group g on r.group_id=g.ID where t.tenant_id="{team_id}" and t.service_region="{region_name}" and r.group_id="{group_id}" ORDER by t.update_time DESC ;
        '''.format(team_id=team_id, region_name=region_name, group_id=group_id)
        services = dsn.query(query_sql)
        return services

    def get_no_group_services_list(self, team_id, region_name):
        dsn = BaseConnection()
        query_sql = '''
                SELECT t.service_id,t.service_alias,t.service_cname,t.service_type,t.create_status,t.deploy_version,t.version,t.update_time,t.min_memory*t.min_node as min_memory,g.group_name FROM tenant_service t left join service_group_relation r on t.service_id=r.service_id LEFT join service_group g on r.group_id=g.ID where t.tenant_id="{team_id}" and t.service_region="{region_name}" and r.group_id IS NULL ORDER by t.update_time DESC ;
            '''.format(team_id=team_id, region_name=region_name)
        services = dsn.query(query_sql)
        return services

    def get_fuzzy_services_list(self, team_id, region_name, query_key, fields, order):
        if fields != "update_time" and fields != "ID":
            fields = "ID"
        if order != "desc" and order != "asc":
            order = "desc"
        dsn = BaseConnection()
        query_sql = '''
            SELECT t.create_status, t.service_id,t.service_cname,t.min_memory*t.min_node as min_memory,t.service_alias,t.service_type,t.deploy_version,t.version,t.update_time,r.group_id,g.group_name FROM tenant_service t left join service_group_relation r on t.service_id=r.service_id LEFT join service_group g on r.group_id=g.ID where t.tenant_id="{team_id}" and t.service_region="{region_name}" and t.service_cname LIKE "%{query_key}%" ORDER by t.{fields} {order} ;
        '''.format(team_id=team_id, region_name=region_name, query_key=query_key, fields=fields, order=order)
        services = dsn.query(query_sql)
        return services

    def status_multi_service(self, region, tenant_name, service_ids, enterprise_id):
        try:
            body = region_api.service_status(region, tenant_name,
                                             {"service_ids": service_ids, "enterprise_id": enterprise_id})
            return body["list"]
        except Exception as e:
            logger.exception( e)
            return None


base_service = BaseService()

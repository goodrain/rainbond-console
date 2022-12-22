# -*- coding: utf8 -*-
import logging

from console.services.team_services import team_services
from console.repositories.region_app import region_app_repo
from console.repositories.app_config import domain_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo

from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()

logger = logging.getLogger('default')


class RainbondPluginService(object):
    def list_plugins(self, enterprise_id, region_name):
        team_names, team_ids, region_app_ids, app_ids, component_ids = [], [], [], [], []
        region_apps_map = {}

        _, body = region_api.list_plugins(enterprise_id, region_name)
        plugins = body.get("list", [])
        for plugin in plugins:
            region_app_ids.append(plugin["region_app_id"])
            team_names.append(plugin["team_name"])

        teams = team_services.list_by_team_names(team_names)
        team_ids = [team.tenant_id for team in teams]

        region_apps = region_app_repo.list_by_region_app_ids(region_name, region_app_ids)
        for region_app in region_apps:
            app_ids.append(region_app.app_id)
            region_apps_map = {region_app.region_app_id: region_app.app_id}

        app_component_rels = {}
        relations = service_group_relation_repo.list_by_tenant_ids(team_ids)
        for relation in relations:
            component_ids.append(relation.service_id)
            if app_component_rels.get(relation.group_id):
                app_component_rels[relation.group_id].append(relation.service_id)
                continue
            app_component_rels[relation.group_id] = [relation.service_id]

        component_url_rels = {}
        domains = domain_repo.list_by_component_ids(component_ids)
        for domain in domains:
            url = domain.protocol + "://" + domain.domain_name
            if component_url_rels.get(domain.service_id):
                component_url_rels[domain.service_id].append(url)
                continue
            component_url_rels[domain.service_id] = [url]

        for plugin in plugins:
            app_id = region_apps_map.get(plugin["region_app_id"], -1)
            plugin["team_name"] = plugin["team_name"]
            plugin["app_id"] = app_id
            plugin["urls"] = []
            if app_component_rels.get(app_id):
                for component_id in app_component_rels[app_id]:
                    if component_url_rels.get(component_id):
                        plugin["urls"].extend(component_url_rels[component_id])

        return plugins


rbd_plugin_service = RainbondPluginService()

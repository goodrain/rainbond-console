# -*- coding: utf8 -*-
import logging
import time

from console.services.team_services import team_services
from console.services.platform_plugin_service import platform_plugin_service
from console.repositories.region_app import region_app_repo
from console.repositories.app_config import domain_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo
from console.utils.offline import is_cloud_market_disabled

from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()

logger = logging.getLogger('default')


class RainbondPluginService(object):
    def list_plugins(self, enterprise_id, region_name, official=False):
        team_names, team_ids, region_app_ids, app_ids, component_ids = [], [], [], [], []
        region_apps_map = {}

        total_start = time.time()
        region_elapsed_ms = 0
        market_elapsed_ms = 0
        console_db_elapsed_ms = 0
        enrich_elapsed_ms = 0
        need_authz = False
        logger.info("Calling region_api.list_plugins: enterprise_id={}, region_name={}, official={}".format(
            enterprise_id, region_name, official))
        region_start = time.time()
        _, body = region_api.list_plugins(enterprise_id, region_name, official)
        region_elapsed_ms = (time.time() - region_start) * 1000
        plugins = body["list"] if body.get("list") else []
        logger.info("region_api.list_plugins returned {} plugins from region".format(len(plugins)))

        # Log raw plugin data from region API
        for idx, plugin in enumerate(plugins):
            logger.info("Raw plugin {} from region: name={}, category={}, alias={}".format(
                idx + 1,
                plugin.get("name", "unknown"),
                plugin.get("category", "unknown"),
                plugin.get("alias", "unknown")))

        market_plugins = []
        market_plugin_map = {}
        if official and not is_cloud_market_disabled():
            market_start = time.time()
            try:
                _, market_plugins = platform_plugin_service._get_market_platform_plugins_cached(enterprise_id)
                for plugin in plugins:
                    plugin_id = plugin.get("name", "")
                    market_plugin = platform_plugin_service._select_market_plugin(market_plugins, plugin_id, {})
                    if market_plugin:
                        market_plugin_map[plugin_id] = market_plugin
            except Exception as e:
                logger.warning("failed to fetch platform plugin market metadata: %s", e)
            finally:
                market_elapsed_ms = (time.time() - market_start) * 1000
        elif official:
            logger.info("official plugin market metadata skipped because cloud market is disabled")

        for plugin in plugins:
            region_app_ids.append(plugin["region_app_id"])
            team_names.append(plugin["team_name"])
            plugin_id = plugin.get("name", "")
            app_level = ""
            if official and market_plugin_map.get(plugin_id):
                app_level = platform_plugin_service._normalize_app_level(market_plugin_map[plugin_id])
                plugin["app_level"] = app_level
            if app_level == "enterprise":
                need_authz = True

        console_db_start = time.time()
        teams = team_services.list_by_team_names(team_names)
        team_ids = [team.tenant_id for team in teams]

        region_apps = region_app_repo.list_by_region_app_ids(region_name, region_app_ids)
        for region_app in region_apps:
            app_ids.append(region_app.app_id)
            region_apps_map[region_app.region_app_id] = region_app.app_id
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
            if domain.is_outer_service:
                url = domain.protocol + "://" + domain.domain_name
                if component_url_rels.get(domain.service_id):
                    component_url_rels[domain.service_id].append(url)
                    continue
                component_url_rels[domain.service_id] = [url]
        console_db_elapsed_ms = (time.time() - console_db_start) * 1000

        enrich_start = time.time()
        for plugin in plugins:
            app_id = region_apps_map.get(plugin["region_app_id"], -1)
            plugin["team_name"] = plugin["team_name"]
            plugin["app_id"] = app_id
            plugin["urls"] = []
            plugin["display_name"] = plugin["alias"]
            plugin["backend"] = plugin["backend"]
            if official and plugin["access_urls"] and len(plugin["access_urls"]) > 0:
                plugin["urls"] = plugin["access_urls"]
            elif app_component_rels.get(app_id):
                for component_id in app_component_rels[app_id]:
                    if component_url_rels.get(component_id):
                        plugin["urls"].extend(component_url_rels[component_id])
        enrich_elapsed_ms = (time.time() - enrich_start) * 1000
        logger.info(
            "official plugin list timing enterprise_id=%s region_name=%s official=%s plugin_count=%s "
            "market_plugin_count=%s region_ms=%.1f market_ms=%.1f console_db_ms=%.1f enrich_ms=%.1f total_ms=%.1f",
            enterprise_id,
            region_name,
            official,
            len(plugins),
            len(market_plugins),
            region_elapsed_ms,
            market_elapsed_ms,
            console_db_elapsed_ms,
            enrich_elapsed_ms,
            (time.time() - total_start) * 1000,
        )
        return plugins, need_authz


rbd_plugin_service = RainbondPluginService()

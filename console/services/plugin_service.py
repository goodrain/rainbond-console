# -*- coding: utf8 -*-
import logging
from urllib.parse import urlparse, urlunparse

from console.services.app_config import port_service
from console.services.team_services import team_services
from console.services.platform_plugin_service import platform_plugin_service
from console.repositories.region_app import region_app_repo
from console.repositories.app_config import domain_repo
from console.repositories.service_group_relation_repo import service_group_relation_repo

from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo

region_api = RegionInvokeApi()

logger = logging.getLogger('default')


class RainbondPluginService(object):
    @staticmethod
    def _request_host_name(request):
        if not request or not hasattr(request, "get_host"):
            return ""
        host = str(request.get_host() or "").strip()
        if not host:
            return ""
        if ":" in host:
            return host.rsplit(":", 1)[0]
        return host

    def _normalize_access_url(self, raw_url, request=None):
        raw_url = str(raw_url or "").strip()
        if not raw_url:
            return ""

        request_scheme = getattr(request, "scheme", "") or "http"
        request_host_name = self._request_host_name(request)

        if raw_url.startswith(("http://", "https://")):
            parsed = urlparse(raw_url)
            hostname = parsed.hostname or ""
            if request_host_name and hostname in ("0.0.0.0", "127.0.0.1", "localhost"):
                netloc = request_host_name
                if parsed.port:
                    netloc = "{}:{}".format(request_host_name, parsed.port)
                return urlunparse(
                    (request_scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
                ).rstrip("/")
            return raw_url.rstrip("/")

        if request_host_name and raw_url.startswith(("0.0.0.0:", "127.0.0.1:", "localhost:")):
            return "{}://{}:{}".format(request_scheme, request_host_name, raw_url.rsplit(":", 1)[1]).rstrip("/")

        if "://" not in raw_url and ":" in raw_url:
            return "{}://{}".format(request_scheme if request else "http", raw_url).rstrip("/")

        return raw_url.rstrip("/")

    def _resolve_vm_plugin_urls(self, plugin, app_id, team, app_component_rels, request=None):
        if plugin.get("name") != "rainbond-vm":
            return []
        frontend_component_name = plugin.get("frontend_component", "")
        if not frontend_component_name or not team or not app_component_rels.get(app_id):
            return []

        frontend_component = TenantServiceInfo.objects.filter(
            tenant_id=team.tenant_id,
            service_id__in=app_component_rels[app_id],
            service_cname=frontend_component_name
        ).first()
        if not frontend_component:
            return []

        _, access_info = port_service.get_access_info(team, frontend_component)
        urls = []
        for item in access_info or []:
            for raw_url in item.get("access_urls") or []:
                url = self._normalize_access_url(raw_url, request=request)
                if url and url not in urls:
                    urls.append(url)
        return urls

    def get_vm_plugin_url(self, enterprise_id, region_name, request=None):
        plugins, _ = self.list_plugins(enterprise_id, region_name, official=True, request=request)
        for plugin in plugins:
            if plugin.get("name") == "rainbond-vm":
                urls = plugin.get("urls") or []
                if urls:
                    return urls[0]
        return ""

    def list_plugins(self, enterprise_id, region_name, official=False, request=None):
        team_names, team_ids, region_app_ids, app_ids, component_ids = [], [], [], [], []
        region_apps_map = {}

        need_authz = False
        logger.info("Calling region_api.list_plugins: enterprise_id={}, region_name={}, official={}".format(
            enterprise_id, region_name, official))
        _, body = region_api.list_plugins(enterprise_id, region_name, official)
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
        if official:
            try:
                _, market_plugins = platform_plugin_service._get_market_platform_plugins(enterprise_id)
                for plugin in plugins:
                    plugin_id = plugin.get("name", "")
                    market_plugin = platform_plugin_service._select_market_plugin(market_plugins, plugin_id, {})
                    if market_plugin:
                        market_plugin_map[plugin_id] = market_plugin
            except Exception as e:
                logger.warning("failed to fetch platform plugin market metadata: %s", e)

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

        teams = team_services.list_by_team_names(team_names)
        teams_by_name = {}
        for team in teams:
            team_key = getattr(team, "tenant_name", "") or getattr(team, "name", "")
            if team_key:
                teams_by_name[team_key] = team
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

        for plugin in plugins:
            app_id = region_apps_map.get(plugin["region_app_id"], -1)
            plugin["team_name"] = plugin["team_name"]
            plugin["app_id"] = app_id
            plugin["urls"] = []
            plugin["display_name"] = plugin["alias"]
            plugin["backend"] = plugin.get("backend", "")
            access_urls = plugin.get("access_urls") or []
            if official and isinstance(access_urls, (list, tuple)) and len(access_urls) > 0:
                plugin["urls"] = list(access_urls)
            elif app_component_rels.get(app_id):
                for component_id in app_component_rels[app_id]:
                    if component_url_rels.get(component_id):
                        plugin["urls"].extend(component_url_rels[component_id])
            if official and not plugin["urls"]:
                plugin["urls"] = self._resolve_vm_plugin_urls(
                    plugin,
                    app_id,
                    teams_by_name.get(plugin["team_name"]),
                    app_component_rels,
                    request=request
                )
            plugin["urls"] = [self._normalize_access_url(url, request=request) for url in plugin["urls"] if url]
        return plugins, need_authz


rbd_plugin_service = RainbondPluginService()

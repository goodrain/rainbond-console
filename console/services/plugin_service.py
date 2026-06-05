# -*- coding: utf8 -*-
import logging
from urllib.parse import urlparse, urlunparse
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

VM_PLUGIN_VNC_SERVICE_NAME = "virtvnc"


class RainbondPluginService(object):
    @staticmethod
    def _parse_frontend_service(frontend_service):
        frontend_service = str(frontend_service or "").strip()
        if not frontend_service:
            return "", None
        parse_target = frontend_service
        if not parse_target.startswith(("http://", "https://")):
            parse_target = "http://" + parse_target
        parsed = urlparse(parse_target)
        service_name = parsed.hostname or ""
        if "." in service_name:
            service_name = service_name.split(".", 1)[0]
        return service_name, parsed.port

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

    def _get_ns_service_resource(self, region_name, team_name, service_name):
        if not team_name or not service_name:
            return {}
        try:
            _, body = region_api.get_tenant_ns_resource(
                region_name,
                team_name,
                service_name,
                params={"group": "", "version": "v1", "resource": "services"}
            )
        except Exception as err:
            logger.warning(
                "failed to get service resource for vm plugin region=%s team=%s service=%s: %s",
                region_name,
                team_name,
                service_name,
                err
            )
            return {}
        bean = body.get("bean", {}) if isinstance(body, dict) else {}
        return bean if isinstance(bean, dict) else {}

    def _build_service_nodeport_url(self, service_resource, target_port, request=None):
        spec = service_resource.get("spec", {}) if isinstance(service_resource, dict) else {}
        ports = spec.get("ports", []) if isinstance(spec, dict) else []
        if not isinstance(ports, list):
            return ""

        matched_ports = []
        if target_port is not None:
            for port in ports:
                if not isinstance(port, dict):
                    continue
                if port.get("port") == target_port or str(port.get("targetPort", "")) == str(target_port):
                    matched_ports.append(port)

        for port in matched_ports or ports:
            if not isinstance(port, dict):
                continue
            node_port = port.get("nodePort")
            if node_port:
                return self._normalize_access_url("0.0.0.0:{}".format(node_port), request=request)
        return ""

    def _resolve_vm_plugin_urls(self, plugin, app_id, team, app_component_rels, region_name, request=None):
        if plugin.get("name") != "rainbond-vm":
            return []
        if not team:
            return []
        _, target_port = self._parse_frontend_service(plugin.get("frontend_service"))
        service_resource = self._get_ns_service_resource(
            region_name,
            team.tenant_name,
            VM_PLUGIN_VNC_SERVICE_NAME
        )
        nodeport_url = self._build_service_nodeport_url(service_resource, target_port, request=request)
        if nodeport_url:
            return [nodeport_url]
        return []

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
        console_db_elapsed_ms = (time.time() - console_db_start) * 1000

        enrich_start = time.time()
        for plugin in plugins:
            app_id = region_apps_map.get(plugin["region_app_id"], -1)
            plugin["team_name"] = plugin["team_name"]
            plugin["app_id"] = app_id
            plugin["urls"] = []
            plugin["display_name"] = plugin["alias"]
            plugin["backend"] = plugin.get("backend", "")
            access_urls = plugin.get("access_urls") or []
            preferred_vm_urls = []
            if official and plugin.get("name") == "rainbond-vm":
                preferred_vm_urls = self._resolve_vm_plugin_urls(
                    plugin,
                    app_id,
                    teams_by_name.get(plugin["team_name"]),
                    app_component_rels,
                    region_name,
                    request=request
                )
            if preferred_vm_urls:
                plugin["urls"] = preferred_vm_urls
            elif official and isinstance(access_urls, (list, tuple)) and len(access_urls) > 0:
                plugin["urls"] = list(access_urls)
            elif app_component_rels.get(app_id):
                for component_id in app_component_rels[app_id]:
                    if component_url_rels.get(component_id):
                        plugin["urls"].extend(component_url_rels[component_id])
            plugin["urls"] = [self._normalize_access_url(url, request=request) for url in plugin["urls"] if url]
            plugin["urls"] = [self._normalize_access_url(url, request=request) for url in plugin["urls"] if url]
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

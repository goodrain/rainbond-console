# -*- coding: utf-8 -*-
import base64
import copy
import datetime
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Any, Callable, Dict, Iterable, Optional, Tuple
from urllib.parse import urlencode

from console.models.main import RegionConfig
from console.repositories.region_repo import region_repo
from console.services.enterprise_services import enterprise_services
from console.services.platform_plugin_service import platform_plugin_service
from django.core.cache import cache
from django.db import close_old_connections
from django.db.models import Count, F, IntegerField, Sum
from django.db.models.expressions import ExpressionWrapper
from django.utils import timezone
from OpenSSL import crypto
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import (ServiceDomain, ServiceDomainCertificate, ServiceGroup, ServiceGroupRelation, ServiceTcpDomain,
                             TenantRegionInfo, TenantServiceInfo, Tenants, Users)

logger = logging.getLogger("default")


class PlatformOverviewRegionNotFound(Exception):
    pass


class PlatformOverviewService(object):
    """Fast, failure-isolated data aggregation for the enterprise homepage."""

    RUNTIME_CACHE_SECONDS = 15
    SNAPSHOT_CACHE_SECONDS = 10
    METRICS_CACHE_SECONDS = 15
    DISK_ALERT_THRESHOLD = 70.0
    REGION_CONNECT_TIMEOUT_SECONDS = 2
    REGION_READ_TIMEOUT_SECONDS = 3
    SECTION_DEADLINE_SECONDS = 5
    _RUNTIME_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="platform-overview-runtime")
    _SNAPSHOT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="platform-overview-snapshot")
    _CACHE_LOCKS = tuple(threading.Lock() for _ in range(64))
    METRIC_QUERIES = {
        "cpu":
        '(1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))) * 100',
        "memory":
        '(1 - sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes)) * 100',
        "network": ('sum(rate(node_network_receive_bytes_total{device!="lo"}[5m])) + '
                    'sum(rate(node_network_transmit_bytes_total{device!="lo"}[5m]))'),
    }
    METRIC_UNITS = {"cpu": "percent", "memory": "percent", "network": "bytes_per_second"}
    RANGE_CONFIG = {"1h": (3600, 60), "6h": (21600, 300), "24h": (86400, 900)}

    def __init__(self,
                 cache_backend: Any = None,
                 region_api: Any = None,
                 region_api_factory: Optional[Callable[[], Any]] = None) -> None:
        self._cache = cache_backend or cache
        self._region_api = region_api
        if region_api_factory is not None:
            self._region_api_factory = region_api_factory
        elif region_api is not None:
            self._region_api_factory = lambda: region_api
        else:
            self._region_api_factory = RegionInvokeApi

    def _new_region_api(self) -> Any:
        return self._region_api_factory()

    def _cached(self, cache_key: str, timeout: int, loader: Callable[[], dict]) -> dict:
        cached = self._cache.get(cache_key)
        if cached is not None:
            return copy.deepcopy(cached)
        lock = self._CACHE_LOCKS[hash(cache_key) % len(self._CACHE_LOCKS)]
        with lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return copy.deepcopy(cached)
            result = loader()
            self._cache.set(cache_key, copy.deepcopy(result), timeout)
            return result

    @staticmethod
    def _generated_at() -> str:
        return timezone.now().isoformat()

    @staticmethod
    def _cache_key(kind: str, *parts: Any) -> str:
        return "platform-overview:{}:{}".format(kind, ":".join(str(part) for part in parts))

    def get_shell(self, enterprise_id: str) -> dict:
        regions = self._list_region_records(enterprise_id)
        return {
            "status": "ok",
            "generated_at": self._generated_at(),
            "global": self._database_counts(enterprise_id),
            "clusters": [self._region_metadata(region) for region in regions],
        }

    def get_runtime(self, enterprise_id: str) -> dict:
        cache_key = self._cache_key("runtime", enterprise_id)
        return self._cached(cache_key, self.RUNTIME_CACHE_SECONDS, lambda: self._build_runtime(enterprise_id))

    def _build_runtime(self, enterprise_id: str) -> dict:
        regions = self._list_region_records(enterprise_id)
        active_regions = [region for region in regions if region.status == "1"]
        region_sections = self._fetch_runtime_regions(enterprise_id, active_regions)
        running_service_ids = []
        abnormal_service_ids = []
        region_data = []
        node_total = 0
        node_ready = 0
        cluster_healthy = 0
        cluster_warning = 0
        cluster_unavailable = 0
        cluster_disabled = 0
        runtime_partial = False
        workload_runtime_complete = True
        alarm_runtime_complete = True
        for region in regions:
            if region.status != "1":
                cluster_disabled += 1
                region_data.append({
                    "region_name": region.region_name,
                    "region_alias": region.region_alias,
                    "status": "disabled",
                    "nodes": None,
                })
                continue
            section = region_sections.get(region.region_name, {"status": "unavailable", "data": None})
            if section["status"] != "ok":
                cluster_unavailable += 1
                workload_runtime_complete = False
                alarm_runtime_complete = False
                runtime_partial = True
                region_data.append({
                    "region_name": region.region_name,
                    "region_alias": region.region_alias,
                    "status": "unavailable",
                    "nodes": None,
                })
                continue
            data = section["data"] or {}
            if data.get("status") == "partial":
                runtime_partial = True
            workload_runtime_complete = workload_runtime_complete and data.get("workloads_status") == "ok"
            alarm_runtime_complete = alarm_runtime_complete and data.get("alarms_status") == "ok"
            nodes = data.get("nodes")
            if nodes is None:
                health = "unavailable"
                cluster_unavailable += 1
            else:
                node_total += int(nodes.get("total") or 0)
                node_ready += int(nodes.get("ready") or 0)
                health = "healthy" if nodes.get("total") and nodes.get("total") == nodes.get("ready") else "warning"
                if health == "healthy":
                    cluster_healthy += 1
                else:
                    cluster_warning += 1
            running_service_ids.extend(data.get("running_service_ids") or [])
            abnormal_service_ids.extend(data.get("abnormal_service_ids") or [])
            region_data.append({
                "region_name":
                region.region_name,
                "region_alias":
                region.region_alias,
                "status":
                health,
                "nodes": ({
                    "total": nodes.get("total", 0),
                    "ready": nodes.get("ready", 0)
                } if nodes is not None else None),
            })

        totals = self._database_workload_counts(enterprise_id)
        running = self._database_running_workload_counts(enterprise_id, [region.region_name for region in regions],
                                                         set(running_service_ids))
        application_alarms = self._database_application_alerts(enterprise_id, set(abnormal_service_ids))
        status = self._overall_status(region_sections)
        result = {
            "status": status,
            "generated_at": self._generated_at(),
            "global": {
                "clusters": {
                    "total": len(regions),
                    "healthy": cluster_healthy,
                    "warning": cluster_warning,
                    "unavailable": cluster_unavailable,
                    "disabled": cluster_disabled,
                },
                "nodes": {
                    "total": node_total,
                    "ready": node_ready
                },
                "applications": {
                    "total": totals["applications"],
                    "running": running["applications"],
                    "status": "ok" if workload_runtime_complete else "partial",
                },
                "components": {
                    "total": totals["components"],
                    "running": running["components"],
                    "status": "ok" if workload_runtime_complete else "partial",
                },
                "application_alarms": {
                    "total": len(application_alarms),
                    "items": application_alarms,
                    "status": "ok" if alarm_runtime_complete else "partial",
                },
            },
            "regions": region_data,
        }
        if status == "ok" and runtime_partial:
            result["status"] = "partial"
        return result

    def get_cluster_overview(self, enterprise_id: str, region_name: str) -> dict:
        region = self._get_enterprise_region(enterprise_id, region_name)
        cache_key = self._cache_key("snapshot", enterprise_id, region_name)
        return self._cached(cache_key, self.SNAPSHOT_CACHE_SECONDS,
                            lambda: self._build_cluster_overview(enterprise_id, region_name, region))

    def _build_cluster_overview(self, enterprise_id: str, region_name: str, region: RegionConfig) -> dict:
        calls = {
            "resources": self._deferred(self._fetch_cluster_resources, enterprise_id, region_name),
            "nodes": self._deferred(self._fetch_nodes, region_name),
            "components": self._deferred(self._fetch_components, region_name),
            "plugins": self._deferred(self._fetch_plugins, enterprise_id, region_name),
            "teams": self._deferred(self._database_team_ranking, enterprise_id, region_name),
            "gateway": self._deferred(self._database_gateway_summary, enterprise_id, region),
        }
        sections = self._run_sections(calls, max_workers=4)
        if sections.get("gateway", {}).get("status") == "ok" and not sections["gateway"]["data"]:
            sections["gateway"] = {"status": "empty", "data": None}
        overall_status = self._overall_status(sections)
        sections["cluster"] = {"status": "ok", "data": self._region_metadata(region)}
        result = {
            "status": overall_status,
            "generated_at": self._generated_at(),
            "region_name": region_name,
            "sections": sections,
        }
        return result

    def get_metrics(self, enterprise_id: str, region_name: str, metric: str, time_range: str) -> dict:
        if metric not in self.METRIC_QUERIES:
            raise ValueError("unsupported metric")
        if time_range not in self.RANGE_CONFIG:
            raise ValueError("unsupported range")
        self._get_enterprise_region(enterprise_id, region_name)
        cache_key = self._cache_key("metrics", enterprise_id, region_name, metric, time_range)
        return self._cached(cache_key, self.METRICS_CACHE_SECONDS,
                            lambda: self._load_metrics(enterprise_id, region_name, metric, time_range))

    def _load_metrics(self, enterprise_id: str, region_name: str, metric: str, time_range: str) -> dict:
        try:
            result = self._query_metrics(enterprise_id, region_name, metric, time_range)
        except Exception:
            logger.warning(
                "platform overview metric query failed: enterprise=%s region=%s metric=%s range=%s",
                enterprise_id,
                region_name,
                metric,
                time_range,
                exc_info=True,
            )
            result = {
                "status": "unavailable",
                "generated_at": self._generated_at(),
                "metric": metric,
                "range": time_range,
                "unit": self.METRIC_UNITS[metric],
                "series": [],
            }
        return result

    def _query_metrics(self, enterprise_id: str, region_name: str, metric: str, time_range: str) -> dict:
        tenant_name = self._metric_tenant_name(enterprise_id, region_name)
        tenant_name = tenant_name or ""
        duration, step = self.RANGE_CONFIG[time_range]
        end = int(timezone.now().timestamp())
        params = "?{}".format(
            urlencode({
                "query": self.METRIC_QUERIES[metric],
                "start": end - duration,
                "end": end,
                "step": step,
            }))
        response, body = self._new_region_api().get_query_range_data(region_name,
                                                                     tenant_name,
                                                                     params,
                                                                     connect_timeout=self.REGION_CONNECT_TIMEOUT_SECONDS,
                                                                     timeout=self.REGION_READ_TIMEOUT_SECONDS,
                                                                     retries=0)
        if not isinstance(body, dict) or body.get("status") != "success":
            raise RuntimeError("invalid Prometheus response")
        return {
            "status": "ok",
            "generated_at": self._generated_at(),
            "metric": metric,
            "range": time_range,
            "unit": self.METRIC_UNITS[metric],
            "series": (body.get("data") or {}).get("result") or [],
        }

    @staticmethod
    def _deferred(func: Callable[..., Any], *args: Any) -> Callable[[], Any]:
        return lambda: func(*args)

    def _run_sections(self,
                      calls: Dict[str, Callable[[], Any]],
                      max_workers: int,
                      timeout_seconds: Optional[float] = None) -> dict:
        if not calls:
            return {}
        deadline = self.SECTION_DEADLINE_SECONDS if timeout_seconds is None else timeout_seconds
        sections = {}
        executor = self._RUNTIME_EXECUTOR if max_workers > 4 else self._SNAPSHOT_EXECUTOR
        futures = {}
        futures = {executor.submit(self._execute_section, call): name for name, call in calls.items()}
        done, pending = wait(tuple(futures.keys()), timeout=deadline)
        for future in done:
            name = futures[future]
            try:
                sections[name] = {"status": "ok", "data": future.result()}
            except Exception:
                logger.warning("platform overview section failed: %s", name, exc_info=True)
                sections[name] = {"status": "unavailable", "data": None}
        for future in pending:
            name = futures[future]
            future.cancel()
            logger.warning("platform overview section deadline exceeded: %s", name)
            sections[name] = {"status": "unavailable", "data": None}
        return sections

    @staticmethod
    def _execute_section(call: Callable[[], Any]) -> Any:
        close_old_connections()
        try:
            return call()
        finally:
            close_old_connections()

    @staticmethod
    def _overall_status(sections: dict) -> str:
        statuses = [section.get("status") for section in sections.values()]
        unavailable = statuses.count("unavailable")
        if statuses and unavailable == len(statuses):
            return "unavailable"
        if unavailable:
            return "partial"
        return "ok"

    def _list_region_records(self, enterprise_id: str) -> list:
        return list(region_repo.get_regions_by_enterprise_id(enterprise_id).order_by("ID"))

    def _get_enterprise_region(self, enterprise_id: str, region_name: str) -> RegionConfig:
        region = region_repo.get_enterprise_region_by_region_name(enterprise_id, region_name)
        if not region:
            raise PlatformOverviewRegionNotFound(region_name)
        return region

    @staticmethod
    def _region_metadata(region: RegionConfig) -> dict:
        create_time = getattr(region, "create_time", None)
        return {
            "region_id": region.region_id,
            "region_name": region.region_name,
            "region_alias": region.region_alias,
            "status": region.status,
            "provider": getattr(region, "provider", "") or "",
            "create_time": create_time.isoformat() if create_time else None,
        }

    @staticmethod
    def _tenant_ids(enterprise_id: str, region_name: Optional[str] = None) -> Any:
        active_team_ids = Tenants.objects.filter(enterprise_id=enterprise_id, is_active=True).values_list("tenant_id",
                                                                                                          flat=True)
        filters = {
            "enterprise_id": enterprise_id,
            "tenant_id__in": active_team_ids,
            "is_active": True,
            "is_init": True,
        }
        if region_name:
            filters["region_name"] = region_name
        query = TenantRegionInfo.objects.filter(**filters)
        return query.values_list("tenant_id", flat=True)

    def _database_counts(self, enterprise_id: str) -> dict:
        tenant_ids = self._tenant_ids(enterprise_id)
        return {
            "clusters": RegionConfig.objects.filter(enterprise_id=enterprise_id).count(),
            "teams": Tenants.objects.filter(enterprise_id=enterprise_id, is_active=True).count(),
            "users": Users.objects.filter(enterprise_id=enterprise_id, is_active=True).count(),
            "applications": ServiceGroup.objects.filter(tenant_id__in=tenant_ids).count(),
            "components": TenantServiceInfo.objects.filter(tenant_id__in=tenant_ids).count(),
        }

    def _database_workload_counts(self, enterprise_id: str) -> dict:
        counts = self._database_counts(enterprise_id)
        return {"applications": counts["applications"], "components": counts["components"]}

    def _database_running_workload_counts(self, enterprise_id: str, region_names: Iterable[str],
                                          running_service_ids: Iterable[str]) -> dict:
        service_ids = list(set(running_service_ids))
        if not service_ids:
            return {"applications": 0, "components": 0}
        tenant_ids = self._tenant_ids(enterprise_id)
        groups = ServiceGroup.objects.filter(tenant_id__in=tenant_ids, region_name__in=region_names)
        group_ids = groups.values_list("ID", flat=True)
        relations = ServiceGroupRelation.objects.filter(group_id__in=group_ids,
                                                        service_id__in=service_ids,
                                                        tenant_id__in=tenant_ids,
                                                        region_name__in=region_names)
        return {
            "applications": relations.values("group_id").distinct().count(),
            "components": relations.values("service_id").distinct().count(),
        }

    def _database_application_alerts(self, enterprise_id: str, service_ids: Iterable[str]) -> list:
        service_ids = sorted(set(service_ids))
        if not service_ids:
            return []
        tenant_ids = list(self._tenant_ids(enterprise_id))
        teams = {team.tenant_id: team for team in Tenants.objects.filter(tenant_id__in=tenant_ids)}
        services = list(TenantServiceInfo.objects.filter(tenant_id__in=tenant_ids, service_id__in=service_ids))
        region_names = sorted({service.service_region for service in services})
        service_scope = {service.service_id: (service.tenant_id, service.service_region) for service in services}
        relation_candidates = list(
            ServiceGroupRelation.objects.filter(service_id__in=service_ids,
                                                tenant_id__in=tenant_ids,
                                                region_name__in=region_names))
        candidate_group_ids = sorted({relation.group_id for relation in relation_candidates})
        groups = {
            group.ID: group
            for group in ServiceGroup.objects.filter(
                ID__in=candidate_group_ids, tenant_id__in=tenant_ids, region_name__in=region_names)
        }
        relations = {}
        for relation in relation_candidates:
            expected_scope = service_scope.get(relation.service_id)
            if (expected_scope == (relation.tenant_id, relation.region_name) and relation.group_id in groups):
                relations[relation.service_id] = relation.group_id
        items = []
        for service in services:
            team = teams.get(service.tenant_id)
            group_id = relations.get(service.service_id)
            group = groups.get(group_id)
            items.append({
                "service_id": service.service_id,
                "service_alias": service.service_alias,
                "service_name": service.service_cname,
                "tenant_id": service.tenant_id,
                "tenant_name": team.tenant_name if team else None,
                "tenant_alias": team.tenant_alias if team else None,
                "application_id": group_id,
                "application_name": group.group_name if group else None,
                "region_name": service.service_region,
            })
        return sorted(items, key=lambda item: (item["region_name"], item["service_name"] or ""))

    def _fetch_runtime_regions(self, enterprise_id: str, regions: list) -> dict:
        calls = {}
        for region in regions:
            calls[self._runtime_key(region.region_name, "nodes")] = self._deferred(self._fetch_nodes, region.region_name)
            calls[self._runtime_key(region.region_name, "workloads")] = self._deferred(self._fetch_running_service_ids,
                                                                                       enterprise_id, region.region_name)
            calls[self._runtime_key(region.region_name, "alarms")] = self._deferred(self._fetch_abnormal_service_ids,
                                                                                    enterprise_id, region.region_name)
        raw_sections = self._run_sections(calls, max_workers=8, timeout_seconds=self.SECTION_DEADLINE_SECONDS)
        return {region.region_name: self._compose_region_runtime(region.region_name, raw_sections) for region in regions}

    def _fetch_region_runtime(self, enterprise_id: str, region: RegionConfig) -> dict:
        calls = {
            "nodes": self._deferred(self._fetch_nodes, region.region_name),
            "workloads": self._deferred(self._fetch_running_service_ids, enterprise_id, region.region_name),
            "alarms": self._deferred(self._fetch_abnormal_service_ids, enterprise_id, region.region_name),
        }
        sections = self._run_sections(calls, max_workers=3, timeout_seconds=self.SECTION_DEADLINE_SECONDS)
        composed = self._compose_region_runtime(region.region_name, sections, prefixed=False)
        if composed["data"] is None:
            raise RuntimeError("all region runtime sections are unavailable")
        return composed["data"]

    @staticmethod
    def _runtime_key(region_name: str, section_name: str) -> str:
        return "{}::{}".format(region_name, section_name)

    def _compose_region_runtime(self, region_name: str, sections: dict, prefixed: bool = True) -> dict:
        def section(name: str) -> dict:
            key = self._runtime_key(region_name, name) if prefixed else name
            return sections.get(key, {"status": "unavailable", "data": None})

        nodes = section("nodes")
        workloads = section("workloads")
        alarms = section("alarms")
        region_sections = {"nodes": nodes, "workloads": workloads, "alarms": alarms}
        unavailable = [name for name, value in region_sections.items() if value["status"] != "ok"]
        if len(unavailable) == len(region_sections):
            return {"status": "unavailable", "data": None}
        return {
            "status": "ok",
            "data": {
                "region_name": region_name,
                "nodes": nodes["data"] if nodes["status"] == "ok" else None,
                "running_service_ids": workloads["data"] if workloads["status"] == "ok" else [],
                "abnormal_service_ids": alarms["data"] if alarms["status"] == "ok" else [],
                "workloads_status": workloads["status"],
                "alarms_status": alarms["status"],
                "status": "partial" if unavailable else "ok",
                "unavailable_sections": unavailable,
            },
        }

    def _fetch_running_service_ids(self, enterprise_id: str, region_name: str) -> list:
        running = self._new_region_api().get_enterprise_running_services(enterprise_id,
                                                                         region_name,
                                                                         test=False,
                                                                         connect_timeout=self.REGION_CONNECT_TIMEOUT_SECONDS,
                                                                         timeout=self.REGION_READ_TIMEOUT_SECONDS,
                                                                         retries=0)
        if not isinstance(running, dict):
            raise RuntimeError("invalid running services response")
        return running.get("service_ids") or []

    def _fetch_abnormal_service_ids(self, enterprise_id: str, region_name: str) -> list:
        abnormal = self._new_region_api().get_user_service_abnormal_status(region_name,
                                                                           enterprise_id,
                                                                           connect_timeout=self.REGION_CONNECT_TIMEOUT_SECONDS,
                                                                           timeout=self.REGION_READ_TIMEOUT_SECONDS,
                                                                           retries=0)
        if not isinstance(abnormal, dict):
            raise RuntimeError("invalid application alarms response")
        return abnormal.get("service_ids") or []

    def _fetch_cluster_resources(self, enterprise_id: str, region_name: str) -> dict:
        response, body = self._new_region_api().get_region_resources(enterprise_id,
                                                                     region=region_name,
                                                                     connect_timeout=self.REGION_CONNECT_TIMEOUT_SECONDS,
                                                                     timeout=self.REGION_READ_TIMEOUT_SECONDS,
                                                                     retries=0)
        if not isinstance(body, dict) or response.get("status") != 200:
            raise RuntimeError("invalid cluster resource response")
        bean = body.get("bean") or {}
        cap_cpu = self._number(bean.get("cap_cpu"))
        req_cpu = self._number(bean.get("req_cpu"))
        cap_mem = self._number(bean.get("cap_mem"))
        req_mem = self._number(bean.get("req_mem"))
        pods = bean.get("pods")
        pod_total = None
        if isinstance(pods, list):
            pod_total = len(pods)
        elif bean.get("pod_number") is not None:
            pod_total = self._integer(bean.get("pod_number"))
        elif bean.get("total_pods") is not None:
            pod_total = self._integer(bean.get("total_pods"))
        return {
            "cpu": {
                "capacity": cap_cpu,
                "allocated": req_cpu,
                "allocation_percent": self._percentage(req_cpu, cap_cpu),
                "unit": "core",
            },
            "memory": {
                "capacity": cap_mem,
                "allocated": req_mem,
                "allocation_percent": self._percentage(req_mem, cap_mem),
                "unit": "MiB",
            },
            "pods": {
                "running": self._integer(bean.get("run_pod_number", bean.get("running_pods"))),
                "total": pod_total,
            },
            "versions": {
                "rainbond": bean.get("rbd_version"),
                "kubernetes": bean.get("k8s_version"),
            },
            "resource_proxy_status": bean.get("resource_proxy_status"),
        }

    def _fetch_nodes(self, region_name: str) -> dict:
        response, body = self._new_region_api().get_cluster_nodes(region_name,
                                                                  connect_timeout=self.REGION_CONNECT_TIMEOUT_SECONDS,
                                                                  timeout=self.REGION_READ_TIMEOUT_SECONDS,
                                                                  retries=0)
        if not isinstance(body, dict) or response.get("status") != 200:
            raise RuntimeError("invalid node response")
        return self._normalize_nodes(body)

    def _normalize_nodes(self, body: dict) -> dict:
        nodes = []
        alerts = []
        ready_count = 0
        for source in body.get("list") or []:
            conditions = source.get("conditions") or []
            ready = any(
                condition.get("type") == "Ready" and str(condition.get("status")).lower() == "true" for condition in conditions)
            if ready:
                ready_count += 1
            resource = source.get("resource") or {}
            name = source.get("name") or source.get("internal_ip") or ""
            node = {
                "name": name,
                "internal_ip": source.get("internal_ip"),
                "external_ip": source.get("external_ip"),
                "ready": ready,
                "unschedulable": bool(source.get("unschedulable")),
                "roles": source.get("roles") or [],
                "architecture": source.get("architecture"),
                "cpu": {
                    "capacity": self._number(resource.get("cap_cpu")),
                    "allocated": self._number(resource.get("req_cpu")),
                    "unit": "core",
                },
                "memory": {
                    "capacity": self._number(resource.get("cap_memory")),
                    "allocated": self._number(resource.get("req_memory")),
                    "unit": "MiB",
                },
                "disks": [],
            }
            if not ready:
                alerts.append({
                    "type": "node_not_ready",
                    "severity": "critical",
                    "node_name": name,
                    "message": "节点未就绪",
                })
            disk_fields = (
                ("root", resource.get("req_disk"), resource.get("cap_disk")),
                ("container", resource.get("req_container_disk"), resource.get("cap_container_disk")),
            )
            for filesystem, used, capacity in disk_fields:
                used_value = self._number(used)
                capacity_value = self._number(capacity)
                if capacity_value <= 0:
                    continue
                usage = self._percentage(used_value, capacity_value)
                node["disks"].append({
                    "filesystem": filesystem,
                    "used_bytes": used_value,
                    "capacity_bytes": capacity_value,
                    "usage_percent": usage,
                })
                if usage >= self.DISK_ALERT_THRESHOLD:
                    alerts.append({
                        "type":
                        "disk_usage",
                        "severity":
                        "critical" if usage >= 80 else "warning",
                        "node_name":
                        name,
                        "filesystem":
                        filesystem,
                        "usage_percent":
                        usage,
                        "message":
                        "磁盘空间使用率已超过 {}%，当前已使用 {}%".format(int(self.DISK_ALERT_THRESHOLD), self._display_percentage(usage)),
                    })
            nodes.append(node)
        return {"total": len(nodes), "ready": ready_count, "items": nodes, "alerts": alerts}

    def _fetch_components(self, region_name: str) -> list:
        return enterprise_services.get_rbdcomponents(region_name,
                                                     connect_timeout=self.REGION_CONNECT_TIMEOUT_SECONDS,
                                                     timeout=self.REGION_READ_TIMEOUT_SECONDS,
                                                     retries=0,
                                                     region_api_client=self._new_region_api())

    def _fetch_plugins(self, enterprise_id: str, region_name: str) -> list:
        return platform_plugin_service.list_installed_platform_plugins(enterprise_id,
                                                                       region_name,
                                                                       region_api_client=self._new_region_api())

    def _database_team_ranking(self, enterprise_id: str, region_name: str) -> dict:
        tenant_ids = list(self._tenant_ids(enterprise_id, region_name))
        if not tenant_ids:
            return {"cpu": [], "memory": [], "applications": []}
        teams = list(Tenants.objects.filter(tenant_id__in=tenant_ids).values("tenant_id", "tenant_name", "tenant_alias"))
        cpu_expression = ExpressionWrapper(F("min_cpu") * F("min_node"), output_field=IntegerField())
        memory_expression = ExpressionWrapper(F("min_memory") * F("min_node"), output_field=IntegerField())
        resources = list(
            TenantServiceInfo.objects.filter(tenant_id__in=tenant_ids, service_region=region_name).values("tenant_id").annotate(
                cpu_millicores=Sum(cpu_expression), memory_mib=Sum(memory_expression)))
        applications = list(
            ServiceGroup.objects.filter(tenant_id__in=tenant_ids,
                                        region_name=region_name).values("tenant_id").annotate(total=Count("ID")))
        return self._build_team_rankings(teams, resources, applications)

    def _build_team_rankings(self, teams: list, resources: list, applications: list) -> dict:
        resource_map = {row["tenant_id"]: row for row in resources}
        application_map = {row["tenant_id"]: row["total"] for row in applications}
        items = []
        for team in teams:
            resource = resource_map.get(team["tenant_id"], {})
            items.append({
                "tenant_id": team["tenant_id"],
                "tenant_name": team["tenant_name"],
                "tenant_alias": team["tenant_alias"],
                "cpu_cores": round(float(resource.get("cpu_millicores") or 0) / 1000, 3),
                "memory_gib": round(float(resource.get("memory_mib") or 0) / 1024, 3),
                "applications": int(application_map.get(team["tenant_id"], 0)),
            })
        return {
            "cpu": self._top_five(items, "cpu_cores"),
            "memory": self._top_five(items, "memory_gib"),
            "applications": self._top_five(items, "applications"),
        }

    @staticmethod
    def _top_five(items: list, field: str) -> list:
        return sorted(items, key=lambda item: (-item[field], item["tenant_alias"] or item["tenant_name"]))[:5]

    def _database_gateway_summary(self, enterprise_id: str, region: RegionConfig) -> Optional[dict]:
        tenant_ids = list(self._tenant_ids(enterprise_id, region.region_name))
        if not tenant_ids:
            return None
        services = list(
            TenantServiceInfo.objects.filter(tenant_id__in=tenant_ids, service_region=region.region_name).values(
                "service_id", "service_alias", "service_cname", "tenant_id"))
        service_ids = [service["service_id"] for service in services]
        if not service_ids:
            return None
        http_domains = list(ServiceDomain.objects.filter(service_id__in=service_ids, is_outer_service=True))
        tcp_domains = list(ServiceTcpDomain.objects.filter(service_id__in=service_ids, is_outer_service=True))
        if not http_domains and not tcp_domains:
            return None
        certificate_pks = {domain.certificate_id for domain in http_domains if domain.certificate_id}
        certificates = {
            certificate.ID: certificate
            for certificate in ServiceDomainCertificate.objects.filter(ID__in=certificate_pks)
        }
        teams = {team.tenant_id: team for team in Tenants.objects.filter(tenant_id__in=tenant_ids)}
        service_map = {service["service_id"]: service for service in services}
        group_ids = list(
            ServiceGroup.objects.filter(tenant_id__in=tenant_ids, region_name=region.region_name).values_list("ID", flat=True))
        relation_candidates = ServiceGroupRelation.objects.filter(service_id__in=service_ids,
                                                                  tenant_id__in=tenant_ids,
                                                                  region_name=region.region_name,
                                                                  group_id__in=group_ids)
        valid_group_ids = set(group_ids)
        relations = {}
        for relation in relation_candidates:
            service = service_map.get(relation.service_id)
            if (service and relation.tenant_id == service["tenant_id"] and
                    relation.region_name == region.region_name and relation.group_id in valid_group_ids):
                relations[relation.service_id] = relation.group_id
        issues = []
        now = timezone.now()
        certificate_items = []
        for certificate_id in sorted(certificate_pks):
            certificate = certificates.get(certificate_id)
            if not certificate:
                certificate_items.append({"id": certificate_id, "status": "unknown", "expires_at": None})
                for domain in (domain for domain in http_domains if domain.certificate_id == certificate_id):
                    issues.append(self._gateway_issue(domain, service_map, teams, relations, "unknown", None))
                continue
            status, expires_at = self._certificate_status(certificate, now)
            item = {"id": certificate.ID, "alias": certificate.alias, "status": status, "expires_at": expires_at}
            certificate_items.append(item)
            if status in ("warning", "critical", "unknown"):
                for domain in (domain for domain in http_domains if domain.certificate_id == certificate_id):
                    issues.append(self._gateway_issue(domain, service_map, teams, relations, status, expires_at))
        return {
            "http_domains": len(http_domains),
            "tcp_routes": len(tcp_domains),
            "certificates": certificate_items,
            "issues": issues,
        }

    def _certificate_status(self, certificate: ServiceDomainCertificate, now: datetime.datetime) -> Tuple[str, Optional[str]]:
        try:
            content = base64.b64decode(certificate.certificate).decode("utf-8")
            parsed = crypto.load_certificate(crypto.FILETYPE_PEM, content)
            not_after = parsed.get_notAfter()
            if isinstance(not_after, bytes):
                not_after = not_after.decode("ascii")
            expires = datetime.datetime.strptime(not_after, "%Y%m%d%H%M%SZ").replace(tzinfo=datetime.timezone.utc)
            if timezone.is_naive(now):
                now = timezone.make_aware(now, timezone.get_current_timezone())
            now = now.astimezone(datetime.timezone.utc)
            if expires <= now:
                return "critical", expires.isoformat()
            if expires <= now + datetime.timedelta(days=30):
                return "warning", expires.isoformat()
            return "normal", expires.isoformat()
        except Exception:
            logger.warning("failed to analyze overview certificate id=%s", certificate.ID, exc_info=True)
            return "unknown", None

    @staticmethod
    def _gateway_issue(domain: ServiceDomain, service_map: dict, teams: dict, relations: dict, status: str,
                       expires_at: Optional[str]) -> dict:
        service = service_map.get(domain.service_id, {})
        team = teams.get(domain.tenant_id)
        return {
            "type": "certificate",
            "severity": status,
            "domain": domain.domain_name,
            "certificate_id": domain.certificate_id,
            "expires_at": expires_at,
            "service_id": domain.service_id,
            "service_alias": service.get("service_alias") or domain.service_alias,
            "service_name": service.get("service_cname") or domain.service_name,
            "tenant_id": domain.tenant_id,
            "tenant_name": team.tenant_name if team else None,
            "application_id": relations.get(domain.service_id),
        }

    def _metric_tenant_name(self, enterprise_id: str, region_name: str) -> Optional[str]:
        tenant_ids = self._tenant_ids(enterprise_id, region_name)
        return Tenants.objects.filter(tenant_id__in=tenant_ids).order_by("ID").values_list("tenant_name", flat=True).first()

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _integer(cls, value: Any) -> int:
        return int(cls._number(value))

    @classmethod
    def _percentage(cls, used: Any, capacity: Any) -> float:
        capacity_value = cls._number(capacity)
        if capacity_value <= 0:
            return 0.0
        return round(cls._number(used) * 100 / capacity_value, 2)

    @staticmethod
    def _display_percentage(value: float) -> Any:
        return int(value) if value.is_integer() else value


platform_overview_service = PlatformOverviewService()

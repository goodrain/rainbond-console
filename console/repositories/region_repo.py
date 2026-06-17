# -*- coding: utf-8 -*-
from typing import Any, List, Optional

from console.exception.main import RegionNotFound
from console.models.main import RegionConfig
from console.repositories.base import BaseConnection
from console.repositories.init_cluster import rke_cluster
from console.repositories.team_repo import team_repo
from django.db.models import Q, QuerySet
from www.models.main import TenantRegionInfo


class RegionRepo(object):
    def get_active_region_by_tenant_name(self, tenant_name: str) -> Optional[QuerySet[TenantRegionInfo]]:
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=True)
        # exception=True guarantees a non-None tenant (raises otherwise)
        regions = TenantRegionInfo.objects.filter(
            tenant_id=tenant.tenant_id, is_active=True, is_init=True)  # type: ignore[union-attr]
        if regions:
            return regions
        return None

    def list_active_region_by_tenant_ids(self, tenant_ids: List[str]) -> Optional[QuerySet[TenantRegionInfo]]:
        regions = TenantRegionInfo.objects.filter(tenant_id__in=tenant_ids, is_active=True, is_init=True)
        if regions:
            return regions
        return None

    def get_region_by_tenant_name(self, tenant_name: str) -> Optional[QuerySet[TenantRegionInfo]]:
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=True)
        # exception=True guarantees a non-None tenant (raises otherwise)
        regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id)  # type: ignore[union-attr]
        if regions:
            return regions
        return None

    def get_region_by_region_id(self, region_id: str) -> RegionConfig:
        return RegionConfig.objects.get(region_id=region_id)

    def get_region_by_enterprise_id(self, enterprise_id: str) -> Optional[RegionConfig]:
        regions = RegionConfig.objects.filter(enterprise_id=enterprise_id)
        if regions:
            return regions[0]
        return None

    def get_region_desc_by_region_name(self, region_name: str) -> Optional[str]:
        regions = RegionConfig.objects.filter(region_name=region_name)
        if regions:
            region_desc = regions[0].desc
            return region_desc
        else:
            return None

    def get_usable_regions(self, enterprise_id: str) -> QuerySet[RegionConfig]:
        """获取可使用的数据中心"""
        usable_regions = RegionConfig.objects.filter(status="1", enterprise_id=enterprise_id)
        return usable_regions

    def get_team_opened_region(self, team_name: str) -> Optional[QuerySet[TenantRegionInfo]]:
        """获取团队已开通的数据中心"""
        tenant = team_repo.get_team_by_team_name(team_name)
        if not tenant:
            return None
        return TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id)

    def get_region_by_region_name(self, region_name: str) -> Optional[RegionConfig]:
        region_configs = RegionConfig.objects.filter(region_name=region_name)
        if region_configs:
            return region_configs[0]
        return None

    def get_region_info_all(self) -> QuerySet[RegionConfig]:
        return RegionConfig.objects.all()

    def get_enterprise_region_by_region_name(self, enterprise_id: str, region_name: str) -> Optional[RegionConfig]:
        region_configs = RegionConfig.objects.filter(enterprise_id=enterprise_id, region_name=region_name)
        if region_configs:
            return region_configs[0]
        return None

    def get_by_region_name(self, region_name: str) -> RegionConfig:
        return RegionConfig.objects.get(region_name=region_name)

    def get_region_by_region_names(self, region_names: List[str]) -> QuerySet[RegionConfig]:
        return RegionConfig.objects.filter(region_name__in=region_names)

    def get_team_region_by_tenant_and_region(self, tenant_id: str, region: str) -> Optional[TenantRegionInfo]:
        tenant_regions = TenantRegionInfo.objects.filter(tenant_id=tenant_id, region_name=region)
        if tenant_regions:
            return tenant_regions[0]
        return None

    def create_tenant_region(self, **params: Any) -> TenantRegionInfo:
        return TenantRegionInfo.objects.create(**params)

    def create_region(self, region_data: dict) -> RegionConfig:
        region_config = RegionConfig(**region_data)
        region_config.save()
        return region_config

    def update_region(self, region: RegionConfig) -> RegionConfig:
        region.save()
        return region

    def get_all_regions(self, query: str = "") -> QuerySet[RegionConfig]:
        if query:
            return RegionConfig.objects.filter(Q(region_name__constains=query) | Q(region_alias__constains=query)).all()
        return RegionConfig.objects.all()

    def get_regions_by_region_ids(self, enterprise_id: str, region_ids: List[str]) -> QuerySet[RegionConfig]:
        return RegionConfig.objects.filter(region_id__in=region_ids, enterprise_id=enterprise_id)

    def get_regions_by_tenant_ids(self, tenant_ids: List[str]) -> Any:
        # values_list(flat=True) returns a scalar QuerySet of region_name strings
        return TenantRegionInfo.objects.filter(tenant_id__in=tenant_ids, is_init=True).values_list("region_name", flat=True)

    def get_region_info_by_region_name(self, region_name: str) -> QuerySet[RegionConfig]:
        return RegionConfig.objects.filter(region_name=region_name)

    def get_tenant_regions_by_teamid(self, team_id: str) -> QuerySet[TenantRegionInfo]:
        return TenantRegionInfo.objects.filter(tenant_id=team_id)

    # not list tenant region if region is not exist
    def list_by_tenant_id(self, tenant_id: str, query: str = "", page: Optional[int] = None,
                          page_size: Optional[int] = None) -> Any:
        limit = ""
        if page is not None and page_size is not None:
            page = page if page > 0 else 1
            page = (page - 1) * page_size
            limit = "LIMIT {page}, {page_size}".format(page=page, page_size=page_size)
        where = """
        WHERE
            ti.tenant_id = tr.tenant_id
            AND ri.region_name = tr.region_name
            AND ti.tenant_id = "{tenant_id}"
        """.format(tenant_id=tenant_id)
        if query:
            where += "AND (ri.region_name like '%{query}% OR ri.region_alias like '%{query}%)'".format(query=query)
        sql = """
        SELECT
            ri.*, ti.tenant_name
        FROM
            region_info ri,
            tenant_info ti,
            tenant_region tr
        {where}
        {limit}
        """.format(
            where=where, limit=limit)
        conn = BaseConnection()
        return conn.query(sql)

    def count_by_tenant_id(self, tenant_id: str, query: str = "") -> Any:
        where = """
        WHERE
            ti.tenant_id = tr.tenant_id
            AND ri.region_name = tr.region_name
            AND ti.tenant_id = "{tenant_id}"
        """.format(tenant_id=tenant_id)
        if query:
            where += "AND (ri.region_name like '%{query}% OR ri.region_alias like '%{query}%)'".format(query=query)
        sql = """
        SELECT
            count(*) as total
        FROM
            region_info ri,
            tenant_info ti,
            tenant_region tr
        {where}
        """.format(where=where)
        conn = BaseConnection()
        result = conn.query(sql)
        return result[0]["total"]

    def del_by_enterprise_region_id(self, enterprise_id: str, region_id: str) -> RegionConfig:
        region = RegionConfig.objects.get(region_id=region_id, enterprise_id=enterprise_id)
        region.delete()
        rke_cluster.delete_cluster(cluster_id=region.region_name)
        return region

    def del_by_region_id(self, region_id: str) -> RegionConfig:
        region = RegionConfig.objects.get(region_id=region_id)
        region.delete()
        return region

    def get_team_used_region_by_enterprise_id(self, eid: str) -> Optional[TenantRegionInfo]:
        trs = TenantRegionInfo.objects.filter(enterprise_id=eid)
        if trs:
            for tr in trs:
                region = RegionConfig.objects.filter(enterprise_id=eid, region_name=tr.region_name)
                if region:
                    return tr
        return None

    def get_regions_by_enterprise_id(self, eid: str, status: Optional[str] = None) -> QuerySet[RegionConfig]:
        if status:
            return RegionConfig.objects.filter(enterprise_id=eid, status=status)
        return RegionConfig.objects.filter(enterprise_id=eid)

    def get_region_by_id(self, eid: str, region_id: str) -> Optional[RegionConfig]:
        return RegionConfig.objects.filter(enterprise_id=eid, region_id=region_id).first()

    def get_region_by_token(self, eid: str, token: str) -> Optional[RegionConfig]:
        return RegionConfig.objects.filter(enterprise_id=eid, token=token).first()

    def update_enterprise_region(self, eid: str, region_id: str, data: dict) -> RegionConfig:
        region = self.get_region_by_id(eid, region_id)
        if not region:
            raise RegionNotFound("region no found")
        # data.get() yields Any|None; assigning to non-null model fields trips
        # django-stubs strictness but is safe at runtime (callers pass values).
        region.region_alias = data.get("region_alias")  # type: ignore[assignment]
        region.url = data.get("url")  # type: ignore[assignment]
        region.wsurl = data.get("wsurl")  # type: ignore[assignment]
        region.httpdomain = data.get("httpdomain")  # type: ignore[assignment]
        region.tcpdomain = data.get("tcpdomain")  # type: ignore[assignment]
        if data.get("scope"):
            region.scope = data.get("scope")  # type: ignore[assignment]
        region.ssl_ca_cert = data.get("ssl_ca_cert")  # type: ignore[assignment]
        region.cert_file = data.get("cert_file")  # type: ignore[assignment]
        region.desc = data.get("desc")  # type: ignore[assignment]
        region.key_file = data.get("key_file")  # type: ignore[assignment]
        region.save()
        return region

    def get_tenants_by_region_name(self, region_name: str) -> List[str]:
        tenant_region_info_list = TenantRegionInfo.objects.filter(region_name=region_name)
        tenant_id_list = [tenant_region_info.tenant_id for tenant_region_info in tenant_region_info_list]
        return tenant_id_list

    def get_service_status_count_by_region_name(self, region: RegionConfig) -> dict:
        from console.services.team_services import team_services
        region_services_status = {"running": 0}
        region_tenants, total = team_services.get_tenant_list_by_region(
            # NOTE: region.enterprise_id is Optional[str]; get_tenant_list_by_region declares eid: str
            region.enterprise_id, region.region_id, page=1, page_size=9999)  # type: ignore[arg-type]
        for region_tenant in region_tenants:
            region_services_status["running"] += region_tenant["running_app_num"]
        return region_services_status


region_repo = RegionRepo()

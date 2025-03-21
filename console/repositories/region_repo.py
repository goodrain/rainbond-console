# -*- coding: utf-8 -*-
from console.exception.main import RegionNotFound
from console.models.main import RegionConfig
from console.repositories.base import BaseConnection
from console.repositories.init_cluster import rke_cluster
from console.repositories.team_repo import team_repo
from django.db.models import Q
from www.models.main import TenantRegionInfo


class RegionRepo(object):
    def get_active_region_by_tenant_name(self, tenant_name):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=True)
        regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, is_active=1, is_init=1)
        if regions:
            return regions
        return None

    def list_active_region_by_tenant_ids(self, tenant_ids):
        regions = TenantRegionInfo.objects.filter(tenant_id__in=tenant_ids, is_active=1, is_init=1)
        if regions:
            return regions
        return None

    def get_region_by_tenant_name(self, tenant_name):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name, exception=True)
        regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id)
        if regions:
            return regions
        return None

    def get_region_by_region_id(self, region_id):
        return RegionConfig.objects.get(region_id=region_id)

    def get_region_by_enterprise_id(self, enterprise_id):
        regions = RegionConfig.objects.filter(enterprise_id=enterprise_id)
        if regions:
            return regions[0]
        return None

    def get_region_desc_by_region_name(self, region_name):
        regions = RegionConfig.objects.filter(region_name=region_name)
        if regions:
            region_desc = regions[0].desc
            return region_desc
        else:
            return None

    def get_usable_regions(self, enterprise_id):
        """获取可使用的数据中心"""
        usable_regions = RegionConfig.objects.filter(status="1", enterprise_id=enterprise_id)
        return usable_regions

    def get_team_opened_region(self, team_name):
        """获取团队已开通的数据中心"""
        tenant = team_repo.get_team_by_team_name(team_name)
        if not tenant:
            return None
        return TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id)

    def get_region_by_region_name(self, region_name):
        region_configs = RegionConfig.objects.filter(region_name=region_name)
        if region_configs:
            return region_configs[0]
        return None

    def get_region_info_all(self):
        return RegionConfig.objects.all()

    def get_enterprise_region_by_region_name(self, enterprise_id, region_name):
        region_configs = RegionConfig.objects.filter(enterprise_id=enterprise_id, region_name=region_name)
        if region_configs:
            return region_configs[0]
        return None

    def get_by_region_name(self, region_name):
        return RegionConfig.objects.get(region_name=region_name)

    def get_region_by_region_names(self, region_names):
        return RegionConfig.objects.filter(region_name__in=region_names)

    def get_team_region_by_tenant_and_region(self, tenant_id, region):
        tenant_regions = TenantRegionInfo.objects.filter(tenant_id=tenant_id, region_name=region)
        if tenant_regions:
            return tenant_regions[0]
        return None

    def create_tenant_region(self, **params):
        return TenantRegionInfo.objects.create(**params)

    def create_region(self, region_data):
        region_config = RegionConfig(**region_data)
        region_config.save()
        return region_config

    def update_region(self, region):
        region.save()
        return region

    def get_all_regions(self, query=""):
        if query:
            return RegionConfig.objects.filter(Q(region_name__constains=query) | Q(region_alias__constains=query)).all()
        return RegionConfig.objects.all()

    def get_regions_by_region_ids(self, enterprise_id, region_ids):
        return RegionConfig.objects.filter(region_id__in=region_ids, enterprise_id=enterprise_id)

    def get_regions_by_tenant_ids(self, tenant_ids):
        return TenantRegionInfo.objects.filter(tenant_id__in=tenant_ids, is_init=True).values_list("region_name", flat=True)

    def get_region_info_by_region_name(self, region_name):
        return RegionConfig.objects.filter(region_name=region_name)

    def get_tenant_regions_by_teamid(self, team_id):
        return TenantRegionInfo.objects.filter(tenant_id=team_id)

    # not list tenant region if region is not exist
    def list_by_tenant_id(self, tenant_id, query="", page=None, page_size=None):
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

    def count_by_tenant_id(self, tenant_id, query=""):
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

    def del_by_enterprise_region_id(self, enterprise_id, region_id):
        region = RegionConfig.objects.get(region_id=region_id, enterprise_id=enterprise_id)
        region.delete()
        rke_cluster.delete_cluster(cluster_id=region.region_name)
        return region

    def del_by_region_id(self, region_id):
        region = RegionConfig.objects.get(region_id=region_id)
        region.delete()
        return region

    def get_team_used_region_by_enterprise_id(self, eid):
        trs = TenantRegionInfo.objects.filter(enterprise_id=eid)
        if trs:
            for tr in trs:
                region = RegionConfig.objects.filter(enterprise_id=eid, region_name=tr.region_name)
                if region:
                    return tr
        return None

    def get_regions_by_enterprise_id(self, eid, status=None):
        if status:
            return RegionConfig.objects.filter(enterprise_id=eid, status=status)
        return RegionConfig.objects.filter(enterprise_id=eid)

    def get_region_by_id(self, eid, region_id):
        return RegionConfig.objects.filter(enterprise_id=eid, region_id=region_id).first()

    def get_region_by_token(self, eid, token):
        return RegionConfig.objects.filter(enterprise_id=eid, token=token).first()

    def update_enterprise_region(self, eid, region_id, data):
        region = self.get_region_by_id(eid, region_id)
        if not region:
            raise RegionNotFound("region no found")
        region.region_alias = data.get("region_alias")
        region.url = data.get("url")
        region.wsurl = data.get("wsurl")
        region.httpdomain = data.get("httpdomain")
        region.tcpdomain = data.get("tcpdomain")
        if data.get("scope"):
            region.scope = data.get("scope")
        region.ssl_ca_cert = data.get("ssl_ca_cert")
        region.cert_file = data.get("cert_file")
        region.desc = data.get("desc")
        region.key_file = data.get("key_file")
        region.save()
        return region

    def get_tenants_by_region_name(self, region_name):
        tenant_region_info_list = TenantRegionInfo.objects.filter(region_name=region_name)
        tenant_id_list = [tenant_region_info.tenant_id for tenant_region_info in tenant_region_info_list]
        return tenant_id_list

    def get_service_status_count_by_region_name(self, region):
        from console.services.team_services import team_services
        region_services_status = {"running": 0}
        region_tenants, total = team_services.get_tenant_list_by_region(
            region.enterprise_id, region.region_id, page=1, page_size=9999)
        for region_tenant in region_tenants:
            region_services_status["running"] += region_tenant["running_app_num"]
        return region_services_status


region_repo = RegionRepo()

# -*- coding: utf8 -*-
"""
  Created on 18/1/16.
"""
from www.models import TenantServiceInfo, TenantServiceInfoDelete
from console.models.main import ServiceSourceInfo, ServiceRecycleBin, ServiceRelationRecycleBin


class TenantServiceInfoRepository(object):
    def get_services_by_service_ids(self, *service_ids):
        return TenantServiceInfo.objects.filter(service_id__in=service_ids)

    def get_service_by_tenant_and_id(self, tenant_id, service_id):
        services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_id=service_id)
        if services:
            return services[0]
        return None

    def get_service_by_service_id(self, service_id):
        services = TenantServiceInfo.objects.filter(service_id=service_id)
        if services:
            return services[0]
        return None

    def get_tenant_region_services(self, region, tenant_id):
        return TenantServiceInfo.objects.filter(service_region=region, tenant_id=tenant_id)

    def get_service_by_tenant_and_name(self, tenant_id, service_cname):
        services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_cname=service_cname)
        if services:
            return services[0]
        return None

    def get_service_by_region_tenant_and_name(self, tenant_id, service_cname, region):
        services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_cname=service_cname,
                                                    service_region=region)
        if services:
            return services[0]
        return None

    def get_services_by_service_group_id(self, service_group_id):
        return TenantServiceInfo.objects.filter(tenant_service_group_id=service_group_id)

    def get_services_by_raw_sql(self, raw_sql):
        return TenantServiceInfo.objects.raw(raw_sql)

    def get_service_by_tenant_and_alias(self, tenant_id, service_alias):
        services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias)
        if services:
            return services[0]
        return None

    def get_service_by_service_alias(self,service_alias):
        services = TenantServiceInfo.objects.filter(service_alias=service_alias)
        if services:
            return services[0]
        return None


class ServiceSourceRepository(object):
    def get_service_source(self, team_id, service_id):
        service_sources = ServiceSourceInfo.objects.filter(team_id=team_id, service_id=service_id)
        if service_sources:
            return service_sources[0]
        return None

    def create_service_source(self, **params):
        return ServiceSourceInfo.objects.create(**params)


class ServiceRecycleBinRepository(object):
    def get_team_trash_services(self, tenant_id):
        return ServiceRecycleBin.objects.filter(tenant_id=tenant_id)

    def create_trash_service(self, **params):
        return ServiceRecycleBin.objects.create(**params)

    def delete_trash_service_by_service_id(self, service_id):
        ServiceRecycleBin.objects.filter(service_id=service_id).delete()

    def delete_transh_service_by_service_ids(self, service_ids):
        ServiceRecycleBin.objects.filter(service_id__in=service_ids).delete()


class ServiceRelationRecycleBinRepository(object):
    def create_trash_service_relation(self, **params):
        ServiceRelationRecycleBin.objects.create(**params)

    def get_by_dep_service_id(self, dep_service_id):
        return ServiceRelationRecycleBin.objects.filter(dep_service_id=dep_service_id)

    def get_by_service_id(self, service_id):
        return ServiceRelationRecycleBin.objects.filter(service_id=service_id)

class TenantServiceDeleteRepository(object):
    def create_delete_service(self, **params):
        return TenantServiceInfoDelete.objects.create(**params)


service_repo = TenantServiceInfoRepository()
service_source_repo = ServiceSourceRepository()
recycle_bin_repo = ServiceRecycleBinRepository()
delete_service_repo = TenantServiceDeleteRepository()
relation_recycle_bin_repo = ServiceRelationRecycleBinRepository()

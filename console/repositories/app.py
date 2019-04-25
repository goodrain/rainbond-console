# -*- coding: utf8 -*-
"""
  Created on 18/1/16.
"""
from docker_image import reference

from console.models.main import ServiceRecycleBin
from console.models.main import ServiceRelationRecycleBin
from console.models.main import ServiceSourceInfo
from console.repositories.base import BaseConnection
from www.models import ServiceWebhooks
from www.models import TenantServiceInfo
from www.models import TenantServiceInfoDelete


class TenantServiceInfoRepository(object):
    def list_by_svc_share_uuids(self, group_id, dep_uuids):
        uuids = "'{}'".format("','".join(str(uuid)
                                         for uuid in dep_uuids))
        conn = BaseConnection()
        sql = """
            SELECT
                a.service_id,
                a.service_cname
            FROM
                tenant_service a,
                service_source b,
                service_group_relation c
            WHERE
                a.tenant_id = b.team_id
                AND a.service_id = b.service_id
                AND b.service_share_uuid IN ( {uuids} )
                AND a.service_id = c.service_id
                AND c.group_id = {group_id}
            """.format(group_id=group_id, uuids=uuids)
        result = conn.query(sql)
        return result

    def list_by_ids(self, service_ids):
        return TenantServiceInfo.objects.filter(service_id__in=service_ids)

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

    def get_service_by_region_and_tenant(self, region, tenant_id):
        return TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region)

    def get_service_by_region_tenant_and_name(self, tenant_id, service_cname, region):
        services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_cname=service_cname,
                                                    service_region=region)
        if services:
            return services[0]
        return None

    def get_services_by_service_group_id(self, service_group_id):
        return TenantServiceInfo.objects.filter(tenant_service_group_id=service_group_id)

    def get_services_by_raw_sql(self, raw_sql):
        print raw_sql
        return TenantServiceInfo.objects.raw(raw_sql)

    def get_service_by_tenant_and_alias(self, tenant_id, service_alias):
        services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias)
        if services:
            return services[0]
        return None

    def get_services_by_tenant_id(self, tenant_id):
        services = TenantServiceInfo.objects.filter(tenant_id=tenant_id).count()
        if services:
            return services
        return 0

    def get_service_by_service_alias(self, service_alias):
        services = TenantServiceInfo.objects.filter(service_alias=service_alias)
        if services:
            return services[0]
        return None

    def get_tenant_services(self, tenant_id):
        service_list = TenantServiceInfo.objects.filter(tenant_id=tenant_id).all()
        return service_list

    def get_service_by_key(self, tenant_id):
        ServiceSourceInfo.objects.filter()

    def change_service_image_tag(self, service, tag):
        """改变镜像标签"""
        ref = reference.Reference.parse(service.image)
        service.image = "{}:{}".format(ref['name'], tag)
        service.version = tag
        service.save()

    def update(self, tenant_id, service_id, **params):
        TenantServiceInfo.objects.filter(
            tenant_id=tenant_id, service_id=service_id).update(**params)


class ServiceSourceRepository(object):
    def get_service_source(self, team_id, service_id):
        service_sources = ServiceSourceInfo.objects.filter(team_id=team_id, service_id=service_id)
        if service_sources:
            return service_sources[0]
        return None

    def create_service_source(self, **params):
        return ServiceSourceInfo.objects.create(**params)

    def delete_service_source(self, team_id, service_id):
        ServiceSourceInfo.objects.filter(team_id=team_id, service_id=service_id).delete()

    def update_service_source(self, team_id, service_id, **data):
        ServiceSourceInfo.objects.filter(team_id=team_id, service_id=service_id).update(**data)

    def get_by_share_key(self, team_id, service_share_uuid):
        service_sources = ServiceSourceInfo.objects.filter(team_id=team_id, service_share_uuid=service_share_uuid)
        if service_sources:
            return service_sources[0]
        return None

    def get_service_sources_by_service_ids(self, service_ids):
        """使用service_ids获取服务源信息的查询集"""
        return ServiceSourceInfo.objects.filter(service_id__in=service_ids)


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


class TenantServiceWebhooks(object):
    def get_service_webhooks_by_service_id_and_type(self, service_id, webhooks_type):
        return ServiceWebhooks.objects.filter(service_id=service_id, webhooks_type=webhooks_type).first()

    def create_service_webhooks(self, service_id, webhooks_type):
        return ServiceWebhooks.objects.create(service_id=service_id, webhooks_type=webhooks_type)

    def get_or_create_service_webhook(self, service_id, deployment_way):
        """获取或创建service_webhook"""
        return self.get_service_webhooks_by_service_id_and_type(
            service_id, deployment_way) or self.create_service_webhooks(
            service_id, deployment_way)


service_repo = TenantServiceInfoRepository()
service_source_repo = ServiceSourceRepository()
recycle_bin_repo = ServiceRecycleBinRepository()
delete_service_repo = TenantServiceDeleteRepository()
relation_recycle_bin_repo = ServiceRelationRecycleBinRepository()
service_webhooks_repo = TenantServiceWebhooks()

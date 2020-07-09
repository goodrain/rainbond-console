# -*- coding: utf8 -*-
"""
  Created on 18/1/16.
"""
import logging
from docker_image import reference
from django.db import transaction

from console.exception.main import ServiceHandleException
from console.models.main import ServiceRecycleBin
from console.models.main import ServiceRelationRecycleBin
from console.models.main import ServiceSourceInfo
from console.models.main import RainbondCenterAppTag
from console.models.main import RainbondCenterAppTagsRelation
from console.models.main import AppMarket
from console.repositories.base import BaseConnection
from www.models.main import ServiceWebhooks
from www.models.main import TenantServiceInfo
from www.models.main import TenantServiceInfoDelete

logger = logging.getLogger('default')


class TenantServiceInfoRepository(object):
    def list_by_svc_share_uuids(self, group_id, dep_uuids):
        uuids = "'{}'".format("','".join(str(uuid) for uuid in dep_uuids))
        conn = BaseConnection()
        sql = """
            SELECT
                a.service_id,
                a.service_cname,
                b.service_share_uuid
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
            """.format(
            group_id=group_id, uuids=uuids)
        result = conn.query(sql)
        return result

    def list_by_ids(self, service_ids):
        return TenantServiceInfo.objects.filter(service_id__in=service_ids)

    def get_services_by_service_ids(self, service_ids):
        return TenantServiceInfo.objects.filter(service_id__in=service_ids)

    def get_services_in_multi_apps_with_app_info(self, group_ids):
        ids = "{0}".format(",".join(str(group_id) for group_id in group_ids))
        sql = """
        select svc.*, sg.id as group_id, sg.group_name, sg.region_name, sg.is_default, sg.note
        from tenant_service svc
            left join service_group_relation sgr on svc.service_id = sgr.service_id
            left join service_group sg on sg.id = sgr.group_id
        where sg.id in ({ids});
        """.format(ids=ids)

        conn = BaseConnection()
        return conn.query(sql)

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
        services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_cname=service_cname, service_region=region)
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
        TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_id=service_id).update(**params)

    def get_services_by_service_ids_and_group_key(self, group_key, service_ids):
        """使用service_ids 和 group_key 查找一组云市应用下的组件"""
        service_source = ServiceSourceInfo.objects.filter(group_key=group_key, service__in=service_ids)
        service_ids = service_source.values_list("service", flat=True)
        return TenantServiceInfo.objects.filter(service_id__in=service_ids)

    def del_by_sid(self, sid):
        TenantServiceInfo.objects.filter(service_id=sid).delete()

    def create(self, service_base):
        TenantServiceInfo(**service_base).save()


class ServiceSourceRepository(object):
    def get_service_source(self, team_id, service_id):
        service_sources = ServiceSourceInfo.objects.filter(team_id=team_id, service_id=service_id)
        if service_sources:
            return service_sources[0]
        return None

    def get_service_sources(self, team_id, service_ids):
        return ServiceSourceInfo.objects.filter(team_id=team_id, service_id__in=service_ids)

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
        """使用service_ids获取组件源信息的查询集"""
        return ServiceSourceInfo.objects.filter(service_id__in=service_ids)

    def get_service_sources_by_group_key(self, group_key):
        """使用group_key获取一组云市应用下的所有组件源信息的查询集"""
        return ServiceSourceInfo.objects.filter(group_key=group_key)


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
        return self.get_service_webhooks_by_service_id_and_type(service_id, deployment_way) or self.create_service_webhooks(
            service_id, deployment_way)


class AppTagRepository(object):
    def get_all_tag_list(self, enterprise_id):
        return RainbondCenterAppTag.objects.filter(enterprise_id=enterprise_id, is_deleted=False)

    def create_tag(self, enterprise_id, name):
        old_tag = RainbondCenterAppTag.objects.filter(enterprise_id=enterprise_id, name=name)
        if old_tag:
            return False
        return RainbondCenterAppTag.objects.create(enterprise_id=enterprise_id, name=name, is_deleted=False)

    def create_tags(self, enterprise_id, names):
        tag_list = []
        old_tag = RainbondCenterAppTag.objects.filter(name__in=names)
        if old_tag:
            return False
        for name in names:
            tag_list.append(RainbondCenterAppTag.objects.create(enterprise_id=enterprise_id, name=name, is_deleted=False))
        return RainbondCenterAppTag.objects.bulk_create(tag_list)

    def create_app_tag_relation(self, app, tag_id):
        old_relation = RainbondCenterAppTagsRelation.objects.filter(
            enterprise_id=app.enterprise_id, app_id=app.app_id, tag_id=tag_id)
        if old_relation:
            return True
        return RainbondCenterAppTagsRelation.objects.create(enterprise_id=app.enterprise_id, app_id=app.app_id, tag_id=tag_id)

    @transaction.atomic
    def create_app_tags_relation(self, app, tag_ids):
        relation_list = []
        RainbondCenterAppTagsRelation.objects.filter(enterprise_id=app.enterprise_id, app_id=app.app_id).delete()
        for tag_id in tag_ids:
            relation_list.append(
                RainbondCenterAppTagsRelation(enterprise_id=app.enterprise_id, app_id=app.app_id, tag_id=tag_id))
        return RainbondCenterAppTagsRelation.objects.bulk_create(relation_list)

    def delete_app_tag_relation(self, app, tag_id):
        return RainbondCenterAppTagsRelation.objects.filter(
            enterprise_id=app.enterprise_id, app_id=app.app_id, tag_id=tag_id).delete()

    def delete_tag(self, enterprise_id, tag_id):
        status = True
        try:
            app_tag = RainbondCenterAppTag.objects.get(ID=tag_id, enterprise_id=enterprise_id)
            app_tag_relation = RainbondCenterAppTagsRelation.objects.filter(tag_id=tag_id, enterprise_id=enterprise_id)
            app_tag.delete()
            app_tag_relation.delete()
        except Exception:
            status = False
        return status

    def delete_tags(self, tag_ids, enterprise_id):
        status = True
        try:
            app_tag = RainbondCenterAppTag.objects.filter(ID__in=tag_ids, enterprise_id=enterprise_id)
            app_tag_relation = RainbondCenterAppTagsRelation.objects.filter(tag_id__in=tag_ids, enterprise_id=enterprise_id)
            app_tag.delete()
            app_tag_relation.delete()
        except Exception:
            status = False
        return status

    def update_tag_name(self, enterprise_id, tag_id, name):
        status = True
        try:
            app_tag = RainbondCenterAppTag.objects.get(ID=tag_id, enterprise_id=enterprise_id)
            app_tag.name = name
            app_tag.save()
        except Exception:
            status = False
        return status

    def get_app_tags(self, enterprise_id, app_id):
        return RainbondCenterAppTagsRelation.objects.filter(enterprise_id=enterprise_id, app_id=app_id)

    def get_multi_apps_tags(self, eid, app_ids):
        if not app_ids:
            return None
        app_ids = ",".join("'{0}'".format(app_id) for app_id in app_ids)

        sql = """
        select
            atr.app_id, tag.*
        from
            console.rainbond_center_app_tag_relation atr
        left join console.rainbond_center_app_tag tag on
            atr.enterprise_id = tag.enterprise_id
            and atr.tag_id = tag.ID
        where
            atr.enterprise_id = '{eid}'
            and atr.app_id in ({app_ids});
        """.format(
            eid=eid, app_ids=app_ids)
        conn = BaseConnection()
        apps = conn.query(sql)
        return apps

    def get_app_with_tags(self, eid, app_id):
        sql = """
                select
                     tag.*
                from
                    console.rainbond_center_app_tag_relation atr
                left join console.rainbond_center_app_tag tag on
                    atr.enterprise_id = tag.enterprise_id
                    and atr.tag_id = tag.ID
                where
                    atr.enterprise_id = '{eid}'
                    and atr.app_id = '{app_id}';
                """.format(
            eid=eid, app_id=app_id)
        conn = BaseConnection()
        apps = conn.query(sql)
        return apps


class AppMarketRepository(object):
    def get_app_markets(self, enterprise_id):
        return AppMarket.objects.filter(enterprise_id=enterprise_id)

    def get_app_market(self, enterprise_id, market_id, raise_exception=False):
        market = AppMarket.objects.filter(enterprise_id=enterprise_id, ID=market_id).first()
        if raise_exception:
            if not market:
                raise ServiceHandleException(status_code=404, msg="no found app market", msg_show=u"应用商店不存在")
        return market

    def get_app_market_by_name(self, enterprise_id, name, raise_exception=False):
        market = AppMarket.objects.filter(enterprise_id=enterprise_id, name=name).first()
        if raise_exception:
            if not market:
                raise ServiceHandleException(status_code=404, msg="no found app market", msg_show=u"应用商店不存在")
        return market

    def get_app_market_by_domain_url(self, enterprise_id, domain, url, raise_exception=False):
        market = AppMarket.objects.filter(enterprise_id=enterprise_id, domain=domain, url=url).first()
        if raise_exception:
            if not market:
                raise ServiceHandleException(status_code=404, msg="no found app market", msg_show=u"应用商店不存在")
        return market

    def create_app_market(self, **kwargs):
        return AppMarket.objects.create(**kwargs)

    def update_app_market(self, app_market, data):
        app_market.update(**data)


service_repo = TenantServiceInfoRepository()
service_source_repo = ServiceSourceRepository()
recycle_bin_repo = ServiceRecycleBinRepository()
delete_service_repo = TenantServiceDeleteRepository()
relation_recycle_bin_repo = ServiceRelationRecycleBinRepository()
service_webhooks_repo = TenantServiceWebhooks()
app_tag_repo = AppTagRepository()
app_market_repo = AppMarketRepository()

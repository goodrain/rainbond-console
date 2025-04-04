# -*- coding: utf-8 -*-
from django.db.models import Q
from console.models.main import ServiceShareRecord, RainbondCenterPlugin
from www.models.main import ServiceGroupRelation, TenantServiceInfo, TenantServicesPort, TenantServiceRelation, \
    TenantServiceEnvVar, TenantServiceVolume, ServiceProbe
from www.models.plugin import ServicePluginConfigVar, TenantServicePluginRelation, TenantServicePluginAttr
from www.db.base import BaseConnection
from django.core.paginator import Paginator


class ShareRepo(object):
    def get_service_list_by_group_id(self, team, group_id):
        svc_relations = ServiceGroupRelation.objects.filter(tenant_id=team.tenant_id, group_id=group_id)
        if not svc_relations:
            return []
        svc_ids = [svc_rel.service_id for svc_rel in svc_relations]
        return TenantServiceInfo.objects.filter(service_id__in=svc_ids).exclude(service_source="third_party").exclude(
            service_source="vm_run")

    def get_port_list_by_service_ids(self, service_ids):
        port_list = TenantServicesPort.objects.filter(service_id__in=service_ids)
        if port_list:
            return port_list
        else:
            return []

    def get_relation_list_by_service_ids(self, service_ids):
        return TenantServiceRelation.objects.filter(service_id__in=service_ids)

    def get_env_list_by_service_ids(self, service_ids):
        env_list = TenantServiceEnvVar.objects.filter(service_id__in=service_ids)
        if env_list:
            return env_list
        else:
            return []

    def get_volume_list_by_service_ids(self, service_ids):
        volume_list = TenantServiceVolume.objects.filter(service_id__in=service_ids)
        if volume_list:
            return volume_list
        else:
            return []

    def get_plugins_attr_by_service_ids(self, service_ids):
        plugins_attr_list = TenantServicePluginAttr.objects.filter(service_id__in=service_ids).all()
        return plugins_attr_list or []

    def get_plugin_config_var_by_service_ids(self, service_ids):
        return ServicePluginConfigVar.objects.filter(service_id__in=service_ids)

    def get_plugins_relation_by_service_ids(self, service_ids):
        plugins_relation_list = TenantServicePluginRelation.objects.filter(service_id__in=service_ids).all()
        return plugins_relation_list or []

    def get_probe_list_by_service_ids(self, service_ids):
        probes = ServiceProbe.objects.filter(service_id__in=service_ids).all()
        return probes or []

    def get_last_shared_app_version_by_group_id(self, group_id, team_name=None, scope=None):
        if scope == "goodrain":
            return ServiceShareRecord.objects.filter(
                group_id=group_id, scope=scope, is_success=True).order_by("-create_time").first()
        else:
            return ServiceShareRecord.objects.filter(
                group_id=group_id, scope__in=["team", "enterprise"], team_name=team_name,
                is_success=True).order_by("-create_time").first()

    def get_last_app_versions_by_app_id(self, app_id):
        conn = BaseConnection()
        sql = """
            SELECT B.version, B.version_alias, B.dev_status, B.app_version_info as `describe`
            FROM (SELECT app_id, version, max(upgrade_time) as upgrade_time
                FROM rainbond_center_app_version
                WHERE is_complete=1
                GROUP BY app_id, version) A
            LEFT JOIN rainbond_center_app_version B
            ON A.app_id=B.app_id AND A.version=B.version AND A.upgrade_time=B.upgrade_time
            WHERE A.app_id = "{app_id}"
            """.format(app_id=app_id)
        result = conn.query(sql)
        return result

    def create_service(self, **kwargs):
        service = ServiceInfo(**kwargs)
        service.save()
        return service

    def create_tenant_service(self, **kwargs):
        tenant_service = TenantServiceInfo(**kwargs)
        tenant_service.save()
        return tenant_service

    def create_tenant_service_port(self, **kwargs):
        tenant_service_port = TenantServicesPort(**kwargs)
        tenant_service_port.save()
        return tenant_service_port

    def create_tenant_service_env_var(self, **kwargs):
        tenant_service_env_var = TenantServiceEnvVar(**kwargs)
        tenant_service_env_var.save()
        return tenant_service_env_var

    def create_tenant_service_volume(self, **kwargs):
        tenant_service_volume = TenantServiceVolume(**kwargs)
        tenant_service_volume.save()
        return tenant_service_volume

    def create_tenant_service_relation(self, **kwargs):
        tenant_service_relation = TenantServiceRelation(**kwargs)
        tenant_service_relation.save()
        return tenant_service_relation

    def create_tenant_service_plugin(self, **kwargs):
        tenant_service_plugin = TenantServicePluginAttr(**kwargs)
        tenant_service_plugin.save()
        return tenant_service_plugin

    def create_tenant_service_plugin_relation(self, **kwargs):
        tenant_service_plugin_relation = TenantServicePluginRelation(**kwargs)
        tenant_service_plugin_relation.save()
        return tenant_service_plugin_relation

    def delete_tenant_service_plugin_relation(self, service_id):
        TenantServicePluginRelation.objects.filter(service_id=service_id).delete()

    def create_service_share_record(self, **kwargs):
        service_share_record = ServiceShareRecord(**kwargs)
        service_share_record.save()
        return service_share_record

    def get_service_share_record(self, group_share_id):
        share_record = ServiceShareRecord.objects.filter(group_share_id=group_share_id)
        if not share_record:
            return None
        else:
            return share_record[0]

    def get_service_share_record_by_ID(self, ID, team_name):
        share_record = ServiceShareRecord.objects.filter(ID=ID, team_name=team_name)
        if not share_record:
            return None
        else:
            return share_record[0]

    def get_service_share_record_by_groupid(self, group_id):
        share_record = ServiceShareRecord.objects.filter(group_id=group_id)
        if not share_record:
            return None
        else:
            return share_record[0]

    def get_service_share_records_by_groupid(self, team_name, group_id, page=1, page_size=10):
        query = ServiceShareRecord.objects.filter(
            group_id=group_id, team_name=team_name, status__in=[0, 1, 2]).order_by("-create_time")
        ptr = Paginator(query, page_size)
        return ptr.count, ptr.page(page)

    def get_service_share_record_by_id(self, group_id, record_id):
        return ServiceShareRecord.objects.filter(group_id=group_id, ID=record_id).first()

    def get_multi_app_share_records(self, group_ids):
        return ServiceShareRecord.objects.filter(group_id__in=group_ids)

    def get_app_share_records_by_groupid(self, team_name, group_id):
        return ServiceShareRecord.objects.filter(group_id=group_id, team_name=team_name, status__in=[0, 1, 2])

    def get_app_share_record_count_by_groupid(self, group_id):
        return ServiceShareRecord.objects.filter(group_id=group_id, step=3).count()

    @staticmethod
    def count_by_app_id(app_id):
        return ServiceShareRecord.objects.filter(group_id=app_id).count()

    def get_share_plugin(self, plugin_id):
        plugins = RainbondCenterPlugin.objects.filter(plugin_id=plugin_id).order_by('-ID')
        return plugins.first() if plugins else None

    def check_app_by_eid(self, eid):
        """
        check if an app has been shared
        """
        conn = BaseConnection()
        sql = """
            SELECT
                a.team_name
            FROM
                service_share_record a,
                tenant_info b
            WHERE
                a.team_name = b.tenant_name
                AND b.enterprise_id = "{eid}"
                LIMIT 1""".format(eid=eid)
        result = conn.query(sql)
        return True if len(result) > 0 else False


share_repo = ShareRepo()

# -*- coding: utf-8 -*-
from console.models.main import RainbondCenterApp, ServiceShareRecord
from www.models import ServiceGroupRelation, TenantServiceInfo, TenantServicesPort, TenantServiceRelation, \
    TenantServiceEnvVar, TenantServiceVolume, TenantServicePluginRelation, TenantServicePluginAttr, ServiceInfo, \
    TenantServiceExtendMethod, ServiceProbe


class ShareRepo(object):
    def get_service_list_by_group_id(self, team, group_id):
        svc_relations = ServiceGroupRelation.objects.filter(tenant_id=team.tenant_id, group_id=group_id)
        if not svc_relations:
            return []
        svc_ids = [svc_rel.service_id for svc_rel in svc_relations]
        return TenantServiceInfo.objects.filter(service_id__in=svc_ids)

    def get_rainbond_cent_app_by_tenant_service_group_id(self, group_id):
        rainbond_cent_app = RainbondCenterApp.objects.filter(
            tenant_service_group_id=group_id).order_by("-create_time").first()
        return rainbond_cent_app

    def get_port_list_by_service_ids(self, service_ids):
        port_list = TenantServicesPort.objects.filter(service_id__in=service_ids)
        if port_list:
            return port_list
        else:
            return []

    def get_relation_list_by_service_ids(self, service_ids):
        relation_list = TenantServiceRelation.objects.filter(service_id__in=service_ids)
        if relation_list:
            return relation_list
        else:
            return []

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

    def get_service_extend_method_by_keys(self, service_keys):
        extend_method_list = TenantServiceExtendMethod.objects.filter(service_key__in=service_keys)
        if extend_method_list:
            return extend_method_list
        else:
            return []

    def get_plugins_attr_by_service_ids(self, service_ids):
        plugins_attr_list = TenantServicePluginAttr.objects.filter(service_id__in=service_ids).all()
        return plugins_attr_list or []

    def get_plugins_relation_by_service_ids(self, service_ids):
        plugins_relation_list = TenantServicePluginRelation.objects.filter(service_id__in=service_ids).all()
        return plugins_relation_list or []

    def get_probe_list_by_service_ids(self, service_ids):
        probes = ServiceProbe.objects.filter(service_id__in=service_ids).all()
        return probes or []

    def add_basic_app_info(self, **kwargs):
        app = RainbondCenterApp(**kwargs)
        app.save()
        return app

    def get_app_by_app_id(self, app_id):
        app = RainbondCenterApp.objects.filter(ID=app_id)
        if app:
            return app[0]
        else:
            return None

    def get_app_by_key(self, key):
        app = RainbondCenterApp.objects.filter(group_key=key)
        if app:
            return app[0]
        else:
            return None

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

    def create_tenant_service_extend_method(self, **kwargs):
        tenant_service_extend_method = TenantServiceExtendMethod(**kwargs).save()
        return tenant_service_extend_method

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


share_repo = ShareRepo()

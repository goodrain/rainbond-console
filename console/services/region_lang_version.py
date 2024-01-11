import datetime

from console.enum.app import GovernanceModeEnum
from console.models.main import AutoscalerRuleMetrics, ComponentK8sAttributes, K8sResource
from console.repositories.app_config import env_var_repo, volume_repo, port_repo, compile_env_repo
from console.repositories.autoscaler_repo import autoscaler_rules_repo
from console.repositories.group import group_repo, group_service_relation_repo
from console.repositories.k8s_attribute import k8s_attribute_repo
from console.repositories.k8s_resources import k8s_resources_repo
from console.repositories.region_app import region_app_repo
from console.services.app_actions import app_manage_service
from console.services.app_config import compile_env_service
from console.services.perm_services import role_kind_services
from console.services.team_services import team_services
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants, ServiceGroup, TenantServiceInfo, TenantRegionInfo, TenantServiceVolume, \
    TenantServiceEnvVar, TenantServicesPort, ServiceProbe

region_api = RegionInvokeApi()


class RegionLongVersion(object):
    def show_long_version(self, eid, region_id, language):
        return region_api.get_lang_version(eid, region_id, language)

    def create_long_version(self, eid, region_id, lang, version, event_id, file_name):
        data = {
            "lang": lang,
            "version": version,
            "event_id": event_id,
            "file_name": file_name,
        }
        region_api.create_lang_version(eid, region_id, data)

    def update_long_version(self, eid, region_id, lang, version):
        data = {
            "lang": lang,
            "version": version,
        }
        region_api.update_lang_version(eid, region_id, data)

    def delete_long_version(self, eid, region_id, lang, version):
        data = {
            "lang": lang,
            "version": version,
        }
        use_components = compile_env_repo.get_lang_version_in_use(lang, version)
        if use_components:
            return use_components
        region_api.delete_lang_version(eid, region_id, data)
        return ""


region_lang_version = RegionLongVersion()

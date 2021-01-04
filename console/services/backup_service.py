# -*- coding: utf8 -*-
"""
  Created on 2018/5/23.
"""
import json
import logging

from console.enum.component_enum import is_state

from console.exception.main import ServiceHandleException

from console.repositories.app import service_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import auth_repo
from console.repositories.app_config import compile_env_repo
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import domain_repo
from console.repositories.app_config import env_var_repo
from console.repositories.app_config import extend_repo
from console.repositories.app_config import mnt_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import tcp_domain
from console.repositories.app_config import volume_repo
from console.repositories.app_config import service_endpoints_repo
from console.repositories.backup_repo import backup_record_repo
from console.repositories.compose_repo import compose_relation_repo
from console.repositories.compose_repo import compose_repo
from console.repositories.group import group_repo
from console.repositories.group import group_service_relation_repo
from console.repositories.label_repo import service_label_repo
from console.repositories.plugin import app_plugin_relation_repo
from console.repositories.plugin import service_plugin_config_repo
from console.repositories.plugin.plugin import plugin_repo
from console.repositories.plugin.plugin_config import plugin_config_group_repo
from console.repositories.plugin.plugin_config import plugin_config_items_repo
from console.repositories.plugin.plugin_version import build_version_repo
from console.repositories.app_config_group import app_config_group_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.component_graph import component_graph_repo
from console.services.app_config.service_monitor import service_monitor_repo
from console.services.app_config_group import app_config_group_service
from console.services.config_service import EnterpriseConfigService
from console.services.exception import ErrBackupInProgress
from console.services.exception import ErrBackupRecordNotFound
from console.services.exception import ErrObjectStorageInfoNotFound
from console.services.group_service import group_service
from console.utils.timeutil import current_time_str
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import AuthCode
from www.utils.crypt import make_uuid
from console.services.app_config.volume_service import AppVolumeService

logger = logging.getLogger("default")
region_api = RegionInvokeApi()
volume_service = AppVolumeService()

KEY = "GOODRAINLOVE"


class GroupAppBackupService(object):
    def get_group_back_up_info(self, tenant, region, group_id):
        return backup_record_repo.get_group_backup_records(tenant.tenant_id, region, group_id).order_by("-ID")

    def get_all_group_back_up_info(self, tenant, region):
        return backup_record_repo.get_group_backup_records_by_team_id(tenant.tenant_id, region).order_by("-ID")

    def check_backup_condition(self, tenant, region, group_id):
        """
        检测备份条件，有状态组件备份应该
        """
        services = group_service.get_group_services(group_id)
        service_ids = [s.service_id for s in services]
        body = region_api.service_status(region, tenant.tenant_name, {
            "service_ids": service_ids,
            "enterprise_id": tenant.enterprise_id
        })
        status_list = body["list"]
        service_status_map = {status_map["service_id"]: status_map["status"] for status_map in status_list}
        # 处于运行中的有状态
        running_state_services = []
        for service in services:
            if is_state(service.extend_method):
                if service_status_map.get(service.service_id) not in ("closed", "undeploy"):
                    running_state_services.append(service.service_cname)

        return 200, running_state_services

    def check_backup_app_used_custom_volume(self, group_id):
        services = group_service.get_group_services(group_id)
        service_list = dict()
        for service in services:
            service_list[service.service_id] = service.service_cname

        service_ids = [service.service_id for service in services]
        volumes = volume_repo.list_custom_volumes(service_ids)

        use_custom_svc = []
        for volume in volumes:
            if service_list[volume.service_id] not in use_custom_svc:
                use_custom_svc.append(service_list[volume.service_id])

        return use_custom_svc

    def backup_group_apps(self, tenant, user, region, group_id, mode, note, force=False):
        s3_config = EnterpriseConfigService(tenant.enterprise_id).get_cloud_obj_storage_info()
        if mode == "full-online" and not s3_config:
            raise ErrObjectStorageInfoNotFound
        services = group_service.get_group_services(group_id)
        event_id = make_uuid()
        group_uuid = self.get_backup_group_uuid(group_id)
        total_memory, metadata = self.get_group_app_metadata(group_id, tenant)
        version = current_time_str("%Y%m%d%H%M%S")

        data = {
            "event_id": event_id,
            "group_id": group_uuid,
            "metadata": json.dumps(metadata),
            "service_ids": [s.service_id for s in services],
            "mode": mode,
            "version": version,
            "s3_config": s3_config,
            "force": force,
        }
        # 向数据中心发起备份任务
        try:
            body = region_api.backup_group_apps(region, tenant.tenant_name, data)
            bean = body["bean"]
            record_data = {
                "group_id": group_id,
                "event_id": event_id,
                "group_uuid": group_uuid,
                "version": version,
                "team_id": tenant.tenant_id,
                "region": region,
                "status": bean["status"],
                "note": note,
                "mode": mode,
                "backup_id": bean.get("backup_id", ""),
                "source_dir": bean.get("source_dir", ""),
                "source_type": bean.get("source_type", ""),
                "backup_size": bean.get("backup_size", 0),
                "user": user.nick_name,
                "total_memory": total_memory,
            }
            return backup_record_repo.create_backup_records(**record_data)
        except region_api.CallApiError as e:
            logger.exception(e)
            if e.status == 401:
                raise ServiceHandleException(msg="backup failed", msg_show="有状态组件必须停止方可进行备份")

    def get_backup_group_uuid(self, group_id):
        backup_record = backup_record_repo.get_record_by_group_id(group_id)
        if backup_record:
            return backup_record[0].group_uuid
        return make_uuid()

    def get_groupapp_backup_status_by_backup_id(self, tenant, region, backup_id):
        backup_record = backup_record_repo.get_record_by_backup_id(tenant.tenant_id, backup_id)
        if not backup_record:
            return 404, "不存在该备份记录", None
        if backup_record.status == "starting":
            body = region_api.get_backup_status_by_backup_id(region, tenant.tenant_name, backup_id)
            bean = body["bean"]
            backup_record.status = bean["status"]
            backup_record.source_dir = bean["source_dir"]
            backup_record.source_type = bean["source_type"]
            backup_record.backup_size = bean["backup_size"]
            backup_record.save()
        return 200, "success", backup_record

    def delete_group_backup_by_backup_id(self, tenant, region, backup_id):
        backup_record = backup_record_repo.get_record_by_backup_id(tenant.tenant_id, backup_id)
        if not backup_record:
            raise ErrBackupRecordNotFound
        if backup_record.status == "starting":
            return ErrBackupInProgress

        try:
            region_api.delete_backup_by_backup_id(region, tenant.tenant_name, backup_id)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e

        backup_record_repo.delete_record_by_backup_id(tenant.tenant_id, backup_id)

    def get_group_backup_status_by_group_id(self, tenant, region, group_id):
        backup_records = backup_record_repo.get_record_by_group_id(group_id)
        if not backup_records:
            return 404, "该组没有任何备份记录", None
        group_uuid = backup_records[0].group_uuid
        event_id_record_map = {record.event_id: record for record in backup_records}
        body = region_api.get_backup_status_by_group_id(region, tenant.tenant_name, group_uuid)
        res_list = body["list"]
        for data in res_list:
            backup_record = event_id_record_map.get(data["event_id"], None)
            if backup_record and backup_record.status == "starting":
                backup_record.status = data["status"]
                backup_record.source_dir = data["source_dir"]
                backup_record.backup_size = data["backup_size"]
                backup_record.save()
        backup_records = backup_record_repo.get_record_by_group_id(group_id)
        return 200, "success", backup_records

    def get_group_app_metadata(self, group_id, tenant):
        all_data = dict()
        compose_group_info = compose_repo.get_group_compose_by_group_id(group_id)
        compose_service_relation = None
        if compose_group_info:
            compose_service_relation = compose_relation_repo.get_compose_service_relation_by_compose_id(
                compose_group_info.compose_id)
        group_info = group_repo.get_group_by_id(group_id)

        service_group_relations = group_service_relation_repo.get_services_by_group(group_id)
        service_ids = [sgr.service_id for sgr in service_group_relations]
        services = service_repo.get_services_by_service_ids(service_ids)

        all_data["compose_group_info"] = compose_group_info.to_dict() if compose_group_info else None
        all_data["compose_service_relation"] = [relation.to_dict()
                                                for relation in compose_service_relation] if compose_service_relation else None
        all_data["group_info"] = group_info.to_dict()
        all_data["service_group_relation"] = [sgr.to_dict() for sgr in service_group_relations]
        apps = []
        total_memory = 0
        plugin_ids = []
        for service in services:
            if service.create_status != "complete":
                continue
            if service.service_source != "third_party":
                total_memory += service.min_memory * service.min_node
            app_info, pids = self.get_service_details(tenant, service)
            plugin_ids.extend(pids)
            apps.append(app_info)
        all_data["apps"] = apps

        # plugin
        plugins = []
        plugin_build_versions = []
        plugin_config_groups = []
        plugin_config_items = []
        for plugin_id in plugin_ids:
            plugin = plugin_repo.get_plugin_by_plugin_id(tenant.tenant_id, plugin_id)
            if plugin is None:
                continue
            plugins.append(plugin.to_dict())
            bv = build_version_repo.get_last_ok_one(plugin_id, tenant.tenant_id)
            if bv is None:
                continue
            plugin_build_versions.append(bv.to_dict())
            pcgs = plugin_config_group_repo.list_by_plugin_id(plugin_id)
            if pcgs:
                plugin_config_groups.extend([p.to_dict() for p in pcgs])
            pcis = plugin_config_items_repo.list_by_plugin_id(plugin_id)
            if pcis:
                plugin_config_items.extend([p.to_dict() for p in pcis])
        all_data["plugin_info"] = {}
        all_data["plugin_info"]["plugins"] = plugins
        all_data["plugin_info"]["plugin_build_versions"] = plugin_build_versions
        all_data["plugin_info"]["plugin_config_groups"] = plugin_config_groups
        all_data["plugin_info"]["plugin_config_items"] = plugin_config_items

        # application config group
        config_group_infos = app_config_group_repo.get_config_group_in_use(tenant.region, group_id)
        app_config_groups = []
        for cgroup_info in config_group_infos:
            config_group = app_config_group_service.get_config_group(tenant.region, group_id, cgroup_info["config_group_name"])
            app_config_groups.append(config_group)
        all_data["app_config_group_info"] = app_config_groups
        return total_memory, all_data

    def get_service_details(self, tenant, service):
        service_base = service.to_dict()
        service_labels = service_label_repo.get_service_labels(service.service_id)
        service_domains = domain_repo.get_service_domains(service.service_id)
        service_tcpdomains = tcp_domain.get_service_tcpdomains(service.service_id)
        service_probes = probe_repo.get_service_probe(service.service_id)
        service_source = service_source_repo.get_service_source(tenant.tenant_id, service.service_id)
        service_auths = auth_repo.get_service_auth(service.service_id)
        service_env_vars = env_var_repo.get_service_env(tenant.tenant_id, service.service_id)
        service_compile_env = compile_env_repo.get_service_compile_env(service.service_id)
        service_extend_method = extend_repo.get_extend_method_by_service(service)
        service_mnts = mnt_repo.get_service_mnts(tenant.tenant_id, service.service_id)
        service_volumes = volume_repo.get_service_volumes_with_config_file(service.service_id)
        service_config_file = volume_repo.get_service_config_files(service.service_id)
        service_ports = port_repo.get_service_ports(tenant.tenant_id, service.service_id)
        service_relation = dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id)
        service_monitors = service_monitor_repo.get_component_service_monitors(tenant.tenant_id, service.service_id)
        component_graphs = component_graph_repo.list(service.service_id)
        # plugin
        service_plugin_relation = app_plugin_relation_repo.get_service_plugin_relation_by_service_id(service.service_id)
        service_plugin_config = service_plugin_config_repo.get_service_plugin_all_config(service.service_id)
        # third_party_service
        third_party_service_endpoints = service_endpoints_repo.get_service_endpoints_by_service_id(service.service_id)
        if service.service_source == "third_party":
            if not third_party_service_endpoints:
                raise ServiceHandleException(msg="third party service endpoints can't be null", msg_show="第三方组件实例不可为空")
        app_info = {
            "service_base": service_base,
            "service_labels": [label.to_dict() for label in service_labels],
            "service_domains": [domain.to_dict() for domain in service_domains],
            "service_tcpdomains": [tcpdomain.to_dict() for tcpdomain in service_tcpdomains],
            "service_probes": [probe.to_dict() for probe in service_probes],
            "service_source": service_source.to_dict() if service_source else None,
            "service_auths": [auth.to_dict() for auth in service_auths],
            "service_env_vars": [env_var.to_dict() for env_var in service_env_vars],
            "service_compile_env": service_compile_env.to_dict() if service_compile_env else None,
            "service_extend_method": service_extend_method.to_dict() if service_extend_method else None,
            "service_mnts": [mnt.to_dict() for mnt in service_mnts],
            "service_plugin_relation": [plugin_relation.to_dict() for plugin_relation in service_plugin_relation],
            "service_plugin_config": [config.to_dict() for config in service_plugin_config],
            "service_relation": [relation.to_dict() for relation in service_relation],
            "service_volumes": [volume.to_dict() for volume in service_volumes],
            "service_config_file": [config_file.to_dict() for config_file in service_config_file],
            "service_ports": [port.to_dict() for port in service_ports],
            "third_party_service_endpoints": [endpoint.to_dict() for endpoint in third_party_service_endpoints],
            "service_monitors": [monitor.to_dict() for monitor in service_monitors],
            "component_graphs": [graph.to_dict() for graph in component_graphs]
        }
        plugin_ids = [pr.plugin_id for pr in service_plugin_relation]

        return app_info, plugin_ids

    def export_group_backup(self, tenant, backup_id):
        backup_record = backup_record_repo.get_record_by_backup_id(tenant.tenant_id, backup_id)
        if not backup_record:
            return 404, "不存在该备份记录", None
        if backup_record.mode == "full-offline":
            return 409, "本地备份数据暂不支持导出", None
        if backup_record.status == "starting":
            return 409, "正在备份中，请稍后重试", None

        data_str = AuthCode.encode(json.dumps(backup_record.to_dict()), KEY)
        return 200, "success", data_str

    def import_group_backup(self, tenant, region, group_id, upload_file):
        group = group_repo.get_group_by_id(group_id)
        if not group:
            return 404, "需要导入的组不存在", None
        services = group_service.get_group_services(group_id)
        if services:
            return 409, "请确保需要导入的组中不存在组件", None
        content = upload_file.read().strip()
        data = json.loads(AuthCode.decode(content, KEY))
        current_backup = backup_record_repo.get_record_by_group_id_and_backup_id(group_id, data["backup_id"])
        if current_backup:
            return 412, "当前团队已导入过该备份", None
        event_id = make_uuid()
        group_uuid = make_uuid()
        params = {
            "event_id": event_id,
            "group_id": group_uuid,
            "status": data["status"],
            "version": data["version"],
            "source_dir": data["source_dir"],
            "source_type": data["source_type"],
            "backup_mode": data["mode"],
            "backup_size": data["backup_size"]
        }
        body = region_api.copy_backup_data(region, tenant.tenant_name, params)

        bean = body["bean"]
        record_data = {
            "group_id": group.ID,
            "event_id": event_id,
            "group_uuid": group_uuid,
            "version": data["version"],
            "team_id": tenant.tenant_id,
            "region": region,
            "status": bean["status"],
            "note": data["note"],
            "mode": data["mode"],
            "backup_id": bean["backup_id"],
            "source_dir": data["source_dir"],
            "source_type": data["source_type"],
            "backup_size": data["backup_size"],
            "user": data["user"],
            "total_memory": data["total_memory"],
            "backup_server_info": data["backup_server_info"]
        }

        new_backup_record = backup_record_repo.create_backup_records(**record_data)
        return 200, "success", new_backup_record

    def update_backup_record_group_id(self, group_id, new_group_id):
        """修改Groupid"""
        backup_record_repo.get_record_by_group_id(group_id).update(group_id=new_group_id)


groupapp_backup_service = GroupAppBackupService()

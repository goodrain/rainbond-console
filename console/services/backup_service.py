# -*- coding: utf8 -*-
"""
  Created on 2018/5/23.
"""
from cadmin.models import ConsoleSysConfig
from console.repositories.backup_repo import backup_record_repo
from console.services.group_service import group_service
from www.apiclient.regionapi import RegionInvokeApi
from console.appstore.appstore import app_store
from www.utils.crypt import make_uuid
from console.utils.timeutil import current_time_str
from console.repositories.compose_repo import compose_repo, compose_relation_repo
from console.repositories.group import group_repo, group_service_relation_repo
from console.repositories.label_repo import service_label_repo
from console.repositories.app_config import domain_repo, auth_repo, env_var_repo, compile_env_repo, extend_repo, \
    image_service_relation_repo, mnt_repo, dep_relation_repo, volume_repo, port_repo, tcp_domain
from console.repositories.event_repo import event_repo
from console.repositories.perm_repo import service_perm_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.app import service_source_repo
from console.repositories.plugin import app_plugin_relation_repo, service_plugin_config_repo
from console.repositories.app_config import service_endpoints_repo


import json
import logging
from console.repositories.app import service_repo
from www.utils.crypt import AuthCode

logger = logging.getLogger("default")
region_api = RegionInvokeApi()

KEY = "GOODRAINLOVE"


class GroupAppBackupService(object):
    def get_group_back_up_info(self, tenant, region, group_id):
        return backup_record_repo.get_group_backup_records(tenant.tenant_id, region, group_id).order_by("-ID")

    def get_all_group_back_up_info(self, tenant, region):
        return backup_record_repo.get_group_backup_records_by_team_id(tenant.tenant_id, region).order_by("-ID")

    def check_backup_condition(self, tenant, region, group_id):
        """
        检测备份条件，有状态应用备份应该
        """
        services = group_service.get_group_services(group_id)
        service_ids = [s.service_id for s in services]
        body = region_api.service_status(region, tenant.tenant_name,
                                         {"service_ids": service_ids, "enterprise_id": tenant.enterprise_id})
        status_list = body["list"]
        service_status_map = {status_map["service_id"]: status_map["status"] for status_map in status_list}
        # 处于运行中的有状态
        running_state_services = []
        for service in services:
            if service.extend_method == "state":
                if service_status_map.get(service.service_id) not in ("closed", "undeploy"):
                    running_state_services.append(service.service_cname)

        return 200, running_state_services

    def is_hub_and_sftp_info_configed(self):
        slug_config = ConsoleSysConfig.objects.filter(key='APPSTORE_SLUG_PATH')
        image_config = ConsoleSysConfig.objects.filter(key='APPSTORE_IMAGE_HUB')
        if not slug_config or not image_config:
            return False
        return True

    def back_up_group_apps(self, tenant, user, region, group_id, mode, note):
        service_slug = app_store.get_slug_connection_info("enterprise", tenant.tenant_name)
        service_image = app_store.get_image_connection_info("enterprise", tenant.tenant_name)
        if mode == "full-online":
            if not self.is_hub_and_sftp_info_configed():
                return 412, "未配置sftp和hub仓库信息", None
        services = group_service.get_group_services(group_id)
        event_id = make_uuid()
        group_uuid = self.get_backup_group_uuid(group_id)
        total_memory, metadata = self.get_group_app_metadata(group_id, tenant)
        version = current_time_str("%Y%m%d%H%M%S")
        data = {
            "event_id": event_id,
            "group_id": group_uuid,
            "metadata": metadata,
            "service_ids": [s.service_id for s in services],
            "mode": mode,
            "version": version,
            "slug_info": service_slug,
            "image_info": service_image
        }
        # 向数据中心发起备份任务
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
            "backup_server_info": json.dumps({"slug_info": service_slug, "image_info": service_image})
        }
        backup_record = backup_record_repo.create_backup_records(**record_data)
        return 200, "success", backup_record

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
            return 404, "不存在该备份记录"
        if backup_record.status == "starting":
            return 409, "该备份正在进行中"
        if backup_record.status == "success":
            return 409, "该备份不可删除"
        region_api.delete_backup_by_backup_id(region, tenant.tenant_name, backup_id)
        backup_record_repo.delete_record_by_backup_id(tenant.tenant_id, backup_id)
        return 200, "success"

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
        services = service_repo.get_services_by_service_ids(*service_ids)
        all_data["compose_group_info"] = compose_group_info.to_dict() if compose_group_info else None
        all_data["compose_service_relation"] = [relation.to_dict() for relation in
                                                compose_service_relation] if compose_service_relation else None
        all_data["group_info"] = group_info.to_dict()
        all_data["service_group_relation"] = [sgr.to_dict() for sgr in service_group_relations]
        apps = []
        total_memory = 0
        for service in services:
            if service.service_source == "third_party" or service.create_status != "complete":
                continue
            total_memory += service.min_memory * service.min_node
            app_info = self.get_service_details(tenant, service)
            apps.append(app_info)
        all_data["apps"] = apps
        return total_memory, json.dumps(all_data)

    def get_service_details(self, tenant, service):
        service_base = service.to_dict()
        service_labels = service_label_repo.get_service_labels(service.service_id)
        service_domains = domain_repo.get_service_domains(service.service_id)
        service_tcpdomains = tcp_domain.get_service_tcpdomains(service.service_id)
        service_events = event_repo.get_specified_num_events(tenant.tenant_id, service.service_id)
        service_perms = service_perm_repo.get_service_perms_by_service_pk(service.ID)
        service_probes = probe_repo.get_service_probe(service.service_id)
        service_source = service_source_repo.get_service_source(tenant.tenant_id, service.service_id)
        service_auths = auth_repo.get_service_auth(service.service_id)
        service_env_vars = env_var_repo.get_service_env(tenant.tenant_id, service.service_id)
        service_compile_env = compile_env_repo.get_service_compile_env(service.service_id)
        service_extend_method = extend_repo.get_extend_method_by_service(service)
        image_service_relation = image_service_relation_repo.get_image_service_relation(tenant.tenant_id,
                                                                                        service.service_id)
        service_mnts = mnt_repo.get_service_mnts(tenant.tenant_id, service.service_id)
        service_plugin_relation = app_plugin_relation_repo.get_service_plugin_relation_by_service_id(service.service_id)
        service_plugin_config = service_plugin_config_repo.get_service_plugin_all_config(service.service_id)
        service_relation = dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id)
        service_volumes = volume_repo.get_service_volumes(service.service_id)
        service_config_file = volume_repo.get_service_config_files(service.service_id)
        service_ports = port_repo.get_service_ports(tenant.tenant_id, service.service_id)

        app_info = {
            "service_base": service_base,
            "service_labels": [label.to_dict() for label in service_labels],
            "service_domains": [domain.to_dict() for domain in service_domains],
            "service_tcpdomains": [tcpdomain.to_dict() for tcpdomain in service_tcpdomains],
            "service_events": [event.to_dict() for event in service_events],
            "service_perms": [perm.to_dict() for perm in service_perms],
            "service_probes": [probe.to_dict() for probe in service_probes],
            "service_source": service_source.to_dict() if service_source else None,
            "service_auths": [auth.to_dict() for auth in service_auths],
            "service_env_vars": [env_var.to_dict() for env_var in service_env_vars],
            "service_compile_env": service_compile_env.to_dict() if service_compile_env else None,
            "service_extend_method": service_extend_method.to_dict() if service_extend_method else None,
            "image_service_relation": image_service_relation.to_dict() if image_service_relation else None,
            "service_mnts": [mnt.to_dict() for mnt in service_mnts],
            "service_plugin_relation": [plugin_relation.to_dict() for plugin_relation in service_plugin_relation],
            "service_plugin_config": [config.to_dict() for config in service_plugin_config],
            "service_relation": [relation.to_dict() for relation in service_relation],
            "service_volumes": [volume.to_dict() for volume in service_volumes],
            "service_config_file": [config_file.to_dict() for config_file in service_config_file],
            "service_ports": [port.to_dict() for port in service_ports]
        }
        return app_info

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
            return 409, "请确保需要导入的组中不存在应用", None
        content = upload_file.read().strip()
        data = json.loads(AuthCode.decode(content, KEY))
        current_backup = backup_record_repo.get_record_by_group_id_and_backup_id(group_id, data["backup_id"])
        if current_backup:
            return 412,"当前团队已导入过该备份", None
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

# -*- coding: utf8 -*-
"""
  Created on 2018/5/23.
"""
from console.repositories.backup_repo import backup_record_repo
from console.services.group_service import group_service
from www.apiclient.regionapi import RegionInvokeApi
from console.appstore.appstore import app_store
from www.utils.crypt import make_uuid
from console.utils.timeutil import current_time_str
import json
import logging

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class GroupAppBackupService(object):
    def get_group_back_up_info(self, tenant, region, group_id):
        return backup_record_repo.get_group_backup_records(tenant.tenant_id, region, group_id).order_by("-ID")

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
                if service_status_map.get(service.service_id) not in ("running", "undeploy"):
                    running_state_services.append(service.service_cname)

        return 200, running_state_services

    def back_up_group_apps(self, tenant, user, region, group_id, mode, note):
        service_slug = app_store.get_slug_connection_info("enterprise", tenant.tenant_name)
        service_image = app_store.get_image_connection_info("enterprise", tenant.tenant_name)

        services = group_service.get_group_services(group_id)
        event_id = make_uuid()
        group_uuid = self.get_backup_group_uuid(group_id)
        metadata = self.get_group_app_metadata(group_id, tenant, region)
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
            "backup_id":bean.get("backup_id", ""),
            "source_dir": bean.get("source_dir", ""),
            "backup_size": bean.get("backup_size", 0),
            "user": user.nick_name,
            "backup_server_info": json.dumps({"slug_info": service_slug, "image_info": service_image})
        }
        backup_record = backup_record_repo.create_backup_records(**record_data)
        return backup_record

    def get_backup_group_uuid(self, group_id):
        backup_record = backup_record_repo.get_record_by_group_id(group_id)
        if backup_record:
            return backup_record[0].group_uuid
        return make_uuid()

    def get_groupapp_backup_status_by_backup_id(self, tenant, region, backup_id):
        backup_record = backup_record_repo.get_record_by_backup_id(backup_id)
        if not backup_record:
            return 404, "不存在该备份记录", None
        if backup_record.status == "starting":
            body = region_api.get_backup_status_by_backup_id(region, tenant.tenant_name, backup_id)
            bean = body["bean"]
            backup_record.status = bean["status"]
            backup_record.source_dir = bean["source_dir"]
            backup_record.backup_size = bean["backup_size"]
            backup_record.save()
        return 200, "success", backup_record

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


    def get_group_app_metadata(self, group_id, tenant, region):
        # TODO 获取应用的所有需要备份的元数据信息
        return "{}"


groupapp_backup_service = GroupAppBackupService()

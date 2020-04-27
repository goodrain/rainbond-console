# -*- coding: utf8 -*-
import logging

from django.db import transaction

from console.exception.main import ServiceHandleException
from console.repositories.group import group_repo
from console.repositories.service_repo import service_repo
from console.repositories.deploy_repo import deploy_repo
from console.services.groupapp_recovery.groupapps_migrate import migrate_service
from console.services.service_services import base_service
from console.services.team_services import team_services
from console.services.backup_service import groupapp_backup_service
from console.services.app import app_service
from console.services.app_actions import app_manage_service
from console.services.app_config import label_service
from console.services.app_config import port_service

from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


class GroupAppCopyService(object):
    @transaction.atomic()
    def copy_group_services(self, user, old_team, tar_team, tar_region_name, tar_group, group_id, choose_services):
        changes = {}
        service_ids = []
        if choose_services:
            for choose_service in choose_services:
                service_ids.append(choose_service["service_id"])
                changes.update({choose_service["service_id"]: choose_service.get("change")})
        services_metadata, change_services_map = self.get_modify_group_metadata(
            old_team, tar_team, group_id, service_ids, changes)
        groupapp_copy_service.save_new_group_app(
            user, tar_team, tar_region_name, tar_group.ID, services_metadata, change_services_map)
        groupapp_copy_service.build_services(user, tar_team, tar_region_name, tar_group.ID, change_services_map)

    def get_group_services_with_build_source(self, tenant, region_name, group_id):
        group_services = base_service.get_group_services_list(tenant.tenant_id, region_name, group_id)
        if not group_services:
            return []
        service_ids = [group_service.get("service_id") for group_service in group_services]
        services = service_repo.get_service_by_service_ids(service_ids=service_ids)
        for group_service in group_services:
            for service in services:
                if group_service["service_id"] == service.service_id:
                    group_service["build_source"] = base_service.get_build_info(tenant, service)
                    group_service["build_source"]["service_id"] = service.service_id
        return group_services

    def check_and_get_team_group(self, user, team_name, region_name, group_id):
        team = team_services.check_and_get_user_team_by_name_and_region(user.user_id, team_name, region_name)
        if not team:
            raise ServiceHandleException(
                msg="no found team or team not join this region",
                msg_show="目标团队不存在，或团队为加入该数据中心", status_code=404)
        group = group_repo.get_group_by_id(group_id)
        if not group:
            raise ServiceHandleException(msg="no found group app", msg_show="目标应用不存在", status_code=404)
        if group.tenant_id != team.tenant_id:
            raise ServiceHandleException(
                msg="group app and team relation no found", msg_show="目标应用不属于目标团队", status_code=400)
        return team, group

    def get_modify_group_metadata(self, old_team, tar_team, group_id, service_ids, changes):
        total_memory, services_metadata = groupapp_backup_service.get_group_app_metadata(group_id, old_team)
        group_all_service_ids = [service["service_id"] for service in services_metadata["service_group_relation"]]
        if not service_ids:
            service_ids = group_all_service_ids
        remove_service_ids = list(set(service_ids) ^ set(group_all_service_ids))
        services_metadata = self.pop_remove_services_metadata(
            old_team, tar_team, services_metadata, remove_service_ids, service_ids)
        services_metadata = self.change_services_metadata_info(services_metadata, changes)
        change_services_map = self.change_services_map(service_ids)
        return services_metadata, change_services_map

    def pop_remove_services_metadata(self, old_team, tar_team, metadata, remove_service_ids, service_ids):
        if not remove_service_ids:
            return metadata
        new_metadata = {}
        new_metadata["compose_group_info"] = metadata["compose_group_info"]
        new_metadata["group_info"] = metadata["group_info"]
        new_metadata["plugin_info"] = metadata["plugin_info"]
        new_metadata["service_group_relation"] = []
        new_metadata["apps"] = []
        new_metadata["compose_service_relation"] = []

        for relation_service in metadata["service_group_relation"]:
            if relation_service["service_id"] not in remove_service_ids:
                new_metadata["service_group_relation"].append(relation_service)
        for service in metadata["apps"]:
            if service["service_base"]["service_id"] not in remove_service_ids:
                new_relation = []
                for dep_service_info in service["service_relation"]:
                    if old_team.tenant_id == tar_team.tenant_id:
                        new_relation.append(dep_service_info)
                    else:
                        if dep_service_info["dep_service_id"] in service_ids and \
                                dep_service_info["dep_service_id"] not in remove_service_ids:
                            new_relation.append(dep_service_info)
                service["service_relation"] = new_relation
                new_metadata["apps"].append(service)
        if metadata["compose_service_relation"] is not None:
            for service in metadata["compose_service_relation"]:
                if service["service_id"] not in remove_service_ids:
                    new_metadata["compose_service_relation"].append(service)
        if not new_metadata["compose_service_relation"]:
            new_metadata["compose_service_relation"] = None
        return new_metadata

    def change_services_metadata_info(self, metadata, changes):
        if not changes:
            return metadata
        for service in metadata["apps"]:
            if changes.get(service["service_base"]["service_id"]):
                # 更新构建源配置
                if changes[service["service_base"]["service_id"]].get("build_source"):
                    version = changes[service["service_base"]["service_id"]]["build_source"].get("version")
                    if version:
                        if service["service_base"]["service_source"] == "source_code":
                            service["service_base"]["code_version"] = version
                        elif service["service_base"]["service_source"] == "docker_image":
                            service["service_base"]["image"] = service["service_base"]["image"].split(":")[0] + ":" + version
                            service["service_base"]["version"] = version
        return metadata

    def save_new_group_app(self, user, tar_team, region_name, group_id, metadata, changed_service_map):
        migrate_service.save_data(tar_team, region_name, user, changed_service_map, metadata, group_id)

    def change_services_map(self, service_ids):
        change_services = {}
        for service_id in service_ids:
            new_service_id = make_uuid()
            change_services.update({
                service_id: {
                    "ServiceID": new_service_id,
                    "ServiceAlias": app_service.create_service_alias(new_service_id)
                }
            })
        return change_services

    def is_need_to_add_default_probe(self, service):
        if service.service_source != "source_code":
            return True
        else:
            ports = port_service.get_service_ports(service)
            for p in ports:
                if p.container_port == 5000:
                    return False
            return True

    def build_services(self, user, tenant, region_name, group_id, change_services_map):
        group_services = base_service.get_group_services_list(tenant.tenant_id, region_name, group_id)
        change_service_ids = [change_service["ServiceID"] for change_service in change_services_map.values()]
        if not group_services:
            return []
        service_ids = [group_service.get("service_id") for group_service in group_services]
        services = service_repo.get_service_by_service_ids(service_ids=service_ids)
        result = []
        for service in services:
            if service.service_id in change_service_ids:
                if service.service_source == "third_party":
                    # 数据中心连接创建第三方组件
                    new_service = app_service.create_third_party_service(tenant, service, user.nick_name)
                else:
                    # 数据中心创建组件
                    new_service = app_service.create_region_service(tenant, service, user.nick_name)

                service = new_service
                # 为组件添加默认探针
                if self.is_need_to_add_default_probe(service):
                    code, msg, probe = app_service.add_service_default_porbe(tenant, service)
                    logger.debug("add default probe; code: {}; msg: {}".format(code, msg))
                # 添加组件有无状态标签
                label_service.update_service_state_label(tenant, service)
                # 部署组件
                app_manage_service.deploy(tenant, service, user, group_version=None)

                # 添加组件部署关系
                deploy_repo.create_deploy_relation_by_service_id(service_id=service.service_id)
                result.push(service)
        return result


groupapp_copy_service = GroupAppCopyService()

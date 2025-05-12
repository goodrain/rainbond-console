# -*- coding: utf8 -*-
import logging
import time

from console.exception.main import ServiceHandleException
from console.repositories.app import TenantServiceInfoRepository
from console.repositories.deploy_repo import deploy_repo
from console.repositories.group import group_repo
from console.repositories.plugin import app_plugin_relation_repo, plugin_repo
from console.repositories.service_repo import service_repo
from console.services.app import app_service, package_upload_service
from console.services.app_actions import app_manage_service
from console.services.app_config import port_service
from console.services.backup_service import groupapp_backup_service
from console.services.groupapp_recovery.groupapps_migrate import \
    migrate_service
from console.services.operation_log import operation_log_service
from console.services.plugin import app_plugin_service, plugin_service
from console.services.service_services import base_service
from console.services.team_services import team_services
from django.db import transaction
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class GroupAppCopyService(object):
    def generate_comment(self, src_app, src_region_name, src_tenant_name, target_app, tar_region_name, tar_team_name, services):
        source_app_name = operation_log_service.process_app_name(src_app.app_name, src_region_name, src_tenant_name,
                                                                 src_app.app_id)
        target_app_name = operation_log_service.process_app_name(target_app.app_name, tar_region_name, tar_team_name,
                                                                 target_app.app_id)
        component_names = []
        idx = 0
        for svc in services:
            if idx >= 2:
                break
            component_names.append(
                operation_log_service.process_component_name(svc.service_cname, tar_region_name, tar_team_name,
                                                             svc.service_alias))
            idx += 1
        component_names = ",".join(component_names)
        if idx >= 2:
            component_names += "等"
        return "将{}组件从应用{}复制到应用{}".format(component_names, source_app_name, target_app_name)


    @transaction.atomic()
    def copy_group_services(self, user, old_team, old_region_name, tar_team, tar_region_name, tar_group, group_id,
                            choose_services):
        changes = {}
        service_ids = []
        if choose_services:
            for choose_service in choose_services:
                service_ids.append(choose_service["service_id"])
                changes.update({choose_service["service_id"]: choose_service.get("change")})
        services_metadata, change_services_map = self.get_modify_group_metadata(old_team, old_region_name, tar_team,
                                                                                tar_region_name, group_id, service_ids, changes)
        groupapp_copy_service.save_new_group_app(user, tar_team, tar_region_name, tar_group.ID, services_metadata,
                                                 change_services_map, old_team == tar_team, old_region_name == tar_region_name)
        return groupapp_copy_service.build_services(user, tar_team, tar_region_name, tar_group.ID, change_services_map)

    def get_group_services_with_build_source(self, tenant, region_name, group_id):
        group_services = base_service.get_group_services_list(tenant.tenant_id, region_name, group_id)
        if not group_services:
            return []
        service_ids = [group_service.get("service_id") for group_service in group_services]
        build_infos = base_service.get_build_infos(tenant, service_ids)
        gl_group_services = []
        for group_service in group_services:
            group_service["app_name"] = group_service.get("group_name")
            if build_infos.get(group_service["service_id"], None):
                group_service["build_source"] = build_infos[group_service["service_id"]]
                group_service["build_source"]["service_id"] = group_service["service_id"]
            if group_service["build_source"]["service_source"] == "docker_image":
                if group_service["build_source"]["image"]:
                    gl_group_services.append(group_service)
            else:
                gl_group_services.append(group_service)
        return gl_group_services

    def check_and_get_team_group(self, user, team_name, region_name, group_id):
        team = team_services.check_and_get_user_team_by_name_and_region(user.user_id, team_name, region_name)
        if not team:
            raise ServiceHandleException(
                msg="no found team or team not join this region", msg_show="目标团队不存在，或团队为加入该数据中心", status_code=404)
        group = group_repo.get_group_by_id(group_id)
        if not group:
            raise ServiceHandleException(msg="no found group app", msg_show="目标应用不存在", status_code=404)
        if group.tenant_id != team.tenant_id:
            raise ServiceHandleException(msg="group app and team relation no found", msg_show="目标应用不属于目标团队", status_code=400)
        return team, group

    def get_modify_group_metadata(self, old_team, old_region_name, tar_team, tar_region_name, group_id, service_ids, changes):
        total_memory, services_metadata = groupapp_backup_service.get_group_app_metadata(group_id, old_team, old_region_name)
        old_services_map = {
            app["service_base"]["service_id"]: app["service_base"]["k8s_component_name"]
            for app in services_metadata["apps"]
        }
        group_all_service_ids = [service["service_id"] for service in services_metadata["service_group_relation"]]
        if not service_ids:
            service_ids = group_all_service_ids
        remove_service_ids = list(set(service_ids) ^ set(group_all_service_ids))
        change_services_map = self.change_services_map(service_ids, old_services_map)
        services_metadata = self.pop_services_metadata(old_team, old_region_name, tar_team, tar_region_name, services_metadata,
                                                       remove_service_ids, service_ids, change_services_map)
        services_metadata = self.change_services_metadata_info(services_metadata, changes)
        return services_metadata, change_services_map

    def pop_services_metadata(self,
                              old_team,
                              old_region_name,
                              tar_team,
                              tar_region_name,
                              metadata,
                              remove_service_ids,
                              service_ids,
                              change_service_map=None):
        same_team_and_region_copy = False
        if old_team.tenant_id == tar_team.tenant_id and old_region_name == tar_region_name:
            same_team_and_region_copy = True
        if not remove_service_ids:
            for service in metadata["apps"]:
                # 处理组件存储依赖关系
                if service["service_mnts"]:
                    new_service_mnts = []
                    for service_mnt in service["service_mnts"]:
                        if same_team_and_region_copy and service_mnt["dep_service_id"] not in (
                                set(remove_service_ids) ^ set(service_ids)):
                            new_service_mnts.append(service_mnt)
                    service["service_mnts"] = new_service_mnts
                # Handling plugin config
                if change_service_map and service["service_plugin_config"]:
                    for plugin in service["service_plugin_config"]:
                        if plugin["dest_service_id"] != "":
                            # Get the new next service ID pointed to by the plugin through the old service ID
                            plugin["dest_service_alias"] = change_service_map.get(plugin["dest_service_id"], {}).get(
                                "ServiceAlias", "")
                            plugin["dest_service_id"] = change_service_map.get(plugin["dest_service_id"], {}).get(
                                "ServiceID", "")
            return metadata
        new_metadata = {}
        new_metadata["compose_group_info"] = metadata["compose_group_info"]
        new_metadata["group_info"] = metadata["group_info"]
        new_metadata["plugin_info"] = metadata["plugin_info"]
        new_metadata["app_config_group_info"] = metadata["app_config_group_info"]
        new_metadata["service_group_relation"] = []
        new_metadata["apps"] = []
        new_metadata["compose_service_relation"] = []

        for relation_service in metadata["service_group_relation"]:
            if relation_service["service_id"] not in remove_service_ids:
                new_metadata["service_group_relation"].append(relation_service)
        for service in metadata["apps"]:
            # 处理组件之间的依赖关系
            if service["service_base"]["service_id"] not in remove_service_ids:
                new_relation = []
                for dep_service_info in service["service_relation"]:
                    if same_team_and_region_copy:
                        new_relation.append(dep_service_info)
                    else:
                        if dep_service_info["dep_service_id"] in service_ids and \
                                dep_service_info["dep_service_id"] not in remove_service_ids:
                            new_relation.append(dep_service_info)
                service["service_relation"] = new_relation
                new_metadata["apps"].append(service)
            # 处理组件存储依赖关系
            if service["service_mnts"]:
                new_service_mnts = []
                for service_mnt in service["service_mnts"]:
                    if same_team_and_region_copy and service_mnt["dep_service_id"] not in (
                            set(remove_service_ids) ^ set(service_ids)):
                        new_service_mnts.append(service_mnt)
                service["service_mnts"] = new_service_mnts
            # Handling plugin config
            if change_service_map and service["service_plugin_config"]:
                for plugin in service["service_plugin_config"]:
                    if plugin["dest_service_id"] != "" and plugin["dest_service_id"]:
                        # Handles plugin configuration of dependent components
                        new_dep_component_c = change_service_map.get(plugin["dest_service_id"], None)
                        if new_dep_component_c:
                            plugin["dest_service_alias"] = new_dep_component_c.get("ServiceAlias")
                            plugin["dest_service_id"] = new_dep_component_c.get("ServiceID")
                        elif not same_team_and_region_copy:
                            plugin["dest_service_alias"] = ""
                            plugin["dest_service_id"] = ""

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
                envs = changes[service["service_base"]["service_id"]].get("envs")
                if not envs:
                    continue
                for env in service["service_env_vars"]:
                    if not envs.get(env["attr_name"]):
                        continue
                    env["attr_name"] = envs[env["attr_name"]]
        return metadata

    def save_new_group_app(self, user, tar_team, region_name, group_id, metadata, changed_service_map, same_team, same_region):
        migrate_service.save_data(tar_team, region_name, user, changed_service_map, metadata, group_id, same_team, same_region)

    def change_services_map(self, service_ids, old_services_map):
        change_services = {}
        for service_id in service_ids:
            new_service_id = make_uuid()
            change_services.update({
                service_id: {
                    "ServiceID": new_service_id,
                    "ServiceAlias": app_service.create_service_alias(new_service_id),
                    "k8s_component_name": old_services_map[service_id]
                }
            })
        return change_services

    def new_services_and_copy_path(self, tar_team_name, region, change_services):
        service_copy_path = {}
        old_service_ids = [old_service_id for old_service_id in list(change_services.keys())]
        service_repo_info = TenantServiceInfoRepository()
        for old_service_id in old_service_ids:
            service_info = service_repo_info.get_service_by_service_id(old_service_id)
            old_file_path = service_info.git_url
            new_service_id = change_services[old_service_id]["ServiceID"]
            service_copy_path.update({new_service_id: old_file_path})
            event_id = old_file_path.split("/")[-1]
            pkg_copy_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            # 复制组件信息
            app_service.change_package_upload_info(new_service_id, event_id, pkg_copy_time)
            # 获取文件名
            package_names = package_upload_service.get_name_by_component_id([old_service_id])
            # 增加记录
            copy_record_info = {
                "event_id": event_id,
                "status": "finished",
                "source_dir": package_names,
                "team_name": tar_team_name,
                "region": region,
                "component_id": new_service_id
            }
            package_upload_service.create_upload_record(**copy_record_info)
        return service_copy_path

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
        change_service_ids = [change_service["ServiceID"] for change_service in list(change_services_map.values())]
        if not group_services:
            return []
        service_ids = [group_service.get("service_id") for group_service in group_services]
        services = service_repo.list_by_component_ids(service_ids=service_ids)
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
                # 上传文件复制
                service_copy_path = None
                if service.service_source == "package_build":
                    service_copy_path = self.new_services_and_copy_path(tenant.tenant_name, region_name, change_services_map)
                # 部署组件
                app_manage_service.deploy(tenant, service, user, service_copy_path=service_copy_path)

                # 添加组件部署关系
                deploy_repo.create_deploy_relation_by_service_id(service_id=service.service_id)
                result.append(service)
                # 为组件创建插件
                build_error_plugin_ids = []
                service_plugins = app_plugin_relation_repo.get_service_plugin_relation_by_service_id(service.service_id)
                for service_plugin in service_plugins:
                    plugin = plugin_repo.get_by_plugin_id(tenant.tenant_id, service_plugin.plugin_id)
                    plugin_version = plugin_repo.get_plugin_buildversion(service_plugin.plugin_id, service_plugin.build_version)
                    # 在数据中心创建插件
                    try:
                        event_id = make_uuid()
                        plugin_version.event_id = event_id
                        image_tag = (plugin_version.image_tag if plugin_version.image_tag else "latest")
                        plugin_service.create_region_plugin(region_name, tenant, plugin, image_tag=image_tag)
                        ret = plugin_service.build_plugin(region_name, plugin, plugin_version, user, tenant, event_id)
                        plugin_version.build_status = ret.get('bean').get('status')
                        plugin_version.save()
                    except Exception as e:
                        logger.debug(e)
                    # 为组件开通插件
                    try:
                        region_config = app_plugin_service.get_region_config_from_db(service, service_plugin.plugin_id,
                                                                                     service_plugin.build_version)
                        data = dict()
                        data["plugin_id"] = service_plugin.plugin_id
                        data["switch"] = True
                        data["version_id"] = service_plugin.build_version
                        data["plugin_cpu"] = service_plugin.min_cpu
                        data["plugin_memory"] = service_plugin.min_memory
                        data.update(region_config)
                        region_api.install_service_plugin(region_name, tenant.tenant_name, service.service_alias, data)
                    except region_api.CallApiError as e:
                        logger.debug(e)
                        build_error_plugin_ids.append(service_plugin.plugin_id)
                if build_error_plugin_ids:
                    app_plugin_relation_repo.get_service_plugin_relation_by_service_id(
                        service.service_id).filter(plugin_id__in=build_error_plugin_ids).delete()
        return result


groupapp_copy_service = GroupAppCopyService()

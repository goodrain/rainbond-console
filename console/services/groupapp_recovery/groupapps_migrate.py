# -*- coding: utf8 -*-
"""
  Created on 2018/5/25.
  应用迁移
"""
import datetime
import json
import logging

from console.constants import AppMigrateType
from console.enum.app import GovernanceModeEnum
from console.models.main import ServiceRelPerms, ServiceSourceInfo
from console.repositories.app_config import (domain_repo, tcp_domain, volume_repo)
from console.repositories.app_config_group import app_config_group_repo
from console.repositories.backup_repo import backup_record_repo
from console.repositories.group import group_repo
from console.repositories.migration_repo import migrate_repo
from console.repositories.plugin.plugin import plugin_repo
from console.repositories.plugin.plugin_config import (plugin_config_group_repo, plugin_config_items_repo)
from console.repositories.plugin.plugin_version import build_version_repo
from console.repositories.probe_repo import probe_repo
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.repositories.region_app import region_app_repo
from console.services.app import app_service
from console.services.app_config import port_service, volume_service
from console.services.app_config.component_graph import component_graph_service
from console.services.app_config.port_service import port_repo
from console.services.app_config.service_monitor import service_monitor_repo
from console.services.app_config_group import app_config_group_service
from console.services.config_service import EnterpriseConfigService
from console.services.exception import (ErrBackupRecordNotFound, ErrNeedAllServiceCloesed, ErrObjectStorageInfoNotFound)
from console.services.group_service import group_service
from django.db import transaction
from www.apiclient.regionapi import RegionInvokeApi
from www.models.label import ServiceLabels
from www.models.main import (ServiceDomain, ServiceEvent, ServiceProbe, TenantServiceAuth,
                             TenantServiceConfigurationFile, TenantServiceEnv, TenantServiceEnvVar, TenantServiceInfo,
                             TenantServiceMountRelation, TenantServiceRelation, TenantServicesPort, TenantServiceVolume,
                             ThirdPartyServiceEndpoints)
from www.models.plugin import (ServicePluginConfigVar, TenantServicePluginRelation)
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class GroupappsMigrateService(object):
    def __get_restore_type(self, current_tenant, current_region, migrate_team, migrate_region):
        """获取恢复的类型"""
        if current_region != migrate_region:
            return AppMigrateType.OTHER_REGION
        if migrate_team.tenant_name != current_tenant.tenant_name:
            return AppMigrateType.CURRENT_REGION_OTHER_TENANT
        return AppMigrateType.CURRENT_REGION_CURRENT_TENANT

    def __copy_backup_record(self, restore_mode, origin_backup_record, current_team, current_region, migrate_team,
                             migrate_region, migrate_type):
        """拷贝备份数据"""
        services = group_service.get_group_services(origin_backup_record.group_id)
        if not services and migrate_type == "recover":
            # restore on the original group
            new_group = group_repo.get_group_by_id(origin_backup_record.group_id)
            if not new_group:
                new_group = self.__create_new_group_by_group_name(migrate_team, migrate_region, origin_backup_record.group_id)
        else:
            new_group = self.create_new_group(migrate_team, migrate_region, origin_backup_record.group_id)
        if restore_mode != AppMigrateType.CURRENT_REGION_CURRENT_TENANT:
            # 获取原有数据中心数据
            original_data = region_api.get_backup_status_by_backup_id(current_region, current_team.tenant_name,
                                                                      origin_backup_record.backup_id)

            new_event_id = make_uuid()
            new_group_uuid = make_uuid()
            new_data = original_data["bean"]
            new_data["event_id"] = new_event_id
            new_data["group_id"] = new_group_uuid
            # 存入其他数据中心
            body = region_api.copy_backup_data(migrate_region, migrate_team.tenant_name, new_data)
            bean = body["bean"]
            params = origin_backup_record.to_dict()
            params.pop("ID")
            params["team_id"] = migrate_team.tenant_id
            params["event_id"] = new_event_id
            params["group_id"] = new_group.ID
            params["group_uuid"] = new_group_uuid
            params["region"] = migrate_region
            params["backup_id"] = bean["backup_id"]
            # create a new backup record in the new region
            new_backup_record = backup_record_repo.create_backup_records(**params)
            return new_group, new_backup_record
        return new_group, None

    def __create_new_group_by_group_name(self, tenant, region, old_group_id):
        new_group_name = '_'.join(["备份应用", make_uuid()[-4:]])
        app = group_service.create_app(tenant, region, new_group_name, k8s_app="backup-" + make_uuid()[-4:])
        new_app = group_repo.get_group_by_id(app["ID"])
        return new_app

    def create_new_group(self, tenant, region, old_group_id):
        old_group = group_repo.get_group_by_id(old_group_id)
        if old_group:
            new_group_name = '_'.join([old_group.group_name, make_uuid()[-4:]])
            k8s_app = old_group.k8s_app + "-" + make_uuid()[-4:]
        else:
            new_group_name = make_uuid()[:8]
            k8s_app = "backup-" + make_uuid()[-4:]
        app = group_service.create_app(tenant, region, new_group_name, "备份创建", k8s_app=k8s_app)
        new_app = group_repo.get_group_by_id(app["ID"])
        return new_app

    def start_migrate(self, user, current_team, current_region, migrate_team, migrate_region, backup_id, migrate_type, event_id,
                      restore_id):
        backup_record = backup_record_repo.get_record_by_backup_id(current_team.tenant_id, backup_id)
        if not backup_record:
            raise ErrBackupRecordNotFound

        s3_info = EnterpriseConfigService(user.enterprise_id).get_cloud_obj_storage_info()
        if backup_record.mode == "full-online" and not s3_info:
            raise ErrObjectStorageInfoNotFound

        if migrate_type == "recover":
            is_all_services_closed = self.__check_group_service_status(current_region, current_team, backup_record.group_id)
            if not is_all_services_closed:
                raise ErrNeedAllServiceCloesed

        restore_mode = self.__get_restore_type(current_team, current_region, migrate_team, migrate_region)

        # 数据迁移到其他地方先处理数据中心数据拷贝
        new_group, new_backup_record = self.__copy_backup_record(restore_mode, backup_record, current_team, current_region,
                                                                 migrate_team, migrate_region, migrate_type)
        if not new_backup_record:
            new_backup_record = backup_record

        data = {
            "event_id": make_uuid(),
            "backup_id": new_backup_record.backup_id,
            "restore_mode": restore_mode,
            "tenant_id": migrate_team.tenant_id,
            "s3_config": s3_info,
        }
        body = region_api.star_apps_migrate_task(migrate_region, migrate_team.tenant_name, new_backup_record.backup_id, data)

        if event_id:
            migrate_record = migrate_repo.get_by_event_id(event_id)
            data = region_api.get_apps_migrate_status(migrate_record.migrate_region, migrate_record.migrate_team,
                                                      migrate_record.backup_id, restore_id)
            bean = data["bean"]
            migrate_record.status = bean["status"]
            migrate_record.save()
        else:
            # 创建迁移记录
            params = {
                "group_id": new_group.ID,
                "group_uuid": new_backup_record.group_uuid,
                "event_id": make_uuid(),
                "version": backup_record.version,
                "backup_id": new_backup_record.backup_id,
                "migrate_team": migrate_team.tenant_name,
                "migrate_region": migrate_region,
                "status": "starting",
                "user": user.nick_name,
                "restore_id": body["bean"]["restore_id"],
                "original_group_id": backup_record.group_id,
                "original_group_uuid": backup_record.group_uuid,
                "migrate_type": migrate_type
            }
            migrate_record = migrate_repo.create_migrate_record(**params)
        return migrate_record

    def __check_group_service_status(self, region, tenant, group_id):
        services = group_service.get_group_services(group_id)
        service_ids = [s.service_id for s in services]
        if not service_ids:
            return True
        body = region_api.service_status(region, tenant.tenant_name, {
            "service_ids": service_ids,
            "enterprise_id": tenant.enterprise_id
        })
        status_list = body["list"]
        for status in status_list:
            if status["status"] not in ("closed", "undeploy"):
                return False
        return True

    def get_and_save_migrate_status(self, user, restore_id, current_team_name, current_region):
        migrate_record = migrate_repo.get_by_restore_id(restore_id)
        if not migrate_record:
            return None
        if migrate_record.status == "starting":
            data = region_api.get_apps_migrate_status(migrate_record.migrate_region, migrate_record.migrate_team,
                                                      migrate_record.backup_id, restore_id)
            bean = data["bean"]
            status = bean["status"]
            if status == "success":
                service_change = bean["service_change"]
                logger.debug("service change : {0}".format(service_change))
                metadata = bean["metadata"]
                migrate_team = team_repo.get_tenant_by_tenant_name(migrate_record.migrate_team)
                try:
                    with transaction.atomic():
                        self.save_data(migrate_team, migrate_record.migrate_region, user, service_change, json.loads(metadata),
                                       migrate_record.group_id, migrate_record.migrate_team == current_team_name,
                                       migrate_record.migrate_region == current_region, True)
                        if migrate_record.migrate_type == "recover":
                            # 如果为恢复操作，将原有备份和迁移的记录的组信息修改
                            backup_record_repo.get_record_by_group_id(
                                migrate_record.original_group_id).update(group_id=migrate_record.group_id)
                            self.update_migrate_original_group_id(migrate_record.original_group_id, migrate_record.group_id)
                        region_app_id = region_app_repo.get_region_app_id(migrate_record.migrate_region,
                                                                          migrate_record.group_id)
                        group_service.sync_app_services(migrate_team, migrate_record.migrate_region, migrate_record.group_id)
                        region_api.change_application_volumes(migrate_team.tenant_name, migrate_record.migrate_region,
                                                              region_app_id)
                except Exception as e:
                    logger.exception(e)
                    status = "failed"
                migrate_record.status = status
                migrate_record.save()
        return migrate_record

    def save_data(
            self,
            migrate_tenant,
            migrate_region,
            user,
            changed_service_map,
            metadata,
            group_id,
            same_team,
            same_region,
            sync_flag=False,
    ):
        from console.services.groupcopy_service import groupapp_copy_service
        group = group_repo.get_group_by_id(group_id)
        services = group_service.get_group_services(group_id)
        tar_group_k8s_component_names = [service.k8s_component_name for service in services]
        apps = metadata["apps"]

        old_new_service_id_map = dict()
        service_relations_list = []
        service_mnt_list = []
        # restore component
        for app in apps:
            service_base_info = app["service_base"]
            new_service_id = changed_service_map[service_base_info["service_id"]]["ServiceID"]
            new_service_alias = changed_service_map[service_base_info["service_id"]]["ServiceAlias"]
            new_k8s_component_name = changed_service_map[service_base_info["service_id"]]["k8s_component_name"]
            if new_k8s_component_name in tar_group_k8s_component_names:
                new_k8s_component_name = "{}-{}".format(new_k8s_component_name, new_service_alias)
            ts = self.__init_app(app["service_base"], new_service_id, new_service_alias, new_k8s_component_name, user,
                                 migrate_region, migrate_tenant, app["service_base"].get("arch"))
            old_new_service_id_map[app["service_base"]["service_id"]] = ts.service_id
            group_service.add_service_to_group(migrate_tenant, migrate_region, group.ID, ts.service_id)
            self.__save_port(migrate_region, migrate_tenant, ts, app["service_ports"], group.governance_mode,
                             app["service_env_vars"], sync_flag)
            self.__save_env(migrate_tenant, ts, app["service_env_vars"])
            self.__save_volume(migrate_tenant, ts, app["service_volumes"],
                               app["service_config_file"] if 'service_config_file' in app else None)
            self.__save_compile_env(ts, app["service_compile_env"])
            self.__save_service_label(migrate_tenant, ts, migrate_region, app["service_labels"])
            if sync_flag:
                self.__save_service_probes(ts, app["service_probes"])
            self.__save_service_source(migrate_tenant, ts, app["service_source"])
            self.__save_service_auth(ts, app["service_auths"])
            self.__save_third_party_service_endpoints(ts, app.get("third_party_service_endpoints", []))
            self.__save_service_monitors(migrate_tenant, ts, app.get("service_monitors"))
            self.__save_component_graphs(ts, app.get("component_graphs"))

            if ts.service_source == "third_party":
                app_service.create_third_party_service(migrate_tenant, ts, user.nick_name)
                probes = probe_repo.get_service_probe(ts.service_id)
                # 为组件添加默认探针
                if not probes:
                    if groupapp_copy_service.is_need_to_add_default_probe(ts):
                        code, msg, probe = app_service.add_service_default_porbe(migrate_tenant, ts)
                        logger.debug("add default probe; code: {}; msg: {}".format(code, msg))
                else:
                    for probe in probes:
                        prob_data = {
                            "service_id": ts.service_id,
                            "scheme": probe.scheme,
                            "path": probe.path,
                            "port": probe.port,
                            "cmd": probe.cmd,
                            "http_header": probe.http_header,
                            "initial_delay_second": probe.initial_delay_second,
                            "period_second": probe.period_second,
                            "timeout_second": probe.timeout_second,
                            "failure_threshold": probe.failure_threshold,
                            "success_threshold": probe.success_threshold,
                            "is_used": (1 if probe.is_used else 0),
                            "probe_id": probe.probe_id,
                            "mode": probe.mode,
                        }
                        try:
                            res, body = region_api.add_service_probe(ts.service_region, migrate_tenant.tenant_name,
                                                                     ts.service_alias, prob_data)
                            if res.get("status") != 200:
                                logger.debug(body)
                                probe.delete()
                        except Exception as e:
                            logger.debug("error", e)
                            probe.delete()
            service_relations = app["service_relation"]
            service_mnts = app["service_mnts"]

            if service_relations:
                service_relations_list[0:0] = list(service_relations)
            if service_mnts:
                service_mnt_list[0:0] = list(service_mnts)
            # 更新状态
            ts.create_status = "complete"
            ts.save()

        # restore plugin info
        self.__save_plugins(migrate_region, migrate_tenant, metadata["plugin_info"]["plugins"])
        self.__save_plugin_config_items(metadata["plugin_info"]["plugin_config_items"])
        self.__save_plugin_config_groups(metadata["plugin_info"]["plugin_config_groups"])
        versions = self.__save_plugin_build_versions(migrate_tenant, metadata["plugin_info"]["plugin_build_versions"])
        for app in apps:
            new_service_id = old_new_service_id_map[app["service_base"]["service_id"]]
            # plugin
            if app.get("service_plugin_relation", None):
                self.__save_plugin_relations(new_service_id, app["service_plugin_relation"], versions)
            if app.get("service_plugin_config", None):
                self.__save_service_plugin_config(new_service_id, app["service_plugin_config"])
        self.__save_service_relations(migrate_tenant, service_relations_list, old_new_service_id_map, same_team, same_region)
        self.__save_service_mnt_relation(migrate_tenant, service_mnt_list, old_new_service_id_map, same_team, same_region)
        # restore application config group
        self.__save_app_config_groups(
            metadata.get("app_config_group_info"), migrate_tenant, migrate_region, group_id, changed_service_map)

    def __init_app(self, service_base_info, new_service_id, new_servie_alias, new_k8s_component_name, user, region, tenant, arch=None):
        service_base_info.pop("ID")
        ts = TenantServiceInfo(**service_base_info)
        if service_base_info["service_source"] == "third_party":
            new_service_id = make_uuid(tenant.tenant_id)
            new_servie_alias = app_service.create_service_alias(new_service_id)
        ts.service_id = new_service_id
        ts.service_alias = new_servie_alias
        ts.service_region = region
        ts.creater = user.user_id
        ts.tenant_id = tenant.tenant_id
        ts.create_status = "creating"
        ts.service_cname = ts.service_cname + "-copy"
        ts.k8s_component_name = new_k8s_component_name
        # initialize arch field
        if arch:
            ts.arch = arch
        elif not hasattr(ts, 'arch') or ts.arch is None:
            ts.arch = service_base_info.get("arch", "amd64")
        # compatible component type
        if ts.extend_method == "state":
            ts.extend_method = "state_multiple"
        if ts.extend_method == "stateless":
            ts.extend_method = "stateless_multiple"
        ts.save()
        return ts

    def __save_env(self, tenant, service, tenant_service_env_vars):
        env_list = []
        for env in tenant_service_env_vars:
            env.pop("ID")
            new_env = TenantServiceEnvVar(**env)
            new_env.tenant_id = tenant.tenant_id
            new_env.service_id = service.service_id
            env_list.append(new_env)
        if env_list:
            TenantServiceEnvVar.objects.bulk_create(env_list)

    def __save_volume(self, tenant, service, tenant_service_volumes, service_config_file):
        volume_list = []
        config_list = []
        volume_name_id = {}
        for volume in tenant_service_volumes:
            index = volume.pop("ID")
            volume_name_id[volume["volume_name"]] = index
            if volume["volume_type"] == "config-file" and service_config_file:
                for config_file in service_config_file:
                    if config_file["service_id"] == volume["service_id"] and config_file["volume_name"] == volume["volume_name"]:
                        config_file.pop("ID")
                        new_config_file = TenantServiceConfigurationFile(**config_file)
                        new_config_file.service_id = service.service_id
                        config_list.append(new_config_file)
            settings = volume_service.get_best_suitable_volume_settings(tenant, service, volume["volume_type"],
                                                                        volume.get("access_mode"), volume.get("share_policy"),
                                                                        volume.get("backup_policy"), None,
                                                                        volume.get("volume_provider_name"))
            if settings["changed"]:
                logger.debug('volume type changed from {0} to {1}'.format(volume["volume_type"], settings["volume_type"]))
                volume["volume_type"] = settings["volume_type"]
            new_volume = TenantServiceVolume(**volume)
            new_volume.service_id = service.service_id
            host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant.tenant_id, service.service_id, new_volume.volume_path)
            new_volume.host_path = host_path
            volume_list.append(new_volume)
        if volume_list:
            # bulk_create do not return volume's id(django database connection feature can_return_ids_from_bulk_insert)
            TenantServiceVolume.objects.bulk_create(volume_list)
            # query again volume for volume_id
            volumes = volume_repo.get_service_volumes_with_config_file(service.service_id)
            # prepare old volume_id and new volume_id relations
            volume_name_ids = [{"volume_name": volume.volume_name, "volume_id": volume.ID} for volume in volumes]
            volume_id_relations = {}
            for vni in volume_name_ids:
                if volume_name_id.get(vni["volume_name"]):
                    old_volume_id = volume_name_id.get(vni["volume_name"])
                    new_volume_id = vni["volume_id"]
                    volume_id_relations[old_volume_id] = new_volume_id
            for config in config_list:
                if volume_id_relations.get(config.volume_id):
                    config.volume_id = volume_id_relations.get(config.volume_id)
            TenantServiceConfigurationFile.objects.bulk_create(config_list)

    def __save_port(self,
                    region_name,
                    tenant,
                    service,
                    tenant_service_ports,
                    governance_mode,
                    tenant_service_env_vars,
                    sync_flag=False):
        port_2_envs = dict()
        for env in tenant_service_env_vars:
            container_port = env.get("container_port")
            if not container_port:
                continue
            envs = port_2_envs.get(container_port) if port_2_envs.get(container_port) else []
            envs.append(env)
            port_2_envs[container_port] = envs

        port_list = []
        for port in tenant_service_ports:
            port.pop("ID")
            # 直接使用 service 的 service_alias 作为 k8s_service_name
            k8s_service_name = service.service_alias

            if sync_flag:
                body = port
                body["k8s_service_name"] = k8s_service_name
                port_service.update_service_port(tenant, region_name, service.service_alias, [body])

            new_port = TenantServicesPort(**port)
            new_port.service_id = service.service_id
            new_port.tenant_id = tenant.tenant_id
            new_port.k8s_service_name = k8s_service_name
            port_list.append(new_port)

            # make sure the value of X_HOST env is correct
            envs = port_2_envs.get(port["container_port"])
            if envs:
                for env in envs:
                    if not env.get("container_port") or not env["attr_name"].endswith("_HOST"):
                        continue
                    origin_attr_value = env["attr_value"]
                    if governance_mode == GovernanceModeEnum.BUILD_IN_SERVICE_MESH.name:
                        env["attr_value"] = "127.0.0.1"
                    else:
                        env["attr_value"] = k8s_service_name
                    # update env if attr_value has changed.
                    if origin_attr_value != env["attr_value"] and sync_flag:
                        region_api.update_service_env(region_name, tenant.tenant_name, service.service_alias, {
                            "env_name": env["attr_name"],
                            "env_value": env["attr_value"]
                        })

        if port_list:
            TenantServicesPort.objects.bulk_create(port_list)
            region = region_repo.get_region_by_region_name(service.service_region)
            for port in port_list:
                if port.is_outer_service:
                    if port.protocol == "http":
                        service_domains = domain_repo.get_service_domain_by_container_port(
                            service.service_id, port.container_port)
                        # 在domain表中保存数据
                        if service_domains:
                            for service_domain in service_domains:
                                service_domain.is_outer_service = True
                                service_domain.save()
                        else:
                            # 在service_domain表中保存数据
                            service_id = service.service_id
                            service_name = service.service_alias
                            container_port = port.container_port
                            domain_name = str(service_name) + "-" + str(container_port) + "-" + str(
                                tenant.tenant_name) + "." + str(region.httpdomain)
                            create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            protocol = "http"
                            http_rule_id = make_uuid(domain_name)
                            tenant_id = tenant.tenant_id
                            service_alias = service.service_cname
                            region_id = region.region_id
                            domain_repo.create_service_domains(service_id, service_name, domain_name, create_time,
                                                               container_port, protocol, http_rule_id, tenant_id, service_alias,
                                                               region_id)
                            # 给数据中心发请求添加默认域名
                            data = dict()
                            data["domain"] = domain_name
                            data["service_id"] = service.service_id
                            data["tenant_id"] = tenant.tenant_id
                            data["tenant_name"] = tenant.tenant_name
                            data["protocol"] = protocol
                            data["container_port"] = int(container_port)
                            data["http_rule_id"] = http_rule_id
                            try:
                                region_api.bind_http_domain(service.service_region, tenant.tenant_name, data)
                            except Exception as e:
                                logger.exception(e)
                                domain_repo.delete_http_domains(http_rule_id)
                                return 412, "数据中心添加策略失败"
                    else:
                        service_tcp_domains = tcp_domain.get_service_tcp_domains_by_service_id_and_port(
                            service.service_id, port.container_port)
                        if service_tcp_domains:
                            for service_tcp_domain in service_tcp_domains:
                                # 改变tcpdomain表中状态
                                service_tcp_domain.is_outer_service = True
                                service_tcp_domain.save()
                        else:
                            # 在service_tcp_domain表中保存数据
                            res, data = region_api.get_port(region.region_name, tenant.tenant_name, True)
                            if int(res.status) != 200:
                                continue
                            end_point = "0.0.0.0:" + str(data["bean"])
                            service_id = service.service_id
                            service_name = service.service_alias
                            create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            container_port = port.container_port
                            protocol = port.protocol
                            service_alias = service.service_cname
                            tcp_rule_id = make_uuid(end_point)
                            tenant_id = tenant.tenant_id
                            region_id = region.region_id
                            tcp_domain.create_service_tcp_domains(service_id, service_name, end_point, create_time,
                                                                  container_port, protocol, service_alias, tcp_rule_id,
                                                                  tenant_id, region_id)
                            port = end_point.split(":")[1]
                            data = dict()
                            data["service_id"] = service.service_id
                            data["container_port"] = int(container_port)
                            data["ip"] = "0.0.0.0"
                            data["port"] = int(port)
                            data["tcp_rule_id"] = tcp_rule_id
                            try:
                                # 给数据中心传送数据添加策略
                                region_api.bindTcpDomain(service.service_region, tenant.tenant_name, data)
                            except Exception as e:
                                logger.exception(e)
                                tcp_domain.delete_tcp_domain(tcp_rule_id)
                                return 412, "数据中心添加策略失败"

    def __save_compile_env(self, service, compile_env):
        if compile_env:
            compile_env.pop("ID")
            new_compile_env = TenantServiceEnv(**compile_env)
            new_compile_env.service_id = service.service_id
            new_compile_env.save()

    def __save_service_label(self, tenant, service, region, service_labels):
        service_label_list = []
        for service_label in service_labels:
            service_label.pop("ID")
            new_service_label = ServiceLabels(**service_label)
            new_service_label.tenant_id = tenant.tenant_id
            new_service_label.service_id = service.service_id
            new_service_label.region = region
            service_label_list.append(new_service_label)
        if service_label_list:
            ServiceLabels.objects.bulk_create(service_label_list)

    def __save_service_domain(self, service, service_domains):
        service_domain_list = []
        for domain in service_domains:
            domain.pop("ID")
            new_service_domain = ServiceDomain(**domain)
            new_service_domain.service_id = service.service_id
            service_domain_list.append(new_service_domain)
        if service_domain_list:
            ServiceDomain.objects.bulk_create(service_domain_list)

    def __save_service_event(self, tenant, service, service_events):
        event_list = []
        for event in service_events:
            event.pop("ID")
            new_service_event = ServiceEvent(**event)
            new_service_event.service_id = service.service_id
            new_service_event.tenant_id = tenant.tenant_id
            event_list.append(new_service_event)
        if event_list:
            ServiceEvent.objects.bulk_create(event_list)

    def __save_service_perms(self, service, service_perms):
        service_perm_list = []
        for service_perm in service_perms:
            service_perm.pop("ID")
            new_service_perm = ServiceRelPerms(**service_perm)
            new_service_perm.service_id = service.ID
            service_perm_list.append(new_service_perm)
        if service_perm_list:
            ServiceRelPerms.objects.bulk_create(service_perm_list)

    def __save_service_probes(self, service, service_probes):
        service_probe_list = []
        for probe in service_probes:
            probe.pop("ID")
            new_service_probe = ServiceProbe(**probe)
            new_service_probe.service_id = service.service_id
            service_probe_list.append(new_service_probe)
        if service_probe_list:
            ServiceProbe.objects.bulk_create(service_probe_list)

    def __save_service_source(self, tenant, service, service_source):
        if service_source:
            service_source.pop("ID")
            if "service" in service_source:
                service_source["service_id"] = service_source.pop("service")
            new_service_source = ServiceSourceInfo(**service_source)
            new_service_source.service_id = service.service_id
            new_service_source.team_id = tenant.tenant_id
            new_service_source.save()

    def __save_service_auth(self, service, service_auth):
        service_auth_list = []
        for auth in service_auth:
            auth.pop("ID")
            new_service_auth = TenantServiceAuth(**auth)
            new_service_auth.service_id = service.service_id
            service_auth_list.append(new_service_auth)
        if service_auth_list:
            TenantServiceAuth.objects.bulk_create(service_auth_list)

    def __save_service_relations(self, tenant, service_relations_list, old_new_service_id_map, same_team, same_region):
        new_service_relation_list = []
        if service_relations_list:
            for relation in service_relations_list:
                relation.pop("ID")
                new_service_relation = TenantServiceRelation(**relation)
                new_service_relation.tenant_id = tenant.tenant_id
                new_service_relation.service_id = old_new_service_id_map[relation["service_id"]]
                if old_new_service_id_map.get(relation["dep_service_id"]):
                    new_service_relation.dep_service_id = old_new_service_id_map[relation["dep_service_id"]]
                elif same_team and same_region:
                    # check new app region is same as old app
                    new_service_relation.dep_service_id = relation["dep_service_id"]
                else:
                    continue
                new_service_relation_list.append(new_service_relation)
            TenantServiceRelation.objects.bulk_create(new_service_relation_list)

    def __save_service_mnt_relation(self, tenant, service_mnt_relation_list, old_new_service_id_map, same_team, same_region):
        new_service_mnt_relation_list = []
        if service_mnt_relation_list:
            for mnt in service_mnt_relation_list:
                mnt.pop("ID")
                new_service_mnt = TenantServiceMountRelation(**mnt)
                new_service_mnt.tenant_id = tenant.tenant_id
                new_service_mnt.service_id = old_new_service_id_map[mnt["service_id"]]
                if old_new_service_id_map.get(mnt["dep_service_id"]):
                    new_service_mnt.dep_service_id = old_new_service_id_map[mnt["dep_service_id"]]
                elif same_team and same_region:
                    new_service_mnt.dep_service_id = mnt["dep_service_id"]
                else:
                    continue
                new_service_mnt_relation_list.append(new_service_mnt)
            TenantServiceMountRelation.objects.bulk_create(new_service_mnt_relation_list)

    def update_migrate_original_group_id(self, old_original_group_id, new_original_group_id):
        migrate_repo.get_by_original_group_id(old_original_group_id).update(original_group_id=new_original_group_id)

    # def __save_service_endpoints(self, tenant, service, service_endpoints):
    #     endpoints_list = []
    #     for endpoint in service_endpoints:
    #         endpoint.pop("ID")
    #         new_service_endpoint = ThirdPartyServiceEndpoints(**endpoint)
    #         new_service_endpoint.service_id = service.service_id
    #         new_service_endpoint.tenant_id = tenant.tenant_id
    #         endpoints_list.append(new_service_endpoint)
    #     if endpoints_list:
    #         ThirdPartyServiceEndpoints.objects.bulk_create(endpoints_list)

    def __save_plugin_relations(self, service_id, plugin_relations, plugin_versions):
        if not plugin_relations:
            return
        new_plugin_relations = []
        for pr in plugin_relations:
            pr.pop("ID")
            new_pr = TenantServicePluginRelation(**pr)
            new_pr.service_id = service_id
            if new_pr.min_memory is None:
                new_pr.min_memory = 0
                new_pr.min_cpu = 0
                for plugin_version in plugin_versions:
                    if new_pr.plugin_id == plugin_version.plugin_id:
                        new_pr.min_memory = plugin_version.min_memory
                        new_pr.min_cpu = plugin_version.min_cpu
                        break
            new_plugin_relations.append(new_pr)
        TenantServicePluginRelation.objects.bulk_create(new_plugin_relations)

    def __save_service_plugin_config(self, sid, service_plugin_configs):
        if not service_plugin_configs:
            return
        new_configs = []
        for cfg in service_plugin_configs:
            cfg.pop("ID")
            new_cfg = ServicePluginConfigVar(**cfg)
            new_cfg.service_id = sid
            new_configs.append(new_cfg)
        ServicePluginConfigVar.objects.bulk_create(new_configs)

    def __save_plugin_config_items(self, plugin_config_items):
        if not plugin_config_items:
            return
        for item in plugin_config_items:
            item.pop("ID")
            plugin_config_items_repo.create_if_not_exist(**item)

    def __save_plugin_config_groups(self, plugin_config_groups):
        if not plugin_config_groups:
            return
        for group in plugin_config_groups:
            group.pop("ID")
            plugin_config_group_repo.create_if_not_exist(**group)

    def __save_plugin_build_versions(self, tenant, plugin_build_versions):
        if not plugin_build_versions:
            return
        create_version_list = []
        for version in plugin_build_versions:
            version.pop("ID")
            version["tenant_id"] = tenant.tenant_id
            create_version = build_version_repo.create_if_not_exist(**version)
            create_version_list.append(create_version)
        return create_version_list

    def __save_plugins(self, region_name, tenant, plugins):
        if not plugins:
            return
        create_plugins = []
        for plugin in plugins:
            plugin.pop("ID")
            plugin["tenant_id"] = tenant.tenant_id
            plugin["region"] = region_name
            plugin = plugin_repo.create_if_not_exist(**plugin)
            if plugin:
                create_plugins.append(plugin)
        return create_plugins

    def __save_third_party_service_endpoints(self, service, service_endpoints):
        service_endpoint_list = []
        for service_endpoint in service_endpoints:
            endpoint = {
                "tenant_id": service.tenant_id,
                "service_id": service.service_id,
                "service_cname": service.service_cname,
                "endpoints_info": service_endpoint["endpoints_info"],
                "endpoints_type": service_endpoint["endpoints_type"]
            }
            service_endpoint_list.append(ThirdPartyServiceEndpoints(**endpoint))
        ThirdPartyServiceEndpoints.objects.bulk_create(service_endpoint_list)

    def __save_app_config_groups(self, config_groups, tenant, region_name, app_id, changed_service_map):
        if not config_groups:
            return
        for cgroup in config_groups:
            service_ids = []
            is_exists = app_config_group_repo.is_exists(region_name, app_id, cgroup["config_group_name"])
            if is_exists:
                cgroup["config_group_name"] = "-".join([cgroup["config_group_name"], make_uuid()[-4:]])
            for service in cgroup["services"]:
                try:
                    service_ids.append(changed_service_map[service["service_id"]]["ServiceID"])
                except KeyError:
                    continue

            app_config_group_service.create_config_group(app_id, cgroup["config_group_name"], cgroup["config_items"],
                                                         cgroup["deploy_type"], cgroup["enable"], service_ids, region_name,
                                                         tenant.tenant_name)

    def __save_service_monitors(self, tenant, service, service_monitors):
        if not service_monitors:
            return
        service_monitor_repo.bulk_create_component_service_monitors(tenant, service, service_monitors)

    def __save_component_graphs(self, service, component_graphs):
        if not component_graphs:
            return
        component_graph_service.bulk_create(service.service_id, component_graphs, service.arch)


migrate_service = GroupappsMigrateService()

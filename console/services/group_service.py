# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import json
import logging
import re
from urllib.parse import quote
from datetime import datetime

from deprecated import deprecated

from console.enum.app import GovernanceModeEnum, AppType
from console.exception.bcode import ErrUserNotFound, ErrApplicationNotFound, ErrK8sAppExists
from console.exception.main import AbortRequest, ServiceHandleException
from console.repositories.app import service_repo, service_source_repo
from console.repositories.app_config import (domain_repo, env_var_repo, port_repo, tcp_domain, dep_relation_repo,
                                             volume_repo)
from console.repositories.app_config_group import app_config_group_repo
from console.repositories.backup_repo import backup_record_repo
from console.repositories.compose_repo import compose_repo
from console.repositories.group import group_repo, group_service_relation_repo
from console.repositories.k8s_resources import k8s_resources_repo
from console.repositories.region_app import region_app_repo
from console.repositories.region_repo import region_repo
from console.repositories.share_repo import share_repo
from console.repositories.team_repo import team_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.repositories.user_repo import user_repo
from console.repositories.migration_repo import migrate_repo
from console.services.app_config_group import app_config_group_service
from console.services.service_services import base_service
from console.utils.shortcuts import get_object_or_404
from django.db import transaction
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import RegionApp, ServiceGroup, ServiceGroupRelation

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class GroupService(object):
    def get_tenant_groups_by_region(self, tenant, region_name):
        return group_repo.list_tenant_group_on_region(tenant, region_name)

    @staticmethod
    def check_app_name(tenant, region_name, group_name, app: ServiceGroup = None, k8s_app=""):
        if not group_name:
            raise ServiceHandleException(msg="app name required", msg_show="应用名不能为空")
        if len(group_name) > 128:
            raise ServiceHandleException(msg="app_name illegal", msg_show="应用名称最多支持128个字符")
        r = re.compile('^[a-zA-Z0-9_\\.\\-\\u4e00-\\u9fa5]+$')
        if not r.match(group_name):
            raise ServiceHandleException(msg="app_name illegal", msg_show="应用名称只支持中英文, 数字, 下划线, 中划线和点")
        exist_app = group_repo.get_group_by_unique_key(tenant.tenant_id, region_name, group_name)
        app_id = app.app_id if app else 0
        if group_repo.is_k8s_app_duplicate(tenant.tenant_id, region_name, k8s_app, app_id):
            raise ErrK8sAppExists
        if not exist_app:
            return
        if not app or exist_app.app_id != app.app_id:
            raise ServiceHandleException(msg="app name exist", msg_show="应用名称已存在")

    @transaction.atomic
    def create_app(self,
                   tenant,
                   region_name,
                   app_name,
                   note="",
                   username="",
                   app_store_name="",
                   app_store_url="",
                   app_template_name="",
                   version="",
                   eid="",
                   logo="",
                   k8s_app=""):
        self.check_app_name(tenant, region_name, app_name, k8s_app=k8s_app)
        # check parameter for helm app
        app_type = AppType.rainbond.name
        if app_store_name or app_template_name or version:
            app_type = AppType.helm.name
            if not app_store_name:
                raise AbortRequest("the field 'app_store_name' is required")
            if not app_store_url:
                raise AbortRequest("the field 'app_store_url' is required")
            if not app_template_name:
                raise AbortRequest("the field 'app_template_name' is required")
            if not version:
                raise AbortRequest("the field 'version' is required")

        app = ServiceGroup(
            tenant_id=tenant.tenant_id,
            region_name=region_name,
            group_name=app_name,
            note=note,
            is_default=False,
            username=username,
            update_time=datetime.now(),
            create_time=datetime.now(),
            app_type=app_type,
            app_store_name=app_store_name,
            app_store_url=app_store_url,
            governance_mode=GovernanceModeEnum.KUBERNETES_NATIVE_SERVICE.name,
            app_template_name=app_template_name,
            version=version,
            logo=logo,
            k8s_app=k8s_app,
        )
        group_repo.create(app)

        self.create_region_app(tenant, region_name, app, eid=eid)

        res = app.to_dict()
        # compatible with the old version
        res["group_id"] = app.ID
        res['app_id'] = app.ID
        res['app_name'] = app.group_name
        res['k8s_app'] = app.k8s_app
        return res

    def json_app(self, app_name, k8s_app, logo, note):
        return json.dumps({"应用名称": app_name, "应用英文名称": k8s_app, "Logo": logo, "应用备注": note}, ensure_ascii=False)

    def create_default_app(self, tenant, region_name):
        app = group_repo.get_or_create_default_group(tenant.tenant_id, region_name)
        self.create_region_app(tenant, region_name, app)
        return app.to_dict()

    def create_region_app(self, tenant, region_name, app, eid=""):
        region_app = region_api.create_application(
            region_name, tenant.tenant_name, {
                "eid": eid,
                "app_name": app.group_name,
                "app_type": app.app_type,
                "app_store_name": app.app_store_name,
                "app_store_url": app.app_store_url,
                "app_template_name": app.app_template_name,
                "version": app.version,
                "k8s_app": app.k8s_app,
            })

        # record the dependencies between region app and console app
        data = {
            "region_name": region_name,
            "region_app_id": region_app["app_id"],
            "app_id": app.ID,
        }
        region_app_repo.create(**data)
        # 集群端创建完应用后，再更新控制台的应用名称
        app.k8s_app = region_app["k8s_app"]
        app.save()

    @staticmethod
    def _parse_overrides(overrides):
        new_overrides = []
        for key in overrides:
            val = overrides[key]
            if type(val) == int:
                val = str(val)
            if type(val) != str:
                raise AbortRequest("wrong override value which type is {}".format(type(val)))
            new_overrides.append(key + "=" + val)
        return new_overrides

    @transaction.atomic
    def update_group(self,
                     tenant,
                     region_name,
                     app_id,
                     app_name,
                     note="",
                     username=None,
                     overrides="",
                     version="",
                     revision=0,
                     logo="",
                     k8s_app=""):
        # check app id
        if not app_id or not str.isdigit(app_id) or int(app_id) < 0:
            raise ServiceHandleException(msg="app id illegal", msg_show="应用ID不合法")
        data = {
            "note": note,
            "logo": logo,
        }
        if username:
            # check username
            try:
                data["username"] = username
                user_repo.get_user_by_username(username)
            except ErrUserNotFound:
                raise ServiceHandleException(msg="user not exists", msg_show="用户不存在,请选择其他应用负责人", status_code=404)

        app = group_repo.get_group_by_id(app_id)

        # check app name
        if app_name:
            self.check_app_name(tenant, region_name, app_name, app, k8s_app)
        if overrides:
            overrides = self._parse_overrides(overrides)

        if app_name:
            data["group_name"] = app_name
        if version:
            data["version"] = version

        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)

        bean = region_api.update_app(region_name, tenant.tenant_name, region_app_id, {
            "overrides": overrides,
            "version": version,
            "revision": revision,
            "k8s_app": k8s_app,
        })
        data["k8s_app"] = bean["k8s_app"]
        group_repo.update(app_id, **data)

    def delete_group(self, group_id, default_group_id):
        if not group_id or not str.isdigit(group_id) or int(group_id) < 0:
            return 400, "需要删除的应用不合法", None
        backups = backup_record_repo.get_record_by_group_id(group_id)
        if backups:
            return 409, "当前应用有备份记录，暂无法删除", None
        # 删除应用
        group_repo.delete_group_by_pk(group_id)
        # 删除应用与应用的关系
        group_service_relation_repo.update_service_relation(group_id, default_group_id)
        return 200, "删除成功", group_id

    @staticmethod
    def add_component_to_app(tenant, region_name, app_id, component_id):
        if not app_id:
            return
        app_id = int(app_id)
        if app_id > 0:
            group = group_repo.get_group_by_pk(tenant.tenant_id, region_name, app_id)
            if not group:
                raise ErrApplicationNotFound
            group_service_relation_repo.add_service_group_relation(app_id, component_id, tenant.tenant_id, region_name)

    @deprecated("You should use 'add_component_to_app'")
    def add_service_to_group(self, tenant, region_name, group_id, service_id):
        if group_id:
            group_id = int(group_id)
            if group_id > 0:
                group = group_repo.get_group_by_pk(tenant.tenant_id, region_name, group_id)
                if not group:
                    return 404, "应用不存在"
                group_service_relation_repo.add_service_group_relation(group_id, service_id, tenant.tenant_id, region_name)
        return 200, "success"

    def sync_app_services(self, tenant, region_name, app_id):
        group_services = base_service.get_group_services_list(tenant.tenant_id, region_name, app_id)
        service_ids = []
        if group_services:
            for service in group_services:
                service_ids.append(service["service_id"])

        app = group_repo.get_group_by_id(app_id)
        try:
            region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
            body = {"service_ids": service_ids}
            region_api.batch_update_service_app_id(region_name, tenant.tenant_name, region_app_id, body)
        except RegionApp.DoesNotExist:
            create_body = {"app_name": app.group_name, "service_ids": service_ids}
            if app.k8s_app:
                create_body["k8s_app"] = app.k8s_app
            bean = region_api.create_application(region_name, tenant, create_body)
            region_app_id = bean["app_id"]
            req = {"region_name": region_name, "region_app_id": region_app_id, "app_id": app_id}
            region_app_repo.create(**req)
            app.k8s_app = bean["k8s_app"]
            app.save()
        if not app.k8s_app:
            status = region_api.get_app_status(region_name, tenant.tenant_name, region_app_id)
            app.k8s_app = status["k8s_app"] if status.get("k8s_app") else ""
            app.save()
        return region_app_id

    def get_app_detail(self, tenant, region, app_id):
        # app metadata
        region_name = region.region_name
        app = group_repo.get_group_by_pk(tenant.tenant_id, region_name, app_id)

        region_app_id = self.sync_app_services(tenant, region_name, app_id)

        res = app.to_dict()
        res['region_app_id'] = region_app_id
        res['namespace'] = tenant.namespace
        res['app_id'] = app.ID
        res['app_name'] = app.group_name
        res['app_type'] = app.app_type
        res['service_num'] = group_service_relation_repo.count_service_by_app_id(app_id)
        res['share_num'] = share_repo.count_by_app_id(app_id)
        res['resources_num'] = k8s_resources_repo.list_by_app_id(app_id).count()
        res['ingress_num'] = 0
        body = region_api.get_api_gateway(region, tenant, app_id)
        if body and body["list"]:
            res['ingress_num'] = len(body["list"])
        res['config_group_num'] = app_config_group_service.count_by_app_id(region_name, app_id)
        res['logo'] = app.logo
        res['k8s_app'] = app.k8s_app
        res['can_edit'] = True
        components = group_service_relation_repo.get_services_by_group(app_id)
        services = service_repo.get_services_by_service_ids([component.service_id for component in components])
        res['app_arch'] = {service.arch: "1" for service in services if service.arch}.keys()
        running_components = region_api.get_dynamic_services_pods(region_name, tenant.tenant_name,
                                                                  [component.service_id for component in components])
        if running_components.get("list") and len(running_components["list"]) > 0:
            res['can_edit'] = False

        try:
            principal = user_repo.get_user_by_username(app.username)
            res['principal'] = principal.get_name()
            res['email'] = principal.email
        except ErrUserNotFound:
            res['principal'] = app.username

        res["create_status"] = "complete"
        res["compose_id"] = None
        if app_id != -1:
            compose_group = compose_repo.get_group_compose_by_group_id(app_id)
            if compose_group:
                res["create_status"] = compose_group.create_status
                res["compose_id"] = compose_group.compose_id

        return res

    def get_service_volume_by_ids(self, service_ids):
        """
        获取组件持久化目录
        """
        volume_list = share_repo.get_volume_list_by_service_ids(service_ids=service_ids)
        if volume_list:
            service_volume_map = {}
            for volume in volume_list:
                service_id = volume.service_id
                tmp_list = []
                if service_id in list(service_volume_map.keys()):
                    tmp_list = service_volume_map.get(service_id)
                tmp_list.append(volume)
                service_volume_map[service_id] = tmp_list
            return service_volume_map
        else:
            return {}

    def is_service_related_by_other_app_service(self, tenant, service):
        tsrs = dep_relation_repo.get_dependency_by_dep_id(tenant.tenant_id, service.service_id)
        if tsrs:
            sids = list(set([tsr.service_id for tsr in tsrs]))
            service_group = ServiceGroupRelation.objects.get(service_id=service.service_id, tenant_id=tenant.tenant_id)
            groups = ServiceGroupRelation.objects.filter(service_id__in=sids, tenant_id=tenant.tenant_id)
            group_ids = set([group.group_id for group in groups])
            if group_ids and service_group.group_id in group_ids:
                group_ids.remove(service_group.group_id)
            if not group_ids:
                return False
            return True
        return False

    def service_status(self, tenant, service):
        status = ""
        try:
            if service.create_status != "complete":
                return False
            status_info = region_api.check_service_status(service.service_region, tenant.tenant_name, service.service_alias,
                                                          tenant.enterprise_id)
            status = status_info["bean"]["cur_status"]
        except region_api.CallApiError as e:
            if int(e.status) == 404:
                return False
        return status

    def get_app_resource(self, tenant_id, region_name, app_id):
        # app all service info
        res = {}
        services_info = []
        tenant = team_repo.get_team_by_team_id(tenant_id)
        service_ids = group_service_relation_repo.list_serivce_ids_by_app_id(tenant_id, region_name, app_id)
        services = service_repo.get_services_by_service_ids(service_ids)
        if len(services) > 0:
            service_volume_map = self.get_service_volume_by_ids(service_ids)
            for service in services:
                service_volumes = []
                volumes = service_volume_map.get(service.service_id, None)
                if volumes:
                    service_volumes = [volume.volume_name for volume in volumes]
                is_related = self.is_service_related_by_other_app_service(tenant, service)
                status = self.service_status(tenant, service)
                service_info = {
                    "service_name": service.service_cname,
                    "volume": service_volumes,
                    "is_related": is_related,
                    "status": status
                }
                services_info.append(service_info)
        res["services_info"] = services_info
        # k8s source
        app_k8s_resources = k8s_resources_repo.list_by_app_id(app_id)

        res['k8s_resources'] = [{"name": resource.name, "type": resource.kind} for resource in app_k8s_resources]
        # domains
        domains = domain_repo.get_domains_by_service_ids(service_ids)
        res['domains'] = [domain.domain_name for domain in domains]
        # config_groups
        config_groups = app_config_group_repo.list(region_name, app_id)
        res['config_groups'] = [config_group.config_group_name for config_group in config_groups]
        # app share records
        share_records = share_repo.get_app_share_records_by_groupid(tenant.tenant_name, group_id=app_id)
        res['app_share_records'] = [{
            "name": share_record.share_app_model_name,
            "version": share_record.share_version
        } for share_record in share_records]
        return res

    def batch_delete_app_services(self, user, tenant_id, region_name, app_id):
        service_ids = group_service_relation_repo.list_serivce_ids_by_app_id(tenant_id, region_name, app_id)
        services = service_repo.get_services_by_service_ids(service_ids)
        tenant = team_repo.get_team_by_team_id(tenant_id)
        # stop
        stop_infos_list = []
        for service in services:
            service_dict = dict()
            if service.create_status == "complete":
                service_dict["service_id"] = service.service_id
                stop_infos_list.append(service_dict)
        body = {"operation": "stop", "stop_infos": stop_infos_list, "operator": user.nick_name}
        try:
            region_api.batch_operation_service(region_name, tenant.tenant_name, body)
        except region_api.CallApiError as e:
            logger.exception(e)
            raise AbortRequest(500, "failed to request region api", "数据中心操作失败")

        # avoid circular import
        from console.services.app_actions import app_manage_service
        # Batch Delete Components
        for service in services:
            app_manage_service.batch_delete(user, tenant, service, is_force=True, is_del_app=True)
        return services

    def delete_app_share_records(self, team_name, app_id):
        share_records = share_repo.get_app_share_records_by_groupid(team_name, app_id)
        if share_records:
            for share_record in share_records:
                share_record.status = 3
                share_record.save()
        return

    def get_group_by_id(self, tenant, region, group_id):
        principal_info = dict()
        principal_info["email"] = ""
        principal_info["is_delete"] = False
        group = group_repo.get_group_by_pk(tenant.tenant_id, region, group_id)
        if not group:
            raise ServiceHandleException(status_code=404, msg="app not found", msg_show="目标应用不存在")
        try:
            user = user_repo.get_user_by_username(group.username)
            principal_info["real_name"] = user.get_name()
            principal_info["username"] = user.nick_name
            principal_info["email"] = user.email
        except ErrUserNotFound:
            principal_info["is_delete"] = True
            principal_info["real_name"] = group.username
            principal_info["username"] = group.username
        return {"group_id": group.ID, "group_name": group.group_name, "group_note": group.note, "principal": principal_info}

    def get_app_by_id(self, tenant, region, app_id):
        return group_repo.get_group_by_pk(tenant.tenant_id, region, app_id)

    def get_group_or_404(self, tenant, response_region, group_id):
        """
        :param tenant:
        :param response_region:
        :param group_id:
        :rtype: ServiceGroup
        """
        return get_object_or_404(
            ServiceGroup,
            msg="Group does not exist",
            msg_show="应用不存在",
            tenant_id=tenant.tenant_id,
            region_name=response_region,
            pk=group_id)

    def get_service_group_info(self, service_id):
        return group_service_relation_repo.get_group_info_by_service_id(service_id)

    def get_services_group_name(self, service_ids):
        return group_service_relation_repo.get_group_by_service_ids(service_ids)

    def delete_service_group_relation_by_service_id(self, service_id):
        group_service_relation_repo.delete_relation_by_service_id(service_id)

    def update_or_create_service_group_relation(self, tenant, service, group_id):
        gsr = group_service_relation_repo.get_group_by_service_id(service.service_id)
        if gsr:
            gsr.group_id = group_id
            gsr.save()
        else:
            params = {
                "service_id": service.service_id,
                "group_id": group_id,
                "tenant_id": tenant.tenant_id,
                "region_name": service.service_region
            }
            group_service_relation_repo.create_service_group_relation(**params)

    def get_groups_and_services(self, tenant, region, query="", app_type=""):
        groups = group_repo.get_tenant_region_groups(tenant.tenant_id, region, query, app_type)
        services = service_repo.get_tenant_region_services(region, tenant.tenant_id).values(
            "service_id", "service_cname", "service_alias")
        service_id_map = {s["service_id"]: s for s in services}
        service_group_relations = group_service_relation_repo.get_service_group_relation_by_groups([g.ID for g in groups])
        service_group_map = {sgr.service_id: sgr.group_id for sgr in service_group_relations}
        group_services_map = dict()
        for k, v in list(service_group_map.items()):
            service_list = group_services_map.get(v, None)
            service_info = service_id_map.get(k, None)
            if service_info:
                if not service_list:
                    group_services_map[v] = [service_info]
                else:
                    service_list.append(service_info)
                service_id_map.pop(k)

        result = []
        for g in groups:
            bean = dict()
            bean["group_id"] = g.ID
            bean["group_name"] = g.group_name
            bean["service_list"] = group_services_map.get(g.ID)
            result.insert(0, bean)

        return result

    def get_group_services(self, group_id):
        """查询某一应用下的组件"""
        gsr = group_service_relation_repo.get_services_by_group(group_id)
        service_ids = [gs.service_id for gs in gsr]
        services = service_repo.get_services_by_service_ids(service_ids)
        return services

    def get_multi_apps_all_info(self, sort, groups, app_ids, region, tenant_name, enterprise_id, tenant):
        app_list = groups.filter(ID__in=app_ids)
        service_list = service_repo.get_services_in_multi_apps_with_app_info(app_ids)
        # memory info
        service_ids = [service.service_id for service in service_list]
        status_list = base_service.status_multi_service(region, tenant_name, service_ids, enterprise_id)
        service_status = dict()
        if status_list is None:
            raise ServiceHandleException(msg="query status failure", msg_show="查询组件状态失败")
        for status in status_list:
            service_status[status["service_id"]] = status

        app_id_statuses = self.get_region_app_statuses(tenant_name, region, app_ids)
        apps = dict()
        volumes = volume_repo.get_services_volumes(service_ids)
        service_volume = dict()
        for volume in volumes:
            if volume.volume_type != "config-file":
                volume.volume_capacity = 10 if volume.volume_capacity == 0 else volume.volume_capacity
                service_volume[volume.service_id] = service_volume.get(volume.service_id, 0) + volume.volume_capacity
        for app in app_list:
            app_status = app_id_statuses.get(app.ID)
            apps[app.ID] = {
                "group_id": app.ID,
                "update_time": app.update_time,
                "create_time": app.create_time,
                "group_name": app.group_name,
                "group_note": app.note,
                "service_list": [],
                "used_mem": app_status.get("memory", 0) if app_status else 0,
                "used_cpu": app_status.get("cpu", 0) if app_status else 0,
                "used_disk": 0,
                "status": app_status.get("status", "UNKNOWN") if app_status else "UNKNOWN",
                "logo": app.logo,
                "accesses": [],
            }
        # 获取应用下组件的访问地址
        from console.services.app_config import port_service
        accesses = port_service.list_access_infos(tenant, service_list)
        for service in service_list:
            svc_sas = service_status.get(service.service_id, {"status": "failure", "used_mem": 0})
            service.status = svc_sas["status"]
            service.used_mem = svc_sas["used_mem"]
            apps[service.group_id]["used_disk"] = apps[service.group_id]["used_disk"] + service_volume.get(service.service_id, 0)
            apps[service.group_id]["service_list"].append(service)
            apps[service.group_id]["accesses"].append(accesses[service.service_id])

        re_app_list = []
        for a in app_list:
            app = apps.get(a.ID)
            app["services_num"] = len(app["service_list"])
            if not app.get("run_service_num"):
                app["run_service_num"] = 0
            if not app.get("used_mem"):
                app["used_mem"] = 0
            if not app.get("allocate_mem"):
                app["allocate_mem"] = 0
            for svc in app["service_list"]:
                app["allocate_mem"] += svc.min_memory
                if svc.status in ["running", "upgrade", "starting", "some_abnormal"]:
                    # if is running used_mem ++
                    app["run_service_num"] += 1
            if app["used_mem"] > app["allocate_mem"]:
                app["allocate_mem"] = app["used_mem"]
            app.pop("service_list")
            re_app_list.append(app)
        if sort != 2:
            re_app_list = sorted(
                re_app_list,
                key=lambda i: (1 if i["status"] == "RUNNING" else 2 if i["status"] == "ABNORMAL" else 3
                               if i["status"] == "STARTING" else 5 if i["status"] == "CLOSED" else 4, -i["used_mem"]))
        return re_app_list

    @staticmethod
    def get_region_app_statuses(tenant_name, region_name, app_ids):
        # Obtain the application ID of the cluster and
        # record the corresponding relationship of the console application ID
        region_apps = region_app_repo.list_by_region_and_app_ids(region_name, app_ids)
        region_app_ids = []
        app_id_rels = dict()
        for region_app in region_apps:
            region_app_ids.append(region_app.region_app_id)
            app_id_rels[region_app.app_id] = region_app.region_app_id
        # Get the status of cluster application
        try:
            resp = region_api.list_app_statuses_by_app_ids(tenant_name, region_name, {"app_ids": region_app_ids})
            app_statuses = resp.get("list", [])
        except Exception:
            app_statuses = list()
        if not app_statuses:
            app_statuses = list()
        # The relationship between cluster application ID and state
        # is transformed into that between console application ID and state
        # Returns the relationship between console application ID and status
        app_id_status_rels = dict()
        region_app_id_status_rels = dict()
        for app_status in app_statuses:
            region_app_id_status_rels[app_status.get("app_id", "")] = app_status
        for app_id in app_ids:
            if not app_id_rels.get(app_id):
                continue
            region_app_id_status = region_app_id_status_rels.get(app_id_rels[app_id])
            if not region_app_id_status:
                continue
            region_app_id_status["group_id"] = app_id
            app_id_status_rels[app_id] = region_app_id_status
        return app_id_status_rels

    @staticmethod
    def list_components_by_upgrade_group_id(group_id, upgrade_group_id):
        gsr = group_service_relation_repo.get_services_by_group(group_id)
        service_ids = gsr.values_list('service_id', flat=True)
        components = service_repo.list_by_ids(service_ids)
        return components.filter(tenant_service_group_id=upgrade_group_id)

    def get_rainbond_services(self, group_id, group_key, upgrade_group_id=None):
        """获取云市应用下的所有组件"""
        gsr = group_service_relation_repo.get_services_by_group(group_id)
        service_ids = gsr.values_list('service_id', flat=True)
        components = service_repo.get_services_by_service_ids_and_group_key(group_key, service_ids)
        if upgrade_group_id:
            return components.filter(tenant_service_group_id=upgrade_group_id)
        return components

    def get_group_service_sources(self, group_id):
        """查询某一应用下的组件源信息"""
        gsr = group_service_relation_repo.get_services_by_group(group_id)
        service_ids = gsr.values_list('service_id', flat=True)
        return service_source_repo.get_service_sources_by_service_ids(service_ids)

    # get component resource list, component will in app and belong to group_ids
    def get_component_and_resource_by_group_ids(self, app_id, group_ids):
        gsr = group_service_relation_repo.get_services_by_group(app_id)
        components = service_repo.get_services_by_service_group_ids(gsr.values_list('service_id', flat=True), group_ids)
        service_ids = components.values_list('service_id', flat=True)
        return components, service_source_repo.get_service_sources_by_service_ids(service_ids)

    def get_group_service_source(self, service_id):
        """ get only one service source"""
        return service_source_repo.get_service_sources_by_service_ids([service_id])

    def get_service_source_by_group_key(self, group_key):
        """ get service source by group key"""
        return service_source_repo.get_service_sources_by_group_key(group_key)

    @transaction.atomic
    def delete_app(self, tenant, region_name, app):
        if app.app_type == AppType.helm.name:
            self._delete_helm_app(tenant, region_name, app)
            return
        self._delete_rainbond_app(tenant, region_name, app)

    def _delete_helm_app(self, tenant, region_name, app, user=None):
        """
        For helm application,  can be delete directly, regardless of whether there are components
        """
        # delete components
        components = self.list_components(app.app_id)
        group_service_relation_repo.delete_relation_by_group_id(app.app_id)
        # avoid circular import
        from console.services.app_actions import app_manage_service
        app_manage_service.delete_components(tenant, components, user)
        self._delete_app(tenant.tenant_name, region_name, app.app_id)

    def _delete_rainbond_app(self, tenant, region_name, app):
        self._delete_app(tenant.tenant_name, region_name, app.app_id)

    @staticmethod
    def _delete_app(tenant_name, region_name, app_id):
        group_repo.delete_group_by_pk(app_id)
        upgrade_repo.delete_app_record_by_group_id(app_id)
        try:
            region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        except RegionApp.DoesNotExist:
            return
        keys = []
        migrate_record = migrate_repo.get_by_original_group_id(app_id)
        if migrate_record:
            for record in migrate_record:
                keys.append(record.restore_id)
        region_api.delete_app(region_name, tenant_name, region_app_id, {"etcd_keys": keys})

    def get_service_group_memory(self, app_template):
        """获取一应用组件内存"""
        try:
            apps = app_template["apps"]
            total_memory = 0
            for app in apps:
                extend_method_map = app.get("extend_method_map", None)
                if extend_method_map and extend_method_map["init_memory"]:
                    total_memory += extend_method_map["min_node"] * extend_method_map["init_memory"]
                elif extend_method_map and extend_method_map["min_memory"]:
                    total_memory += extend_method_map["min_node"] * extend_method_map["min_memory"]
                else:
                    total_memory += 128
            return total_memory
        except Exception as e:
            logger.debug("==============================>{0}".format(e))
            return 0

    def get_apps_list(self, team_id=None, region_name=None, query=None):
        return group_repo.get_apps_list(team_id, region_name, query)

    # get apps by service ids
    # return app id and service id maps
    def get_app_id_by_service_ids(self, service_ids):
        sgr = ServiceGroupRelation.objects.filter(service_id__in=service_ids)
        return {s.service_id: s.group_id for s in sgr}

    def count_ingress_by_app_id(self, tenant_id, region_name, app_id):
        # list service_ids
        service_ids = group_service_relation_repo.list_serivce_ids_by_app_id(tenant_id, region_name, app_id)
        if not service_ids:
            return 0

        region = region_repo.get_by_region_name(region_name)

        # count ingress
        return domain_repo.count_by_service_ids(region.region_id, service_ids) + tcp_domain.count_by_service_ids(
            region.region_id, service_ids)

    def set_app_update_time_by_service(self, service):
        sg = self.get_service_group_info(service.service_id)
        if sg and sg.ID:
            group_repo.update_group_time(sg.ID)

    @transaction.atomic
    def update_governance_mode(self, tenant, region_name, app_id, governance_mode, action=None):
        # update the value of host env. eg. MYSQL_HOST
        component_ids = group_service_relation_repo.list_serivce_ids_by_app_id(tenant.tenant_id, region_name, app_id)

        components = service_repo.list_by_ids(component_ids)
        components = {cpt.component_id: cpt for cpt in components}

        ports = port_repo.list_inner_ports_by_service_ids(tenant.tenant_id, component_ids)
        ports = {port.service_id + str(port.container_port): port for port in ports}

        envs = env_var_repo.list_envs_by_component_ids(tenant.tenant_id, component_ids)
        for env in envs:
            if not env.is_host_env():
                continue
            cpt = components.get(env.service_id)
            if not cpt:
                continue
            port = ports.get(env.service_id + str(env.container_port))
            if not port:
                continue
            if governance_mode != GovernanceModeEnum.BUILD_IN_SERVICE_MESH.name:
                env.attr_value = port.k8s_service_name if port.k8s_service_name else cpt.service_alias + "-" + str(
                    port.container_port)
            else:
                env.attr_value = "127.0.0.1"
        env_var_repo.bulk_update(envs)
        group_repo.update_governance_mode(tenant.tenant_id, region_name, app_id, governance_mode)

        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        self.sync_envs(tenant.tenant_name, region_name, region_app_id, components.values(), envs)
        region_api.update_app(region_name, tenant.tenant_name, region_app_id, {"governance_mode": governance_mode})
        # If the governance pattern is not the default governance pattern, you need to create a CustomResource
        if action == "create":
            governance_cr = region_api.create_governance_mode_cr(region_name, tenant.tenant_name, region_app_id,
                                                                 {"provisioner": governance_mode})
            return governance_cr
        if action == "update":
            governance_cr = region_api.update_governance_mode_cr(region_name, tenant.tenant_name, region_app_id,
                                                                 {"provisioner": governance_mode})
            return governance_cr
        if action == "delete":
            governance_cr = region_api.delete_governance_mode_cr(region_name, tenant.tenant_name, region_app_id)
            return governance_cr

    @staticmethod
    def sync_envs(tenant_name, region_name, region_app_id, components, envs):
        # make sure attr_value is string.
        for env in envs:
            if type(env.attr_value) != str:
                env.attr_value = str(env.attr_value)

        new_components = []
        for cpt in components:
            if cpt.create_status != "complete":
                continue

            component_base = cpt.to_dict()
            component_base["component_id"] = component_base["service_id"]
            component_base["component_name"] = component_base["service_name"]
            component_base["component_alias"] = component_base["service_alias"]
            component_base["container_cpu"] = cpt.min_cpu
            component_base["container_memory"] = cpt.min_memory
            component_base["replicas"] = cpt.min_node
            component = {
                "component_base": component_base,
                "envs": [env.to_dict() for env in envs if env.service_id == cpt.component_id]
            }
            new_components.append(component)

        if not new_components:
            return

        body = {
            "components": new_components,
        }
        region_api.sync_components(tenant_name, region_name, region_app_id, body)

    @staticmethod
    def list_kubernetes_services(tenant_id, region_name, app_id):
        # list service_ids
        service_ids = group_service_relation_repo.list_serivce_ids_by_app_id(tenant_id, region_name, app_id)
        if not service_ids:
            return []
        # service_id to service_alias
        services = service_repo.list_by_ids(service_ids)
        service_aliases = {service.service_id: service.service_alias for service in services}
        service_cnames = {service.service_id: service.service_cname for service in services}

        ports = port_repo.list_inner_ports_by_service_ids(tenant_id, service_ids)
        # build response
        k8s_services = []
        for port in ports:
            # set service_alias_container_port as default kubernetes service name
            k8s_service_name = port.k8s_service_name if port.k8s_service_name else service_aliases[port.service_id] + "-" + str(
                port.container_port)
            k8s_services.append({
                "service_id": port.service_id,
                "service_cname": service_cnames[port.service_id],
                "port": port.container_port,
                "port_alias": port.port_alias,
                "k8s_service_name": k8s_service_name,
            })

        return k8s_services

    @transaction.atomic()
    def update_kubernetes_services(self, tenant, region_name, app, k8s_services):
        from console.services.app_config import port_service
        port_service.check_k8s_service_names(tenant.tenant_id, k8s_services)

        # check if the given k8s_services belong to the app based on app_id
        app_component_ids = group_service_relation_repo.list_serivce_ids_by_app_id(tenant.tenant_id, region_name, app.app_id)
        component_ids = []
        for k8s_service in k8s_services:
            if k8s_service["service_id"] not in app_component_ids:
                raise AbortRequest("service({}) not belong to app({})".format(k8s_service["service_id"], app.app_id))
            component_ids.append(k8s_service["service_id"])

        port_service.update_by_k8s_services(tenant, region_name, app, k8s_services)

    @staticmethod
    def get_app_status(tenant, region_name, app_id):
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        status = region_api.get_app_status(region_name, tenant.tenant_name, region_app_id)
        if status.get("status") == "NIL":
            status["status"] = None
        overrides = status.get("overrides", [])
        if overrides:
            status["overrides"] = [{override.split("=")[0]: override.split("=")[1]} for override in overrides]
        return status

    @staticmethod
    def get_detect_process(tenant, region_name, app_id):
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        process = region_api.get_app_detect_process(region_name, tenant.tenant_name, region_app_id)
        return process

    def install_app(self, tenant, region_name, app_id, overrides):
        if overrides:
            overrides = self._parse_overrides(overrides)

        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        region_api.install_app(region_name, tenant.tenant_name, region_app_id, {
            "overrides": overrides,
        })

    @staticmethod
    def get_pod(tenant, region_name, pod_name):
        return region_api.get_pod(region_name, tenant.tenant_name, pod_name)

    @staticmethod
    def list_components(app_id):
        service_groups = group_service_relation_repo.list_service_groups(app_id)
        return service_repo.list_by_ids([sg.service_id for sg in service_groups])

    def check_governance_mode(self, tenant, region_name, app_id, governance_mode):
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        return region_api.check_app_governance_mode(region_name, tenant.tenant_name, region_app_id, governance_mode)

    def get_file_and_dir(self, region_name, tenant_name, service_alias, path, pod_name, namespace):
        body = region_api.get_files(region_name, tenant_name, service_alias, quote(path), pod_name, namespace)
        return body["list"]

    def get_watch_managed_data(self, tenant, region_name, app_id):
        from console.services.app import app_service
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        watch_managed_data = base_service.get_watch_managed(region_name, tenant.tenant_name, region_app_id)
        services = list()
        if watch_managed_data:
            for service in watch_managed_data.get("services", []):
                if app_service.is_k8s_component_name_duplicate(app_id, service.get("name") + "-svc"):
                    continue
                if service.get("ip") != "None":
                    services.append({
                        "name": service.get("name") + "-svc",
                        "static": True,
                        "address": [service.get("ip") + ":" + port for port in service.get("port").split(",")]
                    })
                else:
                    services.append({
                        "name": service.get("name") + "-svc",
                        "static": False,
                        "namespace": tenant.namespace,
                        "service": service.get("name"),
                        "port": service.get("port")
                    })
        data = {
            "service": services,
        }
        return data


group_service = GroupService()

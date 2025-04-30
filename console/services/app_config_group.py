# -*- coding: utf-8 -*-
import json
import time
import logging

from django.db import transaction
from django.core.paginator import Paginator

from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_service_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app import service_repo
from console.models.main import ApplicationConfigGroup
from console.exception.bcode import ErrAppConfigGroupNotFound, ErrAppConfigGroupExists
from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.region_app import region_app_repo
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppConfigGroupService(object):
    @transaction.atomic
    def create_config_group(self, app_id, config_group_name, config_items, deploy_type, enable, service_ids, region_name,
                            team_name):
        # create application config group
        group_req = {
            "app_id": app_id,
            "config_group_name": config_group_name,
            "deploy_type": deploy_type,
            "enable": enable,
            "region_name": region_name,
            "config_group_id": make_uuid(),
        }

        try:
            app_config_group_repo.get(region_name, app_id, config_group_name)
        except ApplicationConfigGroup.DoesNotExist:
            cgroup = app_config_group_repo.create(**group_req)
            create_items_and_services(cgroup, config_items, service_ids)
            region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
            region_api.create_app_config_group(
                region_name, team_name, region_app_id, {
                    "app_id": region_app_id,
                    "config_group_name": config_group_name,
                    "deploy_type": deploy_type,
                    "service_ids": service_ids,
                    "config_items": config_items,
                    "enable": enable,
                })
        else:
            raise ErrAppConfigGroupExists
        return self.get_config_group(region_name, app_id, config_group_name)

    def json_config_groups(self, config_group_name, config_items, enable, services_names):
        config_groups_dict = dict()
        config_groups_dict["配置组名称"] = config_group_name
        config_groups_dict["生效状态"] = "开启" if enable else "关闭"
        config_groups_dict["配置项"] = config_items
        config_groups_dict["生效组件"] = ','.join(services_names)
        return json.dumps(config_groups_dict, ensure_ascii=False)

    def get_config_group(self, region_name, app_id, config_group_name):
        try:
            cgroup = app_config_group_repo.get(region_name, app_id, config_group_name)
        except ApplicationConfigGroup.DoesNotExist:
            raise ErrAppConfigGroupNotFound
        config_group_info = build_response(cgroup)
        return config_group_info

    @transaction.atomic
    def update_config_group(self, region_name, app_id, config_group_name, config_items, enable, service_ids, team_name):
        group_req = {
            "enable": enable,
            "update_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
        }
        try:
            cgroup = app_config_group_repo.get(region_name, app_id, config_group_name)
        except ApplicationConfigGroup.DoesNotExist:
            raise ErrAppConfigGroupNotFound
        else:
            app_config_group_repo.update(region_name, app_id, config_group_name, **group_req)
            app_config_group_item_repo.delete(cgroup.config_group_id)
            app_config_group_service_repo.delete(cgroup.config_group_id)
            create_items_and_services(cgroup, config_items, service_ids)
            region_app_id = region_app_repo.get_region_app_id(cgroup.region_name, app_id)
            region_api.update_app_config_group(cgroup.region_name, team_name, region_app_id, cgroup.config_group_name, {
                "service_ids": service_ids,
                "config_items": config_items,
                "enable": enable,
            })
        return self.get_config_group(region_name, app_id, config_group_name)

    def list_config_groups(self, region_name, app_id, page, page_size, query=None):
        cgroup_info = []
        config_groups = app_config_group_repo.list(region_name, app_id)
        if query:
            config_groups = config_groups.filter(config_group_name__contains=query)
        p = Paginator(config_groups, page_size)
        total = p.count
        for cgroup in p.page(page):
            config_group_info = build_response(cgroup)
            cgroup_info.append(config_group_info)

        return cgroup_info, total

    def list(self, region_name, app_id):
        cgroup_info = {}
        config_groups = app_config_group_repo.list(region_name, app_id)
        for cgroup in config_groups:
            items = app_config_group_item_repo.list(cgroup.config_group_id)
            config_items = {item.item_key: item.item_value for item in items}
            cgroup_services = app_config_group_service_repo.list(cgroup.config_group_id)
            cgroup_service_ids = [cgroup_service.service_id for cgroup_service in cgroup_services]
            cgroup_info.update({cgroup.config_group_name: {"config_items": config_items, "component_ids": cgroup_service_ids}})
        return cgroup_info

    @transaction.atomic
    def delete_config_group(self, region_name, team_name, app_id, config_group_name):
        cgroup = app_config_group_repo.get(region_name, app_id, config_group_name)
        region_app_id = region_app_repo.get_region_app_id(cgroup.region_name, app_id)
        try:
            region_api.delete_app_config_group(cgroup.region_name, team_name, region_app_id, cgroup.config_group_name)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e

        app_config_group_item_repo.delete(cgroup.config_group_id)
        app_config_group_service_repo.delete(cgroup.config_group_id)
        app_config_group_repo.delete(cgroup.region_name, app_id, config_group_name)

    @transaction.atomic
    def batch_delete_config_group(self, region_name, team_name, app_id):
        config_groups = app_config_group_repo.list(region_name, app_id)
        names = [config_group.config_group_name for config_group in config_groups]
        config_group_ids = [config_group.config_group_id for config_group in config_groups]
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        config_group_names = ",".join(names)
        try:
            region_api.batch_delete_app_config_group(region_name, team_name, region_app_id, config_group_names)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        app_config_group_item_repo.batch_delete(config_group_ids)
        app_config_group_service_repo.batch_delete(config_group_ids)
        app_config_group_repo.batch_delete(region_name, app_id, names)

    def count_by_app_id(self, region_name, app_id):
        return app_config_group_repo.count(region_name, app_id)


def convert_todict(cgroup_items, cgroup_services):
    # Convert application config group items to dict
    config_group_items = []
    if cgroup_items:
        for i in cgroup_items:
            cgi = i.to_dict()
            config_group_items.append(cgi)
    # Convert application config group services to dict
    config_group_services = []
    if cgroup_services:
        for s in cgroup_services:
            service = service_repo.get_service_by_service_id(s.service_id)
            if not service:
                continue
            cgs = s.to_dict()
            if service:
                cgs["service_cname"] = service.service_cname
                cgs["service_alias"] = service.service_alias
            config_group_services.append(cgs)
    return config_group_items, config_group_services


def build_response(cgroup):
    cgroup_services = app_config_group_service_repo.list(cgroup.config_group_id)
    cgroup_items = app_config_group_item_repo.list(cgroup.config_group_id)
    config_group_items, config_group_services = convert_todict(cgroup_items, cgroup_services)

    config_group_info = cgroup.to_dict()
    config_group_info["services"] = config_group_services
    config_group_info["config_items"] = config_group_items
    config_group_info["services_num"] = len(config_group_services)
    return config_group_info


def create_items_and_services(app_config_group, config_items, service_ids):
    # create application config group items
    if config_items:
        for item in config_items:
            group_item = {
                "update_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                "app_id": app_config_group.app_id,
                "config_group_name": app_config_group.config_group_name,
                "item_key": item["item_key"],
                "item_value": item["item_value"],
                "config_group_id": app_config_group.config_group_id,
            }
            app_config_group_item_repo.create(**group_item)

    # create application config group services takes effect
    if service_ids is not None:
        for sid in service_ids:
            s = service_repo.get_service_by_service_id(sid)
            group_service = {
                "update_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                "app_id": app_config_group.app_id,
                "config_group_name": app_config_group.config_group_name,
                "service_id": s.service_id,
                "config_group_id": app_config_group.config_group_id,
            }
            app_config_group_service_repo.create(**group_service)


app_config_group_service = AppConfigGroupService()

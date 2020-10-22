# -*- coding: utf-8 -*-
import time
import uuid

from django.db import transaction
from django.core.paginator import Paginator

from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_service_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app import service_repo
from console.models.main import ApplicationConfigGroup
from console.exception.exceptions import ErrAppConfigGroupNotFound
from console.exception.exceptions import ErrAppConfigGroupExists
from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.region_app import region_app_repo

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
            "uuid": str(uuid.uuid4()).replace('-', ''),
        }

        try:
            app_config_group_repo.get(region_name, app_id, config_group_name)
        except ApplicationConfigGroup.DoesNotExist:
            cgroup = app_config_group_repo.create(**group_req)
            print(cgroup.uuid)
            create_items_and_services(cgroup, config_items, service_ids)
            region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
            region_api.create_app_config_group(
                region_name, team_name, region_app_id, {
                    "app_id": region_app_id,
                    "config_group_name": config_group_name,
                    "deploy_type": deploy_type,
                    "service_ids": service_ids,
                    "config_items": config_items,
                })
        else:
            raise ErrAppConfigGroupExists
        return self.get_config_group(region_name, app_id, config_group_name)

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
            app_config_group_item_repo.delete(cgroup.uuid)
            app_config_group_service_repo.delete(cgroup.uuid)
            create_items_and_services(cgroup, config_items, service_ids)
            region_app_id = region_app_repo.get_region_app_id(cgroup.region_name, app_id)
            region_api.update_app_config_group(cgroup.region_name, team_name, region_app_id, cgroup.config_group_name, {
                "service_ids": service_ids,
                "config_items": config_items,
            })
        return self.get_config_group(region_name, app_id, config_group_name)

    def list_config_groups(self, region_name, app_id, page, page_size):
        cgroup_info = []
        config_groups = app_config_group_repo.list(region_name, app_id)

        p = Paginator(config_groups, page_size)
        total = p.count
        for cgroup in p.page(page):
            config_group_info = build_response(cgroup)
            cgroup_info.append(config_group_info)

        return cgroup_info, total

    @transaction.atomic
    def delete_config_group(self, region_name, team_name, app_id, config_group_name):
        cgroup = app_config_group_repo.get(region_name, app_id, config_group_name)
        region_app_id = region_app_repo.get_region_app_id(cgroup.region_name, app_id)
        try:
            region_api.delete_app_config_group(cgroup.region_name, team_name, region_app_id, cgroup.config_group_name)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e

        app_config_group_item_repo.delete(cgroup.uuid)
        app_config_group_service_repo.delete(cgroup.uuid)
        app_config_group_repo.delete(cgroup.region_name, app_id, config_group_name)


def convert_todict(cgroup_items, cgroup_services):
    # Convert application config group items to dict
    config_group_items = []
    for i in cgroup_items:
        cgi = i.to_dict()
        config_group_items.append(cgi)
    # Convert application config group services to dict
    config_group_services = []
    for s in cgroup_services:
        cgs = s.to_dict()
        config_group_services.append(cgs)
    return config_group_items, config_group_services


def build_response(cgroup):
    cgroup_services = app_config_group_service_repo.list(cgroup.uuid)
    cgroup_items = app_config_group_item_repo.list(cgroup.uuid)
    config_group_items, config_group_services = convert_todict(cgroup_items, cgroup_services)

    config_group_info = cgroup.to_dict()
    config_group_info["services"] = config_group_services
    config_group_info["config_items"] = config_group_items
    return config_group_info


def create_items_and_services(app_config_group, config_items, service_ids):
    # create application config group items
    for item in config_items:
        group_item = {
            "update_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
            "app_id": app_config_group.app_id,
            "config_group_name": app_config_group.config_group_name,
            "item_key": item["item_key"],
            "item_value": item["item_value"],
            "uuid": app_config_group.uuid,
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
                "uuid": app_config_group.uuid,
            }
            app_config_group_service_repo.create(**group_service)


app_config_group_service = AppConfigGroupService()

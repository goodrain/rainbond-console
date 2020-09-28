# -*- coding: utf-8 -*-
from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_service_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app import service_repo
from django.db import transaction


class AppConfigGroupService(object):
    @transaction.atomic
    def create_config_group(self, app_id, config_group_name, config_items, deploy_type, deploy_status, service_ids,
                            region_name):
        # create application config group
        group_req = {
            "app_id": app_id,
            "config_group_name": config_group_name,
            "deploy_type": deploy_type,
            "deploy_status": deploy_status,
            "region_name": region_name,
        }
        app_config_group_repo.create(**group_req)

        # create application config group items
        for item in config_items:
            group_item = {
                "app_id": app_id,
                "config_group_name": config_group_name,
                "item_key": item["item_key"],
                "item_value": item["item_value"],
            }
            app_config_group_item_repo.create(**group_item)

        # create application config group services takes effect
        if service_ids is not None:
            for sid in service_ids:
                s = service_repo.get_service_by_service_id(sid["service_id"])
                group_service = {
                    "app_id": app_id,
                    "config_group_name": config_group_name,
                    "service_id": s.service_id,
                    "service_alias": s.service_alias,
                }
                app_config_group_service_repo.create(**group_service)
        return self.get_config_group(app_id, config_group_name)

    def get_config_group(self, app_id, config_group_name):
        cgroup = app_config_group_repo.get_config_group_by_id(app_id, config_group_name)
        cgroup_services = app_config_group_service_repo.list_config_group_services_by_id(app_id, cgroup.config_group_name)
        cgroup_items = app_config_group_item_repo.list_config_group_items_by_id(app_id, cgroup.config_group_name)

        config_group_items, config_group_services = convert_todict(cgroup_items, cgroup_services)
        config_group = {
            "create_time": cgroup.create_time,
            "update_time": cgroup.update_time,
            "app_id": app_id,
            "config_group_name": cgroup.config_group_name,
            "config_items": config_group_items,
            "deploy_type": cgroup.deploy_type,
            "deploy_status": cgroup.deploy_status,
            "services": config_group_services,
        }
        return config_group

    def list_config_groups(self, app_id, page, page_size):
        cgroup_info = []
        config_groups = app_config_group_repo.list_config_groups_by_app_id(app_id, page, page_size)
        total = app_config_group_repo.count_config_groups_by_app_id(app_id)

        for cgroup in config_groups:
            cgroup_services = app_config_group_service_repo.list_config_group_services_by_id(app_id, cgroup.config_group_name)
            cgroup_items = app_config_group_item_repo.list_config_group_items_by_id(app_id, cgroup.config_group_name)

            config_group_items, config_group_services = convert_todict(cgroup_items, cgroup_services)
            cgroup_info.append({
                "create_time": cgroup.create_time,
                "update_time": cgroup.update_time,
                "config_group_name": cgroup.config_group_name,
                "config_items": config_group_items,
                "deploy_type": cgroup.deploy_type,
                "deploy_status": cgroup.deploy_status,
                "services": config_group_services,
            })

        result = {
            "list": cgroup_info,
            "page": page,
            "page_size": page_size,
            "total": total,
        }
        return result

    @transaction.atomic
    def delete_config_group(self, app_id, config_group_name):
        app_config_group_item_repo.delete(app_id, config_group_name)
        app_config_group_service_repo.delete(app_id, config_group_name)
        app_config_group_repo.delete(app_id, config_group_name)


def convert_todict(cgroup_items, cgroup_services):
    # Convert application config group items to dict
    config_group_items = []
    for i in cgroup_items:
        cgi = i.to_dict()
        config_group_items.append({
            "item_key": cgi["item_key"],
            "item_value": cgi["item_value"],
        })
    # Convert application config group services to dict
    config_group_services = []
    for i in cgroup_services:
        cgi = i.to_dict()
        config_group_services.append({
            "service_id": cgi["service_id"],
            "service_alias": cgi["service_alias"],
        })
    return config_group_items, config_group_services


app_config_group = AppConfigGroupService()

from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_service_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app import service_repo
from django.db import transaction
from console.exception.main import ServiceHandleException


class AppConfigGroupService(object):
    @transaction.atomic
    def create_config_group(self, app_id, config_group_name, config_items, deploy_type, deploy_status, service_ids,
                            region_name):
        group_req = {
            "app_id": app_id,
            "config_group_name": config_group_name,
            "deploy_type": deploy_type,
            "deploy_status": deploy_status,
            "region_name": region_name,
        }
        app_config_group_repo.create(**group_req)

        group_item_reqs = []
        for item in config_items:
            group_item_reqs.append({
                "app_id": app_id,
                "config_group_name": config_group_name,
                "item_key": item.item_key,
                "item_value": item.item_value,
            })
        app_config_group_item_repo.create(**group_item_reqs)

        group_service_reqs = []
        for sid in service_ids:
            s = service_repo.get_service_by_service_id(sid)
            group_service_reqs.append({
                "app_id": app_id,
                "config_group_name": config_group_name,
                "service_id": s.service_id,
                "service_alias": s.service_alias,
            })
        app_config_group_service_repo.create(**group_service_reqs)

    def list_config_groups(self, app_id, page, page_size):
        cgroup_info = []
        config_groups = app_config_group_repo.list_config_groups_by_app_id(app_id, page, page_size)
        total = app_config_group_repo.count_config_groups_by_app_id(app_id)

        for cgroup in config_groups:
            config_group_services = app_config_group_service_repo.list_config_group_services_by_id(
                app_id, cgroup.config_group_name)
            config_group_items = app_config_group_item_repo.list_config_group_items_by_id(app_id, cgroup.config_group_name)
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

    def get_config_group(self, app_id, config_group_name):
        cgroup = app_config_group_repo.get_config_group_by_id(app_id, config_group_name)
        config_group_services = app_config_group_service_repo.list_config_group_services_by_id(app_id, cgroup.config_group_name)
        config_group_items = app_config_group_item_repo.list_config_group_items_by_id(app_id, cgroup.config_group_name)

        config_group = {
            "create_time": cgroup.create_time,
            "update_time": cgroup.update_time,
            "config_group_name": cgroup.config_group_name,
            "config_items": config_group_items,
            "deploy_type": cgroup.deploy_type,
            "deploy_status": cgroup.deploy_status,
            "services": config_group_services,
        }
        return config_group

    @transaction.atomic
    def delete_config_group(self, app_id, config_group_name):
        acg = app_config_group_repo.get_config_group_by_id(app_id, config_group_name)
        if not acg:
            raise ServiceHandleException(msg="application config group is not found", msg_show="应用配置组不存在", status_code=404)
        app_config_group_repo.delete(app_id, config_group_name)
        app_config_group_item_repo.delete(app_id, config_group_name)
        app_config_group_service_repo.delete(app_id, config_group_name)


app_config_group = AppConfigGroupService()

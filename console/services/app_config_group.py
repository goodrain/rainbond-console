from console.repositories.app_config_group import app_config_group_repo
from console.repositories.app_config_group import app_config_group_service_repo
from console.repositories.app_config_group import app_config_group_item_repo
from console.repositories.app import service_repo
from django.db import transaction


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


app_config_group = AppConfigGroupService()

from console.models.main import ApplicationConfigGroup
from console.models.main import ConfigGroupService
from console.models.main import ConfigGroupItem


class ApplicationConfigGroupRepository(object):
    def create(self, **data):
        return ApplicationConfigGroup.objects.create(**data)

    def update(self, app_id, config_group_name, **data):
        ApplicationConfigGroup.objects.filter(app_id=app_id, config_group_name=config_group_name).update(**data)
        res = ApplicationConfigGroup.objects.get(app_id=app_id, config_group_name=config_group_name)
        return res

    def get_config_group_by_id(self, app_id, config_group_name):
        return ApplicationConfigGroup.objects.get(app_id=app_id, config_group_name=config_group_name)

    def list_config_groups_by_app_id(self, app_id):
        return ApplicationConfigGroup.objects.filter(app_id=app_id)

    def delete(self, app_id, config_group_name):
        application = ApplicationConfigGroup.objects.get(app_id=app_id, config_group_name=config_group_name)
        row = ApplicationConfigGroup.objects.filter(app_id=application.ID).delete()
        return row > 0


class ApplicationConfigGroupServiceRepository(object):
    def create(self, **data):
        return ConfigGroupService.objects.create(**data)

    def list_config_group_services_by_id(self, app_id, config_group_name):
        return ConfigGroupService.objects.filter(app_id=app_id, config_group_name=config_group_name)

    def delete(self, app_id, config_group_name):
        return ConfigGroupService.objects.filter(app_id=app_id, config_group_name=config_group_name).delete()



class ApplicationConfigGroupItemRepository(object):
    def create(self, **data):
        return ConfigGroupItem.objects.create(**data)

    def update(self, app_id, config_group_name, item_key, **data):
        ConfigGroupItem.objects.filter(app_id=app_id, config_group_name=config_group_name, item_key=item_key).update(**data)
        res = ConfigGroupItem.objects.get(app_id=app_id, config_group_name=config_group_name, item_key=item_key)
        return res

    def list_config_group_items_by_id(self, app_id, config_group_name):
        return ConfigGroupItem.objects.filter(app_id=app_id, config_group_name=config_group_name)

    def delete(self, app_id, config_group_name):
        return ConfigGroupItem.objects.filter(app_id=app_id, config_group_name=config_group_name).delete()


app_config_group_repo = ApplicationConfigGroupRepository()
app_config_group_service_repo = ApplicationConfigGroupServiceRepository()
app_config_group_item_repo = ApplicationConfigGroupItemRepository()

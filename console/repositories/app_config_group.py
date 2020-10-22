from console.models.main import ApplicationConfigGroup
from console.models.main import ConfigGroupService
from console.models.main import ConfigGroupItem


class ApplicationConfigGroupRepository(object):
    def create(self, **data):
        return ApplicationConfigGroup.objects.create(**data)

    def update(self, region_name, app_id, config_group_name, **data):
        return ApplicationConfigGroup.objects.filter(
            region_name=region_name, app_id=app_id, config_group_name=config_group_name).update(**data)

    def get(self, region_name, app_id, config_group_name):
        return ApplicationConfigGroup.objects.get(region_name=region_name, app_id=app_id, config_group_name=config_group_name)

    def list(self, region_name, app_id):
        return ApplicationConfigGroup.objects.filter(region_name=region_name, app_id=app_id).order_by('-create_time')

    def count(self, region_name, app_id):
        return ApplicationConfigGroup.objects.filter(region_name=region_name, app_id=app_id).count()

    def delete(self, region_name, app_id, config_group_name):
        return ApplicationConfigGroup.objects.filter(
            region_name=region_name, app_id=app_id, config_group_name=config_group_name).delete()


class ApplicationConfigGroupServiceRepository(object):
    def create(self, **data):
        return ConfigGroupService.objects.create(**data)

    def list(self, app_id, config_group_name):
        return ConfigGroupService.objects.filter(app_id=app_id, config_group_name=config_group_name)

    def delete(self, app_id, config_group_name):
        return ConfigGroupService.objects.filter(app_id=app_id, config_group_name=config_group_name).delete()


class ApplicationConfigGroupItemRepository(object):
    def create(self, **data):
        return ConfigGroupItem.objects.create(**data)

    def list(self, app_id, config_group_name):
        return ConfigGroupItem.objects.filter(app_id=app_id, config_group_name=config_group_name)

    def delete(self, app_id, config_group_name):
        return ConfigGroupItem.objects.filter(app_id=app_id, config_group_name=config_group_name).delete()


app_config_group_repo = ApplicationConfigGroupRepository()
app_config_group_service_repo = ApplicationConfigGroupServiceRepository()
app_config_group_item_repo = ApplicationConfigGroupItemRepository()

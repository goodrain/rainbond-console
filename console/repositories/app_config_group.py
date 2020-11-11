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

    def get_by_config_group_id(self, config_group_id):
        cgroup = ApplicationConfigGroup.objects.filter(config_group_id=config_group_id)
        if cgroup:
            return cgroup[0]
        return None

    def get_config_group_in_use(self, region_name, app_id):
        cgroups = ApplicationConfigGroup.objects.filter(region_name=region_name, app_id=app_id, enable=True)
        cgroup_ids = []
        if cgroups:
            for cgroup in cgroups:
                cgroup_services = app_config_group_service_repo.list(cgroup.config_group_id)
                if cgroup_services:
                    cgroup_ids.append(cgroup.config_group_id)
        return cgroup_ids

class ApplicationConfigGroupServiceRepository(object):
    def create(self, **data):
        return ConfigGroupService.objects.create(**data)

    def list(self, config_group_id):
        return ConfigGroupService.objects.filter(config_group_id=config_group_id)

    def delete(self, config_group_id):
        return ConfigGroupService.objects.filter(config_group_id=config_group_id).delete()


class ApplicationConfigGroupItemRepository(object):
    def create(self, **data):
        return ConfigGroupItem.objects.create(**data)

    def list(self, config_group_id):
        return ConfigGroupItem.objects.filter(config_group_id=config_group_id)

    def delete(self, config_group_id):
        return ConfigGroupItem.objects.filter(config_group_id=config_group_id).delete()


app_config_group_repo = ApplicationConfigGroupRepository()
app_config_group_service_repo = ApplicationConfigGroupServiceRepository()
app_config_group_item_repo = ApplicationConfigGroupItemRepository()

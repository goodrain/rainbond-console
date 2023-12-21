from console.models.main import ApplicationConfigGroup
from console.models.main import ConfigGroupService
from console.models.main import ConfigGroupItem


class ApplicationConfigGroupRepository(object):
    def create(self, **data):
        return ApplicationConfigGroup.objects.create(**data)

    def update(self, region_name, app_id, config_group_name, **data):
        return ApplicationConfigGroup.objects.filter(region_name=region_name,
                                                     app_id=app_id,
                                                     config_group_name=config_group_name).update(**data)

    def get(self, region_name, app_id, config_group_name):
        return ApplicationConfigGroup.objects.get(region_name=region_name, app_id=app_id, config_group_name=config_group_name)

    def list(self, region_name, app_id):
        return ApplicationConfigGroup.objects.filter(region_name=region_name, app_id=app_id).order_by('-create_time')

    def count(self, region_name, app_id):
        return ApplicationConfigGroup.objects.filter(region_name=region_name, app_id=app_id).count()

    def delete(self, region_name, app_id, config_group_name):
        return ApplicationConfigGroup.objects.filter(region_name=region_name,
                                                     app_id=app_id,
                                                     config_group_name=config_group_name).delete()

    def batch_delete(self, region_name, app_id, config_group_names):
        return ApplicationConfigGroup.objects.filter(region_name=region_name,
                                                     app_id=app_id,
                                                     config_group_name__in=config_group_names).delete()

    def list_by_service_ids(self, region_name, service_ids):
        config_group_ids = ConfigGroupService.objects.filter(service_id__in=service_ids, ).values_list("config_group_id",
                                                                                                       flat=True)
        return ApplicationConfigGroup.objects.filter(region_name=region_name, config_group_id__in=config_group_ids)

    def get_config_group_in_use(self, region_name, app_id):
        cgroups = ApplicationConfigGroup.objects.filter(region_name=region_name, app_id=app_id, enable=True)
        cgroup_infos = []
        if cgroups:
            for cgroup in cgroups:
                cgroup_services = app_config_group_service_repo.list(cgroup.config_group_id)
                if cgroup_services:
                    cgroup_info = {"config_group_id": cgroup.config_group_id, "config_group_name": cgroup.config_group_name}
                    cgroup_infos.append(cgroup_info)
        return cgroup_infos

    def is_exists(self, region_name, app_id, config_group_name):
        return ApplicationConfigGroup.objects.filter(region_name=region_name,
                                                     app_id=app_id,
                                                     config_group_name=config_group_name).exists()

    @staticmethod
    def bulk_create_or_update(config_groups):
        config_group_ids = [cg.config_group_id for cg in config_groups]
        ApplicationConfigGroup.objects.filter(config_group_id__in=config_group_ids).delete()
        ApplicationConfigGroup.objects.bulk_create(config_groups)


class ApplicationConfigGroupServiceRepository(object):
    def create(self, **data):
        return ConfigGroupService.objects.create(**data)

    def list(self, config_group_id):
        return ConfigGroupService.objects.filter(config_group_id=config_group_id)

    @staticmethod
    def list_by_app_id(app_id):
        return ConfigGroupService.objects.filter(app_id=app_id)

    def delete(self, config_group_id):
        return ConfigGroupService.objects.filter(config_group_id=config_group_id).delete()

    def batch_delete(self, config_group_ids):
        return ConfigGroupService.objects.filter(config_group_id__in=config_group_ids).delete()

    def list_by_service_id(self, service_id):
        return ConfigGroupService.objects.filter(service_id=service_id)

    def delete_effective_service(self, service_id):
        return ConfigGroupService.objects.filter(service_id=service_id).delete()

    @staticmethod
    def bulk_create_or_update(config_group_components):
        cgc_ids = [cgc.ID for cgc in config_group_components]
        ConfigGroupService.objects.filter(pk__in=cgc_ids).delete()
        ConfigGroupService.objects.bulk_create(config_group_components)


class ApplicationConfigGroupItemRepository(object):
    def create(self, **data):
        return ConfigGroupItem.objects.create(**data)

    def list(self, config_group_id):
        return ConfigGroupItem.objects.filter(config_group_id=config_group_id)

    @staticmethod
    def list_by_app_id(app_id):
        return ConfigGroupItem.objects.filter(app_id=app_id)

    def delete(self, config_group_id):
        return ConfigGroupItem.objects.filter(config_group_id=config_group_id).delete()

    def batch_delete(self, config_group_ids):
        return ConfigGroupItem.objects.filter(config_group_id__in=config_group_ids).delete()

    @staticmethod
    def bulk_create_or_update(items):
        item_ids = [item.ID for item in items]
        ConfigGroupItem.objects.filter(pk__in=item_ids).delete()
        ConfigGroupItem.objects.bulk_create(items)


app_config_group_repo = ApplicationConfigGroupRepository()
app_config_group_service_repo = ApplicationConfigGroupServiceRepository()
app_config_group_item_repo = ApplicationConfigGroupItemRepository()

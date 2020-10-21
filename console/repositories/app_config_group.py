from console.models.main import ApplicationConfigGroup
from console.models.main import ConfigGroupService
from console.models.main import ConfigGroupItem
from console.repositories.base import BaseConnection


class ApplicationConfigGroupRepository(object):
    def create(self, **data):
        return ApplicationConfigGroup.objects.create(**data)

    def update(self, region_name, app_id, config_group_name, **data):
        return ApplicationConfigGroup.objects.filter(
            region_name=region_name, app_id=app_id, config_group_name=config_group_name).update(**data)

    def get(self, region_name, app_id, config_group_name):
        return ApplicationConfigGroup.objects.get(region_name=region_name, app_id=app_id, config_group_name=config_group_name)

    def list(self, region_name, app_id, page=None, page_size=None):
        limit = ""
        if page is not None and page_size is not None:
            page = page if page > 0 else 1
            page = (page - 1) * page_size
            limit = "LIMIT {page}, {page_size}".format(page=page, page_size=page_size)
        where = """
                WHERE
                    region_name = "{region_name}"
                    AND
                    app_id = "{app_id}"
                """.format(
            region_name=region_name, app_id=app_id)
        sql = """
                SELECT
                    *
                FROM
                    app_config_group
                {where}
                ORDER BY
                    create_time desc
                {limit}
                """.format(
            where=where, limit=limit)
        conn = BaseConnection()
        return conn.query(sql)

    def count(self, region_name, app_id):
        return ApplicationConfigGroup.objects.filter(region_name=region_name, app_id=app_id).count()

    def delete(self, region_name, app_id, config_group_name):
        return ApplicationConfigGroup.objects.filter(
            region_name=region_name, app_id=app_id, config_group_name=config_group_name).delete()


class ApplicationConfigGroupServiceRepository(object):
    def create(self, **data):
        return ConfigGroupService.objects.create(**data)

    def list(self, region_name, app_id, config_group_name):
        return ConfigGroupService.objects.filter(region_name=region_name, app_id=app_id, config_group_name=config_group_name)

    def delete(self, region_name, app_id, config_group_name):
        return ConfigGroupService.objects.filter(
            region_name=region_name, app_id=app_id, config_group_name=config_group_name).delete()


class ApplicationConfigGroupItemRepository(object):
    def create(self, **data):
        return ConfigGroupItem.objects.create(**data)

    def list(self, region_name, app_id, config_group_name):
        return ConfigGroupItem.objects.filter(region_name=region_name, app_id=app_id, config_group_name=config_group_name)

    def delete(self, region_name, app_id, config_group_name):
        return ConfigGroupItem.objects.filter(
            region_name=region_name, app_id=app_id, config_group_name=config_group_name).delete()


app_config_group_repo = ApplicationConfigGroupRepository()
app_config_group_service_repo = ApplicationConfigGroupServiceRepository()
app_config_group_item_repo = ApplicationConfigGroupItemRepository()

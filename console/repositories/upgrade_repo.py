# coding: utf-8
import json
from datetime import datetime

from console.models.main import (AppUpgradeRecord, ServiceUpgradeRecord, UpgradeStatus)
from console.exception.bcode import ErrAppUpgradeRecordNotFound


class UpgradeRepo(object):
    def get_app_not_upgrade_record(self, **kwargs):
        result = AppUpgradeRecord.objects.filter(**kwargs).order_by("-update_time").first()
        if result is None:
            raise AppUpgradeRecord.DoesNotExist
        return result

    def create_app_upgrade_record(self, **kwargs):
        return AppUpgradeRecord.objects.create(**kwargs)

    def get_last_upgrade_record(self, tenant, app_id, upgrade_group_id):
        return AppUpgradeRecord.objects.filter(
            upgrade_group_id=upgrade_group_id, group_id=app_id, tenant_id=tenant.tenant_id).order_by("-update_time").first()

    def create_service_upgrade_record(self,
                                      app_upgrade_record,
                                      service,
                                      event_id,
                                      update,
                                      status=UpgradeStatus.UPGRADING.value,
                                      upgrade_type=ServiceUpgradeRecord.UpgradeType.UPGRADE.value):
        """创建组件升级记录"""
        return ServiceUpgradeRecord.objects.create(
            create_time=datetime.now(),
            app_upgrade_record=app_upgrade_record,
            service_id=service.service_id,
            service_cname=service.service_cname,
            upgrade_type=upgrade_type,
            event_id=event_id,
            update=json.dumps(update),
            status=status,
        )

    def change_app_record_status(self, app_record, status):
        """改变应用升级记录状态"""
        app_record.status = status
        app_record.save()

    def change_service_record_status(self, service_record, status):
        """改变组件升级记录状态"""
        service_record.status = status
        service_record.save()

    def delete_app_record_by_group_id(self, group_id):
        """级联删除升级记录"""
        AppUpgradeRecord.objects.filter(group_id=group_id).delete()

    @staticmethod
    def get_by_record_id(record_id):
        try:
            return AppUpgradeRecord.objects.get(pk=record_id)
        except AppUpgradeRecord.DoesNotExist:
            raise ErrAppUpgradeRecordNotFound


class ComponentUpgradeRecordRepository(object):
    @staticmethod
    def bulk_create(records):
        ServiceUpgradeRecord.objects.bulk_create(records)

    @staticmethod
    def list_by_app_record_id(app_record_id):
        return ServiceUpgradeRecord.objects.filter(app_upgrade_record_id=app_record_id)

    @staticmethod
    def bulk_update(records):
        # bulk_update is only available after django 2.2
        for record in records:
            record.save()


upgrade_repo = UpgradeRepo()
component_upgrade_record_repo = ComponentUpgradeRecordRepository()

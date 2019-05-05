# coding: utf-8
"""存放应用升级细节"""
from console.exception.main import AbortRequest
from console.models import AppUpgradeRecord
from console.models import UpgradeStatus
from console.repositories.event_repo import event_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.upgrade_repo import upgrade_repo


class UpgradeService(object):
    def get_or_create_upgrade_record(self, tenant_id, group_id, group_key):
        """获取或创建升级记录"""
        recode_kwargs = {
            "tenant_id": tenant_id,
            "group_id": group_id,
            "group_key": group_key,
        }
        try:
            app_record = upgrade_repo.get_app_not_upgrade_record(
                status__lt=UpgradeStatus.UPGRADED.value,
                **recode_kwargs
            )
        except AppUpgradeRecord.DoesNotExist:
            from console.services.group_service import group_service
            service_group_keys = group_service.get_group_service_sources(group_id).values_list('group_key', flat=True)
            if group_key not in set(service_group_keys or []):
                raise AbortRequest(
                    msg="the rainbond app is not in the group",
                    msg_show="该组中没有这个云市应用",
                    status_code=404
                )
            app = rainbond_app_repo.get_rainbond_app_qs_by_key(group_key).first()
            if not app:
                raise AbortRequest(
                    msg="No rainbond app found",
                    msg_show="没有找到此云市应用",
                    status_code=404
                )
            app_record = upgrade_repo.create_app_upgrade_record(
                group_name=app.group_name,
                **recode_kwargs
            )
        return app_record

    def get_app_not_upgrade_record(self, tenant_id, group_id, group_key):
        """获取未完成升级记录"""
        recode_kwargs = {
            "tenant_id": tenant_id,
            "group_id": int(group_id),
            "group_key": group_key,
        }
        try:
            return upgrade_repo.get_app_not_upgrade_record(
                status__lt=UpgradeStatus.UPGRADED.value,
                **recode_kwargs
            )
        except AppUpgradeRecord.DoesNotExist:
            return AppUpgradeRecord()

    def get_app_upgrade_versions(self, tenant, group_id, group_key):
        """获取云市应用可升级版本列表"""
        from console.services.group_service import group_service
        from console.services.market_app_service import market_app_service

        # 查询某一个云市应用下的所有服务
        services = group_service.get_rainbond_services(group_id, group_key)
        versions = set()
        for service in services:
            service_version = market_app_service.list_upgradeable_versions(tenant, service)
            versions |= set(service_version or [])
        return versions

    def synchronous_upgrade_status(self, tenant, record):
        """
        :type tenant: www.models.main.Tenants
        :type record: AppUpgradeRecord
        """
        from console.services.app_actions import event_service

        if record.status not in {UpgradeStatus.UPGRADING.value, UpgradeStatus.ROLLING.value}:
            return

        service_records = record.service_upgrade_records.all()
        event_service_mapping = {
            record.event_id: record
            for record in service_records
        }
        events = event_repo.get_events_by_event_ids(event_service_mapping.keys())
        # 去数据中心同步事件
        event_service.sync_region_service_event_status(tenant.region, tenant.tenant_name, events)

        for event in events:
            service_record = event_service_mapping[event.event_id]
            self._change_service_record_status(event, service_record)

        service_status = set(service_records.values_list('status', flat=True))
        judging_status = {
            # 升级中
            UpgradeStatus.UPGRADING.value: self._judging_status_upgrading,
            # 回滚中
            UpgradeStatus.ROLLING.value: self._judging_status_rolling,
        }

        status = judging_status[record.status](service_status)
        if status:
            record.status = status
            record.save()

    @staticmethod
    def _change_service_record_status(event, service_record):
        """变更服务升级记录状态"""
        operation = {
            # 升级中
            UpgradeStatus.UPGRADING.value: {
                "success": UpgradeStatus.UPGRADED.value,
                "failure": UpgradeStatus.UPGRADE_FAILED.value,
            },
            # 回滚中
            UpgradeStatus.ROLLING.value: {
                "success": UpgradeStatus.UPGRADING.value,
                "failure": UpgradeStatus.ROLLBACK_FAILED.value,
            },
        }
        status = operation.get(service_record.status, {}).get(event.status)
        if status:
            service_record.status = status
            service_record.save()

    @staticmethod
    def _judging_status_upgrading(service_status):
        """判断升级状态"""
        status = None
        if UpgradeStatus.UPGRADING.value in service_status:
            pass
        elif service_status == {UpgradeStatus.UPGRADE_FAILED.value, UpgradeStatus.UPGRADED.value}:
            status = UpgradeStatus.PARTIAL_UPGRADED.value
        elif service_status == {UpgradeStatus.UPGRADED.value}:
            status = UpgradeStatus.UPGRADED.value
        return status

    @staticmethod
    def _judging_status_rolling(service_status):
        """判断回滚状态"""
        status = None
        if UpgradeStatus.ROLLING.value in service_status:
            pass
        elif service_status == {UpgradeStatus.ROLLBACK_FAILED.value, UpgradeStatus.UPGRADED.value}:
            status = UpgradeStatus.PARTIAL_ROLLBACK.value
        elif service_status == {UpgradeStatus.ROLLBACK.value}:
            status = UpgradeStatus.ROLLBACK.value
        return status

    @staticmethod
    def serialized_upgrade_record(app_record):
        """序列化升级记录
        :type : AppUpgradeRecord
        """
        return dict(
            service_record=[
                service_record.to_dict()
                for service_record in app_record.service_upgrade_records.all()
            ],
            **app_record.to_dict()
        )


upgrade_service = UpgradeService()

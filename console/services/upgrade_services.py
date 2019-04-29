# coding: utf-8
"""存放应用升级细节"""
from console.exception.main import AbortRequest
from console.models import AppUpgradeRecord
from console.models import UpgradeStatus
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.upgrade_repo import upgrade_repo


class UpgradeService(object):
    def get_or_create_upgrade_record(self, tenant_id, group_id, group_key):
        """获取或创建升级记录"""
        recode_kwargs = {
            "tenant_id": tenant_id,
            "group_id": int(group_id),
            "group_key": group_key,
        }
        try:
            app_record = upgrade_repo.get_app_not_upgrade_record(
                status__lt=UpgradeStatus.UPGRADED.value,
                **recode_kwargs
            )
        except AppUpgradeRecord.DoesNotExist:
            app = rainbond_app_repo.get_market_app_qs_by_key(group_key).first()
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
            versions |= set(service_version)
        return versions


upgrade_service = UpgradeService()

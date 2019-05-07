# coding: utf-8
"""升级从云市安装的应用"""
from django.core.paginator import Paginator
from django.db.models import Q
from enum import Enum

from console.exception.main import AbortRequest
from console.models import AppUpgradeRecord
from console.models import UpgradeStatus
from console.repositories.app import service_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.upgrade_services import upgrade_service
from console.utils.reqparse import parse_args
from console.utils.reqparse import parse_argument
from console.utils.reqparse import parse_date
from console.utils.reqparse import parse_item
from console.utils.response import MessageResponse
from console.utils.shortcuts import get_object_or_404
from console.views.base import RegionTenantHeaderView


class GroupAppView(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """查询当前组下的云市应用"""
        group_id = int(group_id)
        group = group_service.get_group_or_404(self.tenant, self.response_region, group_id)

        service_group_keys = group_service.get_group_service_sources(group.ID).values_list('group_key', flat=True)

        def yield_app_info():
            for group_key in set(service_group_keys):
                app_qs = rainbond_app_repo.get_rainbond_app_qs_by_key(group_key=group_key)
                app = app_qs.first()
                if not app:
                    continue
                group_version_list = app_qs.values_list('version', flat=True)
                upgrade_versions = upgrade_service.get_app_upgrade_versions(self.tenant, group_id, group_key)
                not_upgrade_record = upgrade_service.get_app_not_upgrade_record(
                    self.tenant.tenant_id,
                    group_id,
                    group_key
                )
                yield {
                    'can_upgrade': bool(upgrade_versions),
                    'not_upgrade_record_id': not_upgrade_record.ID,
                    'group_version_list': group_version_list,
                    'group_key': app.group_key,
                    'group_name': app.group_name,
                    'share_user': app.share_user,
                    'share_team': app.share_team,
                    'tenant_service_group_id': app.tenant_service_group_id,
                    'pic': app.pic,
                    'source': app.source,
                    'describe': app.describe,
                    'enterprise_id': app.enterprise_id,
                    'is_official': app.is_official,
                    'details': app.details,
                    'min_memory': group_service.get_service_group_memory(app.app_template),
                }

        return MessageResponse(msg="success", list=[app_info for app_info in yield_app_info()])


class AppUpgradeVersion(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """获取某云市应用的可升级版本"""
        group_key = parse_argument(request, 'group_key', value_type=str, required=True,
                                   error='group_key is a required parameter')

        # 获取云市应用可升级版本列表
        versions = upgrade_service.get_app_upgrade_versions(self.tenant, int(group_id), group_key)
        return MessageResponse(msg="success", list=list(versions))


class AppUpgradeRecordsView(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """获取升级订单列表"""
        page = parse_argument(request, 'page', value_type=int, default=1)
        page_size = parse_argument(request, 'page_size', value_type=int, default=10)

        rq_args = (
            {'key': 'group_key', 'value_type': str},
            {'key': 'status', 'value_type': int},
        )

        qs_args = parse_args(request, rq_args)
        switch = {
            'group_key': Q(group_key=qs_args.get('group_key')),
            'status': Q(status=qs_args.get('status')),
        }
        q = Q()
        for arg_key in qs_args.keys():
            q &= switch[arg_key]

        record_qs = AppUpgradeRecord.objects.filter(
            tenant_id=self.tenant.tenant_id,
            group_id=int(group_id),
        ).filter(q)

        paginator = Paginator(record_qs, page_size)
        records = paginator.page(page)

        # 同步升级记录状态
        for record in records:
            upgrade_service.synchronous_upgrade_status(self.tenant, record)

        return MessageResponse(
            msg="success",
            bean={

            },
            list=[
                upgrade_service.serialized_upgrade_record(record)
                for record in records
            ]
        )

    def post(self, request, group_id, *args, **kwargs):
        """新增升级订单"""
        group_key = parse_item(request, 'group_key', required=True, error='group_key is a required parameter')

        recode_kwargs = {
            "tenant_id": self.tenant.tenant_id,
            "group_id": int(group_id),
            "group_key": group_key,
        }
        # 查询或创建一条升级记录
        app_record = upgrade_service.get_or_create_upgrade_record(**recode_kwargs)

        return MessageResponse(msg="success", bean=app_record.to_dict())


class AppUpgradeRecordView(RegionTenantHeaderView):
    def get(self, request, group_id, record_id, *args, **kwargs):
        """获取升级订单"""
        record = get_object_or_404(
            AppUpgradeRecord,
            msg="Upgrade record not found",
            tenant_id=self.tenant.tenant_id,
            group_id=int(group_id),
            pk=int(record_id)
        )

        # 同步升级记录状态
        upgrade_service.synchronous_upgrade_status(self.tenant, record)

        return MessageResponse(
            msg="success",
            bean=upgrade_service.serialized_upgrade_record(record)
        )


class UpgradeType(Enum):
    UPGRADE = 'upgrade'
    ADD = 'add'


class AppUpgradeInfoView(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """获取升级信息"""
        group_key = parse_argument(request, 'group_key', value_type=str, required=True,
                                   error='group_key is a required parameter')
        version = parse_argument(request, 'version', value_type=str, required=True,
                                 error='version is a required parameter')

        # 查询某一个云市应用下的所有服务
        services = group_service.get_rainbond_services(int(group_id), group_key)

        upgrade_info = [
            {
                'service': {
                    'service_id': service.service_id,
                    'service_cname': service.service_cname,
                    'service_key': service.service_key,
                    'type': UpgradeType.UPGRADE.value
                },
                'upgrade_info': upgrade_service.get_service_changes(service, self.tenant, version),
            }
            for service in services
        ]

        add_info = [
            {
                'service': {
                    'service_id': '',
                    'service_cname': service_info['service_cname'],
                    'service_key': service_info['service_key'],
                    'type': UpgradeType.ADD.value
                },
                'upgrade_info': service_info,
            }
            for service_info in upgrade_service.get_add_services(services, group_key, version)
        ]

        return MessageResponse(
            msg="success",
            list=upgrade_info + add_info
        )


class AppUpgradeTaskView(RegionTenantHeaderView):
    def post(self, request, group_id, *args, **kwargs):
        """提交升级任务"""
        rq_args = (
            {'key': 'upgrade_record_id', 'required': True, 'error': 'upgrade_record_id is a required parameter'},
            {'key': 'group_key', 'required': True, 'error': 'group_key is a required parameter'},
            {'key': 'version', 'required': True, 'error': 'version is a required parameter'},
            {'key': 'services', 'required': True, 'error': 'services is a required parameter'},
        )
        data = parse_date(request, rq_args)
        app_record = get_object_or_404(
            AppUpgradeRecord,
            msg="Upgrade record not found",
            tenant_id=self.tenant.tenant_id,
            group_id=int(group_id),
            group_key=data['group_key'],
            status=UpgradeStatus.NOT.value,
            pk=data['upgrade_record_id'],
        )
        app_record.version = data['version']
        app_record.save()
        # 处理新增的服务
        add_service_infos = [
            service['upgrade_info']
            for service in data['services']
            if service['service']['type'] == UpgradeType.ADD.value
        ]
        # 获取云市应用
        app = rainbond_app_repo.get_rainbond_app_by_key_version(group_key=data['group_key'], version=app_record.version)
        # mock app信息
        app.app_template = add_service_infos
        market_app_service.check_package_app_resource(self.tenant, self.response_region, app)
        market_app_service.install_service(self.tenant, self.response_region, self.user, group_id, app, True)

        # 处理需要升级的服务
        upgrade_service_infos = {
            service['service']['service_id']: service['upgrade_info']
            for service in data['services']
            if service['service']['type'] == UpgradeType.UPGRADE.value
        }
        services = service_repo.get_services_by_service_ids_and_group_key(
            data['group_key'], upgrade_service_infos.keys()
        )

        market_services = [
            upgrade_service.market_service_and_create_backup(self.tenant, service, app_record.version)
            for service in services
        ]

        upgrade_service.upgrade_database(market_services)
        upgrade_service.send_upgrade_request(
            market_services,
            self.tenant,
            self.user,
            app_record,
            upgrade_service_infos
        )
        upgrade_repo.change_app_record_status(app_record, UpgradeStatus.UPGRADING.value)

        return MessageResponse(
            msg="success",
            bean=upgrade_service.serialized_upgrade_record(app_record)
        )


class AppUpgradeRollbackView(RegionTenantHeaderView):
    def post(self, request, group_id, record_id, *args, **kwargs):
        """提交回滚任务"""
        service_ids = parse_item(request, 'service_ids', required=True, error='service_ids is a required parameter')

        # 判断是不是最后一条升级记录
        app_record = AppUpgradeRecord.objects.filter(
            tenant_id=self.tenant.tenant_id,
            group_id=int(group_id),
            status__in=(UpgradeStatus.UPGRADED.value, UpgradeStatus.PARTIAL_UPGRADED.value)
        ).order_by('-create_time').first()

        if app_record.Id != int(record_id):
            raise AbortRequest(msg="This upgrade cannot be rolled back", msg_show=u"本次升级无法回滚")

        service_records = app_record.service_upgrade_records.filter(
            status__in=(UpgradeStatus.UPGRADED.value, UpgradeStatus.UPGRADE_FAILED.value),
            service_id__in=service_ids
        )
        services = service_repo.get_services_by_service_ids_and_group_key(
            app_record.group_key,
            service_records.values_list('service_id', flat=True) or []
        )

        market_services = [
            upgrade_service.market_service_and_restore_backup(self.tenant, service, app_record.version)
            for service in services
        ]
        upgrade_service.send_rolling_request(
            market_services,
            self.tenant,
            self.user,
            app_record,
        )

        upgrade_repo.change_app_record_status(app_record, UpgradeStatus.ROLLING.value)

        return MessageResponse(
            msg="success",
            bean=upgrade_service.serialized_upgrade_record(app_record)
        )

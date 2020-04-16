# coding: utf-8
"""升级从云市安装的应用"""
import json
import logging
from copy import deepcopy

from django.core.paginator import Paginator
from django.db.models import Q
from enum import Enum

from console.exception.main import AbortRequest
from console.exception.main import AccountOverdueException
from console.exception.main import ResourceNotEnoughException
from console.models.main import AppUpgradeRecord
from console.models.main import ServiceUpgradeRecord
from console.models.main import UpgradeStatus
from console.repositories.app import service_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.app_actions.properties_changes import PropertiesChanges
from console.services.upgrade_services import upgrade_service
from console.utils.reqparse import parse_args
from console.utils.reqparse import parse_argument
from console.utils.reqparse import parse_date
from console.utils.reqparse import parse_item
from console.utils.response import MessageResponse
from console.utils.shortcuts import get_object_or_404
from console.views.base import RegionTenantHeaderView
from console.views.base import CloudEnterpriseCenterView

logger = logging.getLogger('default')


class GroupAppView(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """查询当前组下的云市应用"""
        group_id = int(group_id)
        group = group_service.get_group_or_404(self.tenant, self.response_region, group_id)
        apps = market_app_service.get_market_apps_in_app(self.response_region, self.tenant, group)
        return MessageResponse(msg="success", list=apps)


class AppUpgradeVersion(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """获取某云市应用的可升级版本"""
        group_key = parse_argument(
            request, 'group_key', value_type=str, required=True, error='group_key is a required parameter')

        # 获取云市应用可升级版本列表
        versions = upgrade_service.get_app_upgrade_versions(self.tenant, int(group_id), group_key)
        return MessageResponse(msg="success", list=list(versions))


class AppUpgradeRecordsView(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """获取升级订单列表"""
        page = parse_argument(request, 'page', value_type=int, default=1)
        page_size = parse_argument(request, 'page_size', value_type=int, default=10)

        rq_args = (
            {
                'key': 'group_key',
                'value_type': str
            },
            {
                'key': 'status__in',
                'value_type': list
            },
            {
                'key': 'status__gt',
                'value_type': int
            },
            {
                'key': 'status__lt',
                'value_type': int
            },
        )

        qs_args = parse_args(request, rq_args)
        switch = {
            'group_key': Q(group_key=qs_args.get('group_key')),
            'status__in': Q(status__in=qs_args.get('status__in')),
            'status__gt': Q(status__gt=qs_args.get('status__gt')),
            'status__lt': Q(status__lt=qs_args.get('status__lt')),
        }
        q = Q()
        for arg_key in qs_args.keys():
            q &= switch[arg_key]

        record_qs = AppUpgradeRecord.objects.filter(
            tenant_id=self.tenant.tenant_id,
            group_id=int(group_id),
        ).filter(q).order_by('-create_time')

        paginator = Paginator(record_qs, page_size)
        records = paginator.page(page)

        # 同步升级记录状态
        for record in records:
            upgrade_service.synchronous_upgrade_status(self.tenant, record)

        return MessageResponse(
            msg="success",
            bean={"total": paginator.count},
            list=[upgrade_service.serialized_upgrade_record(record) for record in records])

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
            pk=int(record_id))

        # 同步升级记录状态
        upgrade_service.synchronous_upgrade_status(self.tenant, record)

        return MessageResponse(msg="success", bean=upgrade_service.serialized_upgrade_record(record))


class UpgradeType(Enum):
    UPGRADE = 'upgrade'
    ADD = 'add'


class AppUpgradeInfoView(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """获取升级信息"""
        group_key = parse_argument(
            request, 'group_key', value_type=str, required=True, error='group_key is a required parameter')
        version = parse_argument(request, 'version', value_type=str, required=True,
                                 error='version is a required parameter')

        # 查询某一个云市应用下的所有组件
        services = group_service.get_rainbond_services(int(group_id), group_key)
        upgrade_info = [{
            'service': {
                'service_id': service.service_id,
                'service_cname': service.service_cname,
                'service_key': service.service_key,
                'type': UpgradeType.UPGRADE.value
            },
            'upgrade_info': upgrade_service.get_service_changes(service, self.tenant, version),
        } for service in services]

        add_info = [{
            'service': {
                'service_id': '',
                'service_cname': service_info['service_cname'],
                'service_key': service_info['service_key'],
                'type': UpgradeType.ADD.value
            },
            'upgrade_info': service_info,
        } for service_info in upgrade_service.get_add_services(services, group_key, version)]

        return MessageResponse(msg="success", list=upgrade_info + add_info)


class AppUpgradeTaskView(RegionTenantHeaderView, CloudEnterpriseCenterView):
    def post(self, request, group_id, *args, **kwargs):
        """提交升级任务"""
        rq_args = (
            {
                'key': 'upgrade_record_id',
                'required': True,
                'error': 'upgrade_record_id is a required parameter'
            },
            {
                'key': 'group_key',
                'required': True,
                'error': 'group_key is a required parameter'
            },
            {
                'key': 'version',
                'required': True,
                'error': 'version is a required parameter'
            },
            {
                'key': 'services',
                'required': True,
                'error': 'services is a required parameter'
            },
        )
        data = parse_date(request, rq_args)
        group_key = data['group_key']
        version = data['version']
        app_record = get_object_or_404(
            AppUpgradeRecord,
            msg="Upgrade record not found",
            tenant_id=self.tenant.tenant_id,
            group_id=int(group_id),
            group_key=group_key,
            status=UpgradeStatus.NOT.value,
            pk=data['upgrade_record_id'],
        )

        # 处理新增的组件
        add_service_infos = {
            service['service']['service_key']: service['upgrade_info']
            for service in data['services'] if service['service']['type'] == UpgradeType.ADD.value and service['upgrade_info']
        }
        install_info = {}
        if add_service_infos:
            old_app, install_from_cloud = market_app_service.get_app_version_by_app_model_id(self.tenant, group_key, version)
            new_app = deepcopy(old_app)
            # mock app信息
            template = json.loads(new_app.app_template)
            template['apps'] = add_service_infos.values()
            new_app.app_template = json.dumps(template)

            # 查询某一个云市应用下的所有组件
            services = group_service.get_rainbond_services(int(group_id), group_key)
            try:
                install_info = market_app_service.install_service_when_upgrade_app(
                    self.tenant, self.response_region, self.user,
                    group_id, new_app, old_app, services, True, install_from_cloud
                )

            except ResourceNotEnoughException as re:
                raise re
            except AccountOverdueException as re:
                logger.exception(re)
                return MessageResponse(
                    msg="resource is not enough", msg_show=re.message, status_code=412, error_code=10406)
            upgrade_service.create_add_service_record(app_record, install_info['events'], add_service_infos)

        # 处理需要升级的组件
        upgrade_service_infos = {
            service['service']['service_id']: service['upgrade_info']
            for service in data['services']
            if service['service']['type'] == UpgradeType.UPGRADE.value and service['upgrade_info']
        }

        app_record.version = version
        old_service = group_service.get_rainbond_services(group_id, group_key).first()
        pc = PropertiesChanges(old_service, self.tenant)
        app_record.old_version = pc.current_version.version
        app_record.save()

        services = service_repo.get_services_by_service_ids_and_group_key(
            data['group_key'], upgrade_service_infos.keys())

        market_services = [
            upgrade_service.market_service_and_create_backup(self.tenant, service, app_record.version)
            for service in services]

        # 处理依赖关系
        if add_service_infos:
            market_app_service.save_service_deps_when_upgrade_app(
                self.tenant,
                install_info['service_key_dep_key_map'],
                install_info['key_service_map'],
                install_info['apps'],
                install_info['app_map'],
            )

        upgrade_service.upgrade_database(market_services)
        upgrade_service.send_upgrade_request(
            market_services, self.tenant, self.user, app_record, upgrade_service_infos, self.oauth_instance)
        upgrade_repo.change_app_record_status(app_record, UpgradeStatus.UPGRADING.value)

        return MessageResponse(msg="success", bean=upgrade_service.serialized_upgrade_record(app_record))


class AppUpgradeRollbackView(RegionTenantHeaderView):
    def post(self, request, group_id, record_id, *args, **kwargs):
        """提交回滚任务"""
        service_ids = parse_item(request, 'service_ids', required=True, error='service_ids is a required parameter')

        # 判断是不是最后一条升级记录
        app_record = AppUpgradeRecord.objects.filter(
            tenant_id=self.tenant.tenant_id,
            group_id=int(group_id),
            status__in=(UpgradeStatus.UPGRADED.value,
                        UpgradeStatus.ROLLBACK.value,
                        UpgradeStatus.PARTIAL_UPGRADED.value,
                        UpgradeStatus.PARTIAL_ROLLBACK.value,
                        UpgradeStatus.UPGRADE_FAILED.value,
                        UpgradeStatus.ROLLBACK_FAILED.value)).order_by('-create_time').first()

        if not app_record or app_record.ID != int(record_id):
            raise AbortRequest(msg="This upgrade cannot be rolled back", msg_show=u"本次升级无法回滚")

        service_records = app_record.service_upgrade_records.filter(
            status__in=(UpgradeStatus.UPGRADED.value, UpgradeStatus.ROLLBACK.value, UpgradeStatus.UPGRADE_FAILED.value,
                        UpgradeStatus.ROLLBACK_FAILED.value),
            upgrade_type=ServiceUpgradeRecord.UpgradeType.UPGRADE.value, service_id__in=service_ids)
        services = service_repo.get_services_by_service_ids_and_group_key(
            app_record.group_key,
            service_records.values_list('service_id', flat=True) or [])

        market_services = [
            upgrade_service.market_service_and_restore_backup(self.tenant, service, app_record.version)
            for service in services]
        upgrade_service.send_rolling_request(market_services, self.tenant, self.user, app_record, service_records)

        upgrade_repo.change_app_record_status(app_record, UpgradeStatus.ROLLING.value)

        return MessageResponse(msg="success", bean=upgrade_service.serialized_upgrade_record(app_record))

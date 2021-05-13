# coding: utf-8
"""升级从云市安装的应用"""
import json
import logging
from copy import deepcopy
from enum import Enum

from console.exception.main import (AbortRequest, AccountOverdueException, ResourceNotEnoughException, ServiceHandleException)
from console.models.main import (AppUpgradeRecord, ServiceUpgradeRecord, UpgradeStatus)
from console.repositories.app import service_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.services.app import app_market_service
from console.services.app_actions.properties_changes import PropertiesChanges
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.upgrade_services import upgrade_service
from console.utils.reqparse import (parse_args, parse_argument, parse_date, parse_item)
from console.utils.response import MessageResponse
from console.utils.shortcuts import get_object_or_404
from console.views.base import (RegionTenantHeaderCloudEnterpriseCenterView, RegionTenantHeaderView)
from django.core.paginator import Paginator
from django.db.models import Q

logger = logging.getLogger('default')


class GroupAppView(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """查询当前应用下的应用模版列表及可升级性"""
        group_id = int(group_id)
        group = group_service.get_group_or_404(self.tenant, self.response_region, group_id)
        apps = market_app_service.get_market_apps_in_app(self.response_region, self.tenant, group)
        return MessageResponse(msg="success", list=apps)


class AppUpgradeVersion(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """获取安装的应用模版的可升级版本"""
        group_key = parse_argument(
            request, 'group_key', value_type=str, required=True, error='group_key is a required parameter')

        # get app model upgrade versions
        versions = market_app_service.get_models_upgradeable_version(self.tenant.enterprise_id, group_key, group_id)
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
        for arg_key in list(qs_args.keys()):
            q &= switch[arg_key]

        record_qs = AppUpgradeRecord.objects.filter(
            tenant_id=self.tenant.tenant_id,
            group_id=int(group_id),
        ).filter(q).order_by('-create_time')

        paginator = Paginator(record_qs, page_size)
        records = paginator.page(page)

        # 同步升级记录状态
        for record in records:
            upgrade_service.synchronous_upgrade_status(self.tenant, self.region_name, record)

        return MessageResponse(
            msg="success",
            bean={"total": paginator.count},
            list=[upgrade_service.serialized_upgrade_record(record) for record in records])

    def post(self, request, group_id, *args, **kwargs):
        """新增升级订单"""
        group_key = parse_item(request, 'group_key', required=True, error='group_key is a required parameter')
        is_from_cloud = request.data.get("is_from_cloud", False)
        market_name = request.data.get("market_name", None)
        recode_kwargs = {
            "tenant_id": self.tenant.tenant_id,
            "group_id": int(group_id),
            "group_key": group_key,
            "is_from_cloud": is_from_cloud,
            "market_name": market_name,
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
        upgrade_service.synchronous_upgrade_status(self.tenant, self.region_name, record)

        return MessageResponse(msg="success", bean=upgrade_service.serialized_upgrade_record(record))


class UpgradeType(Enum):
    UPGRADE = 'upgrade'
    ADD = 'add'


class AppUpgradeInfoView(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """获取升级信息"""
        group_key = parse_argument(
            request, 'group_key', value_type=str, required=True, error='group_key is a required parameter')
        version = parse_argument(request, 'version', value_type=str, required=True, error='version is a required parameter')
        market_name = request.GET.get("market_name")

        # 查询某一个云市应用下的所有组件
        services = group_service.get_rainbond_services(int(group_id), group_key)
        upgrade_info = []
        if services:
            upgrade_info = [{
                'service': {
                    'service_id': service.service_id,
                    'service_cname': service.service_cname,
                    'service_key': service.service_key,
                    'type': UpgradeType.UPGRADE.value
                },
                'upgrade_info': upgrade_service.get_service_changes(service, self.tenant, version, services),
            } for service in services]

        add_component = upgrade_service.get_add_services(self.team.enterprise_id, services, group_key, version, market_name)
        add_info = []
        if add_component:
            add_info = [{
                'service': {
                    'service_id': '',
                    'service_cname': service_info['service_cname'],
                    'service_key': service_info['service_key'],
                    'type': UpgradeType.ADD.value
                },
                'upgrade_info': service_info,
            } for service_info in add_component]

        return MessageResponse(msg="success", list=upgrade_info + add_info)


class AppUpgradeTaskView(RegionTenantHeaderCloudEnterpriseCenterView):
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
        old_services = group_service.get_rainbond_services(group_id, group_key)
        pc = PropertiesChanges(old_services.first(), self.tenant, all_component_one_model=old_services)
        if pc.install_from_cloud:
            old_app_model, old_app = app_market_service.cloud_app_model_to_db_model(pc.market, group_key, version)
        else:
            old_app_model, old_app = rainbond_app_repo.get_rainbond_app_and_version(self.tenant.enterprise_id, group_key,
                                                                                    version)
        if not old_app_model:
            raise ServiceHandleException(msg="app is not exist", msg_show="应用市场应用不存在，无法进行升级")
        if not old_app:
            raise ServiceHandleException(msg="app version is not exist", msg_show="应用市场应用版本不存在，无法进行升级")
        old_app.template = old_app.app_template
        old_app.app_name = old_app_model.app_name
        new_app = deepcopy(old_app)
        template = json.loads(new_app.template)
        # 处理新增的组件
        add_service_infos = {
            service['service']['service_key']: service['upgrade_info']
            for service in data['services'] if service['service']['type'] == UpgradeType.ADD.value and service['upgrade_info']
        }
        # 安装插件
        plugins = template.get("plugins", None)
        if plugins:
            market_app_service.create_plugin_for_tenant(self.response_region, self.user, self.tenant, plugins)
        else:
            logger.debug(plugins)
        install_info = {}
        if add_service_infos:
            # mock app信息
            template['apps'] = list(add_service_infos.values())
            new_app.template = json.dumps(template)

            # 查询某一个云市应用下的所有组件
            services = group_service.get_rainbond_services(int(group_id), group_key)
            try:
                install_info = market_app_service.install_service_when_upgrade_app(self.tenant, self.response_region, self.user,
                                                                                   group_id, new_app, old_app, services, True,
                                                                                   pc.install_from_cloud, pc.market_name)

            except ResourceNotEnoughException as re:
                raise re
            except AccountOverdueException as re:
                logger.exception(re)
                return MessageResponse(msg="resource is not enough", msg_show=re.message, status_code=412, error_code=10406)
            upgrade_service.create_add_service_record(app_record, install_info['events'], add_service_infos)

        # 处理需要升级的组件
        upgrade_service_infos = {
            service['service']['service_id']: service['upgrade_info']
            for service in data['services']
            if service['service']['type'] == UpgradeType.UPGRADE.value and service['upgrade_info']
        }
        # 升级应用配置组
        market_app_service.save_app_config_groups_when_upgrade_app(self.region_name, self.tenant, group_id,
                                                                   upgrade_service_infos)

        app_record.version = version
        app_record.old_version = pc.current_version
        app_record.save()

        services = service_repo.get_services_by_service_ids_and_group_key(data['group_key'], list(upgrade_service_infos.keys()))

        market_services = [
            upgrade_service.market_service_and_create_backup(
                self.tenant, service, app_record.version, all_component_one_model=services) for service in services
        ]

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
        upgrade_service.send_upgrade_request(market_services, self.tenant, self.user, app_record, upgrade_service_infos,
                                             self.oauth_instance)
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
            status__in=(UpgradeStatus.UPGRADED.value, UpgradeStatus.ROLLBACK.value, UpgradeStatus.PARTIAL_UPGRADED.value,
                        UpgradeStatus.PARTIAL_ROLLBACK.value, UpgradeStatus.UPGRADE_FAILED.value,
                        UpgradeStatus.ROLLBACK_FAILED.value)).order_by('-create_time').first()

        if not app_record or app_record.ID != int(record_id):
            raise AbortRequest(msg="This upgrade cannot be rolled back", msg_show="本次升级无法回滚")

        service_records = app_record.service_upgrade_records.filter(
            status__in=(UpgradeStatus.UPGRADED.value, UpgradeStatus.ROLLBACK.value, UpgradeStatus.UPGRADE_FAILED.value,
                        UpgradeStatus.ROLLBACK_FAILED.value),
            upgrade_type=ServiceUpgradeRecord.UpgradeType.UPGRADE.value,
            service_id__in=service_ids)

        if not service_records:
            raise AbortRequest(msg="This upgrade cannot be rolled back", msg_show="本次升级无法回滚")

        services = service_repo.get_services_by_service_ids_and_group_key(
            app_record.group_key,
            service_records.values_list('service_id', flat=True) or [])

        market_services = [
            upgrade_service.market_service_and_restore_backup(self.tenant, service, app_record.version) for service in services
        ]
        upgrade_service.send_rolling_request(market_services, self.tenant, self.user, app_record, service_records)

        upgrade_repo.change_app_record_status(app_record, UpgradeStatus.ROLLING.value)

        return MessageResponse(msg="success", bean=upgrade_service.serialized_upgrade_record(app_record))

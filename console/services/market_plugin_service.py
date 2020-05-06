# -*- coding:utf8 -*-
import json
import logging
from datetime import datetime

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q

from console.appstore.appstore import app_store
from console.models.main import PluginShareRecordEvent
from console.models.main import RainbondCenterPlugin
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.plugin import plugin_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.services.plugin import plugin_service
from console.services.plugin import plugin_version_service
from www.apiclient.marketclient import MarketOpenAPI
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import make_uuid
from www.models.plugin import PluginConfigGroup
from www.models.plugin import PluginConfigItems
from www.models.plugin import TenantPlugin
from www.services import plugin_svc

market_api = MarketOpenAPI()
region_api = RegionInvokeApi()
logger = logging.getLogger('default')


class MarketPluginService(object):
    def get_paged_plugins(self,
                          plugin_name="",
                          is_complete=None,
                          scope="",
                          source="",
                          tenant=None,
                          page=1,
                          limit=10,
                          order_by="",
                          category=""):
        q = Q(enterprise_id__in=[tenant.enterprise_id, "public"])

        if source:
            q = q & Q(source=source)

        if is_complete:
            q = q & Q(is_complete=is_complete)

        if plugin_name:
            q = q & Q(plugin_name__icontains=plugin_name)

        if category:
            q = q & Q(category=category)

        if scope == 'team':
            q = q & Q(share_team=tenant.tenant_name)
        elif scope == 'goodrain':
            q = q & Q(scope='goodrain')
        elif scope == 'enterprise':
            tenants = team_repo.get_teams_by_enterprise_id(tenant.enterprise_id)
            tenant_names = [t.tenant_name for t in tenants]
            q = q & Q(share_team__in=tenant_names) & ~Q(scope='team')
        else:
            tenants = team_repo.get_teams_by_enterprise_id(tenant.enterprise_id)
            tenant_names = [t.tenant_name for t in tenants]

            q = q & (Q(share_team__in=tenant_names, scope="enterprise")
                     | Q(scope="goodrain") | Q(share_team=tenant.tenant_name, scope="team"))

        if order_by == 'is_complete':
            plugins = RainbondCenterPlugin.objects.filter(q).order_by('is_complete')
        else:
            plugins = RainbondCenterPlugin.objects.filter(q).order_by('-update_time')

        paged_plugins = Paginator(plugins, limit).page(page)

        data = [{
            'plugin_name': p.plugin_name,
            'plugin_key': p.plugin_key,
            'category': p.category,
            'pic': p.pic,
            'version': p.version,
            'desc': p.desc,
            'id': p.ID,
            'is_complete': p.is_complete,
            'source': p.source,
            'update_time': p.update_time,
            'details': p.details
        } for p in paged_plugins]

        return len(plugins), data

    def sync_market_plugins(self, tenant, user, page, limit, plugin_name=''):
        market_plugins, total = market_api.get_plugins(tenant.tenant_id, page, limit, plugin_name)

        plugins = RainbondCenterPlugin.objects.filter(enterprise_id__in=["public", tenant.enterprise_id])

        for p in market_plugins:
            if plugins.filter(plugin_key=p.get('plugin_key'), version=p.get('version')).exists():
                p['is_complete'] = True
            else:
                p['is_complete'] = False

        return market_plugins, total

    def sync_market_plugin_templates(self, user, tenant, plugin_data):
        plugin_template = market_api.get_plugin_templates(tenant.tenant_id, plugin_data.get('plugin_key'),
                                                          plugin_data.get('version'))
        market_plugin = plugin_template.get('plugin')
        if not market_plugin:
            return True
        rcps = RainbondCenterPlugin.objects.filter(
            plugin_key=market_plugin.get('plugin_key'),
            version=market_plugin.get('major_version'),
            enterprise_id__in=[tenant.enterprise_id, "public"])

        rcp = None
        if rcps:
            # 优先获取企业的插件
            enter_rcp = rcps.filter(enterprise_id=tenant.enterprise_id)
            if enter_rcp:
                rcp = enter_rcp[0]
            else:
                rcp = rcps[0]
        if rcp:
            rcp.share_user = 0
            user_name = market_plugin.get('share_user')
            if user_name:
                try:
                    user = user_repo.get_enterprise_user_by_username(tenant.enterprise_id, user_name)
                    rcp.share_user = user.user_id
                except Exception as e:
                    logger.exception(e)

            rcp.plugin_template = market_plugin.get("template").get('template_content')
            rcp.pic = market_plugin.get('logo')
            rcp.desc = market_plugin.get('intro')
            rcp.version = market_plugin.get('major_version')
            rcp.details = market_plugin.get("desc", "")
            rcp.is_complete = True
            rcp.save()
            return True
        else:
            enterprise_id = tenant.enterprise_id
            rcp = RainbondCenterPlugin(
                plugin_key=market_plugin.get('plugin_key'),
                plugin_name=market_plugin.get('name'),
                version=market_plugin.get('major_version'),
                desc=market_plugin.get('intro'),
                pic=market_plugin.get('logo'),
                build_version=market_plugin.get('build_version'),
                record_id=0,
                category=market_plugin.get('category'),
                scope='goodrain',
                source='market',
                share_user=0,
                share_team='',
                enterprise_id=enterprise_id,
                plugin_template=market_plugin.get("template").get('template_content'),
                is_complete=True,
                details=market_plugin.get("desc", ""))
            rcp.save()
            return True

    @transaction.atomic
    def create_plugin_share_info(self, share_record, share_info, user_id, tenant, region_name):
        tenant_id = tenant.tenant_id
        tenant_name = tenant.tenant_name

        sid = transaction.savepoint()

        try:
            PluginShareRecordEvent.objects.filter(record_id=share_record.ID).delete()
            RainbondCenterPlugin.objects.filter(record_id=share_record.ID).delete()

            plugin_info = share_info.get("share_plugin_info")
            if isinstance(plugin_info, unicode):
                plugin_info = json.loads(plugin_info)

            if plugin_info.get('scope') == 'goodrain':
                ent = enterprise_repo.get_enterprise_by_enterprise_id(tenant.enterprise_id)
                if ent and not ent.is_active:
                    return 10407, "用户未跟云市认证", None

            plugin_id = plugin_info.get("plugin_id")

            plugin_version = plugin_svc.get_tenant_plugin_newest_versions(region_name, tenant, plugin_id)

            if not plugin_version or plugin_version[0].build_status != "build_success":
                return 400, "插件未构建", None

            plugin_version = plugin_version.first()

            tenant_plugin = plugin_repo.get_plugin_by_plugin_id(tenant_id, plugin_id)

            plugin_template = {
                "plugin_id": plugin_info.get("plugin_id"),
                "plugin_key": plugin_info.get("plugin_key"),
                "plugin_name": plugin_info.get("plugin_name"),
                "plugin_version": plugin_info.get("version"),
                "code_repo": tenant_plugin.code_repo,
                "build_source": tenant_plugin.build_source,
                "image": tenant_plugin.image,
                "category": tenant_plugin.category
            }

            if plugin_version.plugin_version_status != "fixed":
                plugin_version.plugin_version_status = "fixed"
                plugin_version.save()

            plugin_template["build_version"] = plugin_version.to_dict()

            plugin_info["plugin_image"] = app_store.get_image_connection_info(plugin_info["scope"], tenant_name)
            if not plugin_info["plugin_image"]:
                if sid:
                    transaction.savepoint_rollback(sid)
                return 400, "获取镜像上传地址错误", None

            event = PluginShareRecordEvent(
                record_id=share_record.ID,
                team_name=tenant_name,
                team_id=tenant_id,
                plugin_id=plugin_info['plugin_id'],
                plugin_name=plugin_info['plugin_name'],
                event_status='not_start')
            event.save()

            RainbondCenterPlugin.objects.filter(version=plugin_info["version"], plugin_id=share_record.group_id).delete()

            plugin_info["source"] = "local"
            plugin_info["record_id"] = share_record.ID

            plugin_template['share_plugin_info'] = plugin_info

            plugin = RainbondCenterPlugin(
                plugin_key=plugin_info.get("plugin_key"),
                plugin_name=plugin_info.get("plugin_name"),
                plugin_id=plugin_info.get("plugin_id"),
                record_id=share_record.ID,
                version=plugin_info.get("version"),
                build_version=plugin_info.get('build_version'),
                pic=plugin_info.get("pic", ""),
                scope=plugin_info.get("scope"),
                source="local",
                share_user=user_id,
                share_team=tenant_name,
                desc=plugin_info.get("desc"),
                enterprise_id=tenant.enterprise_id,
                plugin_template=json.dumps(plugin_template),
                category=plugin_info.get('category'))

            plugin.save()

            share_record.step = 2
            share_record.update_time = datetime.now()
            share_record.save()

            transaction.savepoint_commit(sid)

            return 200, "分享信息处理成功", plugin.to_dict()
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            return 500, "插件分享处理发生错误", None

    def plugin_share_completion(self, tenant, share_record, user_name):
        try:
            plugin = RainbondCenterPlugin.objects.get(record_id=share_record.ID)
            market_url = ""
            if plugin.scope == "goodrain":
                market_url = self._publish_to_market(tenant, user_name, plugin)

            plugin.is_complete = True
            plugin.update_time = datetime.now()
            plugin.save()

            share_record.is_success = True
            share_record.step = 3
            share_record.update_time = datetime.now()
            share_record.save()

            return market_url
        except RainbondCenterPlugin.DoesNotExist:
            return None

    def _publish_to_market(self, tenant, user_name, plugin):
        tenant_plugin = TenantPlugin.objects.get(plugin_id=plugin.plugin_id)
        market_api = MarketOpenAPI()
        data = {
            "tenant_id": tenant.tenant_id,
            "plugin_key": plugin.plugin_key,
            "plugin_version": plugin.version,
            "build_version": plugin.build_version,
            "plugin_name": plugin.plugin_name,
            "share_user": user_name,
            "share_team": tenant.tenant_alias,
            "intro": plugin.desc,
            "plugin_template": plugin.plugin_template,
            "logo": plugin.pic,
            "category": tenant_plugin.category
        }
        result = market_api.publish_plugin_template_data(tenant.tenant_id, data)
        return result["plugin_url"]

    def get_sync_event_result(self, region_name, tenant_name, record_event):
        res, body = region_api.share_plugin_result(region_name, tenant_name, record_event.plugin_id,
                                                   record_event.region_share_id)
        ret = body.get('bean')
        if ret and ret.get('status'):
            record_event.event_status = ret.get("status")
            record_event.save()
        return record_event

    @transaction.atomic
    def sync_event(self, nick_name, region_name, tenant_name, record_event):
        rcps = RainbondCenterPlugin.objects.filter(record_id=record_event.record_id)
        if not rcps:
            return 404, "分享的插件不存在", None
        rcp = rcps[0]
        event_id = make_uuid()
        record_event.event_id = event_id
        plugin_template = json.loads(rcp.plugin_template)
        share_plugin = plugin_template.get("share_plugin_info")
        body = {
            "plugin_id": rcp.plugin_id,
            "plugin_version": rcp.build_version,
            "plugin_key": rcp.plugin_key,
            "event_id": event_id,
            "share_user": nick_name,
            "share_scope": rcp.scope,
            "image_info": share_plugin.get("plugin_image") if share_plugin else "",
        }
        sid = transaction.savepoint()
        try:
            res, body = region_api.share_plugin(region_name, tenant_name, rcp.plugin_id, body)
            data = body.get("bean")
            if not data:
                transaction.savepoint_rollback(sid)
                return 400, "数据中心分享错误", None
            record_event.region_share_id = data.get("share_id", None)
            record_event.event_id = data.get("event_id", None)
            record_event.event_status = "start"
            record_event.update_time = datetime.now()
            record_event.save()
            image_name = data.get("image_name", None)
            if image_name:
                plugin_template["share_image"] = image_name
            rcp.plugin_template = json.dumps(plugin_template)
            rcp.save()
            transaction.savepoint_commit(sid)
            return 200, "数据中心分享开始", record_event
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            return 500, "插件分享事件同步发生错误", None

    @transaction.atomic
    def install_plugin(self, user, tenant, region_name, market_plugin):
        plugin_template = json.loads(market_plugin.plugin_template)
        share_plugin_info = plugin_template.get("share_plugin_info")

        sid = transaction.savepoint()

        try:
            image = None
            image_tag = None
            if plugin_template["share_image"]:
                image_and_tag = plugin_template["share_image"].rsplit(":", 1)
                if len(image_and_tag) > 1:
                    image = image_and_tag[0]
                    image_tag = image_and_tag[1]
                else:
                    image = image_and_tag[0]
                    image_tag = "latest"

            plugin_params = {
                "tenant_id": tenant.tenant_id,
                "region": region_name,
                "create_user": user.user_id,
                "desc": plugin_template["desc"],
                "plugin_alias": plugin_template["plugin_alias"],
                "category": plugin_template["category"],
                "build_source": "image",
                "image": image,
                "code_repo": plugin_template["code_repo"],
                "username": "",
                "password": ""
            }
            status, msg, plugin_base_info = plugin_service.create_tenant_plugin(plugin_params)

            if status != 200:
                return status, msg

            plugin_base_info.origin = 'local_market' if market_plugin.source == 'local' else market_plugin.source
            plugin_base_info.origin_share_id = share_plugin_info.get("plugin_key")
            plugin_base_info.save()

            build_version = plugin_template.get('build_version')
            min_memory = build_version.get('min_memory')

            plugin_build_version = plugin_version_service.create_build_version(
                region_name,
                plugin_base_info.plugin_id,
                tenant.tenant_id,
                user.user_id,
                "",
                "unbuild",
                min_memory,
                image_tag=image_tag,
                code_version="")

            config_groups, config_items = [], []
            share_config_groups = share_plugin_info.get('config_groups', [])

            for group in share_config_groups:
                plugin_config_group = PluginConfigGroup(
                    plugin_id=plugin_base_info.plugin_id,
                    build_version=plugin_build_version.build_version,
                    config_name=group.get("config_name"),
                    service_meta_type=group.get("service_meta_type"),
                    injection=group.get("injection"))
                config_groups.append(plugin_config_group)

                share_config_items = group.get('config_items', [])
                for item in share_config_items:
                    plugin_config_item = PluginConfigItems(
                        plugin_id=plugin_base_info.plugin_id,
                        build_version=plugin_build_version.build_version,
                        service_meta_type=item.get("service_meta_type"),
                        attr_name=item.get("attr_name"),
                        attr_alt_value=item.get("attr_alt_value"),
                        attr_type=item.get("attr_type", "string"),
                        attr_default_value=item.get("attr_default_value", None),
                        is_change=item.get("is_change", False),
                        attr_info=item.get("attr_info", ""),
                        protocol=item.get("protocol", ""))
                    config_items.append(plugin_config_item)

            PluginConfigGroup.objects.bulk_create(config_groups)
            PluginConfigItems.objects.bulk_create(config_items)

            event_id = make_uuid()
            plugin_build_version.event_id = event_id
            plugin_build_version.plugin_version_status = "fixed"

            plugin_service.create_region_plugin(region_name, tenant, plugin_base_info, image_tag=image_tag)

            ret = plugin_service.build_plugin(region_name, plugin_base_info, plugin_build_version, user, tenant, event_id,
                                              share_plugin_info.get("plugin_image", None))
            plugin_build_version.build_status = ret.get('bean').get('status')
            plugin_build_version.save()

            return 200, '安装成功'
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            return 500, '插件安装失败'

    def check_plugin_share_condition(self, tenant, plugin_id, region_name):
        plugin = plugin_repo.get_plugin_by_plugin_id(tenant.tenant_id, plugin_id)
        if not plugin:
            return 404, 'plugin not exist', '插件不存在'

        if plugin.origin in ['market', 'local_market']:
            return 400, 'plugin from market', '插件来源于共享库或应用商店，无法再次分享'

        build_info = plugin_svc.get_tenant_plugin_newest_versions(region_name, tenant, plugin_id)
        if not build_info:
            return 400, 'plugin not build', '插件未构建'

        if build_info[0].build_status != 'build_success':
            return 400, 'plugin not build success', '插件未构建成功，无法分享'
        return 200, 'plugin can share', ''


market_plugin_service = MarketPluginService()

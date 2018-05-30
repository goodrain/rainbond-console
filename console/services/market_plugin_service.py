# -*- coding:utf8 -*-
import json
import logging
from datetime import datetime

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q

from console.appstore.appstore import app_store
from console.models import RainbondCenterPlugin, PluginShareRecordEvent
from console.repositories.user_repo import user_repo
from www.apiclient.marketclient import MarketOpenAPI
from www.apiclient.regionapi import RegionInvokeApi
from www.models import make_uuid, TenantPlugin
from www.services import plugin_svc

market_api = MarketOpenAPI()
region_api = RegionInvokeApi()
logger = logging.getLogger('default')


class MarketPluginService(object):
    def get_paged_plugins(self, plugin_name="", page=1, limit=10):
        q = Q(scope='goodrain', source='market', is_complete=True)

        if plugin_name:
            q = q & Q(plugin_name__icontains=plugin_name)

        plugins = RainbondCenterPlugin.objects.filter(q).order_by('-ID')
        paged_plugins = Paginator(plugins, limit).page(page)

        data = [{
            'plugin_name': p.plugin_name,
            'plugin_key': p.plugin_key,
            'pic': p.pic,
            'version': p.version,
            'desc': p.desc
        } for p in paged_plugins]

        return plugins.total(), data

    def sync_market_plugins(self, tenant_id):
        market_plugins = market_api.get_plugins(tenant_id)

        plugins = []
        for p in market_plugins:
            try:
                rcp = RainbondCenterPlugin.objects.get(plugin_key=p.get('plugin_key'), version=p.get('version'))
                rcp.pic = p.get('pic')
                rcp.desc = p.get('intro')
                rcp.save()
            except RainbondCenterPlugin.DoesNotExist:
                rcp = RainbondCenterPlugin(
                    plugin_key=p.get('plugin_key'),
                    plugin_name=p.get('name'),
                    version=p.get('version'),
                    record_id=0,
                    scope='goodrain',
                    source='market',
                    share_user=0,
                    share_team='',
                    plugin_template=''
                )
                plugins.append(rcp)
        RainbondCenterPlugin.objects.bulk_create(plugins)
        return True

    def sync_market_plugin_templates(self, tenant_id, plugins):
        plugin_templates = market_api.get_plugin_templates(tenant_id, plugins)
        for template in plugin_templates:
            try:
                rcp = RainbondCenterPlugin.object.get(
                    plugin_key=template.get('plugin_key'), version=template.get('version')
                )
                rcp.share_user = 0
                user_name = template.get('share_user')
                if user_name:
                    try:
                        user = user_repo.get_user_by_username(user_name)
                        rcp.share_user = user.user_id
                    except Exception as e:
                        logger.exception(e)

                rcp.share_team = template.get('share_team')
                rcp.plugin_template = template.get('template')
                rcp.pic = template.get('pic')
                rcp.desc = template.get('intro')
                rcp.version = template.get('version')
                rcp.is_complete = True
                rcp.save()
                return True
            except RainbondCenterPlugin.DoesNotExist:
                pass

    @transaction.atomic
    def create_plugin_share_info(self, share_record, share_info, user_id, tenant_id,
                                 tenant_name, region_name):
        sid = transaction.savepoint()
        try:
            PluginShareRecordEvent.objects.filter(record_id=share_record.ID).delete()
            RainbondCenterPlugin.objects.filter(record_id=share_record.ID).delete()

            plugin_info = share_info.get("plugin_share_info")
            plugin_id = plugin_info.get("plugin_id")

            plugin_version = plugin_svc.get_tenant_plugin_newest_versions(
                region_name, tenant_id, plugin_id
            )

            if not plugin_version and plugin_version.build_status != "build_success":
                return 400, "插件未构建", None

            plugin_template = {
                "plugin_id": plugin_info.get("plugin_id"),
                "plugin_key": plugin_info.get("plugin_key"),
                "plugin_name": plugin_info.get("plugin_name"),
                "plugin_version": plugin_info.get("version")
            }

            if plugin_version.plugin_version_status != "fixed":
                plugin_version.plugin_version_status = "fixed"
                plugin_version.save()

            plugin_template["build_version"] = plugin_version.to_dict()

            plugin_info["plugin_image"] = app_store.get_image_connection_info(share_info["scope"], tenant_name)
            if not plugin_info["plugin_image"]:
                if sid:
                    transaction.savepoint_rollback(sid)
                return 400, "获取镜像上传地址错误", None

            plugin_template['plugin_info'] = plugin_info

            event = PluginShareRecordEvent(
                record_id=share_record.ID,
                team_name=tenant_name,
                team_id=tenant_id,
                plugin_id=plugin_info['plugin_id'],
                plugin_name=plugin_info['plugin_name'],
                event_status='not_start'
            )
            event.save()

            RainbondCenterPlugin.objects.filter(
                version=share_info["version"], plugin_id=share_record.group_id).delete()

            share_info["source"] = "local"
            share_info["record_id"] = share_record.ID
            share_info["plugin_template"] = json.dumps(plugin_template)

            plugin = RainbondCenterPlugin(
                plugin_key=plugin_info.get("plugin_key"),
                plugin_name=plugin_info.get("plugin_name"),
                plugin_id=plugin_info.get("plugin_id"),
                record_id=share_record.ID,
                version=share_info.get("version"),
                pic=share_info.get("pic", ""),
                scope=share_info.get("scope"),
                soure="local",
                share_user=user_id,
                share_team=tenant_name,
                desc=share_info.get("desc"),
                plugin_template=json.dumps(plugin_template)
            )

            plugin.save()

            share_record.step = 2
            share_record.update_time = datetime.now()
            share_record.save()

            transaction.savepoint_commit(sid)

            return 200, "分享信息处理成功", plugin
        except Exception as e:
            if sid:
                transaction.savepoint_rollback(sid)
            logger.exception(e)
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
        res, body = region_api.share_plugin_result(
            region_name, tenant_name, record_event.plugin_id, record_event.region_share_id
        )
        ret = body.get('bean')
        if ret and ret.get('status'):
            record_event.event_status = ret.get("status")
            record_event.save()
        return record_event

    # def _create_publish_event(self, record_event, user_name, event_type):
    #     event = ServiceEvent(
    #         event_id=make_uuid(),
    #         service_id=record_event.service_id,
    #         tenant_id=record_event.team_id,
    #         type=event_type,
    #         user_name=user_name,
    #         start_time=datetime.now()
    #     )
    #     event.save()
    #     return event

    @transaction.atomic
    def sync_event(self, nick_name, region_name, tenant_name, record_event):
        rcps = RainbondCenterPlugin.objects.filter(record_id=record_event.record_id)
        if not rcps:
            return 404, "分享的插件不存在", None

        rcp = rcps[0]
        event_type = "share-yb"
        if rcp.scope == "goodrain":
            event_type = "share-ys"

        # event = self._create_publish_event(record_event, nick_name, event_type)
        event_id = make_uuid()
        record_event.event_id = event_id

        plugin_template = json.loads(rcp.plugin_template)

        body = {
            "plugin_id": rcp.plugin_id,
            "plugin_version": rcp.version,
            "event_id": event_id,
            "share_user": nick_name,
            "share_scope": rcp.scope,
            "image_info": plugin_template.get("plugin_image", None),
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

            rcp.plugin_template = plugin_template
            rcp.save()

            transaction.savepoint_commit(sid)
            return 200, "数据中心分享开始", record_event
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            return 500, "应用分享介质同步发生错误", None


market_plugin_service = MarketPluginService()

# -*- coding: utf-8 -*-
import base64
import datetime
import logging
import re

from console.enum.component_enum import is_singleton
from console.exception.main import ServiceHandleException
from console.models.main import PluginShareRecordEvent, ServiceShareRecordEvent
from console.repositories.group import group_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.share_repo import share_repo
from console.services.app import app_market_service
from console.services.share_services import share_service
from console.utils.reqparse import parse_argument
from console.views.base import JWTAuthApiView, RegionTenantHeaderView
from django.db.models import Q
from goodrain_web import settings
from rest_framework.response import Response
from www.utils.crypt import make_uuid
from www.utils.return_message import error_message, general_message
from console.utils.validation import validate_name

logger = logging.getLogger('default')
# 数字和字母组合，不允许纯数字
NUM_LETTER = re.compile("^(?!\\d+$)[\\da-zA-Z_]+$")
# 只能以字母开头
FIRST_LETTER = re.compile("^[a-zA-Z]")


def market_name_format(name):
    if NUM_LETTER.search(name):
        if FIRST_LETTER.search(name):
            return True
    return False


class ServiceShareRecordView(RegionTenantHeaderView):
    def get(self, request, team_name, group_id, *args, **kwargs):
        data = []
        market = dict()
        cloud_app = dict()
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        total, share_records = share_repo.get_service_share_records_by_groupid(
            team_name=team_name, group_id=group_id, page=page, page_size=page_size)
        if not share_records:
            result = general_message(200, "success", "获取成功", bean={'total': total}, list=data)
            return Response(result, status=200)
        for share_record in share_records:
            app_model_name = share_record.share_app_model_name
            app_model_id = share_record.app_id
            upgrade_time = None
            store_name = share_record.share_store_name
            store_id = share_record.share_app_market_name
            scope = share_record.scope
            if scope != "goodrain" and not app_model_name:
                app = rainbond_app_repo.get_rainbond_app_by_app_id(self.tenant.enterprise_id, share_record.app_id)
                app_model_name = app.app_name if app else ""
                app_version = rainbond_app_repo.get_rainbond_app_version_by_record_id(share_record.ID)
                if app_version:
                    upgrade_time = app_version.upgrade_time
                    share_record.share_version_alias = app_version.version_alias
                    share_record.share_app_version_info = app_version.app_version_info
                share_record.share_app_model_name = app_model_name
                share_record.save()
            if scope == "goodrain" and store_id and share_record.app_id and not app_model_name:
                try:
                    mkt = market.get(share_record.share_app_market_name, None)
                    if not mkt:
                        mkt = app_market_service.get_app_market_by_name(
                            self.tenant.enterprise_id, share_record.share_app_market_name, raise_exception=True)
                        market[share_record.share_app_market_name] = mkt

                    c_app = cloud_app.get(share_record.app_id, None)
                    if not c_app:
                        c_app = app_market_service.get_market_app_model(mkt, share_record.app_id, True)
                        cloud_app[share_record.app_id] = c_app
                    store_name = c_app.market_name
                    app_model_name = c_app.app_name
                    share_record.share_app_model_name = app_model_name
                    share_record.share_store_name = store_name
                    share_record.save()
                except ServiceHandleException:
                    app_model_id = share_record.app_id
            data.append({
                "app_model_id": app_model_id,
                "app_model_name": app_model_name,
                "version": share_record.share_version,
                "version_alias": share_record.share_version_alias,
                "scope": scope,
                "create_time": share_record.create_time,
                "upgrade_time": upgrade_time,
                "step": share_record.step,
                "is_success": share_record.is_success,
                "status": share_record.status,
                "scope_target": {
                    "store_name": store_name,
                    "store_id": store_id,
                },
                "record_id": share_record.ID,
                "app_version_info": share_record.share_app_version_info,
            })
        result = general_message(200, "success", "获取成功", bean={'total': total}, list=data)
        return Response(result, status=200)

    def post(self, request, team_name, group_id, *args, **kwargs):
        """
        生成分享订单，会验证是否能够分享
        ---
        parameter:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用id
              required: true
              type: string
              paramType: path
        """
        scope = request.data.get("scope")
        market_name = None
        if scope == "goodrain":
            target = request.data.get("target")
            market_name = target.get("store_id")
            if market_name is None:
                result = general_message(400, "fail", "参数不全")
                return Response(result, status=result.get("code", 200))
        try:
            if group_id == "-1":
                code = 400
                result = general_message(400, "group id error", "未分组应用不可分享")
                return Response(result, status=code)
            team_id = self.team.tenant_id
            group_count = group_repo.get_group_count_by_team_id_and_group_id(team_id=team_id, group_id=group_id)
            if group_count == 0:
                code = 202
                result = general_message(code, "group is not yours!", "当前组已删除或您无权限查看!", bean={})
                return Response(result, status=200)
            # 判断是否满足分享条件
            data = share_service.check_service_source(
                team=self.team, team_name=team_name, group_id=group_id, region_name=self.response_region)
            if data and data["code"] == 400:
                return Response(data, status=data["code"])
            fields_dict = {
                "group_share_id": make_uuid(),
                "group_id": group_id,
                "team_name": team_name,
                "is_success": False,
                "step": 1,
                "share_app_market_name": market_name,
                "scope": scope,
                "create_time": datetime.datetime.now(),
                "update_time": datetime.datetime.now(),
            }
            service_share_record = share_service.create_service_share_record(**fields_dict)
            result = general_message(200, "create success", "创建成功", bean=service_share_record.to_dict())
            return Response(result, status=200)
        except ServiceHandleException as e:
            raise e
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServiceShareRecordInfoView(RegionTenantHeaderView):
    def get(self, request, team_name, group_id, record_id, *args, **kwargs):
        data = None
        share_record = share_repo.get_service_share_record_by_id(group_id=group_id, record_id=record_id)
        if share_record:
            app_model_name = None
            app_model_id = None
            version = None
            version_alias = None
            upgrade_time = None
            store_name = None
            store_version = "1.0"
            store_id = share_record.share_app_market_name
            scope = share_record.scope
            if store_id:
                extend, market = app_market_service.get_app_market(
                    self.tenant.enterprise_id, share_record.share_app_market_name, extend="true", raise_exception=True)
                if market:
                    store_name = market.name
                    store_version = extend.get("version", store_version)
            app = rainbond_app_repo.get_rainbond_app_by_app_id(self.tenant.enterprise_id, share_record.app_id)
            if app:
                app_model_id = share_record.app_id
                app_model_name = app.app_name
            app_version = rainbond_app_repo.get_rainbond_app_version_by_record_id(share_record.ID)
            if app_version:
                version = app_version.version
                version_alias = app_version.version_alias
                upgrade_time = app_version.upgrade_time
            data = {
                "app_model_id": app_model_id,
                "app_model_name": app_model_name,
                "version": version,
                "version_alias": version_alias,
                "scope": scope,
                "create_time": share_record.create_time,
                "upgrade_time": upgrade_time,
                "step": share_record.step,
                "is_success": share_record.is_success,
                "status": share_record.status,
                "scope_target": {
                    "store_name": store_name,
                    "store_id": store_id,
                    "store_version": store_version
                },
                "record_id": share_record.ID,
            }
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=200)

    def put(self, request, team_name, group_id, record_id, *args, **kwargs):
        status = request.data.get("status")
        share_record = share_repo.get_service_share_record_by_id(group_id=group_id, record_id=record_id)
        if share_record and status:
            share_record.status = status
            share_record.save()
            result = general_message(200, "success", None, bean=share_record.to_dict())
            return Response(result, status=200)

    def delete(self, request, team_name, group_id, record_id, *args, **kwargs):
        share_record = share_repo.get_service_share_record_by_id(group_id=group_id, record_id=record_id)
        if share_record:
            share_record.status = 3
            share_record.save()
        result = general_message(200, "success", None)
        return Response(result, status=200)


class ServiceShareDeleteView(RegionTenantHeaderView):
    def delete(self, request, team_name, share_id, *args, **kwargs):
        """
        放弃应用分享操作，放弃时删除分享记录
        ---
        parameter:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: share_id
              description: 分享订单ID
              required: true
              type: string
              paramType: path
        """
        try:
            share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
            if not share_record:
                result = general_message(404, "share record not found", "分享流程不存在，不能放弃")
                return Response(result, status=404)
            if share_record.is_success or share_record.step >= 3:
                result = general_message(400, "share record is complete", "分享流程已经完成，无法放弃")
                return Response(result, status=400)
            app = share_service.get_app_by_key(key=share_record.group_share_id)
            if app and not app.is_complete:
                share_service.delete_app(app)
            share_service.delete_record(share_record)
            result = general_message(200, "delete success", "放弃成功")
            return Response(result, status=200)
        except ServiceHandleException as e:
            raise e
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServiceShareInfoView(RegionTenantHeaderView):
    def get(self, request, team_name, share_id, *args, **kwargs):
        """
        查询分享的所有应用信息和插件信息
        ---
        parameter:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: share_id
              description: 分享订单ID
              required: true
              type: string
              paramType: path
        """
        data = dict()
        scope = request.GET.get("scope")
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
            return Response(result, status=404)
        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
            return Response(result, status=400)
        if not scope:
            scope = share_record.scope
        service_info_list = share_service.query_share_service_info(team=self.team, group_id=share_record.group_id, scope=scope)
        data["share_service_list"] = service_info_list
        plugins = share_service.get_group_services_used_plugins(group_id=share_record.group_id)
        data["share_plugin_list"] = plugins
        result = general_message(200, "query success", "获取成功", bean=data)
        return Response(result, status=200)

    def post(self, request, team_name, share_id, *args, **kwargs):
        """
        生成分享应用实体，向数据中心发送分享任务
        ---
        parameter:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: share_id
              description: 分享流程ID
              required: true
              type: string
              paramType: path
        """
        use_force = parse_argument(request, 'use_force', default=False, value_type=bool)
        is_plugin = parse_argument(request, 'is_plugin', default=False, value_type=bool)
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
            return Response(result, status=404)
        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
            return Response(result, status=400)

        if not request.data:
            result = general_message(400, "share info can not be empty", "分享信息不能为空")
            return Response(result, status=400)
        app_version_info = request.data.get("app_version_info", None)
        share_app_info = request.data.get("share_service_list", None)
        if not app_version_info or not share_app_info:
            result = general_message(400, "share info can not be empty", "分享应用基本信息或应用信息不能为空")
            return Response(result, status=400)
        if not app_version_info.get("app_model_id", None):
            result = general_message(400, "share app model id can not be empty", "分享应用信息不全")
            return Response(result, status=400)

        if share_app_info:
            for app in share_app_info:
                extend_method = app.get("extend_method", "")
                if is_singleton(extend_method):
                    extend_method_map = app.get("extend_method_map")
                    if extend_method_map and extend_method_map.get("max_node", 1) > 1:
                        result = general_message(400, "service type do not allow multiple node", "分享应用不支持多实例")
                        return Response(result, status=400)

        # 继续给app_template_incomplete赋值
        code, msg, bean = share_service.create_share_info(
            tenant=self.tenant,
            region_name=self.region_name,
            share_record=share_record,
            share_team=self.team,
            share_user=request.user,
            share_info=request.data,
            use_force=use_force)
        bean['is_plugin'] = is_plugin
        result = general_message(code, "create share info", msg, bean=bean)
        return Response(result, status=code)


class ServiceShareEventList(RegionTenantHeaderView):
    def get(self, request, team_name, share_id, *args, **kwargs):
        try:
            share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
            if not share_record:
                result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
                return Response(result, status=404)
            if share_record.is_success or share_record.step >= 3:
                result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
                return Response(result, status=400)
            events = ServiceShareRecordEvent.objects.filter(record_id=share_id)
            if not events:
                result = general_message(404, "not exist", "分享事件不存在")
                return Response(result, status=404)
            result = {}
            result["event_list"] = list()
            for event in events:
                if event.event_status != "success":
                    result["is_compelte"] = False
                service_event_map = event.to_dict()
                service_event_map["type"] = "service"
                result["event_list"].append(service_event_map)
            # 查询插件分享事件
            plugin_events = PluginShareRecordEvent.objects.filter(record_id=share_id)
            for plugin_event in plugin_events:
                if plugin_event.event_status != "success":
                    result["is_compelte"] = False
                plugin_event_map = plugin_event.to_dict()
                plugin_event_map["type"] = "plugin"
                result["event_list"].append(plugin_event_map)
            result = general_message(200, "query success", "获取成功", bean=result)
            return Response(result, status=200)
        except ServiceHandleException as e:
            raise e
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServiceShareEventPost(RegionTenantHeaderView):
    def post(self, request, team_name, share_id, event_id, *args, **kwargs):
        try:
            share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
            if not share_record:
                result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
                return Response(result, status=404)
            if share_record.is_success or share_record.step >= 3:
                result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
                return Response(result, status=400)
            events = ServiceShareRecordEvent.objects.filter(record_id=share_id, ID=event_id)
            if not events:
                result = general_message(404, "not exist", "分享事件不存在")
                return Response(result, status=404)
            record_event = share_service.sync_event(self.user, self.response_region, team_name, events[0])
            bean = record_event.to_dict() if record_event is not None else None
            result = general_message(200, "sync share event", "分享完成", bean=bean)
            return Response(result, status=200)
        except ServiceHandleException as e:
            raise e
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)

    def get(self, request, team_name, share_id, event_id, *args, **kwargs):
        try:
            share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
            if not share_record:
                result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
                return Response(result, status=404)
            if share_record.is_success or share_record.step >= 3:
                result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
                return Response(result, status=400)
            events = ServiceShareRecordEvent.objects.filter(record_id=share_id, ID=event_id)
            if not events:
                result = general_message(404, "not exist", "分享事件不存在")
                return Response(result, status=404)
            if events[0].event_status == "success":
                result = general_message(200, "get sync share event result", "查询成功", bean=events[0].to_dict())
                return Response(result, status=200)
            bean = share_service.get_sync_event_result(self.response_region, team_name, events[0])
            result = general_message(200, "get sync share event result", "查询成功", bean=bean.to_dict())
            return Response(result, status=200)
        except ServiceHandleException as e:
            raise e
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServicePluginShareEventPost(RegionTenantHeaderView):
    def post(self, request, team_name, share_id, event_id, *args, **kwargs):
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
            return Response(result, status=404)
        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
            return Response(result, status=400)
        events = PluginShareRecordEvent.objects.filter(record_id=share_id, ID=event_id)
        if not events:
            result = general_message(404, "not exist", "分享事件不存在")
            return Response(result, status=404)

        bean = share_service.sync_service_plugin_event(self.user, self.response_region, self.tenant.tenant_name, share_id,
                                                       events[0])
        if not bean:
            result = general_message(400, "sync share event", "插件不存在无需发布")
        else:
            result = general_message(200, "sync share event", "分享成功", bean=bean.to_dict())
        return Response(result, status=result["code"])

    def get(self, request, team_name, share_id, event_id, *args, **kwargs):
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
            return Response(result, status=404)
        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
            return Response(result, status=400)

        plugin_events = PluginShareRecordEvent.objects.filter(record_id=share_id, ID=event_id).order_by("ID")
        if not plugin_events:
            result = general_message(404, "not exist", "分享事件不存在")
            return Response(result, status=404)

        if plugin_events[0].event_status == "success":
            result = general_message(200, "get sync share event result", "查询成功", bean=plugin_events[0].to_dict())
            return Response(result, status=200)
        bean = share_service.get_sync_plugin_events(self.response_region, team_name, plugin_events[0])
        result = general_message(200, "get sync share event result", "查询成功", bean=bean.to_dict())
        return Response(result, status=200)


class ServiceShareCompleteView(RegionTenantHeaderView):
    def post(self, request, team_name, share_id, *args, **kwargs):
        is_plugin = parse_argument(request, 'is_plugin', default=False, value_type=bool)
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
            return Response(result, status=404)
        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
            return Response(result, status=400)
        # 验证是否所有同步事件已完成
        count = ServiceShareRecordEvent.objects.filter(Q(record_id=share_id) & ~Q(event_status="success")).count()
        plugin_count = PluginShareRecordEvent.objects.filter(Q(record_id=share_id) & ~Q(event_status="success")).count()
        if count > 0 or plugin_count > 0:
            result = general_message(415, "share complete can not do", "组件或插件同步未全部完成")
            return Response(result, status=415)
        app_market_url = share_service.complete(self.tenant, self.user, share_record, is_plugin)
        result = general_message(200, "share complete", "应用分享完成", bean=share_record.to_dict(), app_market_url=app_market_url)
        return Response(result, status=200)


class ShareRecordView(RegionTenantHeaderView):
    def get(self, request, team_name, group_id, *args, **kwargs):
        """
        查询是否有未确认分享订单记录
        ---
        parameter:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用id
              required: true
              type: string
              paramType: path
        """
        share_record = share_repo.get_service_share_record_by_groupid(group_id=group_id)
        if share_record and share_record.step == 2:
            result = general_message(
                200, "the current application does not confirm sharing", "当前应用未确认分享", bean=share_record.to_dict())
            return Response(result, status=200)
        result = general_message(
            200, "the current application is not Shared or Shared", "当前应用未分享或已分享", bean=share_record.to_dict())
        return Response(result, status=200)


class ShareServicesListView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        try:
            share_services = share_repo.get_shared_apps_by_team(team_name)
        except Exception as e:
            logger.debug(e)
            return Response(error_message(e.message), status=404)
        data = list(map(share_service.get_shared_services_list, share_services))
        rst = general_message(200, "get shared apps list complete", None, bean=data)
        return Response(rst, status=200)


class ServiceGroupSharedApps(RegionTenantHeaderView):
    def get(self, request, team_name, group_id, *args, **kwargs):
        scope = request.GET.get("scope", None)
        market_name = request.GET.get("market_id", None)
        data = share_service.get_last_shared_app_and_app_list(self.tenant.enterprise_id, self.tenant, group_id, scope,
                                                              market_name)
        result = general_message(
            200, "get shared apps list complete", None, bean=data["last_shared_app"], list=data["app_model_list"])
        return Response(result, status=200)


class AppMarketCLView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        extend = request.GET.get("extend", "false")
        app_markets = app_market_service.get_app_markets(enterprise_id, extend)
        result = general_message(200, "success", None, list=app_markets)
        return Response(result, status=200)

    def post(self, request, enterprise_id, *args, **kwargs):
        name = request.data.get("name")
        if not market_name_format(name):
            raise ServiceHandleException(msg="name format error", msg_show="标识必须以字母开头且为数字字母组合")
        if len(name) > 64:
            raise ServiceHandleException(msg="store note too lang", msg_show="应用市场标识字符串长度不能超过64")
        access_key = request.data.get("access_key")
        if len(access_key) > 255:
            raise ServiceHandleException(msg="access key too long", msg_show="Access Key 字符串长度不能超过255")
        dt = {
            "name": name,
            "url": request.data.get("url"),
            "type": request.data.get("type"),
            "enterprise_id": enterprise_id,
            "access_key": access_key,
            "domain": request.data.get("domain"),
        }

        app_market = app_market_service.create_app_market(dt)
        result = general_message(200, "success", None, bean=app_market.to_dict())
        return Response(result, status=200)


class AppMarketBatchCView(JWTAuthApiView):
    def post(self, request, enterprise_id, *args, **kwargs):
        data = []
        for market in request.data.get("markets", []):
            name = market["name"]
            if not market_name_format(name):
                raise ServiceHandleException(msg="name format error", msg_show="标识必须以字母开头且为数字字母组合")
            if len(name) > 64:
                raise ServiceHandleException(msg="store note too lang", msg_show="应用市场标识字符串长度不能超过64")
            access_key = market["access_key"]
            if len(access_key) > 255:
                raise ServiceHandleException(msg="access key too long", msg_show="Access Key 字符串长度不能超过255")
            data.append({
                "name": name,
                "url": market["url"],
                "type": market["type"],
                "enterprise_id": enterprise_id,
                "access_key": access_key,
                "domain": market["domain"],
            })

        app_market = app_market_service.batch_create_app_market(enterprise_id, data)
        result = general_message(200, "success", None, bean=app_market)
        return Response(result, status=200)


class AppMarketRUDView(JWTAuthApiView):
    def get(self, request, enterprise_id, market_name, *args, **kwargs):
        extend = request.GET.get("extend", "false")
        market, _ = app_market_service.get_app_market(enterprise_id, market_name, extend, raise_exception=True)
        result = general_message(200, "success", None, list=market)
        return Response(result, status=200)

    def put(self, request, enterprise_id, market_name, *args, **kwargs):
        _, market_model = app_market_service.get_app_market(enterprise_id, market_name, raise_exception=True)
        request.data["enterprise_id"] = enterprise_id
        request.data["market_name"] = market_name
        new_market = app_market_service.update_app_market(market_model, request.data)
        result = general_message(200, "success", None, list=new_market.to_dict())
        return Response(result, status=200)

    def delete(self, request, enterprise_id, market_name, *args, **kwargs):
        _, market_model = app_market_service.get_app_market(enterprise_id, market_name, raise_exception=True)
        market_model.delete()
        result = general_message(200, "success", None)
        return Response(result, status=200)


class AppMarketAppModelLView(JWTAuthApiView):
    def get(self, request, enterprise_id, market_name, *args, **kwargs):
        query = request.GET.get("query", None)
        query_all = request.GET.get("query_all", False)
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        is_plugin = request.GET.get("is_plugin", False)
        market_model = app_market_service.get_app_market_by_name(enterprise_id, market_name, raise_exception=True)
        if is_plugin == "true":
            data, page, page_size, total = app_market_service.get_market_plugins_apps(
                market_model, page, page_size, query=query, query_all=query_all, extend=True)
        else:
            data, page, page_size, total = app_market_service.get_market_app_models(
                market_model, page, page_size, query=query, query_all=query_all, extend=True)
        result = general_message(200, msg="success", msg_show=None, list=data, page=page, page_size=page_size, total=total)
        return Response(result, status=200)

    def post(self, request, enterprise_id, market_name, *args, **kwargs):
        logo = request.data.get("logo")
        base64_logo = ""
        if logo:
            if logo.startswith(settings.MEDIA_URL):
                logo = logo.replace(settings.MEDIA_URL, settings.MEDIA_ROOT + "/")
            try:
                with open(logo, "rb") as f:
                    base64_logo = "data:image/{};base64,".format(logo.split(".")[-1]) + base64.b64encode(f.read()).decode()
            except Exception as e:
                logger.exception(e)
                base64_logo = ""
        name = request.data.get("name", "")
        if not validate_name(name):
            raise ServiceHandleException(msg="error params", msg_show="应用名称只支持中文、字母、数字和-_组合,并且必须以中文、字母、数字开始和结束")

        dt = {
            "desc": request.data.get("desc"),
            "logo": base64_logo,
            "name": name,
            "publish_type": request.data.get("publish_type"),
            "tags": request.data.get("tags"),
            "introduction": request.data.get("introduction"),
            "org_id": request.data.get("org_id")
        }
        market = app_market_service.get_app_market_by_name(enterprise_id, market_name, raise_exception=True)
        rst = app_market_service.create_market_app_model(market, body=dt)
        result = general_message(200, msg="success", msg_show=None, bean=(rst.to_dict() if rst else None))
        return Response(result, status=200)


class AppMarketAppModelVersionsLView(JWTAuthApiView):
    def get(self, request, enterprise_id, market_name, app_id, *args, **kwargs):
        query_all = request.GET.get("query_all", False)
        market_model = app_market_service.get_app_market_by_name(enterprise_id, market_name, raise_exception=True)
        data = app_market_service.get_market_app_model_versions(market_model, app_id, query_all=query_all, extend=True)
        result = general_message(200, "success", None, list=data)
        return Response(result, status=200)


class AppMarketAppModelVersionsRView(JWTAuthApiView):
    def get(self, request, enterprise_id, market_name, app_id, version, *args, **kwargs):
        _, market_model = app_market_service.get_app_market(enterprise_id, market_name, raise_exception=True)
        data = app_market_service.get_market_app_model_version(market_model, app_id, version, extend=True)
        result = general_message(200, "success", None, bean=data)
        return Response(result, status=200)


class AppMarketOrgModelLView(JWTAuthApiView):
    def get(self, request, enterprise_id, market_name):
        market_model = app_market_service.get_app_market_by_name(enterprise_id, market_name, raise_exception=True)
        orgs = app_market_service.get_market_orgs(market_model)
        result = general_message(200, msg="success", msg_show=None, list=orgs)
        return Response(result, status=200)

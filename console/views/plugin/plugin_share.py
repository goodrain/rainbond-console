# -*- coding: utf-8 -*-
import logging

from django.db.models import Q
from rest_framework.response import Response

from console.models.main import PluginShareRecordEvent
from console.repositories.plugin import plugin_repo
from console.repositories.share_repo import share_repo
from console.services.market_plugin_service import market_plugin_service
from console.services.share_services import share_service
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.services import plugin_svc
from www.utils.crypt import make_uuid
from www.utils.return_message import general_message, error_message

logger = logging.getLogger('default')


class PluginShareRecordView(RegionTenantHeaderView):
    def get(self, request, team_name, plugin_id, *args, **kwargs):
        """
        查询插件分享记录
        :param request:
        :param team_name:
        :param plugin_id:
        :param args:
        :param kwargs:
        :return:
        """
        share_record = share_repo.get_service_share_record_by_groupid(plugin_id)
        if share_record:
            if not share_record.is_success and share_record.step < 3:
                result = general_message(20021, "share record not complete", "分享流程未完成", bean=share_record.to_dict())
                return Response(result, status=200)

        result = general_message(200, "not found uncomplete share record", "无未完成分享流程")
        return Response(data=result, status=200)

    # @perm_required('share_plugin')
    def post(self, request, team_name, plugin_id, *args, **kwargs):
        """
        创建分享插件记录
        ---
        parameter:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件id
              required: true
              type: string
              paramType: path
            - name: build_version
              description: 构建版本
              required: true
              type: string
              paramType: path
        """
        # try:
        team_id = self.team.tenant_id

        plugin = plugin_repo.get_plugin_by_plugin_id(team_id, plugin_id)
        if not plugin:
            return Response(general_message(404, 'plugin not exist', '插件不存在'))

        share_record = share_service.get_service_share_record_by_group_id(plugin_id)
        if share_record:
            if not share_record.is_success and share_record.step < 3:
                result = general_message(20021, "share not complete", "有分享流程未完成", bean=share_record.to_dict())
                return Response(result, status=200)

        status, msg, msg_show = market_plugin_service.check_plugin_share_condition(self.team, plugin_id,
                                                                                   self.response_region)
        if status != 200:
            return Response(general_message(status, msg, msg_show), status=status)

        record = {
            "group_share_id": make_uuid(),
            "group_id": plugin_id,
            "team_name": team_name,
            "is_success": False,
            "step": 1,
        }
        service_share_record = share_service.create_service_share_record(**record)
        result = general_message(200, "create success", "创建成功", bean=service_share_record.to_dict())
        return Response(result, status=200)
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        #     return Response(result, status=500)


class PluginShareInfoView(RegionTenantHeaderView):
    # @perm_required("view_plugin")
    def get(self, request, team_name, share_id, *args, **kwargs):
        """
        查询分享的插件信息
        ---
        parameter:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: share_id
              description: 分享记录ID
              required: true
              type: string
              paramType: path
        """
        team_id = self.team.tenant_id

        # try:
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
            return Response(result, status=404)
        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
            return Response(result, status=400)

        share_plugin_info = dict()
        share_plugin = share_repo.get_share_plugin(share_record.group_id)

        if share_plugin:
            plugin_id = share_plugin.plugin_id
            share_plugin_info = share_plugin.to_dict()
            share_plugin_info["is_shared"] = True
            share_plugin_info.pop("update_time")
        else:
            plugin = plugin_repo.get_plugin_by_plugin_id(team_id, share_record.group_id)
            if not plugin:
                result = general_message(404, msg="plugin not exist", msg_show="插件不存在")
                return Response(result, status=400)

            plugin_id = plugin.plugin_id

            share_plugin_info["category"] = plugin.category
            share_plugin_info["plugin_key"] = make_uuid()
            share_plugin_info["plugin_id"] = plugin_id
            share_plugin_info["plugin_name"] = plugin.plugin_alias
            share_plugin_info["version"] = "1.0"
            share_plugin_info["desc"] = "This is a default description."
            share_plugin_info["scope"] = "team"
            share_plugin_info["share_id"] = share_record.group_id
            share_plugin_info["pic"] = ""
            share_plugin_info["share_user"] = str(self.user.user_id)
            share_plugin_info["share_team"] = team_name
            share_plugin_info["is_shared"] = False

            plugin_version = plugin_svc.get_tenant_plugin_newest_versions(self.response_region, self.tenant, plugin_id)

            share_plugin_info["build_version"] = plugin_version[0].build_version

            config_groups = []
            for group in plugin_repo.get_plugin_config_groups(plugin_id, plugin_version[0].build_version):
                group_map = group.to_dict()

                items = plugin_svc.get_config_items_by_id_metadata_and_version(group.plugin_id, group.build_version,
                                                                               group.service_meta_type)

                config_items = []
                for item in items:
                    config_items.append(item.to_dict())

                group_map['config_items'] = config_items
                config_groups.append(group_map)

            share_plugin_info["config_groups"] = config_groups

        return Response(general_message(200, "", "", bean={'share_plugin_info': share_plugin_info}), 200)
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        #     return Response(result, status=500)

    # @perm_required("share_plugin")
    def post(self, request, team_name, share_id, *args, **kwargs):
        """
        创建插件分享
        ---
        parameter:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: share_id
              description: 分享记录ID
              required: true
              type: string
              paramType: path
        """
        # try:
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

        share_info = request.data

        status, msg, plugin = market_plugin_service.create_plugin_share_info(share_record, share_info, self.user.user_id,
                                                                             self.team, self.response_region)

        result = general_message(status, "create share info", msg, bean=plugin)
        return Response(result, status=status)
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        #     return Response(result, status=500)

    # @perm_required("share_plugin")
    def delete(self, request, team_name, share_id, *args, **kwargs):
        """
        放弃插件分享
        ---
        parameter:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: share_id
              description: 分享记录ID
              required: true
              type: string
              paramType: path
        """
        # try:
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在")
            return Response(result, status=404)

        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，无法放弃")
            return Response(result, status=404)

        share_plugin = share_repo.get_share_plugin(share_record.group_id)
        if share_plugin and share_plugin.is_complete:
            share_record.delete()
            PluginShareRecordEvent.objects.filter(record_id=share_record.ID).delete()
            share_plugin.delete()
            return Response(general_message(200, msg='', msg_show=''), 200)

        PluginShareRecordEvent.objects.filter(record_id=share_record.ID).delete()
        share_record.delete()
        result = general_message(200, "delete success", "放弃成功")
        return Response(result, status=200)
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        #     return Response(result, status=500)


class PluginShareEventsView(RegionTenantHeaderView):
    # @perm_required("share_plugin")
    def get(self, request, team_name, share_id, *args, **kwargs):
        """
        获取插件分享事件
        :param request:
        :param team_name:
        :param share_id:
        :param args:
        :param kwargs:
        :return:
        """
        # try:
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
            return Response(result, status=404)

        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
            return Response(result, status=400)

        events = PluginShareRecordEvent.objects.filter(record_id=share_id)
        if not events:
            result = general_message(404, "not exist", "分享事件不存在")
            return Response(result, status=404)

        data = {"event_list": []}

        for event in events:
            if event.event_status != "success":
                data["is_compelte"] = False
            data["event_list"].append(event.to_dict())

        result = general_message(200, "query success", "获取成功", bean=data)
        return Response(result, status=200)
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        #     return Response(result, status=500)


class PluginShareEventView(RegionTenantHeaderView):
    # @perm_required("share_plugin")
    def get(self, request, team_name, share_id, event_id, *args, **kwargs):
        """
        获取插件分享事件列表
        :param request:
        :param team_name: 租户名
        :param share_id: 分享id
        :param event_id: 事件id
        :param args:
        :param kwargs:
        :return:
        """
        # try:
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
            return Response(result, status=404)

        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
            return Response(result, status=400)

        try:
            event = PluginShareRecordEvent.objects.get(ID=event_id)
            if event.event_status == 'success':
                result = general_message(200, "get sync share event result", "查询成功", bean=event.to_dict())
                return Response(result, status=200)

            event_result = market_plugin_service.get_sync_event_result(self.response_region, team_name, event)

            result = general_message(200, "get sync share event result", "查询成功", bean=event_result.to_dict())
            return Response(result, status=200)

        except PluginShareRecordEvent.DoesNotExist:
            result = general_message(404, "not exist", "分享事件不存在")
            return Response(result, status=404)
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        #     return Response(result, status=500)

    # @perm_required("share_plugin")
    def post(self, request, team_name, share_id, event_id, *args, **kwargs):
        """
        创建分享事件
        :param request:
        :param team_name:
        :param share_id:
        :param event_id:
        :param args:
        :param kwargs:
        :return:
        """
        # try:
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
            return Response(result, status=404)

        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
            return Response(result, status=400)

        try:
            event = PluginShareRecordEvent.objects.get(record_id=share_id, ID=event_id)

            status, msg, data = market_plugin_service.sync_event(self.user.nick_name, self.response_region, team_name,
                                                                 event)

            if status != 200:
                result = general_message(status, "sync share event failed", msg)
                return Response(result, status=status)

            result = general_message(status, "sync share event", msg, bean=data.to_dict())
            return Response(result, status=status)

        except PluginShareRecordEvent.DoesNotExist:
            result = general_message(404, "not exist", "分享事件不存在")
            return Response(result, status=404)
        #
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        #     return Response(result, status=500)


class PluginShareCompletionView(RegionTenantHeaderView):
    # @perm_required("share_plugin")
    def post(self, request, team_name, share_id, *args, **kwargs):
        """
        创建分享完成接口
        :param request:
        :param team_name:
        :param share_id:
        :param args:
        :param kwargs:
        :return:
        """
        # try:
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
        if not share_record:
            result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
            return Response(result, status=404)

        if share_record.is_success or share_record.step >= 3:
            result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
            return Response(result, status=400)

        # 验证是否所有同步事件已完成
        count = PluginShareRecordEvent.objects. \
            filter(Q(record_id=share_id) & ~Q(event_status="success")).count()

        if count > 0:
            result = general_message(415, "share complete can not do", "插件同步未完成")
            return Response(result, status=415)

        app_market_url = market_plugin_service.plugin_share_completion(self.tenant, share_record, self.user.nick_name)
        result = general_message(
            200, "share complete", "插件分享完成", bean=share_record.to_dict(), app_market_url=app_market_url)
        return Response(result, status=200)
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        # return Response(result, status=result["code"])

# -*- coding: utf-8 -*-
import datetime
import json
import logging

from django.db.models import Q
from rest_framework.response import Response

from backends.services.exceptions import UserNotExistError
from console.models.main import ServiceShareRecordEvent
from console.repositories.group import group_repo
from console.repositories.share_repo import share_repo
from console.services.group_service import group_service
from console.services.share_services import share_service
from console.services.user_services import user_services
from console.views.base import RegionTenantHeaderView
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.utils.crypt import make_uuid
from www.utils.return_message import general_message, error_message

logger = logging.getLogger('default')
region_api = RegionInvokeApi()


class ServiceShareRecordView(RegionTenantHeaderView):
    def get(self, request, team_name, group_id, *args, **kwargs):
        """
        查询是否有未完成分享订单记录
        ---
        parameter:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用组id
              required: true
              type: string
              paramType: path
        """
        share_record = share_repo.get_service_share_record_by_groupid(group_id=group_id)
        if share_record:
            if not share_record.is_success and share_record.step < 3:
                result = general_message(20021, "share record not complete", "分享流程未完成", bean=share_record.to_dict())
                return Response(result, status=200)
        return Response(data=general_message(200, "not found not completed share record", "无未完成分享流程"), status=200)

    @perm_required('share_service')
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
              description: 应用组id
              required: true
              type: string
              paramType: path
        """
        try:
            if group_id == "-1":
                code = 400
                result = general_message(400, "group id error", "未分组应用不可分享")
                return Response(result, status=code)
            team_id = self.team.tenant_id
            group_count = group_repo.get_group_count_by_team_id_and_group_id(team_id=team_id, group_id=group_id)
            if group_count == 0:
                code = 400
                result = general_message(code, "group is not yours!", "这个应用组不是你的!")
                return Response(result, status=code)
            # 判断是否满足分享条件
            data = share_service.check_service_source(
                team=self.team,
                team_name=team_name,
                group_id=group_id,
                region_name=self.response_region)
            if data and data["code"] == 400:
                return Response(data, status=data["code"])
            # 判断是否有未完成订单
            share_record = share_service.get_service_share_record_by_group_id(group_id)
            if share_record:
                if not share_record.is_success and share_record.step < 3:
                    result = general_message(20021, "share record not complete", "之前有分享流程未完成",
                                             bean=share_record.to_dict())
                    return Response(result, status=200)
            fields_dict = {
                "group_share_id": make_uuid(),
                "group_id": group_id,
                "team_name": team_name,
                "is_success": False,
                "step": 1,
                "create_time": datetime.datetime.now(),
                "update_time": datetime.datetime.now()
            }
            service_share_record = share_service.create_service_share_record(**fields_dict)
            result = general_message(200, "create success", "创建成功", bean=service_share_record.to_dict())
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServiceShareDeleteView(RegionTenantHeaderView):
    @perm_required('share_service')
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
                return Response(result, status=404)
            app = share_service.get_app_by_key(key=share_record.group_share_id)
            if app and not app.is_complete:
                share_service.delete_app(app)
            share_service.delete_record(share_record)
            result = general_message(200, "delete success", "放弃成功")
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServiceShareInfoView(RegionTenantHeaderView):
    @perm_required('view_service')
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
        try:
            share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
            if not share_record:
                result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
                return Response(result, status=404)
            if share_record.is_success or share_record.step >= 3:
                result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
                return Response(result, status=400)
            # 获取分享应用组基本信息
            data = dict()
            share_group_info = dict()
            share_group = share_service.check_whether_have_share_history(group_id=share_record.group_id)
            if share_group:
                share_group_info["group_key"] = share_group.group_key
                share_group_info["group_name"] = share_group.group_name
                share_group_info["version"] = share_group.version
                share_group_info["describe"] = share_group.describe
                share_group_info["scope"] = share_group.scope
                share_group_info["share_id"] = share_group.ID
                share_group_info["pic"] = share_group.pic
                share_group_info["share_team"] = share_group.share_team
                share_group_info["share_user"] = share_group.share_user
                share_group_info["is_shared"] = True
                data["share_group_info"] = share_group_info
            else:
                try:
                    user = user_services.get_user_by_user_name(user_name=request.user)
                    if not user:
                        result = general_message(400, "user failed", "数据紊乱，非当前用户操作页面")
                        return Response(result, status=400)
                except UserNotExistError as e:
                    result = general_message(400, e.message, "用户不存在")
                    return Response(result, status=400)
                code, msg, group = group_service.get_group_by_id(
                    tenant=self.team,
                    region=self.response_region,
                    group_id=share_record.group_id)
                if code == 200:
                    share_group_info["group_key"] = make_uuid()
                    share_group_info["group_name"] = group.get("group_name")
                    share_group_info["version"] = 'v1.0'
                    share_group_info["describe"] = 'This is a default description.'
                    share_group_info["scope"] = 'team'
                    share_group_info["share_id"] = share_record.group_id
                    share_group_info["pic"] = ''
                    share_group_info["share_team"] = team_name
                    share_group_info["share_user"] = str(user.user_id)
                    share_group_info["is_shared"] = False
                    data["share_group_info"] = share_group_info
                else:
                    result = general_message(code=code, msg="failed", msg_show=msg)
                    return Response(result, status=code)
            service_info_list = share_service.query_share_service_info(
                team=self.team, group_id=share_record.group_id)
            data["share_service_list"] = service_info_list
            plugins = share_service.query_group_service_plugin_list(
                team=self.team, group_id=share_record.group_id)
            data["share_plugin_list"] = plugins
            result = general_message(200, "query success", "获取成功", bean=data)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)

    @perm_required('share_service')
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
        try:
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
            share_group_info = request.data.get("share_group_info", None)
            share_app_info = request.data.get("share_service_list", None)
            if not share_group_info or not share_app_info:
                result = general_message(400, "share info can not be empty", "分享应用基本信息或应用信息不能为空")
                return Response(result, status=400)
            if not share_group_info.get("group_key", None):
                result = general_message(400, "share group key can not be empty", "分享应用信息不全")
                return Response(result, status=400)
            # 继续给app_template_incomplete赋值
            code, msg, bean = share_service.create_share_info(
                share_record=share_record,
                share_team=self.team,
                share_user=request.user,
                share_info=request.data)
            result = general_message(code, "create share info", msg, bean=bean)
            return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServiceShareEventList(RegionTenantHeaderView):
    @perm_required('share_service')
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
                result["event_list"].append(event.to_dict())
            result = general_message(200, "query success", "获取成功", bean=result)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServiceShareEventPost(RegionTenantHeaderView):
    @perm_required('share_service')
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
            code, msg, bean = share_service.sync_event(self.user, self.response_region, team_name, events[0])
            result = general_message(code, "sync share event", msg, bean=bean.to_dict())
            return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)

    @perm_required('share_service')
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
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class ServiceShareCompleteView(RegionTenantHeaderView):
    @perm_required('share_service')
    def post(self, request, team_name, share_id, *args, **kwargs):
        try:
            share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team_name)
            if not share_record:
                result = general_message(404, "share record not found", "分享流程不存在，请退出重试")
                return Response(result, status=404)
            if share_record.is_success or share_record.step >= 3:
                result = general_message(400, "share record is complete", "分享流程已经完成，请重新进行分享")
                return Response(result, status=400)
            # 验证是否所有同步事件已完成
            count = ServiceShareRecordEvent.objects.filter(Q(record_id=share_id) & ~Q(event_status="success")).count()
            if count > 0:
                result = general_message(415, "share complete can not do", "应用同步未全部完成")
                return Response(result, status=415)
            app_market_url = share_service.complete(self.tenant, self.user, share_record)
            result = general_message(200, "share complete", "应用分享完成", bean=share_record.to_dict(),
                                     app_market_url=app_market_url)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
from django.views.decorators.cache import never_cache

from rest_framework.response import Response

from console.views.base import RegionTenantHeaderView
from goodrain_web.tools import JuncheePaginator
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
import logging
from console.services.market_app_service import market_app_service
from console.services.group_service import group_service
from console.services.market_app_service import market_sycn_service

logger = logging.getLogger('default')


class CenterAppListView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取本地市场应用
        ---
        parameters:
            - name: scope
              description: 范围
              required: false
              type: string
              paramType: query
            - name: app_name
              description: 应用名字
              required: false
              type: string
              paramType: query
            - name: page
              description: 当前页
              required: true
              type: string
              paramType: query
            - name: page_size
              description: 每页大小,默认为10
              required: true
              type: string
              paramType: query
        """
        scope = request.GET.get("scope", None)
        app_name = request.GET.get("app_name", None)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)
        try:
            apps = market_app_service.get_visiable_apps(self.tenant, scope, app_name)
            paginator = JuncheePaginator(apps, int(page_size))
            show_apps = paginator.page(int(page))
            app_list = []
            for app in show_apps:
                app_bean = app.to_dict()
                app_bean.pop("app_template")
                app_list.append(app_bean)
            result = general_message(200, "success", "查询成功", list=app_list, total=paginator.count,
                                     next_page=int(page) + 1)
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return Response(result, status=result["code"])


class CenterAppView(RegionTenantHeaderView):
    @never_cache
    @perm_required("create_service")
    def post(self, request, *args, **kwargs):
        """
        创建应用市场应用
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组id
              required: true
              type: string
              paramType: form
            - name: app_id
              description: rainbond app id
              required: true
              type: string
              paramType: form
        """
        try:
            group_id = request.data.get("group_id", -1)
            app_id = request.data.get("app_id", None)
            if not app_id:
                return Response(general_message(400, "app id is null", "请指明需要安装的应用"), status=400)
            if int(group_id) != -1:
                code, msg, group_info = group_service.get_group_by_id(self.tenant, self.response_region, group_id)
                if code != 200:
                    return Response(general_message(400, "group not exist", "所选组不存在"), status=400)

            code, app = market_app_service.get_rain_bond_app_by_pk(app_id)
            if not app:
                return Response(general_message(404, "not found", "云市应用不存在"), status=404)
            allow_create, tips, total_memory = market_app_service.check_package_app_resource(self.tenant, app)
            if not allow_create:
                return Response(general_message(412, "over resource", "应用所需内存大小为{0}，{1}".format(total_memory, tips)),
                                status=412)
            market_app_service.install_service(self.tenant, self.response_region, self.user, group_id, app)
            logger.debug("market app create success")
            result = general_message(200, "success", "创建成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class CenterAppManageView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        应用上下线
        ---
        parameters:
            - name: app_id
              description: rainbond app id
              required: true
              type: string
              paramType: form
             - name: action
              description: 操作类型 online|offline
              required: true
              type: string
              paramType: form
        """
        try:
            if not self.user.is_sys_admin:
                return Response(general_message(403, "you are not admin", "此操作需平台管理员才能操作"), status=403)
            app_id = request.data.get("app_id", None)
            action = request.data.get("action", None)
            if not app_id:
                return Response(general_message(400, "app id is null", "请指明需要安装的应用"), status=400)
            if not action:
                return Response(general_message(400, "action is not specified", "操作类型未指定"), status=400)
            if action not in ("online", "offline"):
                return Response(general_message(400, "action is not allow", "不允许的操作类型"), status=400)
            code, app = market_app_service.get_rain_bond_app_by_pk(app_id)
            if not app:
                return Response(general_message(404, "not found", "云市应用不存在"), status=404)
            if action == "online":
                app.is_complete = True
            else:
                app.is_complete = False
            app.save()
            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class DownloadMarketAppGroupView(RegionTenantHeaderView):
    @never_cache
    @perm_required("app_download")
    def get(self, request, *args, **kwargs):
        """
        同步下载云市组概要模板到云帮
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
        """
        try:
            if not self.user.is_sys_admin:
                return Response(general_message(403, "you are not admin", "无权限执行此操作"), status=403)
            logger.debug("start synchronized market apps")
            market_sycn_service.down_market_group_list(self.tenant)
            result = general_message(200, "success", "创建成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class DownloadMarketAppGroupTemplageDetailView(RegionTenantHeaderView):
    @never_cache
    @perm_required("app_download")
    def post(self, request, *args, **kwargs):
        """
        同步下载云市组详情模板到云帮
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: body
              description: 需要同步的应用[{"group_key":"xxxxxxx","version":"xxxxxx"}]
              required: true
              type: string
              paramType: body
        """
        try:
            if not self.user.is_sys_admin:
                return Response(general_message(403, "you are not admin", "无权限执行此操作"), status=403)
            logger.debug("start synchronized market apps detail")
            group_data = request.data["body"]
            logger.debug("group_data ======> {0}".format(group_data))
            # group_data = json.loads(group_data)
            data_list = []
            for d in group_data:
                data_list.append("{0}:{1}".format(d["group_key"], d["version"]))

            market_sycn_service.batch_down_market_group_app_details(self.tenant, data_list)
            result = general_message(200, "success", "创建成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class CenterAllMarketAppView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        查询从公有云同步的应用
        ---
        parameters:
            - name: page
              description: 当前页
              required: true
              type: string
              paramType: query
            - name: page_size
              description: 每页大小,默认为10
              required: true
              type: string
              paramType: query
        """
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)
        try:
            if not self.user.is_sys_admin:
                return Response(general_message(403, "you are not admin", "无权限执行此操作"), status=403)
            logger.debug("start synchronized market apps")
            apps = market_app_service.get_all_goodrain_market_apps()
            paginator = JuncheePaginator(apps, int(page_size))
            show_apps = paginator.page(int(page))
            app_list = []
            for app in show_apps:
                app_bean = app.to_dict()
                app_bean.pop("app_template")
                app_list.append(app_bean)

            result = general_message(200, "success", "查询成功", list=app_list, total=paginator.count,
                                     next_page=int(page) + 1)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

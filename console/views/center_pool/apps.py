# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
from django.views.decorators.cache import never_cache

from rest_framework.response import Response

from console.exception.main import ResourceNotEnoughException
from console.repositories.enterprise_repo import enterprise_repo
from console.views.base import RegionTenantHeaderView
from goodrain_web.tools import JuncheePaginator
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
import logging
from console.services.market_app_service import market_app_service
from console.services.group_service import group_service
from console.services.market_app_service import market_sycn_service
import json
from console.services.app_import_and_export_service import export_service
from console.services.enterprise_services import enterprise_services
from console.services.user_services import user_services

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
            apps = market_app_service.get_visiable_apps(self.tenant, scope, app_name) \
                .order_by('-update_time')
            paginator = JuncheePaginator(apps, int(page_size))
            show_apps = paginator.page(int(page))
            app_list = []
            for app in show_apps:
                min_memory = self.__get_service_group_memory(app.app_template, app_name)
                export_status = export_service.get_export_record_status(self.tenant.enterprise_id, app)
                app_bean = app.to_dict()
                app_bean["min_memory"] = min_memory
                app_bean["export_status"] = export_status
                app_bean.pop("app_template")
                app_list.append(app_bean)
            result = general_message(200, "success", "查询成功", list=app_list, total=paginator.count,
                                     next_page=int(page) + 1)
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return Response(result, status=result["code"])

    def __get_service_group_memory(self, app_template_raw, app_name):
        try:
            app_template = json.loads(app_template_raw)
            apps = app_template["apps"]
            total_memory = 0
            for app in apps:
                extend_method_map = app.get("extend_method_map", None)
                if extend_method_map:
                    total_memory += extend_method_map["min_node"] * extend_method_map["min_memory"]
                else:
                    total_memory += 128
            return total_memory
        except Exception as e:
            logger.debug("==============================>{0}".format(e))
            logger.debug("==============================================>{0}".format(app_name))
            return 0



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
            allow_create, tips, total_memory = market_app_service.check_package_app_resource(self.tenant,
                                                                                             self.response_region, app)
            if not allow_create:
                return Response(general_message(412, "over resource", "应用所需内存大小为{0}，{1}".format(total_memory, tips)),
                                status=412)
            market_app_service.install_service(self.tenant, self.response_region, self.user, group_id, app)
            logger.debug("market app create success")
            result = general_message(200, "success", "创建成功")
        except ResourceNotEnoughException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
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
                if not user_services.is_user_admin_in_current_enterprise(self.user, self.tenant.enterprise_id):
                    return Response(general_message(403, "current user is not enterprise admin", "非企业管理员无法进行此操作"),
                                    status=403)
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
            if app.enterprise_id == "public":
                if not self.user.is_sys_admin:
                    return Response(general_message(403, "only system admin can manage public app", "非平台管理员无权操作"),
                                    status=403)

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


# class DownloadMarketAppGroupView(RegionTenantHeaderView):
#     @never_cache
#     def get(self, request, *args, **kwargs):
#         """
#         同步下载云市组概要模板到云帮
#         ---
#         parameters:
#             - name: tenantName
#               description: 团队名称
#               required: true
#               type: string
#               paramType: path
#         """
#         try:
#             if not self.user.is_sys_admin:
#                 if not user_services.is_user_admin_in_current_enterprise(self.user, self.tenant.enterprise_id):
#                     return Response(general_message(403, "current user is not enterprise admin", "非企业管理员无法进行此操作"),
#                                     status=403)
#             enterprise = enterprise_services.get_enterprise_by_enterprise_id(self.tenant.enterprise_id)
#             if not enterprise.is_active:
#                 return Response(general_message(10407, "enterprise is not active", "您的企业未激活"), status=403)
#             logger.debug("start synchronized market apps")
#             market_sycn_service.down_market_group_list(self.user, self.tenant)
#             result = general_message(200, "success", "同步成功")
#         except Exception as e:
#             logger.exception(e)
#             result = error_message(e.message)
#         return Response(result, status=result["code"])


class DownloadMarketAppGroupTemplageDetailView(RegionTenantHeaderView):
    @never_cache
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
              description: 需要同步的应用[{"group_key":"xxxxxxx","version":"xxxxxx","template_version":"xxxx"}]
              required: true
              type: string
              paramType: body
        """
        try:
            ent = enterprise_repo.get_enterprise_by_enterprise_id(self.tenant.enterprise_id)
            if ent and not ent.is_active:
                result = general_message(10407, "failed", "用户未跟云市认证")
                return Response(result, 500)

            if not self.user.is_sys_admin:
                if not user_services.is_user_admin_in_current_enterprise(self.user, self.tenant.enterprise_id):
                    return Response(general_message(403, "current user is not enterprise admin", "非企业管理员无法进行此操作"),
                                    status=403)
            logger.debug("start synchronized market apps detail")
            enterprise = enterprise_services.get_enterprise_by_enterprise_id(self.tenant.enterprise_id)
            if not enterprise.is_active:
                return Response(general_message(10407, "enterprise is not active", "您的企业未激活"), status=403)
            group_data = request.data

            data = group_data[0]
            market_sycn_service.down_market_group_app_detail(self.user, self.tenant, data["group_key"], data["version"], data.get("template_version", "v2"))
            result = general_message(200, "success", "应用同步成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class CenterAllMarketAppView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        查询远端云市的应用
        ---
        parameters:
            - name: app_name
              description: 搜索的服务名
              required: false
              type: string
              paramType: query
            - name: is_complete
              description: 是否已下载
              required: false
              type: boolean
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
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)
        app_name = request.GET.get("app_name", None)
        try:
            ent = enterprise_repo.get_enterprise_by_enterprise_id(self.tenant.enterprise_id)
            if ent and not ent.is_active:
                result = general_message(10407, "failed", "用户未跟云市认证")
                return Response(result, 500)

            total, apps = market_app_service.get_remote_market_apps(self.tenant, int(page), int(page_size), app_name)

            result = general_message(200, "success", "查询成功", list=apps, total=total,
                                     next_page=int(page) + 1)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

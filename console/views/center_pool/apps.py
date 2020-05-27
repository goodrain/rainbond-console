# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
import logging
import httplib2
import httplib
import json
import datetime

from django.db import transaction
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from rest_framework import status

from console.exception.main import AccountOverdueException
from console.exception.main import ResourceNotEnoughException
from console.exception.main import ServiceHandleException
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.app import app_tag_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.services.enterprise_services import enterprise_services
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.market_app_service import market_sycn_service
from console.services.user_services import user_services
from console.utils.response import MessageResponse
from console.views.base import RegionTenantHeaderView
from console.views.base import JWTAuthApiView
from www.apiclient.baseclient import HttpClient
from www.utils.return_message import error_message
from www.utils.return_message import general_message

logger = logging.getLogger('default')


class CenterAppListView(JWTAuthApiView):
    @never_cache
    def get(self, request, enterprise_id, *args, **kwargs):
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
        tags = request.GET.get("tags", [])
        if tags:
            tags = json.loads(tags)
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        app_list = []
        apps = rainbond_app_repo.get_rainbond_apps_versions_by_eid(enterprise_id, app_name, tags, scope, page, page_size)
        if apps and apps[0].app_name:
            for app in apps:
                versions_info = (json.loads(app.versions_info) if app.versions_info else [])
                app_list.append({
                    "update_time": app.update_time,
                    "is_ingerit": app.is_ingerit,
                    "app_id": app.app_id,
                    "app_name": app.app_name,
                    "pic": app.pic,
                    "describe": app.describe,
                    "create_time": app.create_time,
                    "scope": app.scope,
                    "versions_info": versions_info,
                    "dev_status": app.dev_status,
                    "tags": (json.loads(app.tags) if app.tags else []),
                    "enterprise_id": app.enterprise_id,
                    "is_official": app.is_official,
                    "ID": app.ID,
                    "source": app.source,
                    "details": app.details,
                    "install_number": app.install_number,
                    "create_user": app.create_user,
                    "create_team": app.create_team,
                })

        return MessageResponse("success", msg_show="查询成功", list=app_list, total=len(app_list), next_page=int(page) + 1)


class CenterAppView(RegionTenantHeaderView):
    @never_cache
    @transaction.atomic
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
            - name: install_from_cloud
              description: install app from cloud
              required: false
              type: bool
              paramType: form
        """
        try:
            group_id = request.data.get("group_id", -1)
            app_id = request.data.get("app_id", None)
            app_version = request.data.get("app_version", None)
            is_deploy = request.data.get("is_deploy", True)
            install_from_cloud = request.data.get("install_from_cloud", False)
            if not app_id or not app_version:
                return Response(general_message(400, "app id is null", "请指明需要安装的应用"), status=400)
            if int(group_id) != -1:
                group_service.get_group_by_id(self.tenant, self.response_region, group_id)
            app = None
            app_version_info = None
            if install_from_cloud:
                app, app_version_info = market_app_service.get_app_from_cloud(self.tenant, app_id, app_version, True)
                if not app:
                    return Response(general_message(404, "not found", "云端应用不存在"), status=404)
            else:
                app, app_version_info = market_app_service.get_rainbond_app_and_version(self.user.enterprise_id, app_id,
                                                                                        app_version)
                if not app:
                    return Response(general_message(404, "not found", "云市应用不存在"), status=404)

            market_app_service.install_service(self.tenant, self.response_region, self.user, group_id, app, app_version_info,
                                               is_deploy, install_from_cloud)
            if not install_from_cloud:
                market_app_service.update_rainbond_app_install_num(self.user.enterprise_id, app_id, app_version)
            logger.debug("market app create success")
            result = general_message(200, "success", "创建成功")
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
        except ServiceHandleException as e:
            raise e
        return Response(result, status=result["code"])


class CenterAppCLView(JWTAuthApiView):
    @never_cache
    def get(self, request, enterprise_id, *args, **kwargs):
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
        is_complete = request.GET.get("is_complete", None)
        tags = request.GET.get("tags", [])
        if tags:
            tags = json.loads(tags)
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        apps, count = market_app_service.get_visiable_apps(self.user, enterprise_id, scope, app_name, tags, is_complete, page,
                                                           page_size)
        return MessageResponse("success", msg_show="查询成功", list=apps, total=count, next_page=int(page) + 1)

    @never_cache
    def post(self, request, enterprise_id, *args, **kwargs):
        name = request.data.get("name")
        describe = request.data.get("describe", 'This is a default description.')
        pic = request.data.get("pic")
        details = request.data.get("details")
        dev_status = request.data.get("dev_status")
        tag_ids = request.data.get("tag_ids")
        scope = request.data.get("scope", "enterprise")
        scope_target = request.data.get("scope_target")
        source = request.data.get("source", "local")
        create_team = request.data.get("create_team", request.data.get("team_name", None))
        if scope == "team" and not create_team:
            result = general_message(400, "please select team", "请选择团队")
            return Response(result, status=400)
        if scope == "goodrain" and (not scope_target or not scope_target.get("market_id")):
            result = general_message(400, "parameter market_id not found", None)
            return Response(result, status=400)
        if not name:
            result = general_message(400, "error params", "请填写应用名称")
            return Response(result, status=400)

        app_info = {
            "app_name": name,
            "describe": describe,
            "pic": pic,
            "details": details,
            "dev_status": dev_status,
            "tag_ids": tag_ids,
            "scope": scope,
            "scope_target": scope_target,
            "source": source,
            "create_team": create_team,
        }
        market_app_service.create_rainbond_app(enterprise_id, app_info)

        result = general_message(200, "success", None)
        return Response(result, status=200)


class CenterAppUDView(JWTAuthApiView):
    """
        编辑和删除应用市场应用
        ---
    """

    def put(self, request, enterprise_id, app_id, *args, **kwargs):
        name = request.data.get("name")
        describe = request.data.get("describe", 'This is a default description.')
        pic = request.data.get("pic")
        details = request.data.get("details")
        dev_status = request.data.get("dev_status")
        tag_ids = request.data.get("tag_ids")
        scope = request.data.get("scope", "enterprise")
        create_team = request.data.get("create_team", None)
        if scope == "team" and not create_team:
            result = general_message(400, "please select team", "请选择团队")
            return Response(result, status=400)

        app_info = {
            "name": name,
            "describe": describe,
            "pic": pic,
            "details": details,
            "dev_status": dev_status,
            "tag_ids": tag_ids,
            "scope": scope,
            "create_team": create_team,
        }
        market_app_service.update_rainbond_app(enterprise_id, app_id, app_info)
        result = general_message(200, "success", None)
        return Response(result, status=200)

    def delete(self, request, enterprise_id, app_id, *args, **kwargs):
        market_app_service.delete_rainbond_app_all_info_by_id(enterprise_id, app_id)
        result = general_message(200, "success", None)
        return Response(result, status=200)


class CenterAppManageView(JWTAuthApiView):
    @never_cache
    def post(self, request, enterprise_id, *args, **kwargs):
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
                    return Response(general_message(403, "current user is not enterprise admin", "非企业管理员无法进行此操作"), status=403)
            app_id = request.data.get("app_id", None)
            app_version_list = request.data.get("app_versions", [])
            action = request.data.get("action", None)
            if not app_id:
                return Response(general_message(400, "group_key is null", "请指明需要安装应用的app_id"), status=400)
            if not app_version_list:
                return Response(general_message(400, "group_version_list is null", "请指明需要安装应用的版本"), status=400)
            if not action:
                return Response(general_message(400, "action is not specified", "操作类型未指定"), status=400)
            if action not in ("online", "offline"):
                return Response(general_message(400, "action is not allow", "不允许的操作类型"), status=400)
            for app_version in app_version_list:
                app, version = market_app_service.get_rainbond_app_and_version(self.user.enterprise_id, app_id, app_version)
                if not version:
                    return Response(general_message(404, "not found", "云市应用不存在"), status=404)

                if action == "online":
                    version.is_complete = True
                else:
                    version.is_complete = False
                app.update_time = datetime.datetime.now()
                app.save()
                version.update_time = datetime.datetime.now()
                version.save()
            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class DownloadMarketAppTemplateView(JWTAuthApiView):
    @never_cache
    def post(self, request, enterprise_id, *args, **kwargs):
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
            app_id = request.data.get("app_id", None)
            app_versions = request.data.get("app_versions", [])
            template_version = request.data.get("template_version", "v2")
            if not app_versions or not app_id:
                return Response(general_message(400, "app is null", "请指明需要更新的应用"), status=400)
            ent = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id)
            if ent and not ent.is_active:
                result = general_message(10407, "failed", "用户未跟云市认证")
                return Response(result, 500)

            if not self.user.is_sys_admin:
                if not user_services.is_user_admin_in_current_enterprise(self.user, enterprise_id):
                    return Response(general_message(403, "current user is not enterprise admin", "非企业管理员无法进行此操作"), status=403)
            logger.debug("start synchronized market apps detail")
            enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
            if not enterprise.is_active:
                return Response(general_message(10407, "enterprise is not active", "您的企业未激活"), status=403)

            for version in app_versions:
                market_sycn_service.down_market_group_app_detail(self.user, enterprise_id, app_id, version, template_version)
            result = general_message(200, "success", "应用同步成功")
        except HttpClient.CallApiError as e:
            logger.exception(e)
            if e.status == 403:
                return Response(general_message(10407, "no cloud permission", u"云端授权未通过"), status=403)
            else:
                return Response(general_message(500, "call cloud api failure", u"云端获取应用列表失败"), status=500)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class CenterAllMarketAppView(JWTAuthApiView):
    @never_cache
    def get(self, request, enterprise_id, *args, **kwargs):
        """
        查询远端云市的应用
        ---
        parameters:
            - name: app_name
              description: 搜索的组件名
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
        open_query = request.GET.get("open_query", False)
        try:
            if not open_query:
                ent = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id)
                if ent and not ent.is_active:
                    result = general_message(10407, "failed", "用户未跟云市认证")
                    return Response(result, 500)
            total, apps = market_app_service.get_remote_market_apps(enterprise_id, int(page), int(page_size), app_name)

            result = general_message(200, "success", "查询成功", list=apps, total=total, next_page=int(page) + 1)
        except (httplib2.ServerNotFoundError, httplib.ResponseNotReady) as e:
            logger.exception(e)
            return Response(general_message(10503, "call cloud api failure", u"网络不稳定，无法获取云端应用"), status=210)
        except HttpClient.CallApiError as e:
            logger.exception(e)
            if e.status == 403:
                return Response(general_message(10407, "no cloud permission", u"云端授权未通过"), status=403)
            else:
                return Response(general_message(10503, "call cloud api failure", u"网络不稳定，无法获取云端应用"), status=210)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class CenterVersionlMarversionketAppView(JWTAuthApiView):
    @never_cache
    def get(self, request, enterprise_id, *args, **kwargs):
        """
        查询远端云市指定版本的应用

        """
        version = request.GET.get("version", None)
        app_name = request.GET.get("app_name", None)
        app_id = request.GET.get("app_id", None)
        if not app_id or not app_name or not version:
            result = general_message(400, "not config", "参数缺失")
            return Response(result, status=400)
        try:
            ent = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id)
            if ent and not ent.is_active:
                result = general_message(10407, "failed", "用户未跟云市认证")
                return Response(result, 500)

            total, apps = market_app_service.get_market_version_apps(enterprise_id, app_name, app_id, version)

            result = general_message(200, "success", "查询成功", list=apps)
        except HttpClient.CallApiError as e:
            logger.exception(e)
            if e.status == 403:
                return Response(general_message(10407, "no cloud permission", u"云端授权未通过"), status=403)
            else:
                return Response(general_message(500, "call cloud api failure", u"云端获取应用列表失败"), status=500)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class GetCloudRecommendedAppList(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        """
        获取云端市场推荐应用列表
        ---
        parameters:
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
        app_name = request.GET.get("app_name", None)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)
        try:
            apps, total, page = market_sycn_service.get_recommended_app_list(enterprise_id, page, page_size, app_name)
            if apps:
                return MessageResponse("success", msg_show="查询成功", list=apps, total=total, next_page=int(page) + 1)
            else:
                return Response(general_message(200, "no apps", u"查询成功"), status=200)
        except Exception as e:
            logger.exception(e)
            return Response(general_message(10503, "call cloud api failure", u"网络不稳定，无法获取云端应用"), status=210)


class TagCLView(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        data = []
        app_tag_list = app_tag_repo.get_all_tag_list(enterprise_id)
        if app_tag_list:
            for app_tag in app_tag_list:
                data.append({"name": app_tag.name, "tag_id": app_tag.ID})
        result = general_message(200, "success", None, list=data)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request, enterprise_id, *args, **kwargs):
        name = request.data.get("name", None)
        result = general_message(200, "success", u"创建成功")
        if not name:
            result = general_message(400, "fail", u"参数不正确")
        try:
            rst = app_tag_repo.create_tag(enterprise_id, name)
            if not rst:
                result = general_message(400, "fail", u"标签已存在")
        except Exception as e:
            logger.debug(e)
            result = general_message(400, "fail", u"创建失败")
        return Response(result, status=result.get("code", 200))


class TagUDView(JWTAuthApiView):
    def put(self, request, enterprise_id, tag_id, *args, **kwargs):
        name = request.data.get("name", None)
        result = general_message(200, "success", u"更新成功")
        if not name:
            result = general_message(400, "fail", u"参数不正确")
        rst = app_tag_repo.update_tag_name(enterprise_id, tag_id, name)
        if not rst:
            result = general_message(400, "fail", u"更新失败")
        return Response(result, status=result.get("code", 200))

    def delete(self, request, enterprise_id, tag_id, *args, **kwargs):
        result = general_message(200, "success", u"删除成功")
        rst = app_tag_repo.delete_tag(enterprise_id, tag_id)
        if not rst:
            result = general_message(400, "fail", u"删除失败")
        return Response(result, status=result.get("code", 200))


class AppTagCDView(JWTAuthApiView):
    def post(self, request, enterprise_id, app_id):
        tag_id = request.data.get("tag_id", None)
        result = general_message(200, "success", u"创建成功")
        if not tag_id:
            result = general_message(400, "fail", u"请求参数错误")
        app = rainbond_app_repo.get_rainbond_app_by_app_id(enterprise_id, app_id)
        if not app:
            result = general_message(404, "fail", u"该应用不存在")
        try:
            app_tag_repo.create_app_tag_relation(app, tag_id)
        except Exception as e:
            logger.debug(e)
            result = general_message(404, "fail", u"创建失败")
        return Response(result, status=result.get("code", 200))

    def delete(self, request, enterprise_id, app_id):
        tag_id = request.data.get("tag_id", None)
        result = general_message(200, "success", u"删除成功")
        if not tag_id:
            result = general_message(400, "fail", u"请求参数错误")
        app = rainbond_app_repo.get_rainbond_app_by_app_id(enterprise_id, app_id)
        if not app:
            result = general_message(404, "fail", u"该应用不存在")
        try:
            app_tag_repo.delete_app_tag_relation(app, tag_id)
        except Exception as e:
            logger.debug(e)
            result = general_message(404, "fail", u"删除失败")
        return Response(result, status=result.get("code", 200))

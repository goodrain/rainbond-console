# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
import datetime
import json
import logging
import re

from console.repositories.app import app_tag_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.services.config_service import EnterpriseConfigService
from console.services.market_app_service import market_app_service
from console.services.region_services import region_services
from console.services.user_services import user_services
from console.utils.response import MessageResponse
from console.views.base import JWTAuthApiView, RegionTenantHeaderView
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.response import Response
from www.utils.return_message import error_message, general_message
from console.utils.validation import validate_name
from www.utils.crypt import make_uuid

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
        app_id = request.data.get("group_id", -1)
        app_model_key = request.data.get("app_id", None)
        version = request.data.get("app_version", None)
        is_deploy = request.data.get("is_deploy", True)
        install_from_cloud = request.data.get("install_from_cloud", False)
        dry_run = request.data.get("dry_run", False)
        market_name = request.data.get("market_name", None)

        market_app_service.install_app(self.tenant, self.region, self.user, app_id, app_model_key, version, market_name,
                                       install_from_cloud, is_deploy, dry_run)
        return Response(general_message(200, "success", "创建成功"), status=200)


class CmdInstallAppView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        命令行创建应用
        """
        app_id = request.data.get("group_id", -1)
        cmd = request.data.get("cmd", "")
        app_id_pattern = r"--appID\s+(\S+)"
        version_pattern = r"--version\s+(\S+)"
        appID_match = re.search(app_id_pattern, cmd)
        version_match = re.search(version_pattern, cmd)
        if appID_match and version_match:
            app_model_key = appID_match.group(1) if appID_match else None
            version = version_match.group(1) if version_match else None
            market_app_service.install_app_by_cmd(self.tenant, self.region, self.user, app_id, app_model_key, version)
            return Response(general_message(200, "success", "创建成功"), status=200)
        else:
            return Response(general_message(400, "failed", "解析命令失败"), status=200)


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
        is_plugin = request.GET.get("is_plugin", False)
        scope = request.GET.get("scope", None)
        app_name = request.GET.get("app_name", None)
        tags = request.GET.get("tags", [])
        is_complete = request.GET.get("is_complete", None)
        need_install = request.GET.get("need_install", "false")
        arch = request.GET.get("arch", "")
        if tags:
            tags = json.loads(tags)
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        apps, count = market_app_service.get_visiable_apps(self.user, enterprise_id, scope, app_name, tags, is_complete, page,
                                                           page_size, need_install, is_plugin, arch)
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
        if scope not in ["team", "enterprise"]:
            result = general_message(400, "parameter error", "scope 参数不正确")
            return Response(result, status=400)
        if not name:
            result = general_message(400, "error params", "请填写应用名称")
            return Response(result, status=400)
        if not validate_name(name):
            result = general_message(400, "error params", "应用名称只支持中文、字母、数字和-_组合,并且必须以中文、字母、数字开始和结束")
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
        market_app_service.create_rainbond_app(enterprise_id, app_info, make_uuid())

        result = general_message(200, "success", None)
        return Response(result, status=200)


class CenterAppUDView(JWTAuthApiView):
    """
        编辑和删除应用市场应用
        ---
    """

    def put(self, request, enterprise_id, app_id, *args, **kwargs):
        name = request.data.get("name")
        if not validate_name(name):
            result = general_message(400, "error params", "应用名称只支持中文、字母、数字和-_组合,并且必须以中文、字母、数字开始和结束")
            return Response(result, status=400)
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

    def get(self, request, enterprise_id, app_id, *args, **kwargs):
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        app, versions, total = market_app_service.get_rainbond_app_and_versions(enterprise_id, app_id, page, page_size)
        return MessageResponse("success", msg_show="查询成功", list=versions, bean=app, total=total)


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
            if not self.user.is_sys_admin and not user_services.is_user_admin_in_current_enterprise(
                    self.user, self.tenant.enterprise_id):
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
        result = general_message(200, "success", "创建成功")
        if not name:
            result = general_message(400, "fail", "参数不正确")
        try:
            rst = app_tag_repo.create_tag(enterprise_id, name)
            if not rst:
                result = general_message(400, "fail", "标签已存在")
        except Exception as e:
            logger.debug(e)
            result = general_message(400, "fail", "创建失败")
        return Response(result, status=result.get("code", 200))


class TagUDView(JWTAuthApiView):
    def put(self, request, enterprise_id, tag_id, *args, **kwargs):
        name = request.data.get("name", None)
        result = general_message(200, "success", "更新成功")
        if not name:
            result = general_message(400, "fail", "参数不正确")
        rst = app_tag_repo.update_tag_name(enterprise_id, tag_id, name)
        if not rst:
            result = general_message(400, "fail", "更新失败")
        return Response(result, status=result.get("code", 200))

    def delete(self, request, enterprise_id, tag_id, *args, **kwargs):
        result = general_message(200, "success", "删除成功")
        rst = app_tag_repo.delete_tag(enterprise_id, tag_id)
        if not rst:
            result = general_message(400, "fail", "删除失败")
        return Response(result, status=result.get("code", 200))


class AppTagCDView(JWTAuthApiView):
    def post(self, request, enterprise_id, app_id, *args, **kwargs):
        tag_id = request.data.get("tag_id", None)
        result = general_message(200, "success", "创建成功")
        if not tag_id:
            result = general_message(400, "fail", "请求参数错误")
        app = rainbond_app_repo.get_rainbond_app_by_app_id(enterprise_id, app_id)
        if not app:
            result = general_message(404, "fail", "该应用不存在")
        try:
            app_tag_repo.create_app_tag_relation(app, tag_id)
        except Exception as e:
            logger.debug(e)
            result = general_message(404, "fail", "创建失败")
        return Response(result, status=result.get("code", 200))

    def delete(self, request, enterprise_id, app_id, *args, **kwargs):
        tag_id = request.data.get("tag_id", None)
        result = general_message(200, "success", "删除成功")
        if not tag_id:
            result = general_message(400, "fail", "请求参数错误")
        app = rainbond_app_repo.get_rainbond_app_by_app_id(enterprise_id, app_id)
        if not app:
            result = general_message(404, "fail", "该应用不存在")
        try:
            app_tag_repo.delete_app_tag_relation(app, tag_id)
        except Exception as e:
            logger.debug(e)
            result = general_message(404, "fail", "删除失败")
        return Response(result, status=result.get("code", 200))


class AppVersionUDView(JWTAuthApiView):
    def put(self, request, enterprise_id, app_id, version, *args, **kwargs):
        dev_status = request.data.get("dev_status", "")
        version_alias = request.data.get("version_alias", None)
        app_version_info = request.data.get("app_version_info", None)

        body = {
            "release_user_id": self.user.user_id,
            "dev_status": dev_status,
            "version_alias": version_alias,
            "app_version_info": app_version_info
        }
        version = market_app_service.update_rainbond_app_version_info(enterprise_id, app_id, version, **body)
        result = general_message(200, "success", "更新成功", bean=version.to_dict())
        return Response(result, status=result.get("code", 200))

    def delete(self, request, enterprise_id, app_id, version, *args, **kwargs):
        result = general_message(200, "success", "删除成功")
        market_app_service.delete_rainbond_app_version(enterprise_id, app_id, version)
        return Response(result, status=result.get("code", 200))


# Whether you need to be reminded to configure mirror repositories
class LocalComponentLibraryConfigCheck(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        regions = region_services.get_regions_by_enterprise_id(enterprise_id)
        remind = False
        if regions and len(regions) > 1:
            ent_cfg_svc = EnterpriseConfigService(enterprise_id)
            data = ent_cfg_svc.get_config_by_key("APPSTORE_IMAGE_HUB")
            if data and data.enable:
                image_config_dict = eval(data.value)
                hub_url = image_config_dict.get("hub_url", None)
                if not hub_url:
                    remind = True
            else:
                remind = True
        result = general_message(200, "success", "检测成功", bean={"remind": remind})
        return Response(result, status=result.get("code", 200))


class CenterPluginAppView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        创建应用市场插件型应用
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
        app_model_key = request.data.get("app_id", None)
        version = request.data.get("app_version", None)
        is_deploy = request.data.get("is_deploy", True)
        install_from_cloud = request.data.get("install_from_cloud", False)
        market_name = request.data.get("market_name", None)

        market_app_service.install_plugin_app(self.tenant, self.region, self.user, app_model_key, version, market_name,
                                              install_from_cloud, self.tenant.tenant_id, self.region_name, is_deploy)
        return Response(general_message(200, "success", "安装成功"), status=200)

    @never_cache
    def get(self, request, *args, **kwargs):
        app_model_key = request.GET.get("app_id", None)
        version = request.GET.get("app_version", None)
        install_from_cloud = request.GET.get("install_from_cloud", False)
        market_name = request.GET.get("market_name", None)

        status = market_app_service.get_plugin_install_status(self.tenant, self.region, self.user, app_model_key, version,
                                                              market_name, install_from_cloud)
        return Response(general_message(200, "success", "查询成功", bean={"version": version, "status": status}), status=200)

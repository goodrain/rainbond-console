# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
import datetime
import json
import logging

from console.exception.main import (AccountOverdueException, ResourceNotEnoughException, ServiceHandleException)
from console.repositories.app import app_tag_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.services.app import app_market_service
from console.services.config_service import EnterpriseConfigService
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.region_services import region_services
from console.services.user_services import user_services
from console.utils.response import MessageResponse
from console.views.base import JWTAuthApiView, RegionTenantHeaderView
from django.db import transaction
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.response import Response
from www.utils.return_message import error_message, general_message

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
            market_name = request.data.get("market_name", None)
            if not app_id or not app_version:
                return Response(general_message(400, "app id is null", "请指明需要安装的应用"), status=400)
            if int(group_id) != -1:
                group_service.get_group_by_id(self.tenant, self.response_region, group_id)
            app = None
            app_version_info = None
            if install_from_cloud:
                dt, market = app_market_service.get_app_market(self.tenant.enterprise_id, market_name, raise_exception=True)
                app, app_version_info = app_market_service.cloud_app_model_to_db_model(
                    market, app_id, app_version, for_install=True)
                if not app:
                    return Response(general_message(404, "not found", "云端应用不存在"), status=404)
            else:
                app, app_version_info = market_app_service.get_rainbond_app_and_version(self.user.enterprise_id, app_id,
                                                                                        app_version)
                if not app:
                    return Response(general_message(404, "not found", "云市应用不存在"), status=404)
                if app_version_info and app_version_info.region_name and app_version_info.region_name != self.region_name:
                    raise ServiceHandleException(
                        msg="app version can not install to this region",
                        msg_show="该应用版本属于{}集群，无法跨集群安装，若需要跨集群，请在企业设置中配置跨集群访问的镜像仓库后重新发布。".format(app_version_info.region_name))
            if not app_version_info:
                return Response(general_message(404, "not found", "应用版本不存在，不能进行安装"), status=404)
            market_app_service.install_service(
                self.tenant,
                self.response_region,
                self.user,
                group_id,
                app,
                app_version_info,
                is_deploy,
                install_from_cloud,
                market_name=market_name)
            if not install_from_cloud:
                market_app_service.update_rainbond_app_install_num(self.user.enterprise_id, app_id, app_version)
            logger.debug("market app create success")
            result = general_message(200, "success", "创建成功")
        except ServiceHandleException as e:
            raise e
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
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
        need_install = request.GET.get("need_install", "false")
        if tags:
            tags = json.loads(tags)
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        apps, count = market_app_service.get_visiable_apps(self.user, enterprise_id, scope, app_name, tags, is_complete, page,
                                                           page_size, need_install)
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

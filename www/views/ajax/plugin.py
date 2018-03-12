# -*- coding: utf8 -*-
import json
import logging
import threading

from django.conf import settings
from django.http import JsonResponse
from django.http import QueryDict

from goodrain_web.tools import JuncheePaginator
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.models import ConstKey
from www.services import plugin_svc
from www.utils.crypt import make_uuid
from www.utils.return_message import general_message, error_message
from www.views import AuthedView
from www.views.base import PluginView
import random

logger = logging.getLogger('default')

region_api = RegionInvokeApi()


class PluginBaseInfoView(PluginView, AuthedView):
    @perm_required('view_service')
    def get(self, request, plugin_id, *args, **kwargs):
        result = {}
        region = self.request.COOKIES.get('region')
        try:
            base_info = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, plugin_id)
            data = base_info.to_dict()
            pbvs = plugin_svc.get_tenant_plugin_versions(region, self.tenant,plugin_id)
            if len(pbvs) != 0:
                pbv = pbvs[0]
                data.update(pbv.to_dict())
            result = general_message(200, "success", "查询成功", bean=data)
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])


class PluginEventLogView(PluginView, AuthedView):
    """插件event log展示"""

    @perm_required('view_service')
    def get(self, request, plugin_id, build_version, *args, **kwargs):
        result = {}
        try:
            region = self.request.COOKIES.get('region')
            level = request.GET.get("level", "info")
            pbv = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, plugin_id,
                                                                                build_version)
            event_id = pbv.event_id
            data = plugin_svc.get_plugin_event_log(region, self.tenant, event_id, level)
            result = general_message(200, "success", "查询成功", list=data)
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])


class PluginVersionInfoView(PluginView, AuthedView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """插件版本信息展示"""
        result = {}
        try:

            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 8)
            region = self.request.COOKIES.get('region')
            if not region:
                return JsonResponse(general_message(404, "region not specify", "数据中心未指定"), status=404)
            pbvs = plugin_svc.get_tenant_plugin_versions(region, self.tenant, self.plugin_id)
            paginator = JuncheePaginator(pbvs, int(page_size))
            show_pbvs = paginator.page(int(page))
            update_status_thread = threading.Thread(target=plugin_svc.update_plugin_build_status,
                                                    args=(region, self.tenant))
            update_status_thread.start()
            data = [pbv.to_dict() for pbv in show_pbvs]
            result = general_message(200, "success", "查询成功", list=data, current_page=int(page), next_page=int(page) + 1)
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])


class UpdatePluginInfoView(PluginView, AuthedView):
    @perm_required('manage_service')
    def put(self, request, plugin_id, build_version, *args, **kwargs):
        """更新指定版本的插件信息"""
        result = {}
        try:
            data = json.loads(request.body)
            pbv = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, plugin_id, build_version)
            if not pbv:
                return JsonResponse(general_message(404, "plugin not found", "该版本插件不存在"), status=404)
            base_info = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, plugin_id)
            plugin_alias = data.get("plugin_alias", base_info.plugin_alias)
            update_info = data.get("update_info", pbv.update_info)
            build_cmd = data.get("build_cmd", pbv.build_cmd)
            image_tag = data.get("image_tag", pbv.image_tag)
            code_version = data.get("code_version", pbv.code_version)
            min_memory = data.get("min_memory", pbv.min_memory)
            region = self.request.COOKIES.get('region')
            min_cpu = plugin_svc.calculate_cpu(region, int(min_memory))
            update_params = {"min_memory": min_memory, "build_cmd": build_cmd, "update_info": update_info,
                             "min_cpu": min_cpu, "code_version": code_version, "image_tag": image_tag}
            # 更新数据
            new_pbv = plugin_svc.update_plugin_version_by_unique_key(self.tenant, plugin_id, build_version,
                                                                     **update_params)
            base_info.plugin_alias = plugin_alias
            base_info.save()
            bean = new_pbv.to_dict()
            result = general_message(200, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])


class ConfigPluginManageView(PluginView, AuthedView):
    """插件配置"""

    def get_ws_url(self, default_url, ws_type):
        if default_url != "auto":
            return "{0}/{1}".format(default_url, ws_type)
        host = self.request.META.get('HTTP_HOST').split(':')[0]
        return "ws://{0}:6060/{1}".format(host, ws_type)

    @perm_required('view_service')
    def get(self, request, plugin_id, build_version, *args, **kwargs):
        """获取某版本插件配置"""
        result = {}
        try:
            region = self.request.COOKIES.get('region')
            # 获取插件最新的配置信息
            base_info = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, plugin_id)
            if not base_info:
                return JsonResponse(general_message(404, "plugin not exist", "插件不存在"), status=404)

            data = plugin_svc.get_plugin_config(self.tenant, plugin_id, build_version)
            web_socket_url = self.get_ws_url(settings.EVENT_WEBSOCKET_URL[region], "event_log")
            data["web_socket_url"] = web_socket_url
            result = general_message(200, "success", "查询成功", bean=data)
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(data=result, status=result["code"])

    @perm_required('manage_service')
    def put(self, request, plugin_id, build_version, *args, **kwargs):
        """修改插件配置信息"""
        result = {}
        try:
            config = json.loads(request.body)

            injection = config.get("injection")
            service_meta_type = config.get("service_meta_type")
            config_name = config.get("config_name")
            config_group_pk = config.get("ID")
            config_groups = plugin_svc.get_config_group_by_unique_key(plugin_id, build_version).exclude(pk=config_group_pk)

            is_pass, msg = plugin_svc.check_group_config(service_meta_type, injection, config_groups)
            if not is_pass:
                return JsonResponse(general_message(400, "param error", msg),status=400)

            config_group = plugin_svc.get_config_group_by_pk(config_group_pk)
            old_meta_type = config_group.service_meta_type
            plugin_svc.update_config_group_by_pk(config_group_pk, config_name, service_meta_type, injection)
            # 删除原有配置项
            plugin_svc.delete_config_items_by_meta_type(plugin_id, build_version, old_meta_type)
            # 创建配置
            options = config.get("options")
            plugin_svc.create_config_items(plugin_id, build_version, service_meta_type, *options)

            result = general_message(200, "success", "操作成功")

        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])

    @perm_required('manage_service')
    def post(self, request, plugin_id, build_version, *args, **kwargs):
        result = {}
        try:
            config = json.loads(request.body)
            injection = config.get("injection")
            service_meta_type = config.get("service_meta_type")

            config_groups = plugin_svc.get_config_group_by_unique_key(plugin_id, build_version)

            is_pass, msg = plugin_svc.check_group_config(service_meta_type, injection, config_groups)
            if not is_pass:
                return JsonResponse(general_message(403, "param error", msg))
            create_data =[config]
            plugin_svc.create_config_group(plugin_id, build_version, create_data)
            result = general_message(200, "success", "添加成功")
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])

    @perm_required('manage_service')
    def delete(self, request, plugin_id, build_version, *args, **kwargs):
        result = {}
        try:
            params = QueryDict(request.body)
            config_group_pk = params.get("ID")
            config_group = plugin_svc.get_config_group_by_pk(config_group_pk)
            plugin_svc.delete_config_group_by_meta_type(plugin_id, build_version, config_group.service_meta_type)
            result = general_message(200, "success", "删除成功")
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])


class PluginManageView(PluginView, AuthedView):
    @perm_required('manage_service')
    def post(self, request, plugin_id, build_version, *args, **kwargs):
        """构建插件"""
        result = {}
        try:
            config = json.loads(request.body)
            update_info = config.get("update_info",None)
            pbv = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, self.plugin_id,
                                                                                build_version)
            if not pbv:
                return JsonResponse(general_message(404, "plugin not found", "插件不存在"), status=404)
            if pbv.plugin_version_status == "fixed":
                return JsonResponse(general_message(403, "current version is fixed", "该版本已固定，不能构建"), status=403)
            if pbv.build_status == "building":
                return JsonResponse(general_message(403, "too offen", "构建中，请稍后再试"), status=403)

            if update_info:
                pbv.update_info = update_info
                pbv.save()
            
            region = self.request.COOKIES.get('region')
            event_id = make_uuid()
            base_info = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, self.plugin_id)
            try:
                plugin_svc.build_plugin(region, self.tenant, event_id, self.plugin_id, build_version, base_info.origin)
                pbv.build_status = "building"
                logger.debug("plugin build status is {}".format(pbv.build_status))
                pbv.event_id = event_id
                pbv.save()
                bean = {"event_id": event_id}
                result = general_message(200, "success", "操作成功", bean=bean)
            except Exception as e:
                logger.exception(e)
                result = general_message(500, "region invoke error", "操作失败")
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])

    @perm_required('manage_service')
    def delete(self, request,plugin_id, build_version, *args, **kwargs):
        """删除插件某个版本"""
        result = {}
        try:
            region = self.request.COOKIES.get('region')
            pbvs = plugin_svc.get_tenant_plugin_versions(region,self.tenant,self.plugin_id)
            if len(pbvs) == 1:
                return JsonResponse(general_message(403, "at least one plugin version", "插件插件至少保留一个版本"), status=403)

            tspr = plugin_svc.get_service_plugin_relation_by_plugin_unique_key(self.plugin_id, build_version)
            if tspr:
                return JsonResponse(general_message(403, "plugin is being using", "插件已被使用，无法删除"), status=403)
            plugin_svc.delete_build_version_by_id_and_version(region, self.tenant, self.plugin_id, build_version)
            result = general_message(200, "success", "删除成功")
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])


class CreatePluginVersionView(PluginView, AuthedView):
    @perm_required('manage_service')
    def post(self, request, plugin_id, *args, **kwargs):
        """创建插件新版本"""
        result = {}
        try:
            region = self.request.COOKIES.get('region')
            pbv = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, plugin_id, None)
            base_info = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant,plugin_id)
            if base_info:
                if base_info.origin != "source_code":
                    return JsonResponse(general_message(403, "market plugin can not create new version", "云市插件不能创建版本"), status=403)
            if not pbv:
                return JsonResponse(general_message(403, "current version not exist", "插件不存在任何版本，无法创建"), status=403)
            if pbv.build_status != "build_success":
                return JsonResponse(general_message(403, "no useable plugin version", "您的插件构建未成功，无法创建新版本"), status=403)

            plugin_id, new_version = plugin_svc.copy_config_to_new_version(self.tenant, self.plugin_id,
                                                                           pbv.build_version)

            pbv.plugin_version_status = "fixed"
            pbv.save()
            bean = {"plugin_id": plugin_id, "new_version": new_version}
            result = general_message(200, "success", "操作成功", bean=bean)

        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])


class PluginStatusView(PluginView, AuthedView):
    @perm_required('view_service')
    def get(self, request, plugin_id, build_version, *args, **kwargs):
        """插件构建状态获取"""
        result = {}
        try:
            self.cookie_region = self.request.COOKIES.get('region')
            pbv = plugin_svc.get_plugin_build_status(self.cookie_region, self.tenant, plugin_id, build_version)
            result = general_message(200, "success", "查询成功", {"status": pbv.build_status,"event_id":pbv.event_id})
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])


class TenantPluginStatusView(AuthedView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """批量插件状态获取"""
        logger.debug(request.body)
        result = {}
        try:
            self.cookie_region = self.request.COOKIES.get('region')
            plugins = plugin_svc.get_tenant_plugins(self.cookie_region, self.tenant)
            status_list = []
            for p in plugins:
                pbv = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, p.plugin_id)
                if pbv.build_status in ("building", "time_out"):
                    status = plugin_svc.get_region_plugin_build_status(self.cookie_region, self.tenant.tenant_name,
                                                                       pbv.plugin_id, pbv.build_version)
                    pbv.build_status = status
                    pbv.save()
                status_list.append(
                    {"plugin_id": pbv.plugin_id, "build_version": pbv.build_version, "build_status": pbv.build_status})

            result = general_message(200, "success", "查询成功", list=status_list)
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])


class ConfigPreviewView(PluginView, AuthedView):
    """配置预览"""

    @perm_required('view_service')
    def get(self, request, plugin_id, build_version, *args, **kwargs):
        # wordpress 依赖 mysql
        try:
            wordpress_alias = "wordpress_alias"
            mysql_alias = "mysql_alias"
            wp_ports = [80,8081]
            mysql_port = [3306]
            wp_id = "wp_service_id"
            mysql_id = "mysql_service_id"

            config_groups = plugin_svc.get_service_meta_type(plugin_id, build_version)
            all_config_group = []
            base_ports = []
            base_services = []
            base_normal = {}
            for config_group in config_groups:
                # get options
                config_items = plugin_svc.get_env_attr_by_service_meta_type(plugin_id, build_version,
                                                                            config_group.service_meta_type)
                items = []
                for item in config_items:
                    item_map = {}
                    item_map[item.attr_name] = item.attr_default_value
                    items.append(item_map)

                if config_group.service_meta_type == ConstKey.UPSTREAM_PORT:
                    for port in wp_ports:
                        base_port = {}
                        base_port["service_alias"] = wordpress_alias
                        base_port["service_id"] = wp_id
                        base_port["port"] = port
                        base_port["protocol"] = "http"
                        base_port["options"] = items
                        base_ports.append(base_port)
                if config_group.service_meta_type == ConstKey.DOWNSTREAM_PORT:
                    for port in mysql_port:
                        base_service = {}
                        base_service["service_alias"] = wordpress_alias
                        base_service["service_id"] = wp_id
                        base_service["port"] = port
                        #base_service["protocol"] = "stream"
                        base_service["protocol"] = "mysql"
                        base_service["options"] = items
                        base_service["depend_service_alias"] = mysql_alias
                        base_service["depend_service_id"] = mysql_id
                        base_services.append(base_service)
                if config_group.service_meta_type == ConstKey.UNDEFINE:
                    base_normal["options"] = items

            bean = {"base_ports": base_ports, "base_services": base_services,
                    "base_normal": base_normal.get("options", None)}

            result = general_message(200, "success", "操作成功", bean=bean, list=all_config_group)
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])

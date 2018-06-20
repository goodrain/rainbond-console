# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
from console.views.base import RegionTenantHeaderView
from django.views.decorators.cache import never_cache
from www.decorator import perm_required
from www.utils.crypt import make_uuid
from www.utils.return_message import general_message, error_message
import logging
from rest_framework.response import Response
from console.constants import PluginCategoryConstants
from console.services.plugin import plugin_service
from console.services.plugin import plugin_version_service
from console.services.region_services import region_services
from console.repositories.plugin import config_group_repo, config_item_repo

logger = logging.getLogger("default")


class PluginCreateView(RegionTenantHeaderView):
    @never_cache
    @perm_required('create_plugin')
    def post(self, request, *args, **kwargs):
        """
        插件创建
        ---
        parameters:
            - name: tenantName
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: plugin_alias
              description: 插件名称
              required: true
              type: string
              paramType: form
            - name: build_source
              description: 构建来源 dockerfile | image
              required: true
              type: string
              paramType: form
            - name: min_memory
              description: 最小内存
              required: true
              type: integer
              paramType: form
            - name: category
              description: 插件类别 net-plugin:down|net-plugin:up|analyst-plugin:perf|init-plugin|general-plugin
              required: false
              type: string
              paramType: form
            - name: build_cmd
              description: 构建命令
              required: false
              type: string
              paramType: form
            - name: code_repo
              description: dockerfile构建代码仓库地址,选择dockerfile时必须
              required: false
              type: string
              paramType: form
            - name: code_version
              description: 代码版本，默认master
              required: false
              type: string
              paramType: form
            - name: image
              description: 镜像构建时镜像名称
              required: false
              type: string
              paramType: form
            - name: desc
              description: 镜像说明
              required: true
              type: string
              paramType: form

        """
        # 必要参数
        plugin_alias = request.data.get("plugin_alias", None)
        build_source = request.data.get("build_source", None)
        min_memory = request.data.get("min_memory", None)
        category = request.data.get("category", None)
        desc = request.data.get("desc", None)
        # 非必要参数
        build_cmd = request.data.get("build_cmd", None)
        code_repo = request.data.get("code_repo", None)
        code_version = request.data.get("code_version", None)
        image = request.data.get("image", None)
        tenant_plugin = None
        plugin_build_version = None
        try:
            if not plugin_alias:
                return Response(general_message(400, "plugin alias is null", "插件名称未指明"), status=400)
            if not build_source:
                return Response(general_message(400, "build source is null", "构建来源未指明"), status=400)
            if not min_memory:
                return Response(general_message(400, "plugin min_memroy is null", "插件内存大小未指明"), status=400)
            if not category:
                return Response(general_message(400, "plugin category is null", "插件类别未指明"), status=400)
            else:
                if category not in (
                        PluginCategoryConstants.OUTPUT_NET, PluginCategoryConstants.INPUT_NET,
                        PluginCategoryConstants.PERFORMANCE_ANALYSIS, PluginCategoryConstants.INIT_TYPE,
                        PluginCategoryConstants.COMMON_TYPE):
                    return Response(general_message(400, "plugin category is wrong", "插件类别参数错误，详情请参数API说明"), status=400)
            if not desc:
                return Response(general_message(400, "plugin desc is null", "请填写插件描述"), status=400)

            image_tag = ""
            if image and build_source == "image":
                image_and_tag = image.split(":")
                if len(image_and_tag) > 1:
                    image = image_and_tag[0]
                    image_tag = image_and_tag[1]
                else:
                    image = image_and_tag[0]
                    image_tag = "latest"
            # 创建基本信息
            code, msg, tenant_plugin = plugin_service.create_tenant_plugin(self.tenant, self.user.user_id,
                                                                           self.response_region, desc, plugin_alias,
                                                                           category, build_source, image, code_repo)
            if code != 200:
                return Response(general_message(code, "create plugin error", msg), status=code)

            # 创建插件版本信息
            plugin_build_version = plugin_version_service.create_build_version(self.response_region,
                                                                               tenant_plugin.plugin_id,
                                                                               self.tenant.tenant_id, self.user.user_id,
                                                                               "", "unbuild", min_memory, build_cmd,
                                                                               image_tag, code_version)
            #数据中心创建插件
            code, msg = plugin_service.create_region_plugin(self.response_region, self.tenant, tenant_plugin)
            if code != 200:
                plugin_service.delete_tenant_plugin(tenant_plugin.plugin_id)
                plugin_version_service.delete_build_version_by_id_and_version(tenant_plugin.plugin_id,
                                                                              plugin_build_version.build_version, True)
                return Response(general_message(code, "create plugin error", msg), status=code)

            bean = tenant_plugin.to_dict()
            bean["build_version"] = plugin_build_version.build_version
            bean["code_version"] = plugin_build_version.code_version
            bean["build_status"] = plugin_build_version.build_status
            bean["update_info"] = plugin_build_version.update_info
            bean["image_tag"] = plugin_build_version.image_tag

            result = general_message(200, "success", "创建成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            if tenant_plugin:
                plugin_service.delete_tenant_plugin(tenant_plugin.plugin_id)
            if plugin_build_version:
                plugin_version_service.delete_build_version_by_id_and_version(tenant_plugin.plugin_id,
                                                                              plugin_build_version.build_version, True)
        return Response(result, status=result["code"])


class DefaultPluginCreateView(RegionTenantHeaderView):

    def add_default_plugin(self, user, tenant, regions):
        for region in regions:
            desc = "实时分析(HTTP,Mysql协议)应用的吞吐率、响应时间、在线人数等指标"
            plugin_alias = "服务实时性能分析"
            category = "analyst-plugin:perf"
            image_url = "goodrain.me/tcm"
            code, msg, plugin_base_info = plugin_service.create_tenant_plugin(tenant, user.user_id, region, desc,
                                                                                plugin_alias,
                                                                                category, "image",
                                                                                image_url, "")
            plugin_base_info.origin = "local_market"
            plugin_base_info.origin_share_id = "perf_analyze_plugin"
            plugin_base_info.save()

            plugin_build_version = plugin_version_service.create_build_version(region, plugin_base_info.plugin_id,
                                                                                tenant.tenant_id,
                                                                                user.user_id, "", "unbuild", 64)
            config_params = {
                "plugin_id": plugin_build_version.plugin_id,
                "build_version": plugin_build_version.build_version,
                "config_name": "端口是否开启分析",
                "service_meta_type": "upstream_port",
                "injection": "auto"
            }
            config_group_repo.create_plugin_config_group(**config_params)
            item_params = {
                "plugin_id": plugin_build_version.plugin_id,
                "build_version": plugin_build_version.build_version,
                "service_meta_type": "upstream_port",
                "attr_name": "OPEN",
                "attr_type": "radio",
                "attr_alt_value": "YES,NO",
                "attr_default_value": "YES",
                "is_change": True,
                "attr_info": "是否开启当前端口分析，用户自助选择服务端口",
            }
            config_item_repo.create_plugin_config_items(**item_params)

            event_id = make_uuid()
            plugin_build_version.event_id = event_id
            plugin_build_version.plugin_version_status = "fixed"

            plugin_service.create_region_plugin(region, tenant, plugin_base_info)

            plugin_service.build_plugin(region, plugin_base_info, plugin_build_version, user, tenant,
                                        event_id)
            plugin_build_version.build_status = "build_success"
            plugin_build_version.save()


    def post(self, request, *args, **kwargs):
        """
        插件创建
        ---
        parameters:
            - name: tenantName
              description: 团队名
              required: true
              type: string
              paramType: path
        """ 
        try:  
            regions = region_services.get_region_by_tenant_name(self.team_name)
            if regions:
                region_names = [region.region_name for region in regions]
                self.add_default_plugin(self.user, self.team, region_names)
            result = general_message(200, "success", "创建成功")    
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)



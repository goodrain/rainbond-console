# -*- coding: utf8 -*-
"""
  Created on 18/1/18.
"""
from django.http import JsonResponse

from www.decorator import perm_required
from www.utils.crypt import make_uuid
from www.utils.return_message import error_message, general_message
from www.views import AuthedView
import logging
import json
from www.services import plugin_svc, plugin_share_svc

logger = logging.getLogger("default")


class TenantPluginInstallView(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        """安装插件"""
        result = {}
        region = self.request.COOKIES.get('region')
        try:
            data = json.loads(request.body)
            share_id = data.get("share_id", None)
            share_version = data.get("share_version", None)

            plugin_origin_key = ["82ce36bfd4044931adaa484ed8e75c12", "e003ce85b65d477896ee99798c3d8a54"]
            for p in plugin_origin_key:
                p_info = plugin_svc.get_tenant_plugin_by_origin_key(region, self.tenant, p)
                if len(p_info) != 0:
                    return JsonResponse(general_message(403, "already installed", "您已安装,请跳转至插件页面查看"), status=404)
            

            if not share_id or not share_version:
                return JsonResponse(general_message(400, "params error", "参数异常"), status=400)
            share_info = plugin_share_svc.get_share_info_by_unique_key(share_id, share_version)
            if not share_info:
                logger.debug("share id {0} share version {1} not found !".format(share_id, share_version))
                return JsonResponse(general_message(404, "share info not found", "数据不存在"), status=404)
            # 创建基础信息
            plugin_base_info = plugin_svc.create_plugin(self.tenant, self.user.user_id, region, share_info.desc,
                                                        share_info.plugin_alias, share_info.category, "image",
                                                        share_info.image, "")
            plugin_base_info.origin_share_id = share_info.share_id
            plugin_base_info.origin = "local_market"
            plugin_base_info.save()
            pbv = plugin_svc.create_plugin_build_version(region, plugin_base_info.plugin_id, self.tenant.tenant_id,
                                                         self.user.user_id, share_info.update_info,
                                                         share_info.share_version,
                                                         "build_success", share_info.min_memory, share_info.min_cpu,
                                                         share_info.build_cmd, "lastest", "")
            config_template = json.loads(share_info.config)
            plugin_svc.create_config_group(plugin_base_info.plugin_id, pbv.build_version, config_template)

            # 数据中心创建插件
            event_id = make_uuid()
            pbv.event_id = event_id
            pbv.plugin_version_status = "fixed"
            pbv.save()
            plugin_svc.create_region_plugin(region, self.tenant, plugin_base_info.plugin_id)
            plugin_svc.build_plugin(region, self.tenant, event_id, plugin_base_info.plugin_id, pbv.build_version,plugin_base_info.origin)

            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)

            result = error_message()
        return JsonResponse(result, status=result["code"])


class TenantPluginShareView(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        """
        分享插件
        TODO 此功能暂时不全
        """
        result = {}

        try:
            data = json.loads(request.body)
            plugin_id = data.get("plugin_id", None)
            plugin_version = data.get("build_version", None)
            share_verion = data.get("share_verion", plugin_version)
            region = self.request.COOKIES.get('region')
            if not plugin_id:
                return JsonResponse(general_message(400, "params error", "参数异常"), status=400)
            base_info = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, plugin_id)
            pbv = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, plugin_id, plugin_version)
            image = ""
            config = plugin_svc.get_plugin_config(self.tenant, plugin_id, plugin_version)
            config_group = json.dumps(config["config_group"])
            plugin_share_svc.create_share_info(self.tenant, self.user.user_id, base_info, pbv, share_verion, image,
                                               config_group)

            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result, status=result["code"])

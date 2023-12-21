# -*- coding: utf8 -*-
"""
  Created on 18/3/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.response import Response

from console.exception.main import AbortRequest
from console.services.config_service import EnterpriseConfigService
from console.services.enterprise_services import enterprise_services
from www.utils.return_message import general_message
from console.utils.reqparse import bool_argument
from console.utils.reqparse import parse_item
from console.views.base import EnterpriseAdminView, JWTAuthApiView

logger = logging.getLogger("default")


class EnterpriseObjectStorageView(EnterpriseAdminView):
    @never_cache
    def put(self, request, enterprise_id, *args, **kwargs):
        enable = bool_argument(parse_item(request, "enable", required=True))
        provider = parse_item(request, "provider", required=True)
        endpoint = parse_item(request, "endpoint", required=True)
        bucket_name = parse_item(request, "bucket_name", required=True)
        access_key = parse_item(request, "access_key", required=True)
        secret_key = parse_item(request, "secret_key", required=True)

        if provider not in ("alioss", "s3"):
            raise AbortRequest("provider {} not in (\"alioss\", \"s3\")".format(provider))

        ent_cfg_svc = EnterpriseConfigService(enterprise_id)
        ent_cfg_svc.update_config_enable_status(key="OBJECT_STORAGE", enable=enable)
        ent_cfg_svc.update_config_value(key="OBJECT_STORAGE",
                                        value={
                                            "provider": provider,
                                            "endpoint": endpoint,
                                            "bucket_name": bucket_name,
                                            "access_key": access_key,
                                            "secret_key": secret_key,
                                        })
        return Response(status=status.HTTP_200_OK)


class EnterpriseAppStoreImageHubView(EnterpriseAdminView):
    @never_cache
    def put(self, request, enterprise_id, *args, **kwargs):
        enable = bool_argument(parse_item(request, "enable", required=True))
        hub_url = parse_item(request, "hub_url", required=True)
        namespace = parse_item(request, "namespace")
        hub_user = parse_item(request, "hub_user")
        hub_password = parse_item(request, "hub_password")

        ent_cfg_svc = EnterpriseConfigService(enterprise_id)
        ent_cfg_svc.update_config_enable_status(key="APPSTORE_IMAGE_HUB", enable=enable)
        ent_cfg_svc.update_config_value(key="APPSTORE_IMAGE_HUB",
                                        value={
                                            "hub_url": hub_url,
                                            "namespace": namespace,
                                            "hub_user": hub_user,
                                            "hub_password": hub_password,
                                        })
        return Response(status=status.HTTP_200_OK)


class EnterpriseVisualMonitorView(EnterpriseAdminView):
    @never_cache
    def put(self, request, enterprise_id, *args, **kwargs):
        enable = bool_argument(parse_item(request, "enable", required=True))
        home_url = parse_item(request, "home_url", required=True)
        cluster_monitor_suffix = request.data.get("cluster_monitor_suffix", "/d/cluster/ji-qun-jian-kong-ke-shi-hua")
        node_monitor_suffix = request.data.get("node_monitor_suffix", "/d/node/jie-dian-jian-kong-ke-shi-hua")
        component_monitor_suffix = request.data.get("component_monitor_suffix", "/d/component/zu-jian-jian-kong-ke-shi-hua")
        slo_monitor_suffix = request.data.get("slo_monitor_suffix", "/d/service/fu-wu-jian-kong-ke-shi-hua")

        ent_cfg_svc = EnterpriseConfigService(enterprise_id)
        ent_cfg_svc.update_config_enable_status(key="VISUAL_MONITOR", enable=enable)
        ent_cfg_svc.update_config_value(key="VISUAL_MONITOR",
                                        value={
                                            "home_url": home_url.strip('/'),
                                            "cluster_monitor_suffix": cluster_monitor_suffix,
                                            "node_monitor_suffix": node_monitor_suffix,
                                            "component_monitor_suffix": component_monitor_suffix,
                                            "slo_monitor_suffix": slo_monitor_suffix,
                                        })
        return Response(status=status.HTTP_200_OK)


class EnterpriseAlertsView(JWTAuthApiView):
    @never_cache
    def get(self, request, enterprise_id, *args, **kwargs):
        alerts = enterprise_services.get_enterprise_alerts(enterprise_id)
        return Response(general_message(200, "success", "查询成功", list=alerts), status=status.HTTP_200_OK)

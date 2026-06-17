# -*- coding: utf-8 -*-
import logging
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from console.views.app_config.base import AppBaseView
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.utils.return_message import error_message
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppPodsView(AppBaseView):
    def get(self, req: Request, pod_name: str, *args: Any, **kwargs: Any) -> Response:
        try:
            data = region_api.pod_detail(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                         pod_name)
            if self.service.extend_method == "kubeblocks_component":
                data = region_api.kubeblocks_cluster_pod_detail(self.service.service_region, self.service.service_id, pod_name)
            # NOTE: region_api may return None; union-attr backlog.
            result = general_message(200, 'success', "查询成功", data.get("bean", None))  # type: ignore[union-attr]
        except RegionApiBaseHttpClient.CallApiError as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)

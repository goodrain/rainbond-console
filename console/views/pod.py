# -*- coding: utf-8 -*-
import logging

from rest_framework.response import Response

from console.views.app_config.base import AppBaseView
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.decorator import perm_required
from www.utils.return_message import error_message
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AppPodsView(AppBaseView):
    @perm_required('manage_service_container')
    def get(self, req, pod_name, *args, **kwargs):
        try:
            data = region_api.pod_detail(self.service.service_region, self.tenant.tenant_name, self.service.service_alias,
                                         pod_name)
            result = general_message(200, 'success', "查询成功", data.get("bean", None))
        except RegionApiBaseHttpClient.CallApiError as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)

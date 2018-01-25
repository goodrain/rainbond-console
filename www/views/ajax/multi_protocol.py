# -*- coding: utf8 -*-
from django.http import JsonResponse

from www.decorator import perm_required
from www.views import AuthedView
import logging
from www.views.mixin import LeftSideBarMixin
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

logger = logging.getLogger('default')
region_api = RegionInvokeApi()

class MultiProtocolsView(LeftSideBarMixin, AuthedView):
    @perm_required('tenant_account')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            logger.debug("region is {0}, tenantName is {1}".format(self.response_region, self.tenantName))
            protocols_info = region_api.get_protocols(self.response_region, self.tenantName)
            protocols = protocols_info["list"]
            pList = []
            for p in protocols:
                pList.append(p["protocol_child"])
            logger.debug("plist is {}".format(pList))
            result = general_message(200, "success", u"操作成功", list=pList)
            return JsonResponse(result, status=200)
        except Exception as e:
            logger.exception(e)
            pList = ["http", "stream"]
            logger.debug("error plist is {}".format(pList))
            result = general_message(200, "success", u"操作成功", list=pList)
            return JsonResponse(result, status=200)



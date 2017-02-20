# -*- coding: utf8 -*-
from django.http import JsonResponse

from www.views import AuthedView
from www.models import ThirdAppInfo

import logging

logger = logging.getLogger('default')


class UpdateAppView(AuthedView):
    
    def __init__(self, request, *args, **kwargs):
        
        self.app_id = kwargs.get('app_id', None)
        self.app_info = ThirdAppInfo.objects.get(bucket_name=self.app_id)
        
    def post(self, request, *args, **kwargs):
        """
        修改应用名
        """
        result = {}
        try:
            name = request.POST.get("name", "")
            if name == "":
                result["status"] = "failure"
                result["message"] = "应用名不能为空"
            else:
                self.app_info.name = name
                self.app_info.save()
                result["status"] = "success"
                result["message"] = "修改成功"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = "修改失败"
        return JsonResponse(result)

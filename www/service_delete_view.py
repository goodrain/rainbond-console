# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import datetime
import time
import json

from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from www.views import BaseView
from www.models import TenantServiceInfoDelete
import logging
logger = logging.getLogger('default')

class ServiceDeleteView(BaseView):
    @never_cache
    def get(self, request, *args, **kwargs):        
        try:
            action = request.GET.get("action", "")
            token = request.GET.get("token", "")
            if action == "getList" and token == "goodraindelete":
                data = []
                tsdlist = TenantServiceInfoDelete.objects.all()
                for tsd in tsdlist:
                    data.append(tsd.tenant_id + "=" + tsd.service_id + "=" + str(tsd.git_project_id))
                return JsonResponse({"data":data})
            elif action == "updateList" and token == "goodraindelete":
                tsdid = request.GET.get("tsdid", "")
                if tsdid is not None:
                    TenantServiceInfoDelete.objects.get(service_id=tsdid).delete()
                result = {}
                result["ok"] = True
                return JsonResponse(result)
        except Exception as e:
            logger.exception(e)            
        return JsonResponse({})

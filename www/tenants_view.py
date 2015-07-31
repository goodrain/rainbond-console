# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import datetime
import time
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from www.views import BaseView
from www.models import Tenants
from www.service_http import RegionServiceApi

import logging
logger = logging.getLogger('default')

client = RegionServiceApi()

# 计费
class TenantsVisitorView(BaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get("action", "")
            tenants = request.POST.get("tenants", "")
            if action == "pause":
                if tenants is not None and tenants != "":
                    tenantList = Tenants.objects.filter(service_status=1)
                    arr = []
                    map = {}
                    for tenant in tenantList:
                        arr.append(tenant.tenant_name)
                        map[tenant.tenant_name] = tenant.tenant_id
                    tses = tenants.split(",")
                    for ts in tses:
                        if ts != "":
                            try:
                                pass
                            except Exception:
                                tenant_id = map[ts]
                                if tenant_id is not None and tenant_id != "":
                                    client.pause(tenant_id)
            elif action == "unpause":
                tenants = request.POST.get("tenants", "")
                if tenants is not None and tenants != "":
                    tses = tenants.split(",")
                    for ts in tses:
                        try:
                            t = Tenants.objects.get(tenant_name=ts)
                            tenant_id = t.tenant_id
                            client.pause(tenant_id)
                        except Exception:
                            pass
            data["status"] = "success"
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
        return JsonResponse(data, status=200)

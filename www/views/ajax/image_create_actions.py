# -*- coding: utf8 -*-
import datetime
import json

from django.views.decorators.cache import never_cache
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from www.views import AuthedView
from www.models import Users
from www.decorator import perm_required

import logging
from django.template.defaultfilters import length
logger = logging.getLogger('default')

class ImagePort(AuthedView):

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        action = request.POST["action"]
        dep_service_alias = request.POST["dep_service_alias"]
        try:
            tenant_id = self.tenant.tenant_id
            service_id = self.service.service_id
            if action == "add":
                baseService.create_service_mnt(tenant_id, service_id, dep_service_alias, self.service.service_region)
            elif action == "cancel":
                baseService.cancel_service_mnt(tenant_id, service_id, dep_service_alias, self.service.service_region)
            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)

class ImageEnv(AuthedView):

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        action = request.POST["action"]
        dep_service_alias = request.POST["dep_service_alias"]
        try:
            tenant_id = self.tenant.tenant_id
            service_id = self.service.service_id
            if action == "add":
                baseService.create_service_mnt(tenant_id, service_id, dep_service_alias, self.service.service_region)
            elif action == "cancel":
                baseService.cancel_service_mnt(tenant_id, service_id, dep_service_alias, self.service.service_region)
            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)
    
class ImageMnt(AuthedView):

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        action = request.POST["action"]
        dep_service_alias = request.POST["dep_service_alias"]
        try:
            tenant_id = self.tenant.tenant_id
            service_id = self.service.service_id
            if action == "add":
                baseService.create_service_mnt(tenant_id, service_id, dep_service_alias, self.service.service_region)
            elif action == "cancel":
                baseService.cancel_service_mnt(tenant_id, service_id, dep_service_alias, self.service.service_region)
            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)
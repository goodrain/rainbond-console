# -*- coding: utf8 -*-
from django.http import JsonResponse
from www.views import BaseView

import logging
logger = logging.getLogger('default')


class FormValidView(BaseView):

    def get(self, request, *args, **kwargs):

        params = request.GET.dict()
        if len(params) == 1:
            name, value = params.items()[0]
            if hasattr(self, name + '_check'):
                check_method = getattr(self, name + '_check')
            else:
                return JsonResponse({"ok": False, "info": "unsupport field %s" % name}, status=404)
            try:
                result, code = check_method(value)
                return JsonResponse(result, status=code)
            except Exception:
                return JsonResponse({"ok": False}, status=500)
        else:
            return JsonResponse({"ok": False}, status=400)

    def tenant_check(self, value):
        from www.models import Tenants
        try:
            Tenants.objects.get(tenant_name=value)
            return {"ok": False}, 409
        except Tenants.DoesNotExist:
            return {"ok": True}, 200

    def nick_name_check(self, value):
        from www.models import Users
        try:
            Users.objects.get(nick_name=value)
            return {"ok": False}, 409
        except Users.DoesNotExist:
            return {"ok": True}, 200

    def email_check(self, value):
        from www.models import Users
        try:
            Users.objects.get(email=value)
            return {"ok": False}, 409
        except Users.DoesNotExist:
            return {"ok": True}, 200

    def app_key_check(self, value):
        from www.models import ServiceInfo
        try:
            ServiceInfo.objects.get(service_key=value)
            return {"ok": False}, 409
        except ServiceInfo.DoesNotExist:
            return {"ok": True}, 200

# -*- coding: utf8 -*-
from django.http import HttpResponse
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
                return HttpResponse("unsupport field %s" % name, status=404)
            try:
                result, code = check_method(value)
                return HttpResponse(result, status=code)
            except Exception:
                return HttpResponse("server error", status=500)
        else:
            return HttpResponse("400 request error", status=400)

    def tenant_check(self, value):
        from www.models import Tenants
        try:
            Tenants.objects.get(tenant_name=value)
            return u"团队名已存在", 409
        except Tenants.DoesNotExist:
            return "ok", 200

    def nick_name_check(self, value):
        from www.models import Users
        try:
            Users.objects.get(nick_name=value)
            return u"昵称已存在", 409
        except Users.DoesNotExist:
            return "ok", 200

    def email_check(self, value):
        from www.models import Users
        try:
            Users.objects.get(email=value)
            return u"邮件地址已存在", 409
        except Users.DoesNotExist:
            return "ok", 200

    def app_key_check(self, value):
        from www.models import ServiceInfo
        try:
            ServiceInfo.objects.get(service_key=value)
            return u"要发布的应用名已存在", 409
        except ServiceInfo.DoesNotExist:
            return "ok", 200

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
                return JsonResponse({"feedback": "unsupport field %s" % name}, status=400)
            try:
                result, code = check_method(value)
                return JsonResponse(result, status=code)
            except Exception:
                return JsonResponse({"feedback": "server error"}, status=500)
        else:
            return JsonResponse({"feedback": "400 request error"}, status=400)

    def tenant_check(self, value):
        from www.models import Tenants
        try:
            Tenants.objects.get(tenant_name=value)
            return {"feedback": u"团队名已存在"}, 409
        except Tenants.DoesNotExist:
            return {"feedback": "ok"}, 200

    def nick_name_check(self, value):
        from www.models import Users
        try:
            Users.objects.get(nick_name=value)
            return {"feedback": u"昵称已存在"}, 409
        except Users.DoesNotExist:
            return {"feedback": "ok"}, 200

    def email_check(self, value):
        from www.models import Users
        try:
            Users.objects.get(email=value)
            return {"feedback": u"邮件地址已存在"}, 409
        except Users.DoesNotExist:
            return {"feedback": "ok"}, 200


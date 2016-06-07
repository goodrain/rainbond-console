# -*- coding: utf8 -*-
import json
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from django.conf import settings

from www.views import BaseView, AuthedView, LeftSideBarMixin
from www.models import ServiceLicense

import logging
import rsa
import base64
logger = logging.getLogger('default')

class LicenseViews(LeftSideBarMixin, AuthedView):

    def get_context(self):
        context = super(LicenseViews, self).get_context()
        return context

    def get_media(self):
        media = super(LicenseViews, self).get_media() + \
                self.vendor('www/css/owl.carousel.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    def get(self, request, *args, **kwargs):
        
        licenseList = ServiceLicense.objects.all()
        context = self.get_context()
        context["myLicenseStatus"] = "active"
        context["licenseListStatus"] = "active"
        context["licenseList"] = licenseList
        return TemplateResponse(self.request, 'www/license.html', context)

class LicenseDetailViews(LeftSideBarMixin, AuthedView):

    def get_context(self):
        context = super(LicenseDetailViews, self).get_context()
        return context

    def get_media(self):
        media = super(LicenseDetailViews, self).get_media() + \
                self.vendor('www/css/jquery-ui.css', 'www/css/jquery-ui-timepicker-addon.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
                            'www/js/jquery.scrollTo.min.js', 'www/js/jquery-ui.js', 'www/js/jquery-ui-timepicker-addon.js', 'www/js/jquery-ui-timepicker-addon-i18n.min.js',
                            'www/js/jquery-ui-sliderAccess.js')
        return media

    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["myLicenseStatus"] = "active"
        context["licenseDetailStatus"] = "active"
        id = request.GET.get("id", "")
        action = request.GET.get("action", "")
        if action == "delete":
            ServiceLicense.objects.filter(ID=id).delete()
            return self.redirect_to('/apps/' + self.tenantName + '/license-list')
        return TemplateResponse(self.request, 'www/license_detail.html', context)
        
    def post(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        try:
            if self.user.is_sys_admin:
                post_data = request.POST.dict()
                data = {}
                data["company"] = post_data['company']
                data["code"] = post_data['code']
                data["region"] = post_data['region']
                data["hub_account"] = post_data['hub_account']
                data["allow_node"] = post_data['allow_node']
                data["allow_cpu"] = post_data['allow_cpu']
                data["allow_memory"] = post_data['allow_memory']
                data["start_time"] = post_data['start_time']
                data["end_time"] = post_data['end_time']
                logger.info(json.dumps(data))
                (pubkey, privkey) = rsa.newkeys(2048)
                ciphertext = rsa.encrypt(json.dumps(data), pubkey)
                data["public_pem"] = pubkey.save_pkcs1().encode("utf-8")
                data["private_pem"] = privkey.save_pkcs1().encode("utf-8")
                data["ciphertext"] = base64.b64encode(ciphertext)
                ServiceLicense(**data).save()
                logger.info(data)
                return self.redirect_to('/apps/' + self.tenantName + '/license-list')
            else:
                return HttpResponse(u"没有权限", status=500)
        except Exception as e:
            logger.exception(e)
        return HttpResponse(u"创建过程出现异常", status=500)
    
class LicenseShow(BaseView):
    
    def get_context(self):
        context = super(LicenseShow, self).get_context()
        return context
    
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        id = request.GET.get("id", "")
        action = request.GET.get("action", "")
        result = ""
        fileName = "1.txt"
        try:
            license = ServiceLicense.objects.get(ID=id)
            if action == "private":
                result = license.private_pem
                fileName = "goodrain_" + license.code + ".pem"
            elif action == "key":
                result = license.ciphertext
                fileName = "goodrain_" + license.code + ".cert"
            context["result"] = result
        except Exception as e:
            logger.exception(e)
        response = HttpResponse(result, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename=' + fileName
        return response

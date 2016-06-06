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
        context["myLicenseStatus"]="active"
        context["licenseListStatus"]="active"
        context["licenseList"] = licenseList
        return TemplateResponse(self.request, 'www/license.html', context)

class LicenseDetailViews(LeftSideBarMixin, AuthedView):

    def get_context(self):
        context = super(LicenseDetailViews, self).get_context()
        return context

    def get_media(self):
        media = super(LicenseDetailViews, self).get_media() + \
                self.vendor('www/css/owl.carousel.css','www/js/jquery.cookie.js','www/js/common-scripts.js','www/js/jquery.dcjqaccordion.2.7.js',
                            'www/js/license.js','www/js/jquery.scrollTo.min.js','www/js/jquery-ui.js', 'www/js/jquery-ui-timepicker-addon.js', 'www/js/jquery-ui-timepicker-addon-i18n.min.js')
        return media

    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["myLicenseStatus"]="active"
        context["licenseDetailStatus"]="active"
        return TemplateResponse(self.request,'www/license_detail.html', context)
        
    def post(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        try:
            post_data = request.POST.dict()
            data={}
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
            ciphertext=rsa.encrypt(json.dumps(data), pubkey)
            data["public_pem"]=pubkey.save_pkcs1().encode("utf-8")
            data["private_pem"]=privkey.save_pkcs1().encode("utf-8")
            data["ciphertext"]=base64.b64encode(ciphertext)
            ServiceLicense(**data).save()
            logger.info(data)
            return self.redirect_to('/apps/'+self.tenantName+'/license-list')
        except Exception as e:
            logger.exception(e)
        return HttpResponse(u"创建过程出现异常", status=500)
    
    def delete(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        try:
            post_data = request.POST.dict()
            id = post_data.get('id')
            code = post_data.get('code')
            ServiceLicense.objects.filter(ID=id, code=code).delete()
        except Exception as e:
            logger.exception(e)
        return self.redirect_to('/apps/'+self.tenantName+'/license-list')
    

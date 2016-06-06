# -*- coding: utf8 -*-
import json
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from django.conf import settings

from www.views import AuthedView, LeftSideBarMixin, BaseView
from www.models import ServiceLicense

import logging
import rsa
logger = logging.getLogger('default')

class LicenseViews(LeftSideBarMixin, AuthedView):

    def get_context(self):
        context = super(LicenseViews, self).get_context()
        return context

    def get_media(self):
        media = super(PublishServiceRelationView, self).get_media() + \
                self.vendor('www/css/goodrainstyle.css','www/js/jquery.cookie.js','www/js/validator.min.js')
        return media

    def get(self, request, *args, **kwargs):
        
        licenseList = ServiceLicense.objects.all()
        context = self.get_context()
        context["licenseList"] = licenseList
        # 返回页面
        return TemplateResponse(self.request, 'www/license.html', context)

class LicenseDetailViews(BaseView):

    def get_context(self):
        context = super(LicenseDetailViews, self).get_context()
        return context

    def get_media(self):
        media = super(PublishServiceRelationView, self).get_media() + \
                self.vendor('www/css/goodrainstyle.css','www/js/jquery.cookie.js','www/js/validator.min.js','www/js/gr/app_license.js',
                            'www/js/jquery-ui.js', 'www/js/jquery-ui-timepicker-addon.js', 'www/js/jquery-ui-timepicker-addon-i18n.min.js')
        return media

    def get(self, request, *args, **kwargs):
        return TemplateResponse(self.request,'www/license_detail.html', context)
        
    def post(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        try:
            post_data = request.POST.dict()
            data={}
            data["company"] = post_data.get('company')
            data["code"] = post_data.get('code')
            data["region"] = post_data.get('region')
            data["hub_account"] = post_data.get('hub_account')
            data["allow_node"] = post_data.get('allow_node')
            data["allow_cpu"] = post_data.get('allow_cpu')
            data["allow_memory"] = post_data.get('allow_memory')
            data["start_time"] = post_data.get('start_time')
            data["end_time"] = post_data.get('end_time')
            
            (pubkey, privkey) = rsa.newkeys(1024)
            public_pem=pubkey.save_pkcs1().encode("utf-8")
            private_pem=privkey.save_pkcs1.encode("utf-8")
            ciphertext=rsa.encrypt(json.dumps(data), public_pem)
            
            ServiceLicense(company=company, code=code, region=region, hub_account=hub_account, allow_node=allow_node,
                           allow_cpu=allow_cpu, allow_memory=allow_memory, start_time=start_time, end_time=end_time,
                           public_pem=public_pem, private_pem=private_pem,ciphertext
                           ).save()
        except Exception as e:
            logger.exception(e)
        return self.redirect_to('/license/list')
    
    def delete(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        try:
            post_data = request.POST.dict()
            id = post_data.get('id')
            code = post_data.get('code')
            ServiceLicense.objects.filter(ID=id, code=code).delete()
        except Exception as e:
            logger.exception(e)
        return self.redirect_to('/license/list')
    

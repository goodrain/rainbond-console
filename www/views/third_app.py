# -*- coding: utf8 -*-
import json
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from django.http import HttpResponseRedirect
from www.third_app.cdn.upai.client import YouPaiApi
from www.utils.crypt import make_uuid
from www.models.main import *
from www.views import AuthedView, LeftSideBarMixin
from www.decorator import perm_required
import logging

logger = logging.getLogger('default')


class CreateThirdAppView(LeftSideBarMixin, AuthedView):
    """ 服务信息配置页面 """
    
    def get_context(self):
        context = super(CreateThirdAppView, self).get_context()
        return context
    
    def get_media(self):
        media = super(CreateThirdAppView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css',
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/style.css',
            'www/css/bootstrap-switch.min.css', 'www/css/bootstrap-editable.css',
            'www/css/style-responsive.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js', 'www/js/gr/app_publish.js',
            'www/js/validator.min.js'
        )
        return media
    
    # form提交.
    @perm_required('app_create')
    def post(self, request, *args, **kwargs):
        try:
            app_type = kwargs.get('app_type', None)
            tenant_name = self.tenantName
            create_body = {}
            context = self.get_context()
            if app_type is not None:
                if app_type == "upai_cdn":
                    service_id = make_uuid()
                    create_body["bucket_name"] = "gr" + service_id[-6:]
                    create_body["type"] = "ucdn"
                    create_body["business_type"] = "file"
                
                elif app_type == "upai_oos":
                    service_id = make_uuid()
                    create_body["bucket_name"] = "gr" + service_id[-6:]
                    create_body["type"] = "file"
                    create_body["business_type"] = "file"
                
                res, body = YouPaiApi.createService(body=create_body)
                if res.status == 201:
                    ThirdAppInfo.service_id = service_id
                    ThirdAppInfo.bucket_name = create_body.bucket_name
                    ThirdAppInfo.app_type = "upai_cdn"
                    ThirdAppInfo.tenant_id = tenant_name
                    ThirdAppInfo.save()
                    HttpResponseRedirect("/apps/" + tenant_name + "/" + create_body["bucket_name"] + "/third_show")
                else:
                    logger.error("create upai cdn bucket error,:" + body.message)
                    return HttpResponse(u"创建错误", status=res.status)
            else:
                return HttpResponse(u"参数错误", status=415)
        except Exception as e:
            logger.exception(e)
        return HttpResponse(u"创建异常", status=500)


class ThirdAppView(LeftSideBarMixin, AuthedView):
    def get_context(self):
        context = super(CreateThirdAppView, self).get_context()
        return context
    
    def get_media(self):
        media = super(CreateThirdAppView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css',
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/style.css',
            'www/css/bootstrap-switch.min.css', 'www/css/bootstrap-editable.css',
            'www/css/style-responsive.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js', 'www/js/gr/app_publish.js',
            'www/js/validator.min.js'
        )
        return media
    
    def get(self, request, *args, **kwargs):
        try:
            app_bucket = kwargs.get('app_bucket', None)
            if app_bucket is None:
                return HttpResponse(u"参数错误", status=415)
            app_info = ThirdAppInfo.objects.filter(app_bucket=app_bucket).first()
            if app_info is None:
                return HttpResponse(u"参数错误", status=415)
            context = self.get_context()
            context["app_info"] = app_info
            if app_info.app_type == "upai_cdn":
                res, body = YouPaiApi.getDomainList(app_info.bucket_name)
                if res.status == 200:
                    context["domains"] = body
                res, body = YouPaiApi.getOperatorsList(app_info.bucket_name)
                if res.status == 200:
                    context["operators"] = body
                return TemplateResponse(self.request, "third_app/CDNshow.html", context)
        except Exception as e:
            logger.exception(e)
            return HttpResponse(u"创建异常", status=500)

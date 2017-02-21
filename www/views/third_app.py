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
upai_client = YouPaiApi()


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
    def get(self, request, *args, **kwargs):
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
                
                res, body = upai_client.createService(json.dumps(create_body))
                if res.status == 201:
                    info = ThirdAppInfo()
                    info.service_id = service_id
                    info.bucket_name = create_body["bucket_name"]
                    info.app_type = "upai_cdn"
                    info.tenant_id = tenant_name
                    info.name = "又拍云应用"
                    info.save()
                    return HttpResponseRedirect(
                        "/apps/" + tenant_name + "/" + create_body["bucket_name"] + "/third_show")
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
        context = super(ThirdAppView, self).get_context()
        return context
    
    def get_media(self):
        media = super(ThirdAppView, self).get_media() + self.vendor(
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
            
            tenant_name = self.tenantName
            if app_bucket is None:
                return HttpResponse(u"参数错误", status=415)
            app_info = ThirdAppInfo.objects.filter(bucket_name=app_bucket, tenant_id=tenant_name).first()
            if app_info is None:
                return HttpResponse(u"参数错误", status=415)
            context = self.get_context()
            context["app_info"] = app_info
            context["app_id"] = app_bucket
            if app_info.app_type == "upai_cdn":
                res, body = upai_client.getDomainList(app_info.bucket_name)
                if res.status == 200:
                    context["domains"] = body
                res, body = upai_client.getOperatorsList(app_info.bucket_name)
                if res.status == 200:
                    context["operators"] = body
                return TemplateResponse(self.request, "www/third_app/CDNshow.html", context)
        except Exception as e:
            logger.exception(e)
            return HttpResponse(u"创建异常", status=500)


class ThirdAppListView(LeftSideBarMixin, AuthedView):
    def get_context(self):
        context = super(ThirdAppListView, self).get_context()
        return context
    
    def get_media(self):
        media = super(ThirdAppListView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css',
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/style.css',
            'www/css/bootstrap-switch.min.css', 'www/css/bootstrap-editable.css',
            'www/css/style-responsive.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js', 'www/js/gr/app_publish.js',
            'www/js/validator.min.js'
        )
        return media
    
    def get(self, request, *args, **kwargs):
        tenant_name = self.tenantName
        apps = ThirdAppInfo.objects.filter(tenant_id=tenant_name).all()
        context = self.get_context()
        context["apps"] = apps
        return TemplateResponse(self.request, "www/third_app/thirdApp.html", context)

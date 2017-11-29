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
import time
import datetime
from django.db import connection
from django.http import JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import transaction

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
    
    def get(self, request, *args, **kwargs):
        
        app_type = kwargs.get('app_type', None)
        context = self.get_context()
        context["app_type"] = app_type
        return TemplateResponse(self.request, "www/third_app/CDN_create.html", context)
    
    # form提交.
    @perm_required('app_create')
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            
            app_type = kwargs.get('app_type', None)
            tenant_name = self.tenantName
            app_name = request.POST.get("app_name", None)
            create_body = {}
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
                upai_client = YouPaiApi()
                res, body = upai_client.createService(json.dumps(create_body))
                if res.status == 201:
                    # 创建应用
                    info = ThirdAppInfo()
                    info.service_id = service_id
                    info.bucket_name = create_body["bucket_name"]
                    info.app_type = app_type
                    info.tenant_id = tenant_name
                    if app_name is not None:
                        info.name = app_name
                    elif app_type == "upai_oos":
                        info.name = "又拍云对象存储"
                    elif app_type == "upai_cdn":
                        info.name = "又拍云CDN"
                    info.save()
                    # 创建初始化账单
                    order = ThirdAppOrder(bucket_name=info.bucket_name, tenant_id=self.tenantName,
                                          service_id=service_id)
                    order.order_id = make_uuid()
                    order.start_time = datetime.datetime.now()
                    order.end_time = datetime.datetime.now()
                    order.create_time = datetime.datetime.now()
                    order.save()
                    result["status"] = "success"
                    result["app_id"] = info.bucket_name
                    JsonResponse(result)
                else:
                    
                    logger.error("create upai cdn bucket error,:" + body.message)
                    result["status"] = "failure"
                    result["message"] = body.message
                    JsonResponse(result)
            else:
                result["status"] = "failure"
                result["message"] = "参数错误"
                JsonResponse(result)
        except Exception as e:
            transaction.rollback()
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = "内部错误"
        return JsonResponse(result)


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
            upai_client = YouPaiApi()
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
            if app_info.app_type == "upai_cdn" or app_info.app_type == "upai_oos":
                res, body = upai_client.getDomainList(app_info.bucket_name)
                if res.status == 200:
                    dos = []
                    for domain in body.domains:
                        domain.updated_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(domain.updated_at))
                        if app_info.app_type == "upai_cdn" and domain.domain.endswith("upaiyun.com"):
                            continue
                        dos.append(domain)
                    context["domains"] = dos
                res, body = upai_client.getOperatorsList(app_info.bucket_name)
                
                if res.status == 200:
                    ops = []
                    for op in body.operators:
                        op.bind_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(op.bind_at))
                        ops.append(op)
                    context["operators"] = ops
                    info = ThirdAppOrder.objects.order_by("-create_time").filter(bucket_name=app_bucket).first()
                    
                    logger.info(info)
                    order_info = {}
                    if info.oos_size > 0:
                        order_info["oos_size"] = "{0}MB".format(round(float(info.oos_size) / 1024 / 1024), 2)
                    else:
                        order_info["oos_size"] = "0MB"
                    if info.traffic_size > 0:
                        order_info["traffic_size"] = "{0}MB".format(round(float(info.traffic_size) / 1024 / 1024), 2)
                    else:
                        order_info["traffic_size"] = "0MB"
                    if info.total_cost > 0:
                        order_info["total_cost"] = "{0}元".format(info.total_cost)
                    else:
                        order_info["total_cost"] = "0元"
                    if info.request_size > 0:
                        order_info["request_size"] = "{0}次".format(info.request_size)
                    else:
                        order_info["request_size"] = "0次"
                    context["order_info"] = order_info
                traffic_record = CDNTrafficHourRecord.objects.order_by("-create_time").filter(
                    bucket_name=app_bucket)
                if traffic_record.count() > 0:
                    context["traffic_balance"] = round(float(traffic_record.first().balance) / 1024 / 1024 / 1024,
                                                       4)
                else:
                    context["traffic_balance"] = 0
            if app_info.app_type == "upai_cdn":
                try:
                    res, body = upai_client.get_cdn_source(app_info.bucket_name)
                    if res.status == 200:
                        context["cdn_source"] = body.data
                except Exception as e:
                    logger.exception(e)
            
            return TemplateResponse(self.request, "www/third_app/CDNshow.html", context)
        
        except Exception as e:
            logger.exception(e)
        return HttpResponse(u"获取应用异常", status=500)


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
        apps = ThirdAppInfo.objects.filter(tenant_id=tenant_name, delete=0).all()
        context = self.get_context()
        context["apps"] = apps
        return TemplateResponse(self.request, "www/third_app/thirdApp.html", context)


class ThirdAppOrdersListView(LeftSideBarMixin, AuthedView):
    def get_context(self):
        context = super(ThirdAppOrdersListView, self).get_context()
        return context
    
    def get_media(self):
        media = super(ThirdAppOrdersListView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css',
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/style.css',
            'www/css/bootstrap-switch.min.css', 'www/css/bootstrap-editable.css',
            'www/css/style-responsive.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js', 'www/js/gr/app_publish.js',
            'www/js/validator.min.js'
        )
        return media
    
    def get(self, request, *args, **kwargs):
        app_bucket = kwargs.get('app_bucket', None)
        context = self.get_context()
        context["app_id"] = app_bucket
        app_info = ThirdAppInfo.objects.filter(bucket_name=app_bucket).first()
        if app_info is None:
            return HttpResponse(u"参数错误", status=415)
        context["app_info"] = app_info
        return TemplateResponse(self.request, "www/third_app/CDNcost.html", context)


class ThirdAppOrdersListDataView(AuthedView):
    def get(self, request, *args, **kwargs):
        app_bucket = kwargs.get('app_bucket', None)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 24)
        orders = ThirdAppOrder.objects.order_by("-create_time").filter(bucket_name=app_bucket).all()
        paginator = Paginator(orders, page_size)
        orders_size = orders.count()
        last_page = orders_size / int(page_size) == int(page) - 1
        context = self.get_context()
        try:
            page_orders = paginator.page(page)
            context["orders"] = page_orders
        except PageNotAnInteger:
            # 页码不是整数，返回第一页。
            page_orders = paginator.page(1)
            context["orders"] = page_orders
        except EmptyPage:
            page_orders = paginator.page(paginator.num_pages)
            context["orders"] = page_orders
        context["current_page"] = page
        context["current_page_size"] = page_size
        context["last_page"] = last_page
        return TemplateResponse(self.request, "www/third_app/cost_list.html", context)

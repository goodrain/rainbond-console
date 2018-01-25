# -*- coding: utf8 -*-
import logging
import os

from django.db.models import Q
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from www.app_http import AppServiceApi
from www.decorator import perm_required
from www.models import TenantEnterprise, AppServiceGroup, PermRelTenant
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, \
    CodeRepositoriesService
from www.utils import sn
from www.views import AuthedView, LeftSideBarMixin

logger = logging.getLogger('default')

monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
tenantUsedResource = TenantUsedResource()
baseService = BaseTenantService()
codeRepositoriesService = CodeRepositoriesService()
appClient = AppServiceApi()


class CreateServiceEntranceView(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/css/style.css', 'www/css/style-responsive.css', 'www/js/jquery.cookie.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/respond.min.js')
        return media

    @never_cache
    @perm_required('create_service')
    def get(self, request, *args, **kwargs):
        choose_region = request.GET.get("region", None)
        if choose_region is not None:
            self.response_region = choose_region
        context = self.get_context()
        context["createApp"] = "active"
        context["is_private"] = sn.instance.is_private()
        context["cloud_assistant"] = sn.instance.cloud_assistant
        if self.user.phone:
            git_name = self.user.phone
        else:
            git_name = self.user.nick_name
        context["gitName"] = git_name
        fr = request.GET.get("fr", None)
        if fr is None or fr not in ("private", "deploy", "hot", "new", "thirdApp"):
            fr = "hot"
        context["fr"] = fr
        ty = request.GET.get("ty", None)
        if ty is None or ty not in ("image", 'code', 'app', 'cloud',):
            ty = "image"
        context["ty"] = ty
        try:
            if ty == "app":
                query_app_name = request.GET.get("app_name")
                page_num = request.GET.get("page", "1")
                page_num = int(page_num)
                page_num = page_num if page_num > 0 else 1
                page_size = request.GET.get("limit", "12")
                page_size = int(page_size)
                page_size = page_size if page_size > 0 else 12
                # 数据索引
                begin_index = (page_num - 1) * page_size
                end_index = page_num * page_size

                try:
                    perm = PermRelTenant.objects.filter(tenant_id=self.tenant.ID).first()
                    enterprise = TenantEnterprise.objects.get(pk=perm.enterprise_id)
                    is_active = enterprise.is_active
                    enterprise_id = enterprise.ID

                    context["is_active"] = is_active
                    context['enterprise_id'] = enterprise.enterprise_id
                except (TenantEnterprise.DoesNotExist, PermRelTenant.DoesNotExist):
                    enterprise_id = 0

                # 当前租户已分享的应用
                query = Q(source='remote')
                if query_app_name:
                    query = query & Q(group_share_alias__icontains=query_app_name)

                # 默认按更新时间排序
                order_by = '-update_time'

                # 当前企业已分享的应用
                if fr == "private":
                    query = Q(enterprise_id=enterprise_id, source='local')
                    order_by = "-update_time"

                # 当前租户最新部署的应用
                elif fr == "deploy":
                    order_by = "-deploy_time"

                # 云帮部署最多应用
                elif fr == "hot":
                    order_by = "-installed_count"

                # 云帮最新的应用
                elif fr == "new":
                    order_by = "-update_time"

                query = AppServiceGroup.objects.filter(query)
                total_size = query.count()
                total_page = total_size / page_size
                total_page = 1 if total_page == 0 else total_page + 1
                service_list = query.order_by(order_by)[begin_index:end_index]
                context["service_list"] = [{
                    'key': service.group_share_id,
                    'version': service.group_version,
                    'alias': service.group_share_alias,
                    'is_market': service.is_market,
                } for service in service_list]

                context["page_num"] = page_num
                context["pre_page"] = page_num - 1 if page_num - 1 > 0 else 1
                context["next_page"] = page_num + 1
                context["total_page"] = total_page
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/app_create_step_one.html", context)

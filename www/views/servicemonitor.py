# -*- coding: utf8 -*-
from www.views import AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from django.template.response import TemplateResponse

class SourcesMonitorServicelView(LeftSideBarMixin, AuthedView):
    """服务资源监控配置页面"""

    @perm_required('service_monitor')
    def get(self, request, *args, **kwargs):
        """
        get
        """
        context = self.get_context()
        context["fr"] = "sources"
        return TemplateResponse(self.request,
                                'www/sources/monitorDetail.html',
                                context)

class SourcesAlertServicelView(LeftSideBarMixin, AuthedView):
    """服务资源监控配置页面"""

    @perm_required('service_alert')
    def get(self, request, *args, **kwargs):
        """
        监控页面
        """
        context = self.get_context()
        context["fr"] = "sources"
        return TemplateResponse(self.request,
                                'www/sources/alert.html',
                                context)

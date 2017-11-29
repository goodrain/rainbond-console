# -*- coding: utf8 -*-
from www.views import AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from django.template.response import TemplateResponse

class SourcesMonitorServicelView(LeftSideBarMixin, AuthedView):
    """服务资源监控配置页面"""

    
    def get_media(self):
        media = super(SourcesMonitorServicelView, self).get_media() + self.vendor(
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
            'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media
    
    @perm_required('service_monitor')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["myAppStatus"] = "active"
        context["fr"] = "resource"
        return TemplateResponse(self.request,
                                'www/service_detail.html',
                                context)

class SourcesAlertServicelView(LeftSideBarMixin, AuthedView):
    """服务资源监控配置页面"""

    @perm_required('service_alert')
    def get(self, request, *args, **kwargs):
        """
        监控页面
        """
        context = self.get_context()
        context["myAppStatus"] = "active"
        context["fr"] = "resource"
        return TemplateResponse(self.request,
                                'www/service_detail.html',
                                context)

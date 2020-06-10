# -*- coding: utf-8 -*-
# creater by: barnett
from django.conf.urls import url

from console.utils import perms_route_config as perms
from openapi.views.apps.apps import AppInfoView
from openapi.views.apps.apps import ListAppsView
from openapi.views.apps.apps import APPOperationsView
from openapi.views.gateway.gateway import ListAppGatewayHTTPRuleView
from openapi.views.gateway.gateway import UpdateAppGatewayHTTPRuleView
from openapi.views.apps.apps import ListAppServicesView, AppServicesView, AppServiceEventsView, TeamAppsCloseView
from openapi.views.apps.market import AppInstallView
from openapi.views.groupapp import GroupAppsCopyView

urlpatterns = [
    url(r'^$', ListAppsView.as_view()),
    url(r'^/close$', TeamAppsCloseView.as_view(), perms.TeamAppsCloseView),
    url(r'^/(?P<app_id>[\w\-]+)$', AppInfoView.as_view(), perms.AppInfoView),
    url(r'^/(?P<app_id>[\w\-]+)/install$', AppInstallView.as_view(), perms.AppInstallView),
    url(r'^/(?P<app_id>[\d\-]+)/copy$', GroupAppsCopyView.as_view(), perms.GroupAppsCopyView),
    url(r'^/(?P<app_id>[\d\-]+)/operations$', APPOperationsView.as_view(), perms.APPOperationsView),
    url(r'^/(?P<app_id>[\d\-]+)/httpdomains$', ListAppGatewayHTTPRuleView.as_view(), perms.ListAppGatewayHTTPRuleView),
    url(r'^/(?P<app_id>[\d\-]+)/httpdomains/(?P<rule_id>[\w\-]+)$', UpdateAppGatewayHTTPRuleView.as_view(),
        perms.UpdateAppGatewayHTTPRuleView),
    url(r'^/(?P<app_id>[\d\-]+)/services$', ListAppServicesView.as_view(), perms.ListAppServicesView),
    url(r'^/(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)$', AppServicesView.as_view(), perms.AppServicesView),
    url(r'^/(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)/events$', AppServiceEventsView.as_view(),
        perms.AppServiceEventsView)
]

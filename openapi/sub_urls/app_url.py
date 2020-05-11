# -*- coding: utf-8 -*-
# creater by: barnett
from django.conf.urls import url
from openapi.views.apps.apps import AppInfoView
from openapi.views.apps.apps import ListAppsView
from openapi.views.apps.apps import APPOperationsView
from openapi.views.gateway.gateway import ListAppGatewayHTTPRuleView
from openapi.views.gateway.gateway import UpdateAppGatewayHTTPRuleView
from openapi.views.apps.apps import ListAppServicesView
from openapi.views.apps.market import MarketAppInstallView

from openapi.views.groupapp import GroupAppsCopyView

urlpatterns = [
    url(r'^$', ListAppsView.as_view()),
    url(r'^/(?P<app_id>[\w\-]+)$', AppInfoView.as_view()),
    url(r'^/(?P<app_id>[\w\-]+)/install$', MarketAppInstallView.as_view()),
    url(r'^/(?P<app_id>[\d\-]+)/copy$', GroupAppsCopyView.as_view()),
    url(r'^/(?P<app_id>[\d\-]+)/operations$', APPOperationsView.as_view()),
    url(r'^/(?P<app_id>[\d\-]+)/httpdomains$', ListAppGatewayHTTPRuleView.as_view()),
    url(r'^/(?P<app_id>[\d\-]+)/httpdomains/(?P<rule_id>[\w\-]+)$', UpdateAppGatewayHTTPRuleView.as_view()),
    url(r'^/(?P<app_id>[\d\-]+)/services$', ListAppServicesView.as_view())
]

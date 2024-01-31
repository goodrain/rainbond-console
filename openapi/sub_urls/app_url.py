# -*- coding: utf-8 -*-
# creater by: barnett
from console.utils import perms_route_config as perms
from django.conf.urls import url
from openapi.views.apps.apps import (AppInfoView, APPOperationsView, AppServiceEventsView, AppServicesView,
                                     AppServiceTelescopicHorizontalView, AppServiceTelescopicVerticalView,
                                     ComponentBuildView,
                                     ComponentEnvsUView, CreateThirdComponentView, ListAppServicesView,
                                     TeamAppsCloseView,
                                     TeamAppsMonitorQueryRangeView, TeamAppsMonitorQueryView, ComponentPortsShowView,
                                     ComponentPortsChangeView, ChangeDeploySourceView, ServiceVolumeView)
from openapi.views.apps.market import AppInstallView, AppUpgradeView
from openapi.views.gateway.gateway import (ListAppGatewayHTTPRuleView, ListAppGatewayRuleView,
                                           UpdateAppGatewayHTTPRuleView,
                                           UpdateAppGatewayRuleView)
from openapi.views.groupapp import GroupAppsCopyView

urlpatterns = [
    url(r'^close$', TeamAppsCloseView.as_view(), perms.TeamAppsCloseView),
    url(r'^(?P<app_id>[\d\-]+)$', AppInfoView.as_view(), perms.AppInfoView),
    url(r'^(?P<app_id>[\d\-]+)/monitor/query$', TeamAppsMonitorQueryView.as_view(), perms.AppInfoView),
    url(r'^(?P<app_id>[\d\-]+)/monitor/query_range$', TeamAppsMonitorQueryRangeView.as_view(), perms.AppInfoView),
    url(r'^(?P<app_id>[\d\-]+)/install$', AppInstallView.as_view(), perms.AppInstallView),
    url(r'^(?P<app_id>[\d\-]+)/upgrade$', AppUpgradeView.as_view(), perms.AppUpgradeView),
    url(r'^(?P<app_id>[\d\-]+)/copy$', GroupAppsCopyView.as_view(), perms.GroupAppsCopyView),
    url(r'^(?P<app_id>[\d\-]+)/operations$', APPOperationsView.as_view(), perms.APPOperationsView),
    url(r'^(?P<app_id>[\d\-]+)/httpdomains$', ListAppGatewayHTTPRuleView.as_view(), perms.ListAppGatewayHTTPRuleView),
    url(r'^(?P<app_id>[\d\-]+)/httpdomains/(?P<rule_id>[\w\-]+)$', UpdateAppGatewayHTTPRuleView.as_view(),
        perms.UpdateAppGatewayHTTPRuleView),
    url(r'^(?P<app_id>[\d\-]+)/domains$', ListAppGatewayRuleView.as_view(), perms.ListAppGatewayRuleView),
    url(r'^(?P<app_id>[\d\-]+)/domains/(?P<rule_id>[\w\-]+)$', UpdateAppGatewayRuleView.as_view(),
        perms.UpdateAppGatewayHTTPRuleView),
    url(r'^(?P<app_id>[\d\-]+)/services$', ListAppServicesView.as_view(), perms.ListAppServicesView),
    url(r'^(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)$', AppServicesView.as_view(), perms.AppServicesView),
    url(r'^(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)/events$', AppServiceEventsView.as_view(),
        perms.AppServiceEventsView),
    url(r'^(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)/telescopic/vertical$',
        AppServiceTelescopicVerticalView.as_view(), perms.AppServiceTelescopicVerticalView),
    url(r'^(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)/telescopic/horizontal$',
        AppServiceTelescopicHorizontalView.as_view(), perms.AppServiceTelescopicHorizontalView),
    url(r'^(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)/envs$', ComponentEnvsUView.as_view()),
    url(r'^(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)/ports/(?P<port>[\w\-]+)$',
        ComponentPortsChangeView.as_view()),
    url(r'^(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)/ports$', ComponentPortsShowView.as_view()),
    url(r'^(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)/build$', ComponentBuildView.as_view()),
    url(r'^(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)/docker-image-change$',
        ChangeDeploySourceView.as_view()),
    url(r'^(?P<app_id>[\d\-]+)/services/(?P<service_id>[\w\-]+)/volumes$', ServiceVolumeView.as_view()),

    url(r'^(?P<app_id>[\d\-]+)/third-components$', CreateThirdComponentView.as_view()),
]

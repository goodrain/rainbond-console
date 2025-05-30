# -*- coding: utf-8 -*-
# creater by: barnett
import os

from django.conf.urls import include, url
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from openapi.auth.authentication import OpenAPIAuthentication
from openapi.auth.permissions import OpenAPIPermissions
from openapi.views.admin_view import AdminInfoView, ListAdminsView
from openapi.views.apps.apps import ListAppsView, AppModelImportEvent, AppTarballDirView, \
    AppImportView, AppDeployView, AppChartInfo, DeleteApp, AppsPortView, HelmChart
from openapi.views.enterprise_view import ResourceOverview

from openapi.views.gateway.gateway import ListEnterpriseAppGatewayHTTPRuleView
from openapi.views.region_view import ListRegionInfo, RegionInfo, ReplaceRegionIP
from openapi.views.team_view import (ListRegionsView, ListTeamInfo, TeamAppsResourceView, TeamCertificatesLCView,
                                     TeamCertificatesRUDView, TeamEventLogView, TeamInfo, TeamOverviewView,
                                     TeamsResourceView, EntAppModelView)
from openapi.views.user_view import (ChangePassword, ChangeUserPassword, ListUsersView, UserInfoView, CurrentUsersView,
                                     UserTenantClose, UserTenantDelete)

schema_view = get_schema_view(
    openapi.Info(
        title="Rainbond Open API",
        default_version='v1',
        description="Rainbond open api",
        terms_of_service="https://cloud.goodrain.com",
        contact=openapi.Contact(email="barnett@goodrain.com"),
        license=openapi.License(name="LGPL License"),
    ),
    public=False,
    permission_classes=(OpenAPIPermissions, ),
    authentication_classes=(OpenAPIAuthentication, ),
)

urlpatterns = [
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    # get enterprise regions
    url(r'^v1/regions$', ListRegionInfo.as_view(), name="list_regions"),
    url(r'^v1/regions/(?P<region_id>[\w\-]+)$', RegionInfo.as_view(), name="region_info"),
    url(r'^v1/administrators$', ListAdminsView.as_view()),
    url(r'^v1/administrators/(?P<user_id>[\w\-]+)$', AdminInfoView.as_view()),
    url(r'^v1/changepwd$', ChangePassword.as_view()),
    url(r'^v1/users$', ListUsersView.as_view()),
    url(r'^v1/currentuser$', CurrentUsersView.as_view()),
    url(r'^v1/users/(?P<user_id>[\w\-]+)$', UserInfoView.as_view()),
    url(r'^v1/users/(?P<user_id>[\w\-]+)/close$', UserTenantClose.as_view()),
    url(r'^v1/users/(?P<user_id>[\w\-]+)/delete$', UserTenantDelete.as_view()),
    url(r'^v1/users/(?P<user_id>[\w\-]+)/changepwd$', ChangeUserPassword.as_view()),
    url(r'^v1/teams$', ListTeamInfo.as_view()),
    url(r'^v1/app_model$', EntAppModelView.as_view()),
    url(r'^v1/teams/resource$', TeamsResourceView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)$', TeamInfo.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions$', ListRegionsView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/certificates$', TeamCertificatesLCView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/certificates/(?P<certificate_id>[\d\-]+)$', TeamCertificatesRUDView.as_view()),
    url(r'^v1/httpdomains', ListEnterpriseAppGatewayHTTPRuleView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/resource', TeamAppsResourceView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/overview', TeamOverviewView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/events/(?P<event_id>[\w\-]+)/logs',
        TeamEventLogView.as_view()),
    # apps
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/apps$', ListAppsView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/apps/', include('openapi.sub_urls.app_url')),

    # list port
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/apps_port$', AppsPortView.as_view()),

    # grctl
    url(r'^v1/grctl/ip$', ReplaceRegionIP.as_view()),

    # 应用部署
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/app-model/deploy$', AppDeployView.as_view()),
    # 创建应用导入记录
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/app-model/import$', AppModelImportEvent.as_view()),
    # 应用包目录查询
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/app-model/import/(?P<event_id>[\w\-]+)/dir$',
        AppTarballDirView.as_view()),
    # 应用包生成本地组件库模版
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/app-model/import/(?P<event_id>[\w\-]+)$',
        AppImportView.as_view()),
    # 获取chart包信息
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/app-model/import/(?P<event_id>[\w\-]+)/chart$',
        AppChartInfo.as_view()),
    # 删除应用及所有资源
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/app/(?P<app_id>[\w\-]+)/delete$',
        DeleteApp.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/app/(?P<app_id>[\w\-]+)/helm_chart$',
        HelmChart.as_view()),
    # 资源监控
    url(r'^v1/monitor/resource_over_view$', ResourceOverview.as_view()),

    # MCP 相关接口
    url(r'^v1/mcp/', include('openapi.mcp.urls')),
]

if os.environ.get("OPENAPI_V2") == "true":
    urlpatterns += [url(r'^v2', include('openapi.v2.urls'))]

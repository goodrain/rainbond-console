# -*- coding: utf-8 -*-
# creater by: barnett
import os

from django.conf.urls import include, url
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from console.utils import perms_route_config as perms
from openapi.auth.authentication import OpenAPIAuthentication
from openapi.auth.permissions import OpenAPIPermissions
from openapi.auth.views import TokenInfoView
from openapi.views.admin_view import AdminInfoView, ListAdminsView
from openapi.views.announcement_view import (AnnouncementView, ListAnnouncementView)
from openapi.views.appstore_view import AppStoreInfoView, ListAppStoresView
from openapi.views.enterprise_view import (EnterpriseInfoView, EnterpriseSourceView, ListEnterpriseInfoView,
                                           EnterpriseConfigView)
from openapi.views.gateway.gateway import ListEnterpriseAppGatewayHTTPRuleView
from openapi.views.oauth import OauthTypeView
from openapi.views.region_view import (ListRegionInfo, RegionInfo, RegionStatusView)
from openapi.views.team_view import (ListRegionsView, ListRegionTeamServicesView, ListTeamInfo, ListTeamUsersInfo,
                                     TeamCertificatesLCView, TeamCertificatesRUDView, TeamInfo, TeamRegionView,
                                     TeamUserInfoView)
from openapi.views.upload_view import UploadView
from openapi.views.user_view import (ChangePassword, ListUsersView, UserInfoView, UserTeamInfoView)

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
    # get user teams
    url(r'^v1/configs$', EnterpriseConfigView.as_view(), name="ent-configs"),
    url(r'^v1/teams$', ListTeamInfo.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)$', TeamInfo.as_view(), perms.TeamInfo),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/certificates$', TeamCertificatesLCView.as_view(), perms.TeamCertificatesLCView),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/certificates/(?P<certificate_id>[\d\-]+)$', TeamCertificatesRUDView.as_view(),
        perms.TeamCertificatesRUDView),
    url(r'^v1/httpdomains', ListEnterpriseAppGatewayHTTPRuleView.as_view()),
    # apps
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/apps', include('openapi.sub_urls.app_url')),
]
if os.environ.get("OPENAPI_V2") == "true":
    urlpatterns += [url(r'^v2', include('openapi.v2.urls'))]

if os.environ.get("OPENAPI_DEBUG") == "true":
    urlpatterns += [
        url(r'^v1/auth-token$', TokenInfoView.as_view()),
        url(r'^v1/regions/(?P<region_id>[\w\-]+)$', RegionInfo.as_view(), name="region_info"),
        url(r'^v1/regions/(?P<region_id>[\w\-]+)/status$', RegionStatusView.as_view()),
        url(r'^v1/teams/(?P<team_id>[\w\-]+)$', TeamInfo.as_view()),
        url(r'^v1/teams/(?P<team_id>[\w\-]+)/users$', ListTeamUsersInfo.as_view()),
        # TODO 修改权限控制
        url(r'^v1/teams/(?P<team_id>[\w\-]+)/users/(?P<user_id>[\w\-]+)$', TeamUserInfoView.as_view(), name="team_user"),
        url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions$', ListRegionsView.as_view()),
        url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/services$', ListRegionTeamServicesView.as_view()),
        url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)$', TeamRegionView.as_view()),
        url(r'^v1/users$', ListUsersView.as_view()),
        url(r'^v1/users/(?P<user_id>[\w\-]+)$', UserInfoView.as_view()),
        # TODO 修改权限控制
        url(r'^v1/users/(?P<user_id>[\w\-]+)/teams$', UserTeamInfoView.as_view()),
        url(r'^v1/user/changepwd$', ChangePassword.as_view()),
        url(r'^v1/administrators$', ListAdminsView.as_view()),
        url(r'^v1/users/(?P<user_id>[\w\-]+)/administrator$', AdminInfoView.as_view()),
        url(r'^v1/enterprises$', ListEnterpriseInfoView.as_view(), name="list_ent_info"),
        url(r'^v1/enterprises/(?P<eid>[\w\-]+)/resource$', EnterpriseSourceView.as_view(), name="ent_info"),
        url(r'^v1/enterprises/(?P<eid>[\w\-]+)$', EnterpriseInfoView.as_view(), name="ent_info"),
        url(r'^v1/appstores$', ListAppStoresView.as_view(), name="list_appstore_infos"),
        url(r'^v1/appstores/(?P<eid>[\w\-]+)$', AppStoreInfoView.as_view(), name="appstore_info"),
        url(r'^v1/announcements$', ListAnnouncementView.as_view()),
        url(r'^v1/announcements/(?P<aid>[\w\-]+)$', AnnouncementView.as_view()),
        url(r'^v1/upload-file$', UploadView.as_view()),
        url(r'^v1/oauth/type$', OauthTypeView.as_view()),
    ]

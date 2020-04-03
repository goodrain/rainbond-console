# -*- coding: utf-8 -*-
# creater by: barnett
from django.conf.urls import url
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from openapi.auth.authentication import OpenAPIAuthentication
from openapi.auth.permissions import OpenAPIPermissions
from openapi.auth.views import TokenInfoView
from openapi.views.admin_view import AdminInfoView
from openapi.views.admin_view import ListAdminsView
from openapi.views.announcement_view import AnnouncementView
from openapi.views.announcement_view import ListAnnouncementView
from openapi.views.apps.apps import AppInfoView
from openapi.views.apps.apps import ListAppsView
from openapi.views.apps.apps import APPOperationsView
from openapi.views.apps.apps import APPHttpDomainView
from openapi.views.apps.market import MarketAppInstallView
from openapi.views.appstore_view import AppStoreInfoView
from openapi.views.appstore_view import ListAppStoresView
# from openapi.views.config_view import BaseConfigView
# from openapi.views.config_view import FeatureConfigView
# from openapi.views.config_view import ListFeatureConfigView
from openapi.views.enterprise_view import EnterpriseInfoView
from openapi.views.enterprise_view import ListEnterpriseInfoView
from openapi.views.gateway.gateway import ListAppGatewayHTTPRuleView
from openapi.views.region_view import ListRegionInfo
from openapi.views.enterprise_view import EnterpriseSourceView

from openapi.views.region_view import RegionInfo
from openapi.views.region_view import RegionStatusView
from openapi.views.team_view import ListRegionsView
from openapi.views.team_view import ListRegionTeamServicesView
from openapi.views.team_view import TeamCertificatesLCView
from openapi.views.team_view import TeamCertificatesRUDView
from openapi.views.team_view import ListTeamInfo
from openapi.views.team_view import ListTeamUsersInfo
from openapi.views.team_view import ListUserRolesView
from openapi.views.team_view import TeamInfo
from openapi.views.team_view import TeamRegionView
from openapi.views.team_view import TeamUserInfoView
from openapi.views.upload_view import UploadView
from openapi.views.user_view import ListUsersView
from openapi.views.user_view import ChangePassword
from openapi.views.user_view import UserInfoView
from openapi.views.user_view import UserTeamInfoView
from openapi.views.oauth import OauthTypeView

schema_view = get_schema_view(
    openapi.Info(
        title="Rainbond Open API",
        default_version='v1',
        description="Rainbond open api",
        terms_of_service="https://www.rainbond.com",
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
    url(r'^v1/auth-token$', TokenInfoView.as_view()),
    url(r'^v1/regions$', ListRegionInfo.as_view(), name="list_regions"),
    url(r'^v1/regions/(?P<region_id>[\w\-]+)$', RegionInfo.as_view(), name="region_info"),
    url(r'^v1/regions/(?P<region_id>[\w\-]+)/status$', RegionStatusView.as_view()),
    url(r'^v1/teams$', ListTeamInfo.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)$', TeamInfo.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/users$', ListTeamUsersInfo.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/users/(?P<user_id>[\w\-]+)$', TeamUserInfoView.as_view(), name="team_user"),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/user-roles', ListUserRolesView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions$', ListRegionsView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/services$',
        ListRegionTeamServicesView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)$', TeamRegionView.as_view()),
    url(r'^v1/users$', ListUsersView.as_view()),
    url(r'^v1/users/(?P<user_id>[\w\-]+)$', UserInfoView.as_view()),
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
    # url(r'^v1/configs/base$', BaseConfigView.as_view()),
    # url(r'^v1/configs/feature$', ListFeatureConfigView.as_view()),
    # url(r'^v1/configs/feature/(?P<key>[\w\-]+)$', FeatureConfigView.as_view()),
    url(r'^v1/upload-file$', UploadView.as_view()),
    url(r'^v1/apps/httpdomain$', APPHttpDomainView.as_view()),
    url(r'^v1/apps$', ListAppsView.as_view()),
    url(r'^v1/apps/(?P<app_id>[\w\-]+)$', AppInfoView.as_view()),
    url(r'^v1/apps/(?P<app_id>[\w\-]+)/httprules$', ListAppGatewayHTTPRuleView.as_view()),
    url(r'^v1/market-install', MarketAppInstallView.as_view()),
    url(r'^v1/oauth/type$', OauthTypeView.as_view()),
    url(r'^v1/apps/(?P<app_id>[\w\-]+)/operations$', APPOperationsView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/certificates$', TeamCertificatesLCView.as_view()),
    url(r'^v1/teams/(?P<team_id>[\w\-]+)/certificates/(?P<certificate_id>[\d\-]+)$', TeamCertificatesRUDView.as_view()),

]

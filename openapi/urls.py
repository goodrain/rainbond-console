# -*- coding: utf-8 -*-
# creater by: barnett
from django.conf.urls import url
from openapi.views.region_view import ListRegionInfo
from openapi.views.region_view import RegionInfo
from openapi.views.team_view import ListTeamInfo, TeamInfo
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from openapi.auth.permissions import OpenAPIPermissions
from openapi.auth.authentication import OpenAPIAuthentication
from openapi.auth.views import TokenInfoView

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
    url(r'^v1/regions$', ListRegionInfo.as_view()),
    url(r'^v1/regions/(?P<region_id>[\w\-]+)$', RegionInfo.as_view()),
    url(r'^v1/teams', ListTeamInfo.as_view()),
    url(r'^v1/teams/(?P<team_name>[\w\-]+)$', TeamInfo.as_view()),
    # url(r'^v1/teams/(?P<team_name>[\w\-]+)/users$', ListTeamUserInfo.as_view()),
    # url(r'^v1/users$', ListUserInfo.as_view()),
    # url(r'^v1/users/(?P<user_id>[\w\-]+)$', UserInfo.as_view()),
    # url(r'^v1/administrators$', ListAdministratorInfo.as_view()),
    # url(r'^v1/users/(?P<user_id>[\w\-]+)/administrator$', UserAdministrator.as_view()),
    # url(r'^v1/users/(?P<user_id>[\w\-]+)/password$', UserPassword.as_view()),
    # url(r'^v1/enterprises$', ListEnterpriseInfo.as_view())
    # url(r'^v1/announcement$', ListAnnouncementView.as_view()),
    # url(r'^v1/announcement/(?P<announcement_id>[\w\-]+)$', AnnouncementView.as_view()),
    # url(r'^v1/labels$', ListLabelsView.as_view()),
    # url(r'^v1/labels/(?P<label_id>[\w\-]+)$', LabelView.as_view()),
    # url(r'^v1/configs/base', BaseConfigView.as_view()),
    # url(r'^v1/configs/feature', FeatureConfigView.as_view()),
]

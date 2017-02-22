from django.conf.urls import patterns, url, include
from django.contrib import admin
from rest_framework.authtoken import views

from openapi.views.cloudservices import *
from openapi.views.domain import *
from openapi.views.services import *
from openapi.views.tenants import *
from openapi.views.token import *
from openapi.views.users import *
from openapi.views.wechat import *
from openapi.views.region import *

urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth', views.obtain_auth_token),
    url(r'^docs/', include('rest_framework_swagger.urls')),
    url(r'^oauth2/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    url(r'^oauth2/access_token$', AccessTokenView.as_view()),

    url(r'^v1/register$', TenantServiceView.as_view()),

    url(r'^v1/user/info$', UserInfoView.as_view()),
    # wechat token
    url(r'^v1/wechat/token', WechatTokenView.as_view()),

    url(r'^v1/services/(?P<service_name>[\w\-]+)/create$', CreateServiceView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/delete$', DeleteServiceView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/start$', StartServiceView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/stop$', StopServiceView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/status$', StatusServiceView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/domain$', DomainController.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/published', PublishedView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/upgrade', UpgradeView.as_view()),

    # share module for region
    url(r'^v1/share/region/price$', RegionPriceQueryView.as_view()),

    url(r'^v2/services/(?P<service_name>[\w\-]+)/install$', CloudServiceInstallView.as_view()),
    url(r'^v2/services/(?P<service_id>[\w\-]+)/update$', UpdateServiceView.as_view()),
    url(r'^v2/services/(?P<service_id>[\w\-]+)/restart$', RestartServiceView.as_view()),
    url(r'^v2/services/(?P<service_id>[\w\-]+)/remove$', RemoveServiceView.as_view()),
    url(r'^v2/services/(?P<service_id>[\w\-]+)/detail$', QueryServiceView.as_view()),
    url(r'^v2/services/(?P<service_id>[\w\-]+)/stop$', StopCloudServiceView.as_view()),
    url(r'^v2/services/(?P<service_id>[\w\-]+)/domain$', CloudServiceDomainView.as_view()),
)

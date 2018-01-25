from django.conf.urls import patterns, url

from marketapi.enter_view import *
from marketapi.views import MarketSSOUserAPIView, MarketSSOUserInitAPIView

urlpatterns = patterns(
    '',
    # user operator
    url(r'^v1/sso-users/(?P<sso_user_id>[\w\-]+)/$', MarketSSOUserAPIView.as_view()),
    url(r'^v1/sso-users/(?P<sso_user_id>[\w\-]+)/init/$', MarketSSOUserInitAPIView.as_view()),

    # enterprise operator
    url(r'^v1/enterprises/bind/$', EnterBindAPIView.as_view()),
    url(r'^v1/enterprises/groupsvcs/$', EnterGroupServiceListAPIView.as_view()),
    url(r'^v1/enterprises/groupsvcs/(?P<group_id>[\w\-]+)$', EnterGroupServiceAPIView.as_view()),
    url(r'^v1/enterprises/groups/(?P<group_id>\d+)/http_services$', EnterAppHttpPortAPIView.as_view()),
    url(r'^v1/enterprises/services/(?P<service_id>[\w\-]+)/domain$', EnterDomainAPIView.as_view()),
    url(r'^v1/enterprises/regions/access_token$', RegionEnterpriseAccessTokenAPIView.as_view()),
    url(r'^v1/enterprises/regions/resources$', RegionEnterResourceAPIView.as_view()),
    url(r'^v1/enterprises/tenants$', EnterTenantsAPIView.as_view())
)

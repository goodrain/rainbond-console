from django.conf.urls import patterns, url, include
from marketapi.views import *

urlpatterns = patterns(
    '',
    # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # url(r'^docs/', include('rest_framework_swagger.urls')),

    # user operator
    url(r'^v1/sso-users/(?P<sso_user_id>[\w\-]+)/$', MarketSSOUserAPIView.as_view()),
    url(r'^v1/sso-users/(?P<sso_user_id>[\w\-]+)/init/$', MarketSSOUserInitAPIView.as_view()),
    url(r'^v1/enterprises/(?P<enterprise_id>[\w\-]+)/bind/$', MarketEnterpriseBindAPIView.as_view()),

    # group app operator
    url(r'^v1/tenants/(?P<tenant_name>[\w\-]+)/groupsvcs/$', MarketGroupServiceListAPIView.as_view()),
    url(r'^v1/tenants/(?P<tenant_name>[\w\-]+)/groupsvcs/(?P<group_id>[\w\-]+)/$', MarketGroupServiceAPIView.as_view()),
    url(r'^v1/tenants/(?P<tenant_name>[\w\-]+)/groupsvcs/(?P<group_id>[\w\-]+)/lifecycle/(?P<action>[\w]+)/$', MarketGroupServiceLifeCycleAPIView.as_view()),

    # app operator
    url(r'^v1/tenants/(?P<tenant_name>[\w\-]+)/services/(?P<service_alias>[\w\-]+)/$', MarketServiceAPIView.as_view()),
    url(r'^v1/tenants/(?P<tenant_name>[\w\-]+)/services/(?P<service_alias>[\w\-]+)/lifecycle/(?P<action>[\w]+)/$', MarketServiceLifeCycleAPIView.as_view()),

    # app monitor operator
    url(r'^v1/tenants/(?P<tenant_name>[\w\-]+)/services/(?P<service_alias>[\w\-]+)/monitors/graph/$', MarketServiceMonitorGraphAPIView.as_view()),
)

from django.conf.urls import patterns, url, include
from rest_framework.authtoken import views
from django.contrib import admin

from openapi.controllers.domain import DomainController
from openapi.controllers.services import CreateServiceView, DeleteServiceView, \
    StartServiceView, StopServiceView, StstusServiceView

urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth', views.obtain_auth_token),
    url(r'^docs/', include('rest_framework_swagger.urls')),

    url(r'^v1/services/(?P<service_name>[\w\-]+)/create', CreateServiceView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/delete', DeleteServiceView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/start', StartServiceView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/stop', StopServiceView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/status', StstusServiceView.as_view()),
    url(r'^v1/services/(?P<service_name>[\w\-]+)/domain', DomainController.as_view()),

)

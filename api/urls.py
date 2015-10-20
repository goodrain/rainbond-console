from django.conf.urls import patterns, url, include
from rest_framework.authtoken import views
from api.views.services import SelectedServiceView, ServiceEnvVarView
from api.views.tenants.services import TenantServiceStaticsView, TenantHibernateView, TenantView, AllTenantView, GitCheckCodeView

urlpatterns = patterns(
    '',
    url(r'^services/(?P<serviceId>[a-z0-9\-]+)$', SelectedServiceView.as_view()),
    url(r'^tenants/services/statics$', TenantServiceStaticsView.as_view()),
    url(r'^tenants/services/hibernate$', TenantHibernateView.as_view()),
    url(r'^tenants/member$', TenantView.as_view()),
    url(r'^tenants/all-members$', AllTenantView.as_view()),
    url(r'^tenants/services/codecheck', GitCheckCodeView.as_view()),
    # url(r'^services/rsync/env$', ServiceEnvVarView.as_view()),
    # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth', views.obtain_auth_token),
    url(r'^docs/', include('rest_framework_swagger.urls')),
)

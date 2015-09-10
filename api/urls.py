from django.conf.urls import patterns, url, include

from api.views.services import SelectedServiceView
from api.views.tenants.services import TenantServiceStaticsView, TenantHibernateView, TenantCloseRestartView, TenantView

urlpatterns = patterns(
    '',
    url(r'^services/(?P<serviceId>[a-z0-9\-]+)$', SelectedServiceView.as_view()),
    url(r'^tenants/services/statics$', TenantServiceStaticsView.as_view()),
    url(r'^tenants/services/hibernate$', TenantHibernateView.as_view()),
    url(r'^tenants/services/close-restart$', TenantCloseRestartView.as_view()),
    url(r'^tenants$', TenantView.as_view()),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^docs/', include('rest_framework_swagger.urls')),
)

from django.conf.urls import patterns, url, include
from rest_framework.authtoken import views
from api.views.services import SelectedServiceView, PublishServiceView, \
    ReceiveServiceView, QueryServiceView, QueryTenantView
from api.views.tenants.services import TenantServiceStaticsView, TenantHibernateView, TenantView, AllTenantView, GitCheckCodeView
from api.views.tenants import move

urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth', views.obtain_auth_token),
    url(r'^docs/', include('rest_framework_swagger.urls')),
    
)

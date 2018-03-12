from django.conf.urls import patterns, url, include
from rest_framework.authtoken import views
from api.views.services import SelectedServiceView, PublishServiceView, \
    ReceiveServiceView, QueryServiceView, QueryTenantView
from api.views.tenants.services import TenantServiceStaticsView, TenantHibernateView, TenantView, AllTenantView, \
    GitCheckCodeView, \
    UpdateServiceExpireTime, ServiceEventUpdate,ServiceEventCodeVersionUpdate, ServiceStopView, SendMessageView,DeleteServiceView,GetDeletedServiceView
from api.views.tenants import move
from api.views.rules import *
from api.views.base import LicenseView

urlpatterns = patterns(
    '',
    url(r'^services/(?P<serviceId>[a-z0-9\-]+)$',
        SelectedServiceView.as_view()),
    url(r'^tenants/services/statics$', TenantServiceStaticsView.as_view()),
    url(r'^tenants/services/hibernate$', TenantHibernateView.as_view()),
    url(r'^tenants/services/publish$', PublishServiceView.as_view()),
    url(r'^tenants/services/receive$', ReceiveServiceView.as_view()),
    url(r'^tenants/services/query$', QueryServiceView.as_view()),
    url(r'^tenants/services/querytenant$', QueryTenantView.as_view()),
    url(r'^tenants/member$', TenantView.as_view()),
    url(r'^tenants/all-members$', AllTenantView.as_view()),
    url(r'^tenants/services/codecheck', GitCheckCodeView.as_view()),
    # url(r'^tenants/(?P<tenantId>[a-z0-9\-]+)/move/stop_prepare$',
    #     move.TenantStopView.as_view()),
    # url(r'^tenants/(?P<tenantId>[a-z0-9\-]+)/move/start$',
    #     move.TenantStartView.as_view()),
    # url(r'^tenants/(?P<tenantId>[a-z0-9\-]+)/move/follow_up$',
    #     move.TenantFollowUpView.as_view()),
    # url(r'^tenants/(?P<tenantId>[a-z0-9\-]+)/move/update$',
    #     move.TenantMoveUpdateView.as_view()),
    # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth', views.obtain_auth_token),
    url(r'^docs/', include('rest_framework_swagger.urls')),
    url(r'^tenants/services/update_resource',
        UpdateServiceExpireTime.as_view()),
    url(r'^rules/(?P<service_region>[\w\-]+)$', RulesController.as_view()),
    # url(r'^rules/(?P<rule_id>[\w\-]+)/instance$', InstanceManager.as_view()),
    url(r'^services/(?P<service_id>[\w\-]+)/info$', ServiceInfo.as_view()),
    url(r'^event/update$', ServiceEventUpdate.as_view()),
    url(r'^event/update-code$', ServiceEventCodeVersionUpdate.as_view()),
    url(r'^tenants/services/close_service', ServiceStopView.as_view()),
    url(r'^tenants/services/send_message', SendMessageView.as_view()),
    url(r'^tenants/services/delete_service', DeleteServiceView.as_view()),
    url(r'^tenants/services/get_deleted_services/(?P<day_num>[0-9]+)$', GetDeletedServiceView.as_view()),
    url(r'^license$', LicenseView.as_view()))

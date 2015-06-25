from django.conf.urls import patterns, url
from www.tests import *
from www.services_view import *
from www.views import ajax

urlpatterns = patterns(
    '',
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/app-deploy/$', ajax.service_actions.AppDeploy.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/perms', ajax.ServiceIdentity.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/invite', ajax.InviteServiceUser.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/manage', ajax.ServiceManage.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/upgrade', ajax.ServiceUpgrade.as_view()),    
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/detail', ajax.ServiceDetail.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/net-disk', ajax.ServiceNetAndDisk.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/log', ajax.ServiceLog.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/relation', ajax.ServiceRelation.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/invite', ajax.InviteTenantUser.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/perms', ajax.TenantIdentity.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/serviceinfo', ajax.AllServiceInfo.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/rechargelist', ajax.AccountRecharging.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/consumelist', ajax.AccountQuery.as_view()),    
    url(r'^(?P<tenantName>[\w\-]+)/code_repos', ajax.CodeAction.as_view()),    
)

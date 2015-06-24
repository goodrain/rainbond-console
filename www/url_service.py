from django.conf.urls import patterns, url
from www.tests import *
from www.services_view import *
from www.charging_view import *
from www.views.service import TeamInfo
from django.contrib.auth.decorators import login_required
from www import alipay_view


urlpatterns = patterns(
    '',
    url(r'^$', login_required(TenantServiceAll.as_view())),

    url(r'^app-create/$', login_required(ServiceAppCreate.as_view())),

    url(r'^(?P<serviceAlias>[\w\-]+)/app-deploy/$', login_required(ServiceAppDeploy.as_view())),

    url(r'^service/$', login_required(ServiceMarket.as_view())),
    url(r'^service-deploy/$', login_required(ServiceMarketDeploy.as_view())),

    url(r'^team/$', TeamInfo.as_view()),
    url(r'^gitlab/$', login_required(GitLabManager.as_view())),

    url(r'^(?P<serviceAlias>[\w\-]+)/detail/$', login_required(TenantService.as_view())),
    url(r'^(?P<serviceAlias>[\w\-]+)/domain/$', login_required(ServiceDomainManager.as_view())),
    
    url(r'^recharge/$', login_required(Recharging.as_view())),
    url(r'^consume/$', login_required(Account.as_view())),
    url(r'^bill/$', login_required(AccountBill.as_view())),
    
    url(r'^recharge/alipay', login_required(alipay_view.submit)),
    url(r'^recharge/alipay-return', alipay_view.return_url),
    url(r'^recharge/alipay-notify', alipay_view.notify_url),
    
    url(r'^githup/$', login_required(ServiceGitHub.as_view())),
)

from django.conf.urls import patterns, url

from www.services_group_view import *
from www.compose_service_view import ComposeServiceDeploy, ComposeCreateStep2, ComposeCreateStep3
from www.create_services_view import CreateServiceEntranceView
from www.image_service_view import ImageServiceDeploy, ImageParamsViews
from www.services_view import *
from www.app_services_view import *
from www.back_services_view import *
from www.charging_view import *
from www.views.ajax import UpdateGroupView
from www.views.ajax.service_group import AddGroupView, DeleteGroupView, UpdateServiceGroupView
from www.views.batchrenew import BatchRenewView
from www.views.service import TeamInfo
from django.contrib.auth.decorators import login_required
from www import alipay_view
from django.views.decorators.csrf import csrf_exempt
from www.views.servicepublish import PublishServiceView, PublishServiceRelationView, PublishServiceDetailView
from www.views.serviceshare import *
from www.views.consume import *
from  www.views.servicemonitor import *
from www.views.third_app import *
from www.views.servicegroup import *
from www.group_services_view import *

urlpatterns = patterns(
    '',
    url(r'^/?$', login_required(TenantServiceAll.as_view())),
    
    url(r'^/service-entrance/$', login_required(CreateServiceEntranceView.as_view())),
    
    url(r'^/app-create/$', login_required(AppCreateView.as_view())),
    
    url(r'^/(?P<serviceAlias>[\w\-]+)/app-waiting/$', login_required(AppWaitingCodeView.as_view())),
    
    url(r'^/(?P<serviceAlias>[\w\-]+)/app-setting/$', login_required(AppSettingsView.as_view())),
    
    url(r'^/(?P<serviceAlias>[\w\-]+)/app-language/$', login_required(AppLanguageCodeView.as_view())),

    # url(r'^/(?P<serviceAlias>[\w\-]+)/setup/extra/?$', ServiceDeployExtraView.as_view()),
    
    url(r'^/(?P<serviceAlias>[\w\-]+)/deploy/setting/?$', ServiceDeploySettingView.as_view()),
    
    url(r'^/service/$', login_required(ServiceMarket.as_view())),
    
    url(r'^/service-deploy/$', login_required(ServiceMarketDeploy.as_view())),

    url(r'^/group-deploy/$', login_required(GroupServiceDeployView.as_view())),

    url(r'^/team/$', TeamInfo.as_view()),
    
    url(r'^/(?P<serviceAlias>[\w\-]+)/detail/?$', login_required(TenantService.as_view())),
    
    url(r'^/(?P<serviceAlias>[\w\-]+)/latest-log/$', login_required(ServiceLatestLog.as_view())),
    url(r'^/(?P<serviceAlias>[\w\-]+)/history-log/$', login_required(ServiceHistoryLog.as_view())),
    url(r'^/(?P<serviceAlias>[\w\-]+)/docker/$', login_required(ServiceDockerContainer.as_view())),
    
    url(r'^/recharge/$', login_required(Recharging.as_view())),
    url(r'^/service-cost/$', login_required(RegionsServiceCostView.as_view())),
    url(r'^/batch-renew/$', login_required(ServiceBatchRenewView.as_view())),
    url(r'^/service-renew/$', login_required(BatchRenewView.as_view())),
    url(r'^/consume/$', login_required(Account.as_view())),
    url(r'^/bill/$', login_required(AccountBill.as_view())),
    url(r'^/paymodel/$', login_required(PayModelView.as_view())),
    url(r'^/license/$', login_required(AssistantView.as_view())),
    
    url(r'^/recharge/alipay$', csrf_exempt(login_required(alipay_view.submit))),
    url(r'^/recharge/alipay-return$', alipay_view.return_url),
    url(r'^/recharge/alipay-notify$', csrf_exempt(alipay_view.notify_url)),
    
    # new publish service
    url(r'^/(?P<serviceAlias>[\w\-]+)/publish/$', PublishServiceDetailView.as_view()),
    url(r'^/(?P<serviceAlias>[\w\-]+)/publish/relation/?$', PublishServiceRelationView.as_view()),
    url(r'^/(?P<serviceAlias>[\w\-]+)/publish/extra/?$', PublishServiceView.as_view()),
    
    # new share service
    url(r'^/(?P<serviceAlias>[\w\-]+)/share/step1$', ShareServiceStep1View.as_view()),
    url(r'^/(?P<serviceAlias>[\w\-]+)/share/step2$', ShareServiceStep2View.as_view()),
    url(r'^/(?P<serviceAlias>[\w\-]+)/share/step3$', ShareServiceStep3View.as_view()),
    url(r'^/(?P<serviceAlias>[\w\-]+)/share/step4$', ShareServiceStep4View.as_view()),
    url(r'^/(?P<serviceAlias>[\w\-]+)/share/step5$', ShareServiceStep5View.as_view()),
    url(r'^/(?P<serviceAlias>[\w\-]+)/share/package$', ShareServicePackageView.as_view()),
    url(r'^/(?P<serviceAlias>[\w\-]+)/share/images$', ShareServiceImageView.as_view()),

    # new service group share
    url(r'^/(?P<groupId>[\w\-]+)/preview/$', ServiceGroupSharePreview.as_view()),
    url(r'^/(?P<groupId>[\w\-]+)/first/$', ServiceGroupShareOneView.as_view()),
    url(r'^/(?P<groupId>[\w\-]+)/(?P<share_pk>[\w\-]+)/second/$', ServiceGroupShareTwoView.as_view()),
    url(r'^/(?P<groupId>[\w\-]+)/(?P<share_pk>[\w\-]+)/third/$', ServiceGroupShareThreeView.as_view()),
    url(r'^/(?P<groupId>[\w\-]+)/(?P<share_pk>[\w\-]+)/fourth/$', ServiceGroupShareFourView.as_view()),
    url(r'^/(?P<groupId>[\w\-]+)/(?P<share_pk>[\w\-]+)/five/$', ServiceGroupShareToMarketView.as_view()),

    # consume details
    url(r'^/cost-detail/$', login_required(ConsumeCostDetail.as_view())),
    
    url(r'^/myservice/$', login_required(MyTenantService.as_view())),
    
    # image_service
    url(r'^/image-create/$', login_required(ImageServiceDeploy.as_view())),
    url(r'^/image-params/$', login_required(ImageParamsViews.as_view())),
    # docker-compose
    url(r'^/compose-create/$', login_required(ComposeServiceDeploy.as_view())),
    url(r'^/compose-step2/$', login_required(ComposeCreateStep2.as_view())),
    url(r'^/compose-step3/$', login_required(ComposeCreateStep3.as_view())),
    # new monitor service source
    # url(r'^/(?P<serviceAlias>[\w\-]+)/resource/monitor$', SourcesMonitorServicelView.as_view()),
    # url(r'^/(?P<serviceAlias>[\w\-]+)/resource/alert$', SourcesAlertServicelView.as_view()),
    
    url(r'/third_app/(?P<app_type>[\w\-]+)/create/', login_required(CreateThirdAppView.as_view())),
    url(r'/(?P<app_bucket>[\w\-]+)/third_show$', login_required(ThirdAppView.as_view())),
    url(r'/third_app/list', login_required(ThirdAppListView.as_view())),
    url(r'/(?P<app_bucket>[\w\-]+)/orders$', ThirdAppOrdersListView.as_view()),
    url(r'/(?P<app_bucket>[\w\-]+)/orders_data$', ThirdAppOrdersListDataView.as_view()),
    # group service install
    url(r'^/group-deploy/(?P<groupId>[\w\-]+)/step1/$', login_required(GroupServiceDeployStep1.as_view())),
    url(r'^/group-deploy/(?P<groupId>[\w\-]+)/step2/$', login_required(GroupServiceDeployStep2.as_view())),
    url(r'^/group-deploy/(?P<groupId>[\w\-]+)/step3/$', login_required(GroupServiceDeployStep3.as_view())),
)


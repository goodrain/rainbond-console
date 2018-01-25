# -*- coding: utf8 -*-
from django.conf.urls import patterns, url

from www.views import ajax
from www.views.ajax import UpdateGroupView, BatchActionView
from www.views.ajax.announcement import AnnouncementInfoView
from www.views.ajax.event import *
from www.views.ajax.market_plugin import TenantPluginInstallView, TenantPluginShareView
from www.views.ajax.monitor import QueryMonitorView, QueryRangeMonitorView
from www.views.ajax.plugin import PluginEventLogView, PluginVersionInfoView, PluginStatusView, TenantPluginStatusView,UpdatePluginInfoView, \
    ConfigPluginManageView, PluginManageView, CreatePluginVersionView, ConfigPreviewView, PluginBaseInfoView
from www.views.ajax.price_detail import PriceDetailView
from www.views.ajax.probe import ServiceProbeManager, ServiceProbeInfoUpdateManager, ServiceProbeUsedUpdateManager
from www.views.ajax.service_actions import DockerLogInstanceView
from www.views.ajax.service_fee import *
from www.views.ajax.service_group import AddGroupView, DeleteGroupView, UpdateServiceGroupView
from www.views.ajax.service_market import BatchDownloadMarketAppGroupTempalteView
from www.views.ajax.service_info import BasicInfoEditView
from www.views.ajax.service_labels import ServiceLabelsView, ServiceLabelsManageView
from www.views.ajax.service_log import *
from www.views.ajax.service_rule import *
from www.views.ajax.third_app import *
from www.views.ajax.services import *
from www.views.ajax.enterprise import MarketEnterpriseAccessTokenBindView
from www.views.service import CreateServiceDepInfo
from www.views.ajax.vol_sync import VolSyncApiView, TenantVolsView, TenantDepVolsView, DepVolSyncApiView
from www.views.ajax.code_actions import UserGoodrainGitLabRegisterView
from www.views.ajax.service_plugin import PluginServiceRelation, PluginServiceComplexAttr, PluginServiceSwitch
from www.views.ajax.admin import *
from www.views.ajax.multi_protocol import MultiProtocolsView

from django.views.decorators.csrf import csrf_exempt

urlpatterns = patterns(
    '',
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/appdetails/$', ServiceDetailView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/appinfo/$', AppServiceInfo.as_view()),
    # url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/hisotry_logs/$', ServiceHistoryLog.as_view()),
    # url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/latest_logs/$', ServiceLatestLog.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/app-deploy/$',
        ajax.service_actions.AppDeploy.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/overview$', ServiceOverView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/apps$', ServiceListView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/teams$', ServiceTeamView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/recharge$', ServiceRechargeView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/costs$', ServiceCostView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/batch_renewal$', ServiceBatchRenewalView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/recharges$', SerivceAccountRechargesView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/deductions$', ServiceDeductionsView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/perms',
        ajax.ServiceIdentity.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/invite',
        ajax.InviteServiceUser.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/manage',
        ajax.ServiceManage.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/upgrade',
        ajax.ServiceUpgrade.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/detail',
        ajax.ServiceDetail.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/net-disk',
        ajax.ServiceNetAndDisk.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/log$',
        ajax.ServiceLog.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/relation',
        ajax.ServiceRelation.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/is_midrain',
        ajax.UseMidRain.as_view()),
    # url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/l7info',
    #     ajax.L7ServiceSet.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/check',
        ajax.ServiceCheck.as_view()),
    # url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/mapping-port',
    #     ajax.ServiceMappingPort.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/domain$',
        ajax.ServiceDomainManager.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/certificate',
        ajax.DomainCertificationManager.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/envvar',
        ajax.ServiceEnvVarManager.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/graph',
        ajax.ServiceGraph.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/branch', ajax.ServiceBranch.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/ports/(?P<port>\d+)', ajax.ServicePort.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/custom-env', ajax.ServiceEnv.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/custom-port', ajax.ServiceNewPort.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/mnt', ajax.ServiceMnt.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/dep-mnts', ServiceDepMnt.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/docker', ajax.ServiceDockerContainer.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/invite', ajax.InviteTenantUser.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/perms', ajax.TenantIdentity.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/serviceinfo',
        ajax.AllServiceInfo.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/tenant-disk',
        ajax.AllTenantsUsedResource.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/rechargelist',
        ajax.AccountRecharging.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/consumelist', ajax.AccountQuery.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/paymodel', ajax.PayModelInfo.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/code_repos', ajax.CodeAction.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/remote/market',
        ajax.RemoteServiceMarketAjax.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/logtype/services',
        ajax.ServiceLogTypeView.as_view()),
    url(r'form_valid', ajax.FormValidView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/volume',
        ajax.ServiceVolumeView.as_view()),
    # url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/service-mnt-share-type',
    #     ajax.MntShareTypeView.as_view()),
    # url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/container-stats',
    #     ajax.ContainerStatsView.as_view()),
    # url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/resource/monitor',
    #     ajax.ServiceMonitorQuery.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/topological/(?P<group_id>\d+)',
        ajax.TopologicalGraphView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/topological',
        ajax.TopologicalServiceView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<group_id>\d+)/outer-service',
        ajax.TopologicalInternetView.as_view()),
    # service group
    url(r'^(?P<tenantName>[\w\-]+)/group/add$', AddGroupView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/group/update$', UpdateGroupView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/group/delete$', DeleteGroupView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/group/change-group$',
        UpdateServiceGroupView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/batch-action$', BatchActionView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/change-service-name',
        ajax.ServiceNameChangeView.as_view()),

    # service rule
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/rule$',
        ServiceRuleManage.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/rule/update$',
        ServiceRuleUpdate.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/rule/delete$',
        ServiceRuleDelete.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/rule/status$',
        ServiceRuleUpdateStatus.as_view()),
    # service log
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/match-log$',
        ServiceLogMatch.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/match-log/check$',
        ServiceLogMatchCheck.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/match-log/delete$',
        ServiceLogMatchDelete.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/create/dep-info',
        CreateServiceDepInfo.as_view()),
    url(r'^region/price-info', PriceDetailView.as_view()),

    # third apps manager
    url(r'^(?P<tenantName>[\w\-]+)/third_app/(?P<app_type>[\w\-]+)/create$',
        CreateAppView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/updateName$',
        UpdateAppView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/domain/add$',
        AppDomainView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/domain/delete$',
        AppDomainDeleteView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/operator/add',
        AppOperatorView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/operator/delete',
        AppOperatorDeleteView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/traffic/add',
        CDNTrafficRecordView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/open',
        OpenThirdAppView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/close',
        CloseThirdAppView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/delete',
        DeleteThirdAppView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/purge',
        PurgeCDNAppView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<app_id>[\w\-]+)/cdn_source',
        CDNSourceView.as_view()),
    # service fee
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/memory-pay-method$',
        MemoryPayMethodView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/disk-pay-method$',
        DiskPayMethodView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/service-extend$',
        ExtendServiceView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/postpone$',
        PrePaidPostponeView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/pay-money',
        PayPrepaidMoney.as_view()),
    # consume center
    url(r'^(?P<tenantName>[\w\-]+)/regionServiceList',
        ajax.RegionServiceConsumeView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/serviceCostDetail',
        ajax.RegionServiceDetailConsumeView.as_view()),

    url(r'^(?P<tenantName>[\w\-]+)/groupServices',
        ajax.GroupServicesView.as_view()),
    # multi protocols support
    url(r'^(?P<tenantName>[\w\-]+)/protocols', MultiProtocolsView.as_view()),
    # event
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/events$', EventManager.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/event/(?P<event_id>[\w\-]+)/log$',
        EventLogManager.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/log_instance$', DockerLogInstanceView.as_view()),
    # basic info edit
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/service-info-edit', BasicInfoEditView.as_view()),
    # probe
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/probe$',
        ServiceProbeManager.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/probe/(?P<probe_id>[\w\-]+)$',
        ServiceProbeInfoUpdateManager.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/probe/(?P<probe_id>[\w\-]+)/update_used$',
        ServiceProbeUsedUpdateManager.as_view()),

    # announcement
    url(r'^(?P<tenantName>[\w\-]+)/announcement', AnnouncementInfoView.as_view()),
    # label
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/service-labels$', ServiceLabelsView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/service-labels/delete$',
        ServiceLabelsManageView.as_view()),

    # vol sync
    url(r'^vol-sync$', VolSyncApiView.as_view()),
    url(r'^vols$', TenantVolsView.as_view()),
    url(r'^dep-mnt$', DepVolSyncApiView.as_view()),
    url(r'^dep-vols$', TenantDepVolsView.as_view()),


    url(r'^(?P<tenantName>[\w\-]+)/sync-market-apps$', BatchDownloadMarketAppGroupTempalteView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/git-register$', UserGoodrainGitLabRegisterView.as_view()),

    # plugin action url
    url(r'^(?P<tenantName>[\w\-]+)/plugin/(?P<plugin_id>[\w\-]+)/base-info', PluginBaseInfoView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/plugin/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/event-log',
        PluginEventLogView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/plugin/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/update',
        UpdatePluginInfoView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/plugin/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/config$',
        ConfigPluginManageView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/plugin/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/manage',
        PluginManageView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/plugin/(?P<plugin_id>[\w\-]+)/new-version',
        CreatePluginVersionView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/plugin/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/status',
        PluginStatusView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/plugin/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/config/preview',
        ConfigPreviewView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/plugin/(?P<plugin_id>[\w\-]+)/build-history', PluginVersionInfoView.as_view()),

    url(r'^(?P<tenantName>[\w\-]+)/plugin/status', TenantPluginStatusView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/plugin/install', TenantPluginInstallView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/plugin/share', csrf_exempt(TenantPluginShareView.as_view())),

    # service with plugin
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/plugin/relation$', PluginServiceRelation.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/plugin/is_switch$', PluginServiceSwitch.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/plugin/attrs$', PluginServiceComplexAttr.as_view()),

    # monitor
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/query_range$', QueryRangeMonitorView.as_view()),
    url(r'^(?P<tenantName>[\w\-]+)/(?P<serviceAlias>[\w\-]+)/query$', QueryMonitorView.as_view()),
    # enterprise
    url(r'^enterprises/active$', MarketEnterpriseAccessTokenBindView.as_view()),

    # admin query
    url(r'^admin/users/info$', UsersDetailView.as_view()),
    url(r'^admin/tenants/info$', TenantsDetailView.as_view()),
    url(r'^admin/enters/info$', EntersDetailView.as_view()),
)

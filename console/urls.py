# -*- coding: utf8 -*-

from django.conf.urls import url

import console.utils.perms_route_config as perms
from console.captcha.captcha_code import CaptchaView
from console.views import app_upgrade
from console.views.adaptor import Appstore, Appstores, AppstoreCharts, AppstoreChart, HelmRegionInstall
from console.views.api_gateway import AppApiGatewayView, AppApiGatewayConvertView
from console.views.app_autoscaler import (AppAutoscalerView, AppScalingRecords, ListAppAutoscalerView)
from console.views.app_config.app_dependency import (AppDependencyManageView, AppDependencyView, AppNotDependencyView,
                                                     AppDependencyReverseView, AppDependencyViewList)
from console.views.app_config.app_domain import (
    AppServiceDomainQueryView, AppServiceTcpDomainQueryView, DomainQueryView, DomainView, GatewayCustomConfigurationView,
    GetPortView, GetSeniorUrlView, HttpStrategyView, SecondLevelDomainView, ServiceDomainView, ServiceTcpDomainQueryView,
    ServiceTcpDomainView, TenantCertificateManageView, TenantCertificateView, GatewayRouteBatch, GatewayRoute, TenantService,
    VirtualMachineImageView, CalibrationCertificate)
from console.views.app_config.app_env import (AppBuildEnvView, AppEnvManageView, AppEnvView)
from console.views.app_config.app_extend import AppExtendView
from console.views.app_config.app_label import (AppLabelAvailableView, AppLabelView)
from console.views.app_config.app_mnt import AppMntManageView, AppMntView
from console.views.app_config.app_port import (AppPortManageView, AppPortView, AppTcpOuterManageView, TopologicalPortView)
from console.views.app_config.app_probe import AppProbeView
from console.views.app_config.app_volume import (AppVolumeManageView, AppVolumeOptionsView, AppVolumeView)
from console.views.app_config.graph import (ComponentExchangeGraphsView, ComponentGraphListView, ComponentGraphView,
                                            ComponentInternalGraphsView)
from console.views.app_config.service_monitor import (ComponentMetricsView, ComponentServiceMonitorEditView,
                                                      ComponentServiceMonitorView)
from console.views.app_config.app_log import ComponentLogView
from console.views.app_config_group import (AppConfigGroupView, ListAppConfigGroupView)
from console.views.app_create.app_build import AppBuild, ComposeBuildView, CodeBuildLangVersionView
from console.views.app_create.app_check import (AppCheck, AppCheckUpdate, GetCheckUUID, LangUpdate)
from console.views.app_create.docker_compose import (ComposeCheckUpdate, ComposeCheckView, ComposeContentView,
                                                     ComposeDeleteView, ComposeServicesView, DockerComposeCreateView,
                                                     GetComposeCheckUUID)
from console.views.app_create.docker_run import DockerRunCreateView
from console.views.app_create.image_repositories import TenantImageRepositories, TenantImageTags
from console.views.app_create.multi_app import (MultiAppCheckView, MultiAppCreateView)
from console.views.app_create.source_code import (AppCompileEnvView, SourceCodeCreateView, UploadRecordLastView,
                                                  PackageUploadRecordView, PackageCreateView)
from console.views.app_create.source_outer import (ThirdPartyAppPodsView, ThirdPartyHealthzView, ThirdPartyServiceApiView,
                                                   ThirdPartyServiceCreateView, ThirdPartyUpdateSecretKeyView)
from console.views.app_create.vm_run import VMRunCreateView
from console.views.app_event import (AppEventLogView, AppEventsLogView, AppEventsView, AppEventView, AppHistoryLogView,
                                     AppLogInstanceView, AppLogView)
from console.views.app_manage import (AgainDelete, BatchActionView, BatchDelete, ChangeServiceNameView, ChangeServiceTypeView,
                                      ChangeServiceUpgradeView, DeleteAppView, DeployAppView, HorizontalExtendAppView,
                                      MarketServiceUpgradeView, ReStartAppView, RollBackAppView, StartAppView, StopAppView,
                                      TeamAppsCloseView, UpgradeAppView, VerticalExtendAppView, PackageToolView, PauseAppView,
                                      UNPauseAppView, TarImageView, AppsPorConsoletView, ScalingAppView)
from console.views.app_market import BindableMarketsView
from console.views.app_monitor import (AppMonitorQueryRangeView, AppMonitorQueryView, AppResourceQueryView,
                                       AppTraceView,
                                       BatchAppMonitorQueryView, MonitorQueryOverConsoleView, MonitorQueryView)
from console.views.app_overview import (AppAnalyzePluginView, AppBriefView, AppDetailView, AppGroupView,
                                        AppGroupVisitView,
                                        AppKeywordView, AppPluginsBriefView, AppStatusView, AppVisitView,
                                        BuildSourceinfo,
                                        ImageAppView, ListAppPodsView, JobStrategy, ManageFile)
from console.views.backup_data import (BackupDataCView, BackupDateDownload, BackupRecoverCView, BackupUploadCView)
from console.views.center_pool.app_export import CenterAppExportView
from console.views.center_pool.app_import import (CenterAppImportView, CenterAppTarballDirView, EnterpriseAppImportInitView)
from console.views.center_pool.apps import (AppTagCDView, AppVersionUDView, CenterAppCLView, CenterAppUDView, CenterAppView,
                                            LocalComponentLibraryConfigCheck, TagCLView, TagUDView, CenterPluginAppView,
                                            CmdInstallAppView)
from console.views.center_pool.groupapp_backup import (AllTeamGroupAppsBackupView, GroupAppsBackupExportView,
                                                       GroupAppsBackupImportView, GroupAppsBackupStatusView,
                                                       GroupAppsBackupView, TeamGroupAppsBackupView)
from console.views.center_pool.groupapp_copy import GroupAppsCopyView
from console.views.center_pool.groupapp_migration import (GroupAppsMigrateView, GroupAppsView, MigrateRecordView)
from console.views.code_repo import ServiceCodeBranch
from console.views.custom_configs import CustomConfigsCLView, CustomConfigsUserCLView
from console.views.enterprise import (MyEventsView, ServiceAlarm, GetNodes, GetNode, NodeAction, NodeLabelsOperate,
                                      NodeTaintOperate, RainbondComponents, ContainerDisk, EnterpriseMenuManage,
                                      EnterpriseRegionGatewayBatch, EnterpriseTeamNames, EnterpriseRegionLangVersion)
from console.views.enterprise import (EnterpriseRegionNamespace, EnterpriseNamespaceResource, EnterpriseConvertResource,
                                      RbdPods, RbdPodLog, RbdComponentLogs, Goodrainlog, Downlodlog, RbdLogFiles, ShellPod)
from console.views.enterprise import (
    EnterpriseAppComponentsLView, EnterpriseAppOverView, EnterpriseAppsLView, EnterpriseMonitor, EnterpriseMyTeams,
    EnterpriseOverview, EnterpriseRegionDashboard, EnterpriseRegionsLCView, EnterpriseRegionsRUDView,
    EnterpriseRegionTenantLimitView, EnterpriseRegionTenantRUDView, EnterpriseRUDView, Enterprises, EnterpriseTeamOverView,
    EnterpriseTeams, EnterpriseUserTeamRoleView, EnterpriseUserTeams, HelmTokenView, HelmAddReginInfo, HelmInstallStatus, EnterpriseInfoFileView)
from console.views.enterprise_active import (BindMarketEnterpriseAccessTokenView, BindMarketEnterpriseOptimizAccessTokenView)
from console.views.enterprise_config import (EnterpriseAppStoreImageHubView, EnterpriseObjectStorageView,
                                             EnterpriseVisualMonitorView, EnterpriseAlertsView, EnterpriseConfigView)
from console.views.errlog import ErrLogView
from console.views.file_upload import ConsoleUploadFileView
from console.views.group import (
    AppGovernanceModeView, AppKubernetesServiceView, ApplicationStatusView, GroupStatusView, TenantGroupCommonOperationView,
    TenantGroupOperationView, TenantGroupView, ApplicationInstallView, ApplicationPodView, ApplicationHelmAppComponentView,
    ApplicationParseServicesView, ApplicationReleasesView, ApplicationIngressesView, TenantAppUpgradableNumView,
    AppGovernanceModeCheckView, ApplicationVolumesView, AppGovernanceModeCRView, TenantGroupHandleView, AppComponentNameView)
from console.views.helm_app import HelmAppView, HelmRepo, HelmCenterApp, HelmChart, CommandInstallHelm, HelmList, \
    HelmRepoAdd, UploadHelmChart, UploadHelmChartValueResource, UploadHelmChartValue
from console.views.jwt_token_view import JWTTokenView
from console.views.license import LicenseLView
from console.views.k8s_attribute import ComponentK8sAttributeView, ComponentK8sAttributeListView
from console.views.k8s_resource import AppK8sResourceListView, AppK8ResourceView
from console.views.login_event import LoginEventView
from console.views.logos import ConfigRUDView, InitPerms, PhpConfigView, ConfigOSSView, UserSourceView
from console.views.message import UserMessageView
from console.views.oauth import (EnterpriseOauthService, OauthConfig, OAuthGitCodeDetection, OAuthGitUserRepositories,
                                 OAuthGitUserRepository, OAuthGitUserRepositoryBranches, OAuthServerAuthorize,
                                 OAuthServerUserAuthorize, OauthService, OauthServiceInfo, OAuthServiceRedirect,
                                 OauthType,
                                 OAuthUserInfo, UserOAuthLink, OauthUserLogoutView, OverScore)
from console.views.operation_log import OperationLogView, TeamOperationLogView, AppOperationLogView
from console.views.perms import (PermsInfoLView, TeamRolePermsRUDView, TeamRolesLCView, TeamRolesPermsLView, TeamRolesRUDView,
                                 TeamUserPermsLView, TeamUserRolesRUDView, TeamUsersRolesLView)
from console.views.plugin.plugin_config import (ConfigPluginManageView, ConfigPreviewView)
from console.views.plugin.plugin_create import (DefaultPluginCreateView, PluginCreateView)
from console.views.plugin.plugin_info import (AllPluginBaseInfoView, AllPluginVersionInfoView, PluginBaseInfoView,
                                              PluginEventLogView, PluginUsedServiceView, PluginVersionInfoView)
from console.views.plugin.plugin_manage import (CreatePluginVersionView, PluginBuildStatusView, PluginBuildView)
from console.views.plugin.plugin_market import (InstallableInteralPluginsView, InstallMarketPlugin, InternalMarketPluginsView,
                                                MarketPluginsView, SyncMarketPluginsView, SyncMarketPluginTemplatesView,
                                                UninstallPluginTemplateView)
from console.views.plugin.plugin_share import (PluginShareCompletionView, PluginShareEventsView, PluginShareEventView,
                                               PluginShareInfoView, PluginShareRecordView)
from console.views.plugin.service_plugin import (ServicePluginConfigView, ServicePluginInstallView, ServicePluginOperationView,
                                                 ServicePluginsView)
from console.views.pod import AppPodsView
from console.views.protocols import RegionProtocolView
from console.views.proxy import ProxyPassView, ProxySSEView
from console.views.public_areas import (AllServiceInfo, GroupServiceView, ServiceEventsView, ServiceGroupView,
                                        TeamAppSortViewView, TeamOverView, TeamServiceOverViewView, TenantServiceEnvsView,
                                        GroupOperatorManagedView, AccessTokenView, TeamArchView, TeamAppNamesView)
from console.views.rbd_ability import RainbondAbilityRUDView, RainbondAbilityLView
from console.views.rbd_plugin import RainbondPluginLView, RainbondOfficialPluginLView, RainbondPluginStaticView, RainbondPluginBackendView, RainbondPluginStatusView
from console.views.region import (GetRegionFeature, GetRegionPublicKeyView, MavenSettingRUDView, MavenSettingView,
                                  OpenRegionView, QyeryRegionView, RegQuyView, RegUnopenView)
from console.views.registry import HubRegistryView, HubRegistryImageView
from console.views.rke2 import ClusterRKE, ClusterRKENode, ClusterNodeIP, ClusterRKEInstallRB, \
    ClusterRKERBStatus, ClusterRKERBEvent, ClusterRKEUNInstallInstallRB, InstallRKECluster, RKERegionConfig
from console.views.role_prems import TeamAddUserView
from console.views.service_docker import DockerContainerView
from console.views.service_share import ServiceShareRecordView, ShareRecordView, ServiceGroupSharedApps, \
    ServiceShareInfoView, ServiceShareDeleteView, ServiceShareEventList, ServiceShareCompleteView, \
    ServiceShareEventPost, ServiceShareRecordInfoView, ServicePluginShareEventPost, AppMarketAppModelVersionsRView, \
    AppMarketOrgModelLView, AppMarketAppModelVersionsLView, AppMarketAppModelLView, AppMarketCLView, AppMarketRUDView, \
    AppMarketBatchCView
from console.views.service_version import AppVersionsView, AppVersionManageView
from console.views.services_toplogical import TopologicalGraphView, GroupServiceDetView, TopologicalInternetView
from console.views.storage_statistics import StorageStatistics
from console.views.task_guidance import BaseGuidance
from console.views.team import UserFuzSerView, TeamUserDetaislView, TeamCheckResourceName, TeamSortServiceQueryView, \
    TeamCheckKubernetesServiceName, TeamRegistryAuthLView, TeamRegistryAuthRUDView, AddTeamView, TeamUserView, \
    NotJoinTeamUserView, UserDelView, TeamNameModView, TeamSortDomainQueryView, TeamDelView, TeamExitView, \
    TeamRegionInitView, ApplicantsView, RegisterStatusView, MonitorAlarmStatusView, EnterpriseInfoView, \
    InitDefaultInfoView, AdminAddUserView, CertificateView, TeamUserCanJoin, TeamsPermissionCreateApp, JoinTeamView, \
    UserApplyStatusView
from console.views.upgrade import UpgradeView, UpgradeVersionLView, UpgradeVersionRView, UpgradeVersionImagesView
from console.views.user import CheckSourceView, UserLogoutView, UserPemTraView, AdministratorJoinTeamView, \
    EnterPriseUsersCLView, EnterPriseUsersUDView, AdminUserView, AdminUserLCView, \
    AdminRolesView
from console.views.user_accesstoken import UserAccessTokenCLView, UserAccessTokenRUDView
from console.views.user_operation import TenantServiceView, SendResetEmail, PasswordResetBegin, ChangeLoginPassword, \
    UserDetailsView, UserFavoriteLCView, UserFavoriteUDView, UserInviteView, UserInviteJoinView
from console.views.webhook import WebHooksDeploy, ImageWebHooksDeploy, CustomWebHooksDeploy, GetWebHooksUrl, \
    ImageWebHooksTrigger, WebHooksStatus, UpdateSecretKey
from console.views.yaml_resource import YamlResourceName, YamlResourceDetailed
from console.views.team_overview import UserTeamDetailsView
from console.views.sms_config import SMSConfigView
from console.views.sms_verification import SMSVerificationView
from console.views.user_operation import RegisterByPhoneView, LoginByPhoneView

urlpatterns = [
    # 升级
    url(r'^update$', UpgradeView.as_view()),
    url(r'^update/regions/(?P<region_name>[\w\-]+)/status$', UpgradeView.as_view()),
    url(r'^update/versions$', UpgradeVersionLView.as_view()),
    url(r'^update/versions/(?P<version>[\w\-.]+)$', UpgradeVersionRView.as_view()),
    url(r'^update/versions/(?P<version>[\w\-.]+)/images$', UpgradeVersionImagesView.as_view()),
    # 直接代理到 普罗米修斯
    url(r'^open/monitor/query$', MonitorQueryOverConsoleView.as_view()),
    url(r'^monitor/query$', MonitorQueryView.as_view()),
    url(r'^api-gateway/v1/(?P<tenantName>[\w\-]+)/(.*?)', AppApiGatewayView.as_view()),
    url(r'^api-gateway/convert', AppApiGatewayConvertView.as_view()),
    url(r'^v2/proxy-pass/(.*?)', ProxyPassView.as_view()),
    url(r'^sse/(.*?)', ProxySSEView.as_view()),

    # record error logs
    url(r'^errlog$', ErrLogView.as_view()),

    url(r'^user_source$', UserSourceView.as_view()),

    # 获取云帮Logo、标题、github、gitlab配置信息
    url(r'^config/info$', ConfigRUDView.as_view()),
    url(r'^config/oss$', ConfigOSSView.as_view()),
    url(r'^init/perms$', InitPerms.as_view()),
    # 获取权限列表
    url(r'^perms$', PermsInfoLView.as_view()),
    url(r'^custom_configs$', CustomConfigsCLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/licenses$', LicenseLView.as_view()),
    # 超分比例
    url(r"^over_score$", OverScore.as_view()),
    # OAuth
    url(r"^oauth/oauth-config$", OauthConfig.as_view()),
    url(r"^oauth/oauth-services$", OauthService.as_view()),
    url(r"^oauth/oauth-services/(?P<service_id>[\w\-]+)$", OauthServiceInfo.as_view()),
    url(r"^oauth/redirect$", OAuthServiceRedirect.as_view()),
    url(r"^oauth/authorize$", OAuthServerAuthorize.as_view()),
    url(r"^oauth/type$", OauthType.as_view()),
    url(r"^oauth/user/authorize$", OAuthServerUserAuthorize.as_view()),
    url(r"^oauth/user$", OAuthUserInfo.as_view()),
    url(r"^oauth/user/logout$", OauthUserLogoutView.as_view()),
    url(r"^oauth/user/link$", UserOAuthLink.as_view()),
    url(r"^oauth/service/(?P<service_id>[\w\-]+)/user/repositories$", OAuthGitUserRepositories.as_view()),
    url(r"^oauth/service/(?P<service_id>[\w\-]+)/user/repository/(?P<path>[\w\-]+)/(?P<name>.*)$",
        OAuthGitUserRepository.as_view()),
    url(r"^oauth/service/(?P<service_id>[\w\-]+)/user/repository/branches$", OAuthGitUserRepositoryBranches.as_view()),
    url(r"^oauth/service/(?P<service_id>[\w\-]+)/user/repository/code_detection$", OAuthGitCodeDetection.as_view()),

    # php环境配置
    url(r'^php$', PhpConfigView.as_view()),
    # 注册rke集群
    url(r'^cluster$', ClusterRKE.as_view()),
    url(r'^install_cluster$', InstallRKECluster.as_view()),
    url(r'^cluster_node$', ClusterRKENode.as_view()),
    url(r'^cluster_node_ip$', ClusterNodeIP.as_view()),
    url(r'^cluster_install$', ClusterRKEInstallRB.as_view()),
    url(r'^cluster_uninstall$', ClusterRKEUNInstallInstallRB.as_view()),
    url(r'^rb_components_status$', ClusterRKERBStatus.as_view()),
    url(r'^rb_component_event$', ClusterRKERBEvent.as_view()),
    url(r'^region_config$', RKERegionConfig.as_view()),
    url(r'^storage_statistics$', StorageStatistics.as_view()),
    # 判断是sso还是私有云
    url(r'^checksource$', CheckSourceView.as_view()),
    # 用户登录
    url(r'^users/login$', JWTTokenView.as_view()),
    # 用户登出
    url(r'^users/logout$', UserLogoutView.as_view()),
    # 用户注册
    url(r'^users/register$', TenantServiceView.as_view()),
    url(r'^captcha', CaptchaView.as_view()),
    # 忘记密码
    url(r'^users/send_reset_email$', SendResetEmail.as_view()),
    url(r'^users/begin_password_reset$', PasswordResetBegin.as_view()),
    # 修改密码
    url(r'^users/changepwd$', ChangeLoginPassword.as_view()),
    url(r'^users/custom_configs$', CustomConfigsUserCLView.as_view()),

    # 镜像仓库配置
    url(r'^hub/registry$', HubRegistryView.as_view()),
    url(r'^hub/registry/image$', HubRegistryImageView.as_view()),
    # 我的详情
    url(r'^users/details$', UserDetailsView.as_view()),
    # 模糊查询用户
    url(r'^users/query$', UserFuzSerView.as_view()),
    url(r"^users/access-token$", UserAccessTokenCLView.as_view()),
    url(r"^users/access-token/(?P<id>[\w\-]+)$", UserAccessTokenRUDView.as_view()),
    # 用户邀请
    url(r'^users/invite$', UserInviteView.as_view()),
    url(r'^users/invite/(?P<invitation_id>[\w\-]+)$', UserInviteJoinView.as_view()),

    # 团队中用户详情页
    url(r'^teams/(?P<team_name>[\w\-]+)/(?P<user_name>[\w\-]+)/details$', TeamUserDetaislView.as_view(),
        perms.TEAM_MEMBER_PERMS),
    # 团队角色权限管理
    url(r'^teams/(?P<team_name>[\w\-]+)/roles/perms$', TeamRolesPermsLView.as_view(), perms.TEAM_ROLE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/roles/(?P<role_id>[\w\-]+)/perms$', TeamRolePermsRUDView.as_view(),
        perms.TEAM_ROLE_PERMS),
    # 团队角色管理
    url(r'^teams/(?P<team_name>[\w\-]+)/roles$', TeamRolesLCView.as_view(), perms.TEAM_ROLE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/roles/(?P<role_id>[\w\-]+)$', TeamRolesRUDView.as_view(), perms.TEAM_ROLE_PERMS),
    # 团队成员角色管理
    url(r'^teams/(?P<team_name>[\w\-]+)/users/roles', TeamUsersRolesLView.as_view(), perms.TEAM_MEMBER_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/users/(?P<user_id>[\w\-]+)/roles', TeamUserRolesRUDView.as_view(),
        perms.TEAM_MEMBER_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/users/(?P<user_id>[\w\-]+)/perms', TeamUserPermsLView.as_view(),
        perms.TEAM_MEMBER_PERMS),
    # 团队镜像仓库授权管理
    url(r'^teams/(?P<team_name>[\w\-]+)/registry/auth$', TeamRegistryAuthLView.as_view(), perms.TEAM_REGISTRY_AUTH),
    url(r'^teams/(?P<team_name>[\w\-]+)/registry/auth/(?P<secret_id>[\w\-]+)$', TeamRegistryAuthRUDView.as_view(),
        perms.TEAM_REGISTRY_AUTH),

    # 移交团队管理权
    url(r'^teams/(?P<team_name>[\w\-]+)/pemtransfer$', UserPemTraView.as_view(), perms.TEAM_MEMBER_PERMS),
    # 新建团队
    url(r'^teams/add-teams$', AddTeamView.as_view()),
    # 获取团队下所有用户
    url(r'^teams/(?P<team_name>[\w\-]+)/users$', TeamUserView.as_view(), perms.TEAM_MEMBER_PERMS),
    # 获取企业下未加入当前团队的用户列表
    url(r'^teams/(?P<team_name>[\w\-]+)/notjoinusers$', NotJoinTeamUserView.as_view(), perms.TEAM_MEMBER_PERMS),
    # 删除团队成员
    url(r'^teams/(?P<team_name>[\w\-]+)/users/batch/delete', UserDelView.as_view(), perms.TEAM_MEMBER_PERMS),
    # 修改团队名称
    url(r'^teams/(?P<team_name>[\w\-]+)/modifyname$', TeamNameModView.as_view()),
    # 删除当前团队
    url(r'^teams/(?P<team_name>[\w\-]+)/delete$', TeamDelView.as_view()),
    # 应用(组)访问
    url(r'^teams/(?P<team_name>[\w\-]+)/group/service/visit', AppGroupVisitView.as_view()),
    # 退出当前团队
    url(r'^teams/(?P<team_name>[\w\-]+)/exit$', TeamExitView.as_view()),
    # check kubernetes service name
    url(r'^teams/(?P<team_name>[\w\-]+)/checkK8sServiceName$', TeamCheckKubernetesServiceName.as_view()),
    # 获取团队下域名访问量排序
    url(r'^teams/(?P<team_name>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/sort_domain/query$',
        TeamSortDomainQueryView.as_view()),
    # 获取团队下组件访问量排序
    url(r'^teams/(?P<team_name>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/sort_service/query$',
        TeamSortServiceQueryView.as_view()),
    # 获取当前租户已开通的数据中心(详细)
    url(r'^teams/(?P<team_name>[\w\-]+)/region/query$', RegQuyView.as_view(), perms.TEAM_REGION_DESCRIBE),
    # 获取当前团队未开通的数据中心
    url(r'^teams/(?P<team_name>[\w\-]+)/region/unopen$', RegUnopenView.as_view(), perms.TEAM_REGION_INSTALL),
    # 开通数据中心
    url(r'^teams/(?P<team_name>[\w\-]+)/region$', OpenRegionView.as_view(), perms.TEAM_REGION_INSTALL),

    # 总览 团队信息
    url(r'^teams/(?P<team_name>[\w\-]+)/overview$', TeamOverView.as_view(), perms.TEAM_OVERVIEW_DESCRIBE),
    url(r'^teams/(?P<team_name>[\w\-]+)/arch$', TeamArchView.as_view()),
    # team operation logs
    url(r'^teams/(?P<team_name>[\w\-]+)/operation-logs$', TeamOperationLogView.as_view()),

    # 总览 获取应用状态
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/services/status$', AllServiceInfo.as_view(), perms.TEAM_OVERVIEW_APP_DESCRIBE),
    # 上传yaml文件
    url(r'^teams/(?P<team_name>[\w\-]+)/resource-name$', YamlResourceName.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/resource-detailed$', YamlResourceDetailed.as_view(), perms.APP_OVERVIEW_CREATE),
    # helm应用处理
    url(r'^helm/repos$', HelmRepo.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/helm_app$', HelmAppView.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/chart/version$', HelmChart.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/helm_command$', CommandInstallHelm.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/helm_list$', HelmList.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/helm_cmd_add$', HelmRepoAdd.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/helm_center_app$', HelmCenterApp.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/get_upload_chart_information$', UploadHelmChart.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/check_upload_chart$', UploadHelmChart.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/get_upload_chart_value$', UploadHelmChartValue.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/get_upload_chart_resource$', UploadHelmChartValueResource.as_view(),
        perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<team_name>[\w\-]+)/import_upload_chart_resource$', UploadHelmChartValueResource.as_view(),
        perms.APP_OVERVIEW_CREATE),

    # 获取生成令牌
    url(r'^teams/(?P<team_name>[\w\-]+)/access-token/(?P<token_note>[\w\-]+)$', AccessTokenView.as_view()),

    # 团队应用模块（5.1）
    url(r'^teams/(?P<team_name>[\w\-]+)/apps$', TeamAppSortViewView.as_view(), perms.TEAM_OVERVIEW_APP_DESCRIBE),
    url(r'^teams/(?P<team_name>[\w\-]+)/app_names$', TeamAppNamesView.as_view(), perms.TEAM_OVERVIEW_APP_DESCRIBE),
    # 团队应用信息
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/service/over$', TeamServiceOverViewView.as_view(),
        perms.TEAM_OVERVIEW_APP_DESCRIBE),
    url(r'^teams/(?P<team_name>[\w\-]+)/check-resource-name$', TeamCheckResourceName.as_view(),
        perms.TEAM_OVERVIEW_APP_DESCRIBE),

    # 应用事件动态
    url(r'teams/(?P<team_name>[\w\-]+)/services/event$', ServiceEventsView.as_view()),

    # 团队下应用环境变量模糊查询
    url(r'teams/(?P<team_name>[\w\-]+)/services/envs$', TenantServiceEnvsView.as_view()),

    # 应用列表
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/groups$', ServiceGroupView.as_view()),
    # 应用列表、状态展示
    url(r'^teams/(?P<team_name>[\w\-]+)/service/group$', GroupServiceView.as_view(), perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/operator-managed$', GroupOperatorManagedView.as_view(), perms.APP_OVERVIEW_PERMS),
    # 应用拓扑图
    url(r'^teams/(?P<team_name>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/topological$', TopologicalGraphView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    # 拓扑图中应用详情
    url(r'^teams/(?P<team_name>[\w\-]+)/topological/services/(?P<serviceAlias>[\w\-]+)$', GroupServiceDetView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    # Internet 拓扑详情
    url(r'^teams/(?P<team_name>[\w\-]+)/(?P<group_id>\d+)/outer-service$', TopologicalInternetView.as_view(),
        perms.APP_OVERVIEW_PERMS),

    # 云市分享应用
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/share/record$', ServiceShareRecordView.as_view(),
        perms.APP_RELEASE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/share/record/(?P<record_id>[\w\-]+)$',
        ServiceShareRecordInfoView.as_view(), perms.APP_RELEASE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/share/step$', ShareRecordView.as_view(),
        perms.APP_RELEASE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>\d+)/shared/apps$', ServiceGroupSharedApps.as_view(),
        perms.APP_RELEASE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/info$', ServiceShareInfoView.as_view(),
        perms.APP_RELEASE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/giveup$', ServiceShareDeleteView.as_view(),
        perms.APP_RELEASE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events$', ServiceShareEventList.as_view(),
        perms.APP_RELEASE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events/(?P<event_id>[\w\-]+)$',
        ServiceShareEventPost.as_view(), perms.APP_RELEASE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events/(?P<event_id>[\w\-]+)/plugin$',
        ServicePluginShareEventPost.as_view(), perms.APP_RELEASE_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/complete$', ServiceShareCompleteView.as_view(),
        perms.APP_RELEASE_PERMS),
    # 租户数据中心组信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups$', TenantGroupView.as_view(), perms.APP_CREATE_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)$', TenantGroupOperationView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/handle$', TenantGroupHandleView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/install$', ApplicationInstallView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    # 批量修改该应用下有状态组件的存储路径
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/volumes$', ApplicationVolumesView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/pods/(?P<pod_name>[\w\-]+)$', ApplicationPodView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/upgradable_num$', TenantAppUpgradableNumView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/governancemode$', AppGovernanceModeView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/governancemode-cr$', AppGovernanceModeCRView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/governancemode/check', AppGovernanceModeCheckView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/component_names', AppComponentNameView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/k8sservices', AppKubernetesServiceView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/k8s-resources$', AppK8sResourceListView.as_view(),
        perms.APP_RESOURCE_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/k8s-resources/(?P<name>[\w\-\.]+)$',
        AppK8ResourceView.as_view(), perms.APP_RESOURCE_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/status', ApplicationStatusView.as_view(),
        perms.APP_OVERVIEW_PERMS),

    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<app_id>[\w\-]+)/operation-logs$', AppOperationLogView.as_view()),

    # 应用状态（应用）
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)$', GroupStatusView.as_view(), perms.APP_OVERVIEW_PERMS),
    # 应用(组)常见操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/common_operation$',
        TenantGroupCommonOperationView.as_view(), perms.APP_OVERVIEW_PERMS),
    # Application Config Group
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/configgroups$', ListAppConfigGroupView.as_view(),
        perms.APP_CONFIG_GROUP),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/configgroups/(?P<name>[\w\-]+)$',
        AppConfigGroupView.as_view(), perms.APP_CONFIG_GROUP),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/helmapp-components$',
        ApplicationHelmAppComponentView.as_view(), perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/parse-services$', ApplicationParseServicesView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/releases$', ApplicationReleasesView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<app_id>[\w\-]+)/visit$', ApplicationIngressesView.as_view(),
        perms.APP_OVERVIEW_PERMS),

    # 代码仓库
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/code/branch$', ServiceCodeBranch.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 文件上传最近一次记录
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/package_build/last-record$', UploadRecordLastView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 本地文件上传记录
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/package_build/record$', PackageUploadRecordView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 本地文件创建组件
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/package_build$', PackageCreateView.as_view(), perms.APP_OVERVIEW_CREATE),
    # 源码创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/source_code$', SourceCodeCreateView.as_view(), perms.APP_OVERVIEW_CREATE),
    # 第三方组件创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/third_party$', ThirdPartyServiceCreateView.as_view(), perms.APP_OVERVIEW_CREATE),
    # 第三方组件api注册方式回调地址
    url(r'^third_party/(?P<service_id>[\w\-]+)', ThirdPartyServiceApiView.as_view()),
    # 第三方组件api注册方式重置秘钥
    url(r"^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/third_party/updatekey$",
        ThirdPartyUpdateSecretKeyView.as_view()),
    # 第三方组件健康检测
    url(r"^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/3rd-party/health$", ThirdPartyHealthzView.as_view(),
        perms.APP_OVERVIEW_OTHER_SETTING),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/image_repositories$', TenantImageRepositories.as_view(),
        perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/image_tags$', TenantImageTags.as_view(), perms.APP_OVERVIEW_CREATE),
    # docker镜像创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/docker_run$', DockerRunCreateView.as_view(), perms.APP_OVERVIEW_CREATE),
    # docker-compose文件创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/docker_compose$', DockerComposeCreateView.as_view(), perms.APP_OVERVIEW_CREATE),
    # 虚拟机镜像创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/vm_run$', VMRunCreateView.as_view(), perms.APP_OVERVIEW_CREATE),
    # 应用检测
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/check$', AppCheck.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/lang-update$', LangUpdate.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/get_check_uuid$', GetCheckUUID.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # multiple services check
    url(r'^teams/(?P<tenantName>[\w\-]+)/multi/check$', MultiAppCheckView.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/multi/create$', MultiAppCreateView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 应用检测修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/check_update$', AppCheckUpdate.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # compose文件检测更新
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/compose_update$', ComposeCheckUpdate.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # compose文件检测
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/check$', ComposeCheckView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/get_check_uuid$', GetComposeCheckUUID.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # compose应用构建
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/compose_build$', ComposeBuildView.as_view(),
        perms.APP_OVERVIEW_CONSTRUCT),
    # 放弃compose创建应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/delete$', ComposeDeleteView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 查询compose下的应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/compose/(?P<compose_id>[\w\-]+)/services$', ComposeServicesView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 获取compose文件内容
    url(r'^teams/(?P<tenantName>[\w\-]+)/compose/(?P<compose_id>[\w\-]+)/content$', ComposeContentView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 应用构建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/lang_version$',
        CodeBuildLangVersionView.as_view(), perms.APP_OVERVIEW_CONSTRUCT),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/build$', AppBuild.as_view(),
        perms.APP_OVERVIEW_CONSTRUCT),
    # 应用编译环境信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/compile_env$', AppCompileEnvView.as_view(),
        perms.APP_OVERVIEW_CREATE),

    # 应用删除
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/delete$', DeleteAppView.as_view(),
        perms.APP_OVERVIEW_CREATE),

    # 应用详情
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/detail', AppDetailView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 是否安装性能分析插件
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/analyze_plugins', AppAnalyzePluginView.as_view()),
    # 应用简要信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/brief', AppBriefView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 触发应用自动部署关键字
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/keyword$', AppKeywordView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/status', AppStatusView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins$', AppPluginsBriefView.as_view(),
        perms.APP_OVERVIEW_PLUGIN),
    # 应用信息修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/group', AppGroupView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 应用pod信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/pods$', ListAppPodsView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/pods/(?P<pod_name>[\w\-]+)/detail$',
        AppPodsView.as_view(), perms.APP_OVERVIEW_CREATE),
    # 第三方应用pod信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/third_party/pods', ThirdPartyAppPodsView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/docker_console', DockerContainerView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 应用访问
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/visit', AppVisitView.as_view(),
        perms.APP_OVERVIEW_CREATE),
    # 环境变量配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/envs$', AppEnvView.as_view(), perms.APP_OVERVIEW_ENV),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/envs/(?P<env_id>[\w\-]+)$', AppEnvManageView.as_view(),
        perms.APP_OVERVIEW_ENV),
    # 构建运行时环境变量配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/build_envs$', AppBuildEnvView.as_view(),
        perms.APP_OVERVIEW_SOURCE),
    # 端口配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/ports$', AppPortView.as_view(),
        perms.APP_OVERVIEW_PORT),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/ports/(?P<port>[\w\-]+)$', AppPortManageView.as_view(),
        perms.APP_OVERVIEW_PORT),
    # 拓扑图打开对外端口
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/topological/ports$', TopologicalPortView.as_view(),
        perms.APP_OVERVIEW_PORT),
    # 对外访问tcp端口修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/tcp-ports/(?P<port>[\w\-]+)$',
        AppTcpOuterManageView.as_view(), perms.APP_OVERVIEW_PORT),
    # 组件支持的存储列表
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/volume-opts$', AppVolumeOptionsView.as_view(),
        perms.APP_OVERVIEW_STORAGE),
    # 持久化路径配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/volumes$', AppVolumeView.as_view(),
        perms.APP_OVERVIEW_STORAGE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/volumes/(?P<volume_id>[\w\-]+)$',
        AppVolumeManageView.as_view(), perms.APP_OVERVIEW_STORAGE),
    # 组件依赖
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/dependency$', AppDependencyView.as_view(),
        perms.APP_OVERVIEW_RELY),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/dependency-list$', AppDependencyViewList.as_view(),
        perms.APP_OVERVIEW_RELY),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/dependency-list$', AppDependencyViewList.as_view(),
        perms.APP_OVERVIEW_RELY),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/dependency-reverse$',
        AppDependencyReverseView.as_view(), perms.APP_OVERVIEW_RELY),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/dependency/(?P<dep_service_id>[\w\-]+)$',
        AppDependencyManageView.as_view(), perms.APP_OVERVIEW_RELY),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/un_dependency$', AppNotDependencyView.as_view(),
        perms.APP_OVERVIEW_RELY),
    # 组件挂载
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/mnt$', AppMntView.as_view(),
        perms.APP_OVERVIEW_STORAGE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/mnt/(?P<dep_vol_id>[\w\-]+)$',
        AppMntManageView.as_view(), perms.APP_OVERVIEW_STORAGE),
    # 域名证书
    url(r'^teams/(?P<tenantName>[\w\-]+)/certificates$', TenantCertificateView.as_view(), perms.TEAM_CERTIFICATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/certificates/(?P<certificate_id>[\w\-]+)$', TenantCertificateManageView.as_view(),
        perms.TEAM_CERTIFICATE),

    # Component k8s attribute
    url(r'^teams/(?P<tenantName>[\w\-]+)/components/(?P<serviceAlias>[\w\-]+)/k8s-attributes$',
        ComponentK8sAttributeListView.as_view(), perms.APP_OVERVIEW_OTHER_SETTING),
    url(r'^teams/(?P<tenantName>[\w\-]+)/components/(?P<serviceAlias>[\w\-]+)/k8s-attributes/(?P<name>[\w\-]+)$',
        ComponentK8sAttributeView.as_view(), perms.APP_OVERVIEW_OTHER_SETTING),

    # 组件域名操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/domain$', ServiceDomainView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/sld-domain', SecondLevelDomainView.as_view()),
    # 虚拟机镜像
    url(r'^teams/(?P<tenantName>[\w\-]+)/virtual_machine_image$', VirtualMachineImageView.as_view()),
    # gateway api
    url(r'^teams/(?P<tenantName>[\w\-]+)/batch-gateway-http-route$', GatewayRouteBatch.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/gateway-http-route$', GatewayRoute.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/service$', TenantService.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/domain$', DomainView.as_view()),
    # 查询策略（含模糊搜索）
    url(r'^teams/(?P<tenantName>[\w\-]+)/domain/query$', DomainQueryView.as_view()),
    # http操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/httpdomain$', HttpStrategyView.as_view()),
    # 校验证书
    url(r'^teams/(?P<tenantName>[\w\-]+)/calibration_certificate$', CalibrationCertificate.as_view()),
    # 查看高级路由信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/domain/get_senior_url$', GetSeniorUrlView.as_view()),
    # 查询tcp/udp策略（含模糊搜索）
    url(r'^teams/(?P<tenantName>[\w\-]+)/tcpdomain/query$', ServiceTcpDomainQueryView.as_view()),
    # 获取可用的port
    url(r'^teams/(?P<tenantName>[\w\-]+)/domain/get_port$', GetPortView.as_view()),
    # tcp/udp策略操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/tcpdomain$', ServiceTcpDomainView.as_view()),
    # 查询应用层面tcp/udp策略（含模糊搜索）
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/team/(?P<team_name>[\w\-]+)/app/(?P<app_id>[\w\-]+)/tcpdomain$',
        AppServiceTcpDomainQueryView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/team/(?P<team_name>[\w\-]+)/app/(?P<app_id>[\w\-]+)/domain$',
        AppServiceDomainQueryView.as_view()),

    # 5.1网关自定义参数
    url(r'^teams/(?P<tenantName>[\w\-]+)/domain/(?P<rule_id>[\w\-]+)/put_gateway$', GatewayCustomConfigurationView.as_view()),

    # 组件操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/apps_port$', AppsPorConsoletView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/start$', StartAppView.as_view(),
        perms.APP_OVERVIEW_START),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/stop$', StopAppView.as_view(), perms.APP_OVERVIEW_STOP),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/pause$', PauseAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/unpause$', UNPauseAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/vm_web$', UNPauseAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/restart$', ReStartAppView.as_view(),
        perms.APP_OVERVIEW_UPDATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/deploy$', DeployAppView.as_view(),
        perms.APP_OVERVIEW_CONSTRUCT),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/rollback$', RollBackAppView.as_view(),
        perms.APP_ROLLBACK),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/upgrade$', UpgradeAppView.as_view(), perms.APP_UPGRADE),
    # 设置组件构建后是否升级属性
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/set/is_upgrade$', ChangeServiceUpgradeView.as_view(),
        perms.APP_OVERVIEW_CONSTRUCT),
    # 查询云市安装的应用是否有（小版本，大版本）更新
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/market_service/upgrade$',
        MarketServiceUpgradeView.as_view(), perms.APP_UPGRADE),
    # 组件设置语言和安装依赖
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/package_tool$', PackageToolView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    # tar包设置镜像
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/tar_image$', TarImageView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    # 批量操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/batch_actions$', BatchActionView.as_view(), perms.APP_OVERVIEW_PERMS),
    # 批量删除应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/batch_delete$', BatchDelete.as_view(), perms.APP_OVERVIEW_PERMS),
    # 二次确认删除应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/again_delete$', AgainDelete.as_view(), perms.APP_OVERVIEW_PERMS),

    # 某个组件的event
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/events$', AppEventView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/event_log$', AppEventLogView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    # 某个组件的日志
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/log$', AppLogView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/log_instance$', AppLogInstanceView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/history_log$', AppHistoryLogView.as_view()),

    # 组件探针
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/probe$', AppProbeView.as_view(),
        perms.APP_OVERVIEW_OTHER_SETTING),

    # 组件扩容操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/horizontal$', HorizontalExtendAppView.as_view(),
        perms.APP_OVERVIEW_TELESCOPIC),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/vertical$', VerticalExtendAppView.as_view(),
        perms.APP_OVERVIEW_TELESCOPIC),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/scaling$', ScalingAppView.as_view(),
        perms.APP_OVERVIEW_TELESCOPIC),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/extend_method$', AppExtendView.as_view(),
        perms.APP_OVERVIEW_TELESCOPIC),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/xparules$', ListAppAutoscalerView.as_view(),
        perms.APP_OVERVIEW_TELESCOPIC),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/xparules/(?P<rule_id>[\w\-]+)$',
        AppAutoscalerView.as_view(), perms.APP_OVERVIEW_TELESCOPIC),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/xparecords$', AppScalingRecords.as_view(),
        perms.APP_OVERVIEW_TELESCOPIC),

    # 修改组件应用类型标签
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/deploytype$', ChangeServiceTypeView.as_view(),
        perms.APP_OVERVIEW_OTHER_SETTING),

    # 修改组件名称
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/change/service_name$', ChangeServiceNameView.as_view(),
        perms.APP_OVERVIEW_PERMS),

    # 组件监控
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/monitor/query_range$',
        AppMonitorQueryRangeView.as_view(), perms.APP_OVERVIEW_MONITOR),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/monitor/query$', AppMonitorQueryView.as_view(),
        perms.APP_OVERVIEW_MONITOR),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/monitor/batch_query$', BatchAppMonitorQueryView.as_view(),
        perms.APP_OVERVIEW_MONITOR),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/trace$', AppTraceView.as_view(),
        perms.APP_OVERVIEW_MONITOR),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/service_monitor$',
        ComponentServiceMonitorView.as_view(), perms.APP_OVERVIEW_MONITOR),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/service_monitor/(?P<name>[\w\-]+)$',
        ComponentServiceMonitorEditView.as_view(), perms.APP_OVERVIEW_MONITOR),
    # 组件标签
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/labels$', AppLabelView.as_view(),
        perms.APP_OVERVIEW_OTHER_SETTING),
    # 添加特性获取可用标签
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/labels/available$', AppLabelAvailableView.as_view(),
        perms.APP_OVERVIEW_OTHER_SETTING),
    # 应用资源
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/resource$', AppResourceQueryView.as_view(),
        perms.APP_OVERVIEW_PERMS),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/internal-graphs$',
        ComponentInternalGraphsView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/exchange-graphs$',
        ComponentExchangeGraphsView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/graphs$', ComponentGraphListView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/graphs/(?P<graph_id>[\w\-]+)$',
        ComponentGraphView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/metrics$', ComponentMetricsView.as_view(),
        perms.APP_OVERVIEW_MONITOR),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/logs$', ComponentLogView.as_view()),

    # 获取当前可用全部数据中心
    url(r'^regions$', QyeryRegionView.as_view()),

    # 获取数据中心builder PublicKey
    url(r'^teams/(?P<tenantName>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/publickey$', GetRegionPublicKeyView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/features$', GetRegionFeature.as_view()),

    # 插件
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins$', PluginCreateView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    # 默认插件创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/default$', DefaultPluginCreateView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    # 获取租户下所有插件基础信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/all$', AllPluginBaseInfoView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    # 查询某个插件的基础信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)$', PluginBaseInfoView.as_view(),
        perms.TEAM_PLUGIN_MANAGE),
    # 查询当前插件被使用的组件
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/used_services$', PluginUsedServiceView.as_view(),
        perms.TEAM_PLUGIN_MANAGE),
    # 插件历史版本信息查询
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/build-history$', AllPluginVersionInfoView.as_view(),
        perms.TEAM_PLUGIN_MANAGE),
    # 创建新版本
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/new-version$', CreatePluginVersionView.as_view(),
        perms.TEAM_PLUGIN_MANAGE),
    # 构建日志
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/event-log$',
        PluginEventLogView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    # 某个插件的某个版本查询，删除，修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)$',
        PluginVersionInfoView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    # 插件配置的增删改查
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/config$',
        ConfigPluginManageView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    # 配置预览
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/preview$',
        ConfigPreviewView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    # 构建插件
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/build$',
        PluginBuildView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    # 获取插件构建状态
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/status$',
        PluginBuildStatusView.as_view(), perms.TEAM_PLUGIN_MANAGE),

    # 插件与应用相关API
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/pluginlist$', ServicePluginsView.as_view(),
        perms.TEAM_PLUGIN_MANAGE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/install$',
        ServicePluginInstallView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/open$',
        ServicePluginOperationView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/configs$',
        ServicePluginConfigView.as_view(), perms.TEAM_PLUGIN_MANAGE),

    # 插件分享
    url(r'^teams/(?P<team_name>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/share/record$', PluginShareRecordView.as_view(),
        perms.TEAM_PLUGIN_MANAGE),
    url(r'^teams/(?P<team_name>[\w\-]+)/plugin-share/(?P<share_id>[\w\-]+)$', PluginShareInfoView.as_view(),
        perms.TEAM_PLUGIN_MANAGE),
    url(r'^teams/(?P<team_name>[\w\-]+)/plugin-share/(?P<share_id>[\w\-]+)/events$', PluginShareEventsView.as_view(),
        perms.TEAM_PLUGIN_MANAGE),
    url(r'^teams/(?P<team_name>[\w\-]+)/plugin-share/(?P<share_id>[\w\-]+)/events/(?P<event_id>[\w\-]+)',
        PluginShareEventView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    url(r'^teams/(?P<team_name>[\w\-]+)/plugin-share/(?P<share_id>[\w\-]+)/complete$', PluginShareCompletionView.as_view(),
        perms.TEAM_PLUGIN_MANAGE),

    # 插件市场
    url(r'^market/plugins$', MarketPluginsView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    url(r'^market/plugins/sync$', SyncMarketPluginsView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    url(r'^market/plugins/sync-template$', SyncMarketPluginTemplatesView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    url(r'^market/plugins/uninstall-template$', UninstallPluginTemplateView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    url(r'^market/plugins/install$', InstallMarketPlugin.as_view(), perms.TEAM_PLUGIN_MANAGE),
    url(r'^plugins$', InternalMarketPluginsView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    url(r'^plugins/installable$', InstallableInteralPluginsView.as_view(), perms.TEAM_PLUGIN_MANAGE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/market_create$', CenterAppView.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/cmd_create$', CmdInstallAppView.as_view(), perms.APP_OVERVIEW_CREATE),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/plugins$', CenterPluginAppView.as_view(), perms.TEAM_PLUGIN_MANAGE),

    # 文件上传
    url(r'^files/upload$', ConsoleUploadFileView.as_view()),
    # 云市认证
    url(r'^teams/(?P<tenantName>[\w\-]+)/enterprise/active$', BindMarketEnterpriseAccessTokenView.as_view()),
    # 新版本优化云市认证
    url(r'^teams/(?P<tenantName>[\w\-]+)/enterprise/active/optimiz$', BindMarketEnterpriseOptimizAccessTokenView.as_view()),
    # 获取数据中心协议
    url(r'^teams/(?P<tenantName>[\w\-]+)/protocols$', RegionProtocolView.as_view()),
    # 批量关闭应用下所有组件
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/close$', TeamAppsCloseView.as_view()),
    # 给一个团队添加新用户
    url(r'^teams/(?P<team_name>[\w\-]+)/add_team_user$', TeamAddUserView.as_view()),

    # 站内信信息获取
    url(r'^teams/(?P<team_name>[\w\-]+)/message$', UserMessageView.as_view()),
    # 一组应用备份
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/backup$', GroupAppsBackupView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/backup/all_status$',
        GroupAppsBackupStatusView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/backup/export$', GroupAppsBackupExportView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/backup/import$', GroupAppsBackupImportView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/backup$', TeamGroupAppsBackupView.as_view()),
    # 应用复制
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/copy$', GroupAppsCopyView.as_view(),
        perms.APP_OVERVIEW_COPY),
    # 获取团队下的所有备份记录
    url(r'^teams/(?P<tenantName>[\w\-]+)/all/groupapp/backup$', AllTeamGroupAppsBackupView.as_view()),
    # 应用迁移恢复
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/migrate$', GroupAppsMigrateView.as_view()),

    # 迁移与恢复未完成记录查询
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/migrate/record$', MigrateRecordView.as_view()),

    # 应用数据删除
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/delete$', GroupAppsView.as_view(),
        perms.APP_OVERVIEW_PERMS),

    # 源码仓库webhooks回调地址
    url(r'^webhooks/(?P<service_id>[\w\-]+)', WebHooksDeploy.as_view()),
    # 镜像仓库webhooks回调地址
    url(r'^image/webhooks/(?P<service_id>[\w\-]+)', ImageWebHooksDeploy.as_view()),

    # 自定义自动部署回调地址
    url(r'^custom/deploy/(?P<service_id>[\w\-]+)', CustomWebHooksDeploy.as_view()),

    # 获取自动部署回调地址
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/webhooks/get-url', GetWebHooksUrl.as_view()),

    # 更新自动部署触发方式
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/webhooks/trigger', ImageWebHooksTrigger.as_view()),
    # 自动部署功能状态与操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/webhooks/status', WebHooksStatus.as_view()),
    # 创建并开通数据中心
    url(r'^teams/init', TeamRegionInitView.as_view()),

    # 应用版本管理
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/version$', AppVersionsView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/version/(?P<version_id>[\w\-]+)$',
        AppVersionManageView.as_view()),
    # 获取当前团队所有的申请者
    url(r'^teams/(?P<team_name>[\w\-]+)/applicants$', ApplicantsView.as_view()),
    # enterprise configuration
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/configs$', EnterpriseConfigView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/objectstorage$', EnterpriseObjectStorageView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/appstoreimagehub$', EnterpriseAppStoreImageHubView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/visualmonitor$', EnterpriseVisualMonitorView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/alerts$', EnterpriseAlertsView.as_view()),
    url(r'^enterprise/registerstatus$', RegisterStatusView.as_view()),
    # 获取监控报警信息
    url(r'^enterprise/monitor_alarm$', MonitorAlarmStatusView.as_view()),
    # 获取企业信息
    url(r'^enterprise/info$', EnterpriseInfoView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/login-events$', LoginEventView.as_view()),
    # 初始化集群、团队信息
    url(r'^enterprise/init$', InitDefaultInfoView.as_view()),
    # 上传证书无用接口（为前端提供）
    url(r'^enterprise/team/certificate$', CertificateView.as_view()),
    # 企业管理员添加用户
    url(r'^enterprise/admin/add-user$', AdminAddUserView.as_view()),
    url(r'^enterprise/admin/join-team$', AdministratorJoinTeamView.as_view()),
    # get basic task guided information
    url(r'^enterprises$', Enterprises.as_view()),

    # Get Operation log
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/operation-logs$', OperationLogView.as_view()),

    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/platform-info$', EnterpriseInfoFileView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/backups$', BackupDataCView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/backups/(?P<backup_name>[\w\-\.]+)$', BackupDateDownload.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/recover$', BackupRecoverCView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/upload-backups$', BackupUploadCView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/active/optimiz$', BindMarketEnterpriseOptimizAccessTokenView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/info$', EnterpriseRUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/overview$', EnterpriseOverview.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/overview/app$', EnterpriseAppOverView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/overview/team$', EnterpriseTeamOverView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/monitor$', EnterpriseMonitor.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/users$', EnterPriseUsersCLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/user/(?P<user_id>[\d\-]+)$', EnterPriseUsersUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/user/(?P<user_id>[\d\-]+)/teams$', EnterpriseUserTeams.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/myteams$', EnterpriseMyTeams.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/user/favorite$', UserFavoriteLCView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/user/favorite/(?P<favorite_id>[\w\-]+)$', UserFavoriteUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/admin/user$', AdminUserLCView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/admin/user/(?P<user_id>[\w\-]+)$', AdminUserView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/admin/roles', AdminRolesView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/teams$', EnterpriseTeams.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/team_names$', EnterpriseTeamNames.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/apps$', EnterpriseAppsLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/menu$', EnterpriseMenuManage.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions$', EnterpriseRegionsLCView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_id>[\w\-]+)$', EnterpriseRegionsRUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_id>[\w\-]+)/lang_version',
        EnterpriseRegionLangVersion.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_id>[\w\-]+)/namespace',
        EnterpriseRegionNamespace.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_id>[\w\-]+)/resource',
        EnterpriseNamespaceResource.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_id>[\w\-]+)/convert-resource',
        EnterpriseConvertResource.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_id>[\w\-]+)/tenants$',
        EnterpriseRegionTenantRUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_id>[\w\-]+)/tenants/(?P<tenant_name>[\w\-]+)/limit$',
        EnterpriseRegionTenantLimitView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_id>[\w\-]+)/dashboard/(?P<path>.*)',
        EnterpriseRegionDashboard.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/batch-gateway',
        EnterpriseRegionGatewayBatch.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/plugins$', RainbondPluginLView.as_view()),
    url(r'^regions/(?P<region_name>[\w\-]+)/plugins/(?P<plugin_name>[\w\-]+)/status$', RainbondPluginStatusView.as_view()),
    url(r'^regions/(?P<region_name>[\w\-]+)/static/plugins/(?P<plugin_name>[\w\-]+)$', RainbondPluginStaticView.as_view()),
    url(r'^regions/(?P<region_name>[\w\-]+)/backend/plugins/(?P<plugin_name>[\w\-]+)/(?P<file_path>.*)$', RainbondPluginBackendView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/abilities$', RainbondAbilityLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/abilities/(?P<ability_id>.*)$',
        RainbondAbilityRUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/officialplugins$',
        RainbondOfficialPluginLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/mavensettings$', MavenSettingView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/mavensettings/(?P<name>[\w\-]+)$',
        MavenSettingRUDView.as_view()),
    # 获取节点下rainbond组件
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/rbd-components$',
        RainbondComponents.as_view()),
    # 获取集群节点列表
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/nodes$', GetNodes.as_view()),
    # 获取节点详情
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/nodes/(?P<node_name>[\w\-.]+)$',
        GetNode.as_view()),
    # 操作节点
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/nodes/(?P<node_name>[\w\-.]+)/action$',
        NodeAction.as_view()),
    # 节点标签操作
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/nodes/(?P<node_name>[\w\-.]+)/labels$',
        NodeLabelsOperate.as_view()),
    # 节点污点操作
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/nodes/(?P<node_name>[\w\-.]+)/taints$',
        NodeTaintOperate.as_view()),
    # 容器存储
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/nodes/(?P<node_name>[\w\-.]+)/container$',
        ContainerDisk.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app/(?P<app_id>[\w\-]+)/components$', EnterpriseAppComponentsLView.as_view()),
    url(r'^enterprise/(?P<eid>[\w\-]+)/base-guidance$', BaseGuidance.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/storehub-check$', LocalComponentLibraryConfigCheck.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models$', CenterAppCLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-model/(?P<app_id>[\w\-]+)$', CenterAppUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-model/(?P<app_id>[\w\-]+)/version/(?P<version>.*)',
        AppVersionUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/tag$', TagCLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/tag/(?P<tag_id>[\w\-]+)$', TagUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-model/(?P<app_id>[\w\-]+)/tag$', AppTagCDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/markets$', AppMarketCLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/bind-markets$', AppMarketBatchCView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/markets/(?P<market_name>[\w\-]+)$', AppMarketRUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/markets/(?P<market_name>[\w\-]+)/app-models$',
        AppMarketAppModelLView.as_view()),
    url(
        r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/markets/(?P<market_name>[\w\-]+)/app-models/(?P<app_id>[\w\-]+)'
        r'/versions$', AppMarketAppModelVersionsLView.as_view()),
    url(
        r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/markets/(?P<market_name>[\w\-]+)/app-models/(?P<app_id>[\w\-]+)'
        r'/versions/(?P<version>[\w\-.]+)$', AppMarketAppModelVersionsRView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/bindable-markets$', BindableMarketsView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/markets/(?P<market_name>[\w\-]+)/organizations$',
        AppMarketOrgModelLView.as_view()),

    # 应用导出
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/export$', CenterAppExportView.as_view()),
    # WIP
    # 创建应用导入记录
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/import$', EnterpriseAppImportInitView.as_view()),
    # 应用导入修改、查询、删除
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/import/(?P<event_id>[\w\-]+)$', CenterAppImportView.as_view()),
    # 应用包目录查询
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/import/(?P<event_id>[\w\-]+)/dir$',
        CenterAppTarballDirView.as_view()),
    url(r"^enterprise/(?P<enterprise_id>[\w\-]+)/oauth/oauth-services$", EnterpriseOauthService.as_view()),
    url(r"^enterprise/(?P<eid>[\w\-]+)/users/(?P<user_id>[\w\-]+)/teams/(?P<tenant_name>[\w\-]+)/roles$",
        EnterpriseUserTeamRoleView.as_view(), perms.TEAM_ROLE_PERMS),
    # 查询登录用户可以加入哪些团队
    url(r"^enterprise/(?P<enterprise_id>[\w\-]+)/jointeams$", TeamUserCanJoin.as_view()),
    url(r"^enterprise/(?P<enterprise_id>[\w\-]+)/create-app-teams$", TeamsPermissionCreateApp.as_view()),

    # 集群通过helm对接控制台
    url(r'^enterprise/helm/token$', HelmTokenView.as_view()),
    url(r'^enterprise/helm/region_info$', HelmAddReginInfo.as_view()),
    url(r'^enterprise/helm/region_status$', HelmInstallStatus.as_view()),
    # 查看当前用户所有团队组件日志
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/my_events$', MyEventsView.as_view()),
    # 用户组件报警
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/service_alarm$', ServiceAlarm.as_view()),

    # 查看控制台日志
    url(r'^enterprise/goodrain_log$', Goodrainlog.as_view()),
    url(r'^enterprise/download/goodrain_log$', Downlodlog.as_view(), name='download'),

    # 查看rbd资源日志
    url(r'^enterprise/region_name/(?P<region_name>[\w\-]+)/rbd-pods$', RbdPods.as_view()),
    url(r'^enterprise/region_name/(?P<region_name>[\w\-]+)/rbd-logs$', RbdPodLog.as_view()),
    url(r'^enterprise/region_name/(?P<region_name>[\w\-]+)/rbd-component-logs$', RbdComponentLogs.as_view()),
    url(r'^enterprise/region_name/(?P<region_name>[\w\-]+)/rbd-log-files$', RbdLogFiles.as_view()),

    # shell
    url(r'^enterprise/shell-pod$', ShellPod.as_view()),
    # 查看用户审核状态
    url(r'^user/applicants/status$', UserApplyStatusView.as_view()),
    # 用户申请某个团队
    url(r"^user/applicants/join$", JoinTeamView.as_view()),
    # 修改部署密钥
    url(r"^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/webhooks/updatekey$", UpdateSecretKey.as_view()),
    # 修改镜像源
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/image', ImageAppView.as_view()),
    # 查询构建源
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/buildsource$', BuildSourceinfo.as_view()),
    # job、cronjob策略配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/job_strategy$', JobStrategy.as_view()),
    # 文件上传下载
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/file-manage$', ManageFile.as_view()),
    # 针对target 查看日志
    url(r'^teams/(?P<tenantName>[\w\-]+)/events$', AppEventsView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/events/(?P<eventId>[\w\-]+)/log$', AppEventsLogView.as_view()),
    url(r'^users/team_details$', UserTeamDetailsView.as_view()),
    # 短信配置接口
    url(r'^enterprises/(?P<enterprise_id>[\w\-]+)/sms-config$', SMSConfigView.as_view()),
    # 短信验证码发送
    url(r'^sms/send-code$', SMSVerificationView.as_view()),
    # 用户注册（手机号）
    url(r'^users/register-by-phone$', RegisterByPhoneView.as_view()),
    # 用户登录（手机号）
    url(r'^users/login-by-phone$', LoginByPhoneView.as_view()),
]

# 云市应用升级相关接口
urlpatterns += [
    # 查询当前组下的云市应用
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/apps$', app_upgrade.GroupAppView.as_view()),
    # 查询某个升级应用的详情
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/apps/(?P<upgrade_group_id>[0-9]+)$',
        app_upgrade.AppUpgradeDetailView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/apps/(?P<upgrade_group_id>[\w\-]+)/components',
        app_upgrade.AppUpgradeComponentListView.as_view()),
    # 查询当前组下某云市应用的更新版本
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/upgrade-versions$',
        app_upgrade.AppUpgradeVersion.as_view()),
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[0-9]+)/last-upgrade-record$',
        app_upgrade.AppLastUpgradeRecordView.as_view()),
    # 升级记录集合
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[0-9]+)/upgrade-records$',
        app_upgrade.AppUpgradeRecordsView.as_view()),
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[0-9]+)/upgrade-records/(?P<upgrade_record_id>[0-9]+)' + \
        '/rollback-records$', app_upgrade.AppRollbackRecordsView.as_view()),
    # 某一条升级记录
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/upgrade-records/(?P<record_id>[0-9]+)$',
        app_upgrade.AppUpgradeRecordDetailView.as_view()),
    # 查询某云市应用下组件的更新信息
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/upgrade-info$',
        app_upgrade.AppUpgradeInfoView.as_view()),
    # upgrade application
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[0-9]+)/upgrade-records/(?P<record_id>[0-9]+)/upgrade$',
        app_upgrade.AppUpgradeView.as_view()),
    # 回滚某一条升级
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/upgrade-records/(?P<record_id>[0-9]+)/rollback$',
        app_upgrade.AppUpgradeRollbackView.as_view()),
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<app_id>[0-9]+)/upgrade-records/(?P<record_id>[0-9]+)/deploy$',
        app_upgrade.AppUpgradeDeployView.as_view())
]

urlpatterns += [
    url(r"proxy/enterprise-server/api/v1/enterprises/(?P<enterprise_id>[\w\-]+)/appstores$", Appstores.as_view()),
    url(r"proxy/enterprise-server/api/v1/enterprises/(?P<enterprise_id>[\w\-]+)/appstores/(?P<name>[\w\-]+)$",
        Appstore.as_view()),
    url(r"proxy/enterprise-server/api/v1/enterprises/(?P<enterprise_id>[\w\-]+)/appstores/(?P<name>[\w\-]+)/apps$",
        AppstoreCharts.as_view()),
    url(r"proxy/enterprise-server/api/v1/enterprises/(?P<enterprise_id>[\w\-]+)/appstores/(?P<name>[\w\-]+)/templates/(?P<chart_name>[\w\-]+)/versions/(?P<version>[\d\.]+)$",
        AppstoreChart.as_view()),
    url(r"proxy/enterprise-server/api/v1/enterprises/(?P<enterprise_id>[\w\-]+)/tasks/helm_region_install$",
        HelmRegionInstall.as_view()),
]

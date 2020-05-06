# -*- coding: utf8 -*-
from django.conf.urls import include, url

from console.captcha.captcha_code import CaptchaView
from console.views import app_upgrade
from console.views.app_autoscaler import (AppAutoscalerView, AppScalingRecords, ListAppAutoscalerView)
from console.views.app_config.app_dependency import (AppDependencyManageView, AppDependencyView, AppNotDependencyView)
from console.views.app_config.app_domain import (
    AppServiceDomainQueryView, AppServiceTcpDomainQueryView, DomainQueryView, DomainView, GatewayCustomConfigurationView,
    GetPortView, GetSeniorUrlView, HttpStrategyView, SecondLevelDomainView, ServiceDomainView, ServiceTcpDomainQueryView,
    ServiceTcpDomainView, TenantCertificateManageView, TenantCertificateView)
from console.views.app_config.app_env import (AppBuildEnvView, AppEnvManageView, AppEnvView)
from console.views.app_config.app_extend import AppExtendView
from console.views.app_config.app_label import (AppLabelAvailableView, AppLabelView)
from console.views.app_config.app_mnt import AppMntManageView, AppMntView
from console.views.app_config.app_port import (AppPortManageView, AppPortView, AppTcpOuterManageView, TopologicalPortView)
from console.views.app_config.app_probe import AppProbeView
from console.views.app_config.app_volume import (AppVolumeManageView, AppVolumeOptionsView, AppVolumeView)
from console.views.app_create.app_build import AppBuild, ComposeBuildView
from console.views.app_create.app_check import (AppCheck, AppCheckUpdate, GetCheckUUID)
from console.views.app_create.docker_compose import (ComposeCheckUpdate, ComposeCheckView, ComposeContentView,
                                                     ComposeDeleteView, ComposeServicesView, DockerComposeCreateView,
                                                     GetComposeCheckUUID)
from console.views.app_create.docker_run import DockerRunCreateView
from console.views.app_create.multi_app import (MultiAppCheckView, MultiAppCreateView)
from console.views.app_create.source_code import (AppCompileEnvView, SourceCodeCreateView)
from console.views.app_create.source_outer import (ThirdPartyAppPodsView, ThirdPartyHealthzView, ThirdPartyServiceApiView,
                                                   ThirdPartyServiceCreateView, ThirdPartyUpdateSecretKeyView)
from console.views.app_event import (AppEventLogView, AppEventsLogView, AppEventsView, AppEventView, AppHistoryLogView,
                                     AppLogInstanceView, AppLogView)
from console.views.app_manage import (AgainDelete, BatchActionView, BatchDelete, ChangeServiceNameView, ChangeServiceTypeView,
                                      ChangeServiceUpgradeView, DeleteAppView, DeployAppView, HorizontalExtendAppView,
                                      MarketServiceUpgradeView, ReStartAppView, RollBackAppView, StartAppView, StopAppView,
                                      UpgradeAppView, VerticalExtendAppView)
from console.views.app_monitor import (AppMonitorQueryRangeView, AppMonitorQueryView, AppResourceQueryView,
                                       BatchAppMonitorQueryView)
from console.views.app_overview import (AppAnalyzePluginView, AppBriefView, AppDetailView, AppGroupView, AppGroupVisitView,
                                        AppKeywordView, AppPluginsBriefView, AppStatusView, AppVisitView, BuildSourceinfo,
                                        ImageAppView, ListAppPodsView)
from console.views.center_pool.app_export import (CenterAppExportView, ExportFileDownLoadView)
from console.views.center_pool.app_import import (CenterAppImportingAppsView, CenterAppImportView, CenterAppTarballDirView,
                                                  CenterAppUploadView, EnterpriseAppImportInitView, ImportingRecordView)
from console.views.center_pool.apps import (AppTagCDView, CenterAllMarketAppView, CenterAppCLView, CenterAppUDView,
                                            CenterAppView, CenterVersionlMarversionketAppView, DownloadMarketAppTemplateView,
                                            GetCloudRecommendedAppList, TagCLView, TagUDView)
from console.views.center_pool.groupapp_backup import (AllTeamGroupAppsBackupView, GroupAppsBackupExportView,
                                                       GroupAppsBackupImportView, GroupAppsBackupStatusView,
                                                       GroupAppsBackupView, TeamGroupAppsBackupView)
from console.views.center_pool.groupapp_copy import GroupAppsCopyView
from console.views.center_pool.groupapp_migration import (GroupAppsMigrateView, GroupAppsView, MigrateRecordView)
from console.views.code_repo import (CodeBranchView, GithubCallBackView, GithubCodeRepoView, GitlabCodeRepoView,
                                     GitLabUserRegisterView, ServiceCodeBranch)
from console.views.enterprise import (EnterpriseAppComponentsLView, EnterpriseAppOverView, EnterpriseAppsLView,
                                      EnterpriseMonitor, EnterpriseOverview, EnterpriseRegionsLCView, EnterpriseRegionsRUDView,
                                      EnterpriseRUDView, Enterprises, EnterpriseTeamOverView, EnterpriseTeams,
                                      EnterpriseUserTeams)
from console.views.enterprise_active import (BindMarketEnterpriseAccessTokenView, BindMarketEnterpriseOptimizAccessTokenView)
from console.views.errlog import ErrLogView
from console.views.file_upload import ConsoleUploadFileView
from console.views.group import (GroupStatusView, TenantGroupCommonOperationView, TenantGroupOperationView, TenantGroupView)
# from console.views.jwt_token_view import JWTTokenView
from console.views.logos import ConfigRUDView, PhpConfigView
from console.views.message import UserMessageView
from console.views.oauth import (EnterpriseOauthService, OauthConfig, OAuthGitCodeDetection, OAuthGitUserRepositories,
                                 OAuthGitUserRepository, OAuthGitUserRepositoryBranches, OAuthServerAuthorize,
                                 OAuthServerUserAuthorize, OauthService, OauthServiceInfo, OAuthServiceRedirect, OauthType,
                                 OAuthUserInfo, UserOAuthLink)
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
from console.views.public_areas import (AllServiceInfo, GroupServiceView, ServiceEventsView, ServiceGroupView,
                                        TeamAppSortViewView, TeamOverView, TeamServiceOverViewView, TenantServiceEnvsView)
from console.views.receipt import (EnterReceiptAPIView, EnterReceiptConfirmAPIView, EnterReceiptDetailAPIView,
                                   EnterReceiptOrdersAIPView)
from console.views.region import (GetRegionPublicKeyView, OpenRegionView, QyeryRegionView, RegQuyView, RegSimQuyView,
                                  RegUnopenView)
from console.views.role_prems import (PermOptionsView, ServicePermissionView, TeamAddRoleView, TeamAddUserView, TeamDelRoleView,
                                      ThreeServicePermOptionsView, UserModifyPemView, UserRoleView, UserUpdatePemView)
from console.views.service_docker import DockerContainerView
from console.views.service_share import (
    CloudAppModelMarketInfo, CloudAppModelMarkets, ServiceGroupSharedApps, ServicePluginShareEventPost,
    ServiceShareCompleteView, ServiceShareDeleteView, ServiceShareEventList, ServiceShareEventPost, ServiceShareInfoView,
    ServiceShareRecordInfoView, ServiceShareRecordView, ShareRecordHistoryView, ShareRecordView)
from console.views.service_version import AppVersionManageView, AppVersionsView
from console.views.services_toplogical import (GroupServiceDetView, TopologicalGraphView, TopologicalInternetView)
from console.views.task_guidance import BaseGuidance
from console.views.team import (
    AddTeamView, AdminAddUserView, ApplicantsView, CertificateView, EnterpriseInfoView, JoinTeamView, NotJoinTeamUserView,
    RegisterStatusView, TeamDelView, TeamDetailView, TeamExitView, TeamInvView, TeamNameModView, TeamRegionInitView,
    TeamSortDomainQueryView, TeamSortServiceQueryView, TeamUserAddView, TeamUserAdminView, TeamUserCanJoin, TeamUserDetaislView,
    TeamUserView, UserAllTeamView, UserApplyStatusView, UserDelView, UserFuzSerView)
from console.views.user import (AdminUserDView, AdminUserLCView, CheckSourceView, EnterPriseUsersCLView, EnterPriseUsersUDView,
                                UserAddPemView, UserLogoutView, UserPemTraView, UserPemView)
from console.views.user_accesstoken import (UserAccessTokenCLView, UserAccessTokenRUDView)
# from console.views.user_operation import TenantServiceView
from console.views.user_operation import (ChangeLoginPassword, PasswordResetBegin, SendResetEmail, UserDetailsView,
                                          UserFavoriteLCView, UserFavoriteUDView)
from console.views.webhook import (CustomWebHooksDeploy, GetWebHooksUrl, ImageWebHooksDeploy, ImageWebHooksTrigger,
                                   UpdateSecretKey, WebHooksDeploy, WebHooksStatus)

urlpatterns = [
    # record error logs
    url(r'^errlog$', ErrLogView.as_view()),
    # 获取云帮Logo、标题、github、gitlab配置信息
    url(r'^config/info$', ConfigRUDView.as_view()),
    # OAuth
    url(r"^oauth/oauth-config$", OauthConfig.as_view()),
    url(r"^oauth/oauth-services$", OauthService.as_view()),
    url(r"^oauth/oauth-services/(?P<service_id>[\w\-]+)$", OauthServiceInfo.as_view()),
    url(r"^oauth/redirect$", OAuthServiceRedirect.as_view()),
    url(r"^oauth/authorize$", OAuthServerAuthorize.as_view()),
    url(r"^oauth/type$", OauthType.as_view()),
    url(r"^oauth/user/authorize$", OAuthServerUserAuthorize.as_view()),
    url(r"^oauth/user$", OAuthUserInfo.as_view()),
    url(r"^oauth/user/link$", UserOAuthLink.as_view()),
    url(r"^oauth/service/(?P<service_id>[\w\-]+)/user/repositories$", OAuthGitUserRepositories.as_view()),
    url(r"^oauth/service/(?P<service_id>[\w\-]+)/user/repository/(?P<path>[\w\-]+)/(?P<name>[\w\-]+)$",
        OAuthGitUserRepository.as_view()),
    url(r"^oauth/service/(?P<service_id>[\w\-]+)/user/repository/branches$", OAuthGitUserRepositoryBranches.as_view()),
    url(r"^oauth/service/(?P<service_id>[\w\-]+)/user/repository/code_detection$", OAuthGitCodeDetection.as_view()),

    # php环境配置
    url(r'^php$', PhpConfigView.as_view()),
    # 判断是sso还是私有云
    url(r'^checksource$', CheckSourceView.as_view()),
    # 用户登录
    # url(r'^users/login$', JWTTokenView.as_view()),
    # 用户登出
    url(r'^users/logout$', UserLogoutView.as_view()),
    # 用户注册
    # url(r'^users/register$', TenantServiceView.as_view()),
    url(r'^captcha', CaptchaView.as_view()),
    # 忘记密码
    url(r'^users/send_reset_email$', SendResetEmail.as_view()),
    url(r'^users/begin_password_reset$', PasswordResetBegin.as_view()),
    # 修改密码
    url(r'^users/changepwd$', ChangeLoginPassword.as_view()),

    # 我的详情
    url(r'^users/details$', UserDetailsView.as_view()),
    # 模糊查询用户
    url(r'^users/query$', UserFuzSerView.as_view()),
    url(r"^users/access-token$", UserAccessTokenCLView.as_view()),
    url(r"^users/access-token/(?P<id>[\w\-]+)$", UserAccessTokenRUDView.as_view()),
    # 团队中用户详情页
    url(r'^teams/(?P<team_name>[\w\-]+)/(?P<user_name>[\w\-]+)/details$', TeamUserDetaislView.as_view()),
    # 移交团队管理权
    url(r'^teams/(?P<team_name>[\w\-]+)/pemtransfer$', UserPemTraView.as_view()),
    # 可选权限展示
    url(r'^teams/user/identity$', UserPemView.as_view()),
    # 修改成员权限
    url(r'^teams/(?P<team_name>[\w\-]+)/(?P<user_name>[\w\-]+)/modidentity$', UserAddPemView.as_view()),

    # 获取当前用户加入的所有团队
    url(r'^users/teams/query', UserAllTeamView.as_view()),
    # 新建团队
    url(r'^teams/add-teams$', AddTeamView.as_view()),
    # 获取团队下所有用户
    url(r'^teams/(?P<team_name>[\w\-]+)/users$', TeamUserView.as_view()),
    # 获取企业下未加入当前团队的用户列表
    url(r'^teams/(?P<team_name>[\w\-]+)/notjoinusers$', NotJoinTeamUserView.as_view()),
    # 获取当前用户在团队下是否为管理员或拥有者
    url(r'^teams/(?P<team_name>[\w\-]+)/users/is_admin$', TeamUserAdminView.as_view()),
    # 添加新用户
    url(r'^teams/(?P<team_name>[\w\-]+)/add-user$', TeamUserAddView.as_view()),
    # 删除团队成员
    url(r'^teams/(?P<team_name>[\w\-]+)/users/batch/delete', UserDelView.as_view()),
    # 修改团队名称
    url(r'^teams/(?P<team_name>[\w\-]+)/modifyname$', TeamNameModView.as_view()),
    # 删除当前团队
    url(r'^teams/(?P<team_name>[\w\-]+)/delete$', TeamDelView.as_view()),
    # 应用(组)访问
    url(r'^teams/(?P<team_name>[\w\-]+)/group/service/visit', AppGroupVisitView.as_view()),
    # 退出当前团队
    url(r'^teams/(?P<team_name>[\w\-]+)/exit$', TeamExitView.as_view()),
    # 邀请注册
    url(r'^teams/(?P<team_name>[\w\-]+)/invitation$', TeamInvView.as_view()),
    # 团队详情
    url(r'^teams/(?P<team_name>[\w\-]+)/detail$', TeamDetailView.as_view()),
    # 获取团队下域名访问量排序
    url(r'^teams/(?P<team_name>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/sort_domain/query$',
        TeamSortDomainQueryView.as_view()),
    # 获取团队下组件访问量排序
    url(r'^teams/(?P<team_name>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/sort_service/query$',
        TeamSortServiceQueryView.as_view()),
    # 获取当前租户已开通的数据中心(详细)
    url(r'^teams/(?P<team_name>[\w\-]+)/region/query$', RegQuyView.as_view()),
    # 获取当前租户已开通的数据中心(简表)
    url(r'^teams/(?P<team_name>[\w\-]+)/region/simple/query$', RegSimQuyView.as_view()),
    # 获取当前团队未开通的数据中心
    url(r'^teams/(?P<team_name>[\w\-]+)/region/unopen$', RegUnopenView.as_view()),
    # 开通数据中心
    url(r'^teams/(?P<team_name>[\w\-]+)/region$', OpenRegionView.as_view()),

    # 总览 团队信息
    url(r'^teams/(?P<team_name>[\w\-]+)/overview$', TeamOverView.as_view()),
    # 总览 获取应用状态
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/services/status$', AllServiceInfo.as_view()),

    # 团队应用模块（5.1）
    url(r'^teams/(?P<team_name>[\w\-]+)/apps$', TeamAppSortViewView.as_view()),

    # 团队应用信息
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/service/over$', TeamServiceOverViewView.as_view()),

    # 应用事件动态
    url(r'teams/(?P<team_name>[\w\-]+)/services/event$', ServiceEventsView.as_view()),

    # 团队下应用环境变量模糊查询
    url(r'teams/(?P<team_name>[\w\-]+)/services/envs$', TenantServiceEnvsView.as_view()),

    # 应用列表
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/groups$', ServiceGroupView.as_view()),
    # 应用列表、状态展示
    url(r'^teams/(?P<team_name>[\w\-]+)/service/group$', GroupServiceView.as_view()),

    # 应用拓扑图
    # url(r'^teams/(?P<team_name>[\w\-]+)/topological/services', TopologicalGraphView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/topological$', TopologicalGraphView.as_view()),
    # 拓扑图中应用详情
    url(r'^teams/(?P<team_name>[\w\-]+)/topological/services/(?P<serviceAlias>[\w\-]+)$', GroupServiceDetView.as_view()),
    # Internet 拓扑详情
    url(r'^teams/(?P<team_name>[\w\-]+)/(?P<group_id>\d+)/outer-service$', TopologicalInternetView.as_view()),

    # 云市分享应用
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/share/record$', ServiceShareRecordView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/share/record/(?P<record_id>[\w\-]+)$',
        ServiceShareRecordInfoView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/share/step$', ShareRecordView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>\d+)/shared/apps$', ServiceGroupSharedApps.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>\d+)/shared/history$', ShareRecordHistoryView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/info$', ServiceShareInfoView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/giveup$', ServiceShareDeleteView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events$', ServiceShareEventList.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events/(?P<event_id>[\w\-]+)$',
        ServiceShareEventPost.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events/(?P<event_id>[\w\-]+)/plugin$',
        ServicePluginShareEventPost.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/complete$', ServiceShareCompleteView.as_view()),
    # 租户数据中心组信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups$', TenantGroupView.as_view()),
    # 应用删除
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)$', TenantGroupOperationView.as_view()),
    # 应用状态（应用）
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)$', GroupStatusView.as_view()),
    # 应用(组)常见操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/common_operation$',
        TenantGroupCommonOperationView.as_view()),
    # git仓库对接
    url(r'^teams/(?P<tenantName>[\w\-]+)/code_repo/github$', GithubCodeRepoView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/code_repo/gitlab$', GitlabCodeRepoView.as_view()),
    # 获取代码仓库
    url(r'^teams/(?P<tenantName>[\w\-]+)/code_repo/branchs$', CodeBranchView.as_view()),
    # github回调地址
    url(r'^github/callback$', GithubCallBackView.as_view()),

    # gitlab仓库用户创建
    url(r'^gitlab/register$', GitLabUserRegisterView.as_view()),
    # url(r'^teams/(?P<tenantName>[\w\-]+)/gitlab/register$', GitLabUserRegisterView.as_view()),

    # 源码创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/source_code$', SourceCodeCreateView.as_view()),
    # 第三方组件创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/third_party$', ThirdPartyServiceCreateView.as_view()),
    # 第三方组件api注册方式回调地址
    url(r'^third_party/(?P<service_id>[\w\-]+)', ThirdPartyServiceApiView.as_view()),
    # 第三方组件api注册方式重置秘钥
    url(r"^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/third_party/updatekey$",
        ThirdPartyUpdateSecretKeyView.as_view()),
    # 第三方组件健康检测
    url(r"^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/3rd-party/health$", ThirdPartyHealthzView.as_view()),
    # docker镜像创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/docker_run$', DockerRunCreateView.as_view()),
    # docker-compose文件创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/docker_compose$', DockerComposeCreateView.as_view()),
    # 应用检测
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/check$', AppCheck.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/get_check_uuid$', GetCheckUUID.as_view()),
    # multiple services check
    url(r'^teams/(?P<tenantName>[\w\-]+)/multi/check$', MultiAppCheckView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/multi/create$', MultiAppCreateView.as_view()),
    # 应用检测修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/check_update$', AppCheckUpdate.as_view()),
    # compose文件检测更新
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/compose_update$', ComposeCheckUpdate.as_view()),
    # compose文件检测
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/check$', ComposeCheckView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/get_check_uuid$', GetComposeCheckUUID.as_view()),
    # compose应用构建
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/compose_build$', ComposeBuildView.as_view()),
    # 放弃compose创建应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/delete$', ComposeDeleteView.as_view()),
    # 查询compose下的应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/compose/(?P<compose_id>[\w\-]+)/services$', ComposeServicesView.as_view()),
    # 获取compose文件内容
    url(r'^teams/(?P<tenantName>[\w\-]+)/compose/(?P<compose_id>[\w\-]+)/content$', ComposeContentView.as_view()),
    # 应用构建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/build$', AppBuild.as_view()),
    # 应用编译环境信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/compile_env$', AppCompileEnvView.as_view()),

    # 应用删除
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/delete$', DeleteAppView.as_view()),

    # 应用详情
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/detail', AppDetailView.as_view()),
    # 是否安装性能分析插件
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/analyze_plugins', AppAnalyzePluginView.as_view()),
    # 应用简要信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/brief', AppBriefView.as_view()),
    # 触发应用自动部署关键字
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/keyword', AppKeywordView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/status', AppStatusView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins$', AppPluginsBriefView.as_view()),
    # 应用信息修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/group', AppGroupView.as_view()),
    # 应用pod信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/pods$', ListAppPodsView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/pods/(?P<pod_name>[\w\-]+)/detail$',
        AppPodsView.as_view()),
    # 第三方应用pod信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/third_party/pods', ThirdPartyAppPodsView.as_view()),
    # 应用进入容器页面
    # url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/docker', AppDockerView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/docker_console', DockerContainerView.as_view()),
    # 应用访问
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/visit', AppVisitView.as_view()),
    # 应用配置
    # 环境变量配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/envs$', AppEnvView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/envs/(?P<env_id>[\w\-]+)$', AppEnvManageView.as_view()),
    # 构建运行时环境变量配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/build_envs$', AppBuildEnvView.as_view()),
    # 端口配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/ports$', AppPortView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/ports/(?P<port>[\w\-]+)$', AppPortManageView.as_view()),
    # 拓扑图打开对外端口
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/topological/ports$', TopologicalPortView.as_view()),
    # 对外访问tcp端口修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/tcp-ports/(?P<port>[\w\-]+)$',
        AppTcpOuterManageView.as_view()),
    # 组件支持的存储列表
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/volume-opts$', AppVolumeOptionsView.as_view()),
    # 持久化路径配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/volumes$', AppVolumeView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/volumes/(?P<volume_id>[\w\-]+)$',
        AppVolumeManageView.as_view()),
    # 组件依赖
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/dependency$', AppDependencyView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/dependency/(?P<dep_service_id>[\w\-]+)$',
        AppDependencyManageView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/un_dependency$', AppNotDependencyView.as_view()),
    # 组件挂载
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/mnt$', AppMntView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/mnt/(?P<dep_vol_id>[\w\-]+)$',
        AppMntManageView.as_view()),
    # 域名证书
    url(r'^teams/(?P<tenantName>[\w\-]+)/certificates$', TenantCertificateView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/certificates/(?P<certificate_id>[\w\-]+)$', TenantCertificateManageView.as_view()),

    # 组件域名操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/domain$', ServiceDomainView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/sld-domain', SecondLevelDomainView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/domain$', DomainView.as_view()),
    # 查询策略（含模糊搜索）
    url(r'^teams/(?P<tenantName>[\w\-]+)/domain/query$', DomainQueryView.as_view()),
    # http操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/httpdomain$', HttpStrategyView.as_view()),
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
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/start$', StartAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/stop$', StopAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/restart$', ReStartAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/deploy$', DeployAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/rollback$', RollBackAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/upgrade$', UpgradeAppView.as_view()),
    # 设置组件构建后是否升级属性
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/set/is_upgrade$', ChangeServiceUpgradeView.as_view()),
    # 查询云市安装的应用是否有（小版本，大版本）更新
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/market_service/upgrade$',
        MarketServiceUpgradeView.as_view()),

    # 批量操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/batch_actions$', BatchActionView.as_view()),
    # 批量删除应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/batch_delete$', BatchDelete.as_view()),
    # 二次确认删除应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/again_delete$', AgainDelete.as_view()),

    # 某个组件的event
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/events$', AppEventView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/event_log$', AppEventLogView.as_view()),
    # 某个组件的日志
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/log$', AppLogView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/log_instance$', AppLogInstanceView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/history_log$', AppHistoryLogView.as_view()),

    # 组件探针
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/probe$', AppProbeView.as_view()),

    # 组件扩容操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/horizontal$', HorizontalExtendAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/vertical$', VerticalExtendAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/extend_method$', AppExtendView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/xparules$', ListAppAutoscalerView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/xparules/(?P<rule_id>[\w\-]+)$',
        AppAutoscalerView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/xparecords$', AppScalingRecords.as_view()),

    # 修改组件应用类型标签
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/deploytype$', ChangeServiceTypeView.as_view()),

    # 修改组件名称
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/change/service_name$', ChangeServiceNameView.as_view()),

    # 代码仓库
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/code/branch$', ServiceCodeBranch.as_view()),

    # 组件监控
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/monitor/query_range$',
        AppMonitorQueryRangeView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/monitor/query$', AppMonitorQueryView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/monitor/batch_query$',
        BatchAppMonitorQueryView.as_view()),
    # 组件标签
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/labels$', AppLabelView.as_view()),
    # 添加特性获取可用标签
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/labels/available$', AppLabelAvailableView.as_view()),
    # 应用资源
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/resource$', AppResourceQueryView.as_view()),
    # 获取当前可用全部数据中心
    url(r'^regions$', QyeryRegionView.as_view()),

    # 获取数据中心builder PublicKey
    url(r'^teams/(?P<tenantName>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/publickey$', GetRegionPublicKeyView.as_view()),

    # 插件
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins$', PluginCreateView.as_view()),
    # 默认插件创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/default$', DefaultPluginCreateView.as_view()),
    # 获取租户下所有插件基础信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/all$', AllPluginBaseInfoView.as_view()),
    # 查询某个插件的基础信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)$', PluginBaseInfoView.as_view()),
    # 查询当前插件被使用的组件
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/used_services$', PluginUsedServiceView.as_view()),
    # 插件历史版本信息查询
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/build-history$', AllPluginVersionInfoView.as_view()),
    # 创建新版本
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/new-version$', CreatePluginVersionView.as_view()),
    # 构建日志
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/event-log$',
        PluginEventLogView.as_view()),
    # 某个插件的某个版本查询，删除，修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)$',
        PluginVersionInfoView.as_view()),
    # 插件配置的增删改查
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/config$',
        ConfigPluginManageView.as_view()),
    # 配置预览
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/preview$',
        ConfigPreviewView.as_view()),
    # 构建插件
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/build$',
        PluginBuildView.as_view()),
    # 获取插件构建状态
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/status$',
        PluginBuildStatusView.as_view()),

    # 插件与应用相关API
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/pluginlist$', ServicePluginsView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/install$',
        ServicePluginInstallView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/open$',
        ServicePluginOperationView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/configs$',
        ServicePluginConfigView.as_view()),

    # 插件分享
    url(r'^teams/(?P<team_name>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/share/record$', PluginShareRecordView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/plugin-share/(?P<share_id>[\w\-]+)$', PluginShareInfoView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/plugin-share/(?P<share_id>[\w\-]+)/events$', PluginShareEventsView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/plugin-share/(?P<share_id>[\w\-]+)/events/(?P<event_id>[\w\-]+)',
        PluginShareEventView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/plugin-share/(?P<share_id>[\w\-]+)/complete$', PluginShareCompletionView.as_view()),

    # 插件市场
    url(r'^market/plugins$', MarketPluginsView.as_view()),
    url(r'^market/plugins/sync$', SyncMarketPluginsView.as_view()),
    url(r'^market/plugins/sync-template$', SyncMarketPluginTemplatesView.as_view()),
    url(r'^market/plugins/uninstall-template$', UninstallPluginTemplateView.as_view()),
    url(r'^market/plugins/install$', InstallMarketPlugin.as_view()),
    url(r'^plugins$', InternalMarketPluginsView.as_view()),
    url(r'^plugins/installable$', InstallableInteralPluginsView.as_view()),

    # 内部云市应用相关
    # 获取可安装应用
    # url(r'^apps$', CenterAppListView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/market_create$', CenterAppView.as_view()),

    # 文件上传
    url(r'^files/upload$', ConsoleUploadFileView.as_view()),
    # 云市认证
    url(r'^teams/(?P<tenantName>[\w\-]+)/enterprise/active$', BindMarketEnterpriseAccessTokenView.as_view()),
    # 新版本优化云市认证
    url(r'^teams/(?P<tenantName>[\w\-]+)/enterprise/active/optimiz$', BindMarketEnterpriseOptimizAccessTokenView.as_view()),
    # 获取数据中心协议
    url(r'^teams/(?P<tenantName>[\w\-]+)/protocols$', RegionProtocolView.as_view()),
    # 应用导入
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/upload$', CenterAppUploadView.as_view()),
    # 应用包目录查询
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/import/dir$', CenterAppTarballDirView.as_view()),
    # 应用导入记录
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/import/record$', ImportingRecordView.as_view()),
    # 正在导入的应用查询
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/import/importing-apps$', CenterAppImportingAppsView.as_view()),
    # 应用导入状态查询
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/import/(?P<event_id>[\w\-]+)$', CenterAppImportView.as_view()),
    # 应用下载
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/export/down$', ExportFileDownLoadView.as_view()),

    # 获取自定义角色时可给角色绑定的权限选项
    url(r'^teams/operate_options$', PermOptionsView.as_view()),
    # 获取第三方组件自定义角色时可给角色绑定的权限选项
    url(r'^teams/three_service/operate_options$', ThreeServicePermOptionsView.as_view()),
    # 在一个团队中创建一个角色
    url(r'^teams/(?P<team_name>[\w\-]+)/add-role$', TeamAddRoleView.as_view()),
    # 在一个团队中删除一个角色
    url(r'^teams/(?P<team_name>[\w\-]+)/del-role$', TeamDelRoleView.as_view()),
    # 在一个团队中修改角色名称及角色对应的权限
    url(r'^teams/(?P<team_name>[\w\-]+)/update_role_perms$', UserUpdatePemView.as_view()),
    # 获取一个团队中所有可展示的的角色及角色对应的权限信息展示(不含owner)
    url(r'^teams/(?P<team_name>[\w\-]+)/role-list$', UserRoleView.as_view()),
    # 修改团队中成员角色
    url(r'^teams/(?P<team_name>[\w\-]+)/(?P<user_id>[\w\-]+)/mod-role$', UserModifyPemView.as_view()),
    # 给一个团队添加新用户
    url(r'^teams/(?P<team_name>[\w\-]+)/add_team_user$', TeamAddUserView.as_view()),
    # 应用权限设置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/perms$', ServicePermissionView.as_view()),

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
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/copy$', GroupAppsCopyView.as_view()),
    # 获取团队下的所有备份记录
    url(r'^teams/(?P<tenantName>[\w\-]+)/all/groupapp/backup$', AllTeamGroupAppsBackupView.as_view()),
    # 应用迁移恢复
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/migrate$', GroupAppsMigrateView.as_view()),

    # 迁移与恢复未完成记录查询
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/migrate/record$', MigrateRecordView.as_view()),

    # 应用数据删除
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/delete$', GroupAppsView.as_view()),

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

    # 企业发票相关
    url(r'receipts$', EnterReceiptAPIView.as_view()),
    url(r'receipts/confirm$', EnterReceiptConfirmAPIView.as_view()),
    url(r'receipts/(?P<receipt_id>\d+)$', EnterReceiptDetailAPIView.as_view()),
    url(r'receipt-orders$', EnterReceiptOrdersAIPView.as_view()),
    # 应用版本管理
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/version$', AppVersionsView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/version/(?P<version_id>[\w\-]+)$',
        AppVersionManageView.as_view()),
    # 获取当前团队所有的申请者
    url(r'^teams/(?P<team_name>[\w\-]+)/applicants$', ApplicantsView.as_view()),
    url(r'^enterprise/registerstatus$', RegisterStatusView.as_view()),
    # 获取企业信息
    url(r'^enterprise/info$', EnterpriseInfoView.as_view()),
    # 上传证书无用接口（为前端提供）
    url(r'^enterprise/team/certificate$', CertificateView.as_view()),
    # 企业管理员添加用户
    url(r'^enterprise/admin/add-user$', AdminAddUserView.as_view()),
    # get basic task guided information
    url(r'^enterprises$', Enterprises.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/active/optimiz$', BindMarketEnterpriseOptimizAccessTokenView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/info$', EnterpriseRUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/overview$', EnterpriseOverview.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/overview/app$', EnterpriseAppOverView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/overview/team$', EnterpriseTeamOverView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/monitor$', EnterpriseMonitor.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/users$', EnterPriseUsersCLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/user/(?P<user_id>[\d\-]+)$', EnterPriseUsersUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/user/(?P<user_id>[\d\-]+)/teams$', EnterpriseUserTeams.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/user/favorite$', UserFavoriteLCView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/user/favorite/(?P<favorite_id>[\w\-]+)$', UserFavoriteUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/admin/user$', AdminUserLCView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/admin/user/(?P<user_id>[\w\-]+)$', AdminUserDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/teams$', EnterpriseTeams.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/apps$', EnterpriseAppsLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions$', EnterpriseRegionsLCView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/regions/(?P<region_id>[\w\-]+)$', EnterpriseRegionsRUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app/(?P<app_id>[\w\-]+)/components$', EnterpriseAppComponentsLView.as_view()),
    url(r'^enterprise/(?P<eid>[\w\-]+)/base-guidance$', BaseGuidance.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models$', CenterAppCLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-model/(?P<app_id>[\w\-]+)$', CenterAppUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/app-models$', CenterAllMarketAppView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/app-models/recommend', GetCloudRecommendedAppList.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/app-models/version$', CenterVersionlMarversionketAppView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/tag$', TagCLView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/tag/(?P<tag_id>[\w\-]+)$', TagUDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-model/(?P<app_id>[\w\-]+)/tag$', AppTagCDView.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/markets$', CloudAppModelMarkets.as_view()),
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/market/(?P<market_id>[\w\-]+)/app-models$',
        CloudAppModelMarketInfo.as_view()),

    # 应用导出
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/export$', CenterAppExportView.as_view()),
    # 同步某个应用回来
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/cloud/app-models/download$', DownloadMarketAppTemplateView.as_view()),
    # WIP
    # 创建应用导入记录
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/import$', EnterpriseAppImportInitView.as_view()),
    # 应用导入修改、查询、删除
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/import/(?P<event_id>[\w\-]+)$', CenterAppImportView.as_view()),
    # 应用包目录查询
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/import/(?P<event_id>[\w\-]+)/dir$',
        CenterAppTarballDirView.as_view()),
    # 应用下载
    url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/export/down$', ExportFileDownLoadView.as_view()),
    url(r"^enterprise/(?P<enterprise_id>[\w\-]+)/oauth/oauth-services$", EnterpriseOauthService.as_view()),
    # 查询登录用户可以加入哪些团队
    url(r"^enterprise/(?P<enterprise_id>[\w\-]+)/jointeams$", TeamUserCanJoin.as_view()),
    # 下架应用
    # url(r'^enterprise/(?P<enterprise_id>[\w\-]+)/app-models/manage$', CenterAppManageView.as_view()),
    # 查看用户审核状态
    url(r'^user/applicants/status$', UserApplyStatusView.as_view()),
    # 用户申请某个团队
    url(r"^user/applicants/join$", JoinTeamView.as_view()),
    # 修改部署密钥
    url(r"^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/webhooks/updatekey$", UpdateSecretKey.as_view()),
    # 修改镜像源
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/image', ImageAppView.as_view()),
    # 查询构建源
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/buildsource', BuildSourceinfo.as_view()),

    # 针对target 查看日志
    url(r'^teams/(?P<tenantName>[\w\-]+)/events$', AppEventsView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/events/(?P<eventId>[\w\-]+)/log$', AppEventsLogView.as_view()),
]

# 云市应用升级相关接口
urlpatterns += [
    # 查询当前组下的云市应用
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/apps$', app_upgrade.GroupAppView.as_view()),
    # 查询当前组下某云市应用的更新版本
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/upgrade-versions$',
        app_upgrade.AppUpgradeVersion.as_view()),
    # 升级记录集合
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/upgrade-records$',
        app_upgrade.AppUpgradeRecordsView.as_view()),
    # 某一条升级记录
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/upgrade-records/(?P<record_id>[0-9]+)$',
        app_upgrade.AppUpgradeRecordView.as_view()),
    # 查询某云市应用下组件的更新信息
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/upgrade-info$', app_upgrade.AppUpgradeInfoView.as_view()),
    # 创建升级任务
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/upgrade-tasks$', app_upgrade.AppUpgradeTaskView.as_view()),
    # 回滚某一条升级
    url(r'teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[0-9]+)/upgrade-records/(?P<record_id>[0-9]+)/rollback$',
        app_upgrade.AppUpgradeRollbackView.as_view())
]

# ONLINE 业务相关接口
urlpatterns += [
    url(r'', include('console.cloud.urls')),
]

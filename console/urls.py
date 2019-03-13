# -*- coding: utf8 -*-
from django.conf.urls import patterns, url

from console.captcha.captcha_code import CaptchaView

from console.views.account_fee import EnterpriseRechargeRecordsView, EnterprisePurchaseDetails

from console.views.account_fee import EnterpriseAccountInfoView, EnterpriseTeamFeeView, EnterpriseAllRegionFeeView

from console.views.app_config.app_dependency import AppDependencyView, AppDependencyManageView, AppNotDependencyView
from console.views.app_config.app_domain import TenantCertificateView, TenantCertificateManageView, ServiceDomainView, \
    DomainView, SecondLevelDomainView, DomainQueryView, ServiceTcpDomainQueryView, ServiceTcpDomainView, GetPortView, \
    GetSeniorUrlView, HttpStrategyView, GatewayCustomConfigurationView
from console.views.app_config.app_env import AppEnvView, AppEnvManageView, AppBuildEnvView
from console.views.app_config.app_extend import AppExtendView
from console.views.app_config.app_label import AppLabelView, AppLabelAvailableView
from console.views.app_config.app_mnt import AppMntView, AppMntManageView
from console.views.app_config.app_port import AppPortView, AppPortManageView, AppTcpOuterManageView, TopologicalPortView
from console.views.app_config.app_probe import AppProbeView
from console.views.app_config.app_volume import AppVolumeView, AppVolumeManageView
from console.views.app_create.app_build import AppBuild, ComposeBuildView
from console.views.app_create.app_check import AppCheck, AppCheckUpdate, GetCheckUUID
from console.views.app_create.docker_compose import DockerComposeCreateView, ComposeCheckView, ComposeCheckUpdate, \
    ComposeDeleteView, GetComposeCheckUUID, ComposeServicesView, ComposeContentView
from console.views.app_create.docker_run import DockerRunCreateView
from console.views.app_create.source_code import SourceCodeCreateView, AppCompileEnvView
from console.views.app_create.source_outer import ThirdPartyServiceCreateView, ThirdPartyServiceApiView, \
    ThirdPartyUpdateSecretKeyView, ThirdPartyAppPodsView, ThirdPartyHealthzView
from console.views.app_event import AppEventView, AppEventLogView, AppLogView, AppLogInstanceView, AppHistoryLogView
from console.views.app_manage import ReStartAppView, StopAppView, StartAppView, DeployAppView, BatchActionView, \
    RollBackAppView, HorizontalExtendAppView, VerticalExtendAppView, DeleteAppView, ChangeServiceTypeView, \
    UpgradeAppView, ChangeServiceNameView, ChangeServiceUpgradeView, MarketServiceUpgradeView
from console.views.app_monitor import AppMonitorQueryRangeView, AppMonitorQueryView, AppResourceQueryView, \
    BatchAppMonitorQueryView
from console.views.app_overview import AppDetailView, AppStatusView, AppPodsView, AppVisitView, AppBriefView, \
    AppPluginsBriefView, AppGroupView, AppAnalyzePluginView, ImageAppView, BuildSourceinfo, AppGroupVisitView, AppKeywordView
from console.views.center_pool.app_export import CenterAppExportView, ExportFileDownLoadView
from console.views.center_pool.app_import import CenterAppUploadView, CenterAppImportView, CenterAppTarballDirView, \
    CenterAppImportingAppsView, ImportingRecordView
from console.views.center_pool.apps import CenterAppListView, \
    DownloadMarketAppGroupTemplageDetailView, CenterAllMarketAppView, CenterAppManageView, CenterVersionlMarversionketAppView
from console.views.center_pool.apps import CenterAppView
from console.views.center_pool.groupapp_backup import GroupAppsBackupView, TeamGroupAppsBackupView, \
    GroupAppsBackupStatusView, GroupAppsBackupExportView, GroupAppsBackupImportView, AllTeamGroupAppsBackupView
from console.views.center_pool.groupapp_migration import GroupAppsMigrateView, GroupAppsView, MigrateRecordView
from console.views.code_repo import GithubCodeRepoView, GitlabCodeRepoView, ServiceCodeBranch, GithubCallBackView, \
    GitLabUserRegisterView, CodeBranchView
from console.views.enterprise_active import BindMarketEnterpriseAccessTokenView, \
    BindMarketEnterpriseOptimizAccessTokenView
from console.views.file_upload import ConsoleUploadFileView
from console.views.group import TenantGroupView, TenantGroupOperationView, TenantGroupCommonOperationView, GroupStatusView
from console.views.jwt_token_view import JWTTokenView
from console.views.logos import ConfigInfoView, PhpConfigView
from console.views.message import UserMessageView
from console.views.plugin.plugin_config import ConfigPluginManageView, ConfigPreviewView
from console.views.plugin.plugin_create import PluginCreateView, DefaultPluginCreateView
from console.views.plugin.plugin_info import PluginBaseInfoView, PluginEventLogView, AllPluginVersionInfoView, \
    PluginVersionInfoView, AllPluginBaseInfoView, PluginUsedServiceView
from console.views.plugin.plugin_manage import PluginBuildView, CreatePluginVersionView, PluginBuildStatusView
from console.views.plugin.plugin_market import SyncMarketPluginsView, \
    SyncMarketPluginTemplatesView, InstallMarketPlugin, InternalMarketPluginsView, \
    UninstallPluginTemplateView, InstallableInteralPluginsView, MarketPluginsView
from console.views.plugin.plugin_share import PluginShareRecordView, PluginShareInfoView, \
    PluginShareEventsView, PluginShareEventView, PluginShareCompletionView
from console.views.plugin.service_plugin import ServicePluginsView, \
    ServicePluginInstallView, ServicePluginOperationView, ServicePluginConfigView
from console.views.protocols import RegionProtocolView
from console.views.public_areas import TeamOverView, ServiceGroupView, GroupServiceView, AllServiceInfo, \
    ServiceEventsView, TeamServiceOverViewView, TenantServiceEnvsView, TeamAppSortViewView
from console.views.region import RegQuyView, RegSimQuyView, RegUnopenView, OpenRegionView, QyeryRegionView, \
    GetRegionPublicKeyView, PublicRegionListView, RegionResourceDetailView, RegionResPrice, RegionResPurchage
from console.views.role_prems import PermOptionsView, TeamAddRoleView, TeamDelRoleView, UserUpdatePemView, UserRoleView, \
    UserModifyPemView, TeamAddUserView, ServicePermissionView, ThreeServicePermOptionsView
from console.views.service_docker import DockerContainerView
from console.views.service_share import ServiceShareInfoView, ServiceShareDeleteView, ServiceShareEventList, \
    ServiceShareEventPost, \
    ServiceShareCompleteView, ServiceShareRecordView, ServicePluginShareEventPost
from console.views.service_version import AppVersionsView, AppVersionManageView
from console.views.services_toplogical import TopologicalGraphView, GroupServiceDetView, TopologicalInternetView
from console.views.team import TeamNameModView, TeamDelView, TeamInvView, TeamUserDetaislView, AddTeamView, \
    UserAllTeamView, TeamUserView, UserDelView, UserFuzSerView, TeamUserAddView, TeamExitView, TeamDetailView, \
    TeamRegionInitView, AllTeamsView, RegisterStatusView, EnterpriseInfoView, UserApplyStatusView, JoinTeamView, \
    TeamUserCanJoin, AdminAddUserView, TeamUserAdminView, CertificateView, TeamSortDomainQueryView, TeamSortServiceQueryView
from console.views.user import CheckSourceView, UserLogoutView, UserAddPemView, UserPemTraView, UserPemView
from console.views.user_operation import TenantServiceView, SendResetEmail, PasswordResetBegin, ChangeLoginPassword, \
    UserDetailsView
from console.views.webhook import WebHooksDeploy, GetWebHooksUrl, WebHooksStatus, CustomWebHooksDeploy, UpdateSecretKey, ImageWebHooksDeploy
from console.views.receipt import *
from console.views.team import ApplicantsView
from console.views.app_manage import BatchDelete
from console.views.app_manage import AgainDelete
from console.views.service_share import ShareRecordView


urlpatterns = patterns(
    '',
    # 获取云帮Logo、标题、github、gitlab配置信息
    url(r'^config/info$', ConfigInfoView.as_view()),
    # php环境配置
    url(r'^php$', PhpConfigView.as_view()),
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

    # 我的详情
    url(r'^users/details$', UserDetailsView.as_view()),
    # 模糊查询用户
    url(r'^users/query$', UserFuzSerView.as_view()),
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
    url(r'^teams/(?P<team_name>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/sort_domain/query$', TeamSortDomainQueryView.as_view()),
    # 获取团队下服务访问量排序
    url(r'^teams/(?P<team_name>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/sort_service/query$', TeamSortServiceQueryView.as_view()),
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
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/app/over$', TeamAppSortViewView.as_view()),

    # 团队应用信息
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/service/over$', TeamServiceOverViewView.as_view()),

    # 应用事件动态
    url(r'teams/(?P<team_name>[\w\-]+)/services/event$', ServiceEventsView.as_view()),

    # 团队下应用环境变量模糊查询
    url(r'teams/(?P<team_name>[\w\-]+)/services/envs$', TenantServiceEnvsView.as_view()),


    # 应用组列表
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/groups$', ServiceGroupView.as_view()),
    # 应用组应用列表、状态展示
    url(r'^teams/(?P<team_name>[\w\-]+)/service/group$', GroupServiceView.as_view()),

    # 应用组拓扑图
    # url(r'^teams/(?P<team_name>[\w\-]+)/topological/services', TopologicalGraphView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/topological$', TopologicalGraphView.as_view()),
    # 拓扑图中应用详情
    url(r'^teams/(?P<team_name>[\w\-]+)/topological/services/(?P<serviceAlias>[\w\-]+)$',
        GroupServiceDetView.as_view()),
    # Internet 拓扑详情
    url(r'^teams/(?P<team_name>[\w\-]+)/(?P<group_id>\d+)/outer-service$', TopologicalInternetView.as_view()),

    # 云市分享应用
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/share/step$', ShareRecordView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/share/record$', ServiceShareRecordView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/info$', ServiceShareInfoView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/giveup$', ServiceShareDeleteView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events$', ServiceShareEventList.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events/(?P<event_id>[\w\-]+)$',
        ServiceShareEventPost.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events/(?P<event_id>[\w\-]+)/plugin$',
        ServicePluginShareEventPost.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/complete$', ServiceShareCompleteView.as_view()),


    # 安装应用
    # url(r'^teams/(?P<team_name>[\w\-]+)/service/install$', InstallServiceView.as_view()),

    # 账户与费用相关
    url(r'^enterprise/account$', EnterpriseAccountInfoView.as_view()),
    url(r'^enterprise/team/(?P<team_name>[\w\-]+)/all-region-fee$', EnterpriseAllRegionFeeView.as_view()),
    url(r'^enterprise/team/(?P<team_name>[\w\-]+)/fee', EnterpriseTeamFeeView.as_view()),
    url(r'^enterprise/team/(?P<team_name>[\w\-]+)/recharge-records$', EnterpriseRechargeRecordsView.as_view()),
    url(r'^enterprise/team/(?P<team_name>[\w\-]+)/all-region-fee$', EnterpriseAllRegionFeeView.as_view()),
    url(r'^enterprise/team/(?P<team_name>[\w\-]+)/purchase-detail$', EnterprisePurchaseDetails.as_view()),
    # 数据中心相关
    url(r'^enterprise/regions$', PublicRegionListView.as_view()),
    url(r'^enterprise/region/resource$', RegionResourceDetailView.as_view()),
    url(r'^enterprise/regions/(?P<region_name>[\w\-]+)/res-price$', RegionResPrice.as_view()),
    url(r'^enterprise/regions/(?P<region_name>[\w\-]+)/purchase$', RegionResPurchage.as_view()),

    # 租户数据中心组信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups$', TenantGroupView.as_view()),
    # 应用组删除
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)$',
        TenantGroupOperationView.as_view()),
    # 应用组状态（应用）
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)$',
        GroupStatusView.as_view()),
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
    # 三方服务创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/third_party$', ThirdPartyServiceCreateView.as_view()),
    # 三方服务api注册方式回调地址
    url(r'^third_party/(?P<service_id>[\w\-]+)', ThirdPartyServiceApiView.as_view()),
    # 三方服务api注册方式重置秘钥
    url(r"^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/third_party/updatekey$", ThirdPartyUpdateSecretKeyView.as_view()),
    # 三方服务健康检测
    url(r"^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/3rd-party/health$", ThirdPartyHealthzView.as_view()),
    # docker镜像创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/docker_run$', DockerRunCreateView.as_view()),
    # docker-compose文件创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/docker_compose$', DockerComposeCreateView.as_view()),
    # 应用检测
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/check$', AppCheck.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/get_check_uuid$', GetCheckUUID.as_view()),
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
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/analyze_plugins',
        AppAnalyzePluginView.as_view()),
    # 应用简要信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/brief', AppBriefView.as_view()),
    # 触发应用自动部署关键字
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/keyword', AppKeywordView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/status', AppStatusView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins$', AppPluginsBriefView.as_view()),
    # 应用组信息修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/group', AppGroupView.as_view()),
    # 应用pod信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/pods', AppPodsView.as_view()),
    # 三方应用pod信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/third_party/pods', ThirdPartyAppPodsView.as_view()),
    # 应用进入容器页面
    # url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/docker', AppDockerView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/docker_console', DockerContainerView.as_view()),
    # 应用访问
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/visit', AppVisitView.as_view()),
    # 应用配置
    # 环境变量配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/envs$', AppEnvView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/envs/(?P<attr_name>[\w\-]+)$',
        AppEnvManageView.as_view()),
    # 构建运行时环境变量配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/build_envs$', AppBuildEnvView.as_view()),
    # 端口配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/ports$',
        AppPortView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/ports/(?P<port>[\w\-]+)$',
        AppPortManageView.as_view()),
    # 拓扑图打开对外端口
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/topological/ports$',
        TopologicalPortView.as_view()),
    # 对外访问tcp端口修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/tcp-ports/(?P<port>[\w\-]+)$',
        AppTcpOuterManageView.as_view()),
    # 持久化路径配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/volumes$', AppVolumeView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/volumes/(?P<volume_id>[\w\-]+)$',
        AppVolumeManageView.as_view()),
    # 服务依赖
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/dependency$', AppDependencyView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/dependency/(?P<dep_service_id>[\w\-]+)$',
        AppDependencyManageView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/un_dependency$',
        AppNotDependencyView.as_view()),
    # 服务挂载
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/mnt$', AppMntView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/mnt/(?P<dep_vol_id>[\w\-]+)$',
        AppMntManageView.as_view()),
    # 域名证书
    url(r'^teams/(?P<tenantName>[\w\-]+)/certificates$', TenantCertificateView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/certificates/(?P<certificate_id>[\w\-]+)$',
        TenantCertificateManageView.as_view()),

    # 服务域名操作
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

    # 5.1网关自定义参数
    url(r'^teams/(?P<tenantName>[\w\-]+)/domain/(?P<rule_id>[\w\-]+)/put_gateway$', GatewayCustomConfigurationView.as_view()),

    # 服务操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/start$', StartAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/stop$', StopAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/restart$', ReStartAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/deploy$', DeployAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/rollback$', RollBackAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/upgrade$', UpgradeAppView.as_view()),
    # 设置服务构建后是否升级属性
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/set/is_upgrade$', ChangeServiceUpgradeView.as_view()),
    # 查询云市安装的应用是否有（小版本，大版本）更新
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/market_service/upgrade$', MarketServiceUpgradeView.as_view()),

    # 批量操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/batch_actions$', BatchActionView.as_view()),
    # 批量删除应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/batch_delete$', BatchDelete.as_view()),
    # 二次确认删除应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/again_delete$', AgainDelete.as_view()),

    # 某个服务的event
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/events$', AppEventView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/event_log$', AppEventLogView.as_view()),
    # 某个服务的日志
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/log$', AppLogView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/log_instance$', AppLogInstanceView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/history_log$', AppHistoryLogView.as_view()),

    # 服务探针
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/probe$', AppProbeView.as_view()),

    # 服务扩容操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/horizontal$',
        HorizontalExtendAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/vertical$', VerticalExtendAppView.as_view()),

    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/extend_method$', AppExtendView.as_view()),
    # 修改服务应用类型标签
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/change/service_type$', ChangeServiceTypeView.as_view()),

    # 修改服务名称
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/change/service_name$', ChangeServiceNameView.as_view()),

    # 代码仓库
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/code/branch$', ServiceCodeBranch.as_view()),

    # 服务监控
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/monitor/query_range$',
        AppMonitorQueryRangeView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/monitor/query$',
        AppMonitorQueryView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/monitor/batch_query$',
        BatchAppMonitorQueryView.as_view()),
    # 服务标签
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/labels$', AppLabelView.as_view()),
    # 添加特性获取可用标签
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/labels/available$', AppLabelAvailableView.as_view()),
    # 应用资源
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/resource$', AppResourceQueryView.as_view()),
    # 获取当前可用全部数据中心
    url(r'^regions$', QyeryRegionView.as_view()),

    # 获取数据中心builder PublicKey
    url(r'^teams/(?P<tenantName>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/publickey$',
        GetRegionPublicKeyView.as_view()),

    # 插件
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins$', PluginCreateView.as_view()),
    # 默认插件创建
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/default$', DefaultPluginCreateView.as_view()),
    # 获取租户下所有插件基础信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/all$', AllPluginBaseInfoView.as_view()),
    # 查询某个插件的基础信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)$', PluginBaseInfoView.as_view()),
    # 查询当前插件被使用的应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/used_services$',
        PluginUsedServiceView.as_view()),
    # 插件历史版本信息查询
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/build-history$',
        AllPluginVersionInfoView.as_view()),
    # 创建新版本
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/new-version$',
        CreatePluginVersionView.as_view()),
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
    url(r'^teams/(?P<team_name>[\w\-]+)/plugin-share/(?P<share_id>[\w\-]+)/complete$',
        PluginShareCompletionView.as_view()),

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
    url(r'^apps$', CenterAppListView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/market_create$', CenterAppView.as_view()),

    # 好雨云市应用同步
    # 同步应用
    # url(r'^teams/(?P<tenantName>[\w\-]+)/apps/all_apps$', DownloadMarketAppGroupView.as_view()),
    # 同步某个应用回来
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/template_details$', DownloadMarketAppGroupTemplageDetailView.as_view()),

    # 查询查询云端app
    url(r'^app_market/all$', CenterAllMarketAppView.as_view()),
    # 查询云端指定版本app
    url(r'^app_market/version$', CenterVersionlMarversionketAppView.as_view()),
    # 下架应用
    url(r'^app_market/manage$', CenterAppManageView.as_view()),

    # 文件上传
    url(r'^files/upload$', ConsoleUploadFileView.as_view()),
    # 云市认证
    url(r'^teams/(?P<tenantName>[\w\-]+)/enterprise/active$', BindMarketEnterpriseAccessTokenView.as_view()),
    # 新版本优化云市认证
    url(r'^teams/(?P<tenantName>[\w\-]+)/enterprise/active/optimiz$', BindMarketEnterpriseOptimizAccessTokenView.as_view()),
    # 获取数据中心协议
    url(r'^teams/(?P<tenantName>[\w\-]+)/protocols$', RegionProtocolView.as_view()),
    # 应用导出
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/export$', CenterAppExportView.as_view()),
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
    # 获取三方服务自定义角色时可给角色绑定的权限选项
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
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/backup/export$',
        GroupAppsBackupExportView.as_view()),

    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/backup/import$',
        GroupAppsBackupImportView.as_view()),

    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/backup$', TeamGroupAppsBackupView.as_view()),
    # 获取团队下的所有备份记录
    url(r'^teams/(?P<tenantName>[\w\-]+)/all/groupapp/backup$', AllTeamGroupAppsBackupView.as_view()),
    # 应用迁移恢复
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/migrate$', GroupAppsMigrateView.as_view()),

    # 迁移与恢复未完成记录查询
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/migrate/record$', MigrateRecordView.as_view()),

    # 应用组数据删除
    url(r'^teams/(?P<tenantName>[\w\-]+)/groupapp/(?P<group_id>[\w\-]+)/delete$', GroupAppsView.as_view()),

    # 源码仓库webhooks回调地址
    url(r'^webhooks/(?P<service_id>[\w\-]+)', WebHooksDeploy.as_view()),
    # 镜像仓库webhooks回调地址
    url(r'^image/webhooks/(?P<service_id>[\w\-]+)', ImageWebHooksDeploy.as_view()),

    # 自定义自动部署回调地址
    url(r'^custom/deploy/(?P<service_id>[\w\-]+)', CustomWebHooksDeploy.as_view()),

    # 获取自动部署回调地址
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/webhooks/get-url', GetWebHooksUrl.as_view()),
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
    # 获取企业下所有团队的列表
    url(r'^enterprise/teams$', AllTeamsView.as_view()),
    url(r'^enterprise/registerstatus$', RegisterStatusView.as_view()),
    # 获取企业信息
    url(r'^enterprise/info$', EnterpriseInfoView.as_view()),
    # 上传证书无用接口（为前端提供）
    url(r'^enterprise/team/certificate$', CertificateView.as_view()),
    # 企业管理员添加用户
    url(r'^enterprise/admin/add-user$', AdminAddUserView.as_view()),
    # # 获取企业下所有用户信息(企业中心中：删除用户)
    # url(r'^enterprise/users$', AllUserView.as_view()),
    # # 企业中心模糊查询团队
    # url(r'^enterprise/tenants/query', TenantsView.as_view()),
    # 查看用户审核状态
    url(r'^user/applicants/status$', UserApplyStatusView.as_view()),
    # 用户申请某个团队
    url(r"^user/applicants/join$", JoinTeamView.as_view()),
    # 查询指定用户可以加入哪些团队
    url(r"^user/jointeams$", TeamUserCanJoin.as_view()),
    # 修改部署密钥
    url(r"^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/webhooks/updatekey$", UpdateSecretKey.as_view()),
    # 修改镜像源
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/image', ImageAppView.as_view()),
    # 查询构建源
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/buildsource', BuildSourceinfo.as_view())
)

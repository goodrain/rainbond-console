# -*- coding: utf8 -*-
from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt

from console.captcha.captcha_code import CaptchaView
from console.views.account import GoorainSsoCallBack, GoodrainSsoNotify
from console.views.account_fee import EnterpriseAccountInfoView, EnterpriseTeamFeeView
from console.views.app_config.app_dependency import AppDependencyView, AppDependencyManageView, AppNotDependencyView
from console.views.app_config.app_domain import TenantCertificateView, TenantCertificateManageView, ServiceDomainView, \
    DomainView
from console.views.app_config.app_env import AppEnvView, AppEnvManageView
from console.views.app_config.app_extend import AppExtendView
from console.views.app_config.app_label import AppLabelView
from console.views.app_config.app_mnt import AppMntView, AppMntManageView
from console.views.app_config.app_perm import ServicePermView
from console.views.app_config.app_port import AppPortView, AppPortManageView
from console.views.app_config.app_probe import AppProbeView
from console.views.app_config.app_volume import AppVolumeView, AppVolumeManageView
from console.views.app_create.app_build import AppBuild, ComposeBuildView
from console.views.app_create.app_check import AppCheck, AppCheckUpdate, GetCheckUUID
from console.views.app_create.docker_compose import DockerComposeCreateView, ComposeCheckView, ComposeCheckUpdate, \
    ComposeDeleteView, GetComposeCheckUUID, ComposeServicesView
from console.views.app_create.docker_run import DockerRunCreateView
from console.views.app_create.source_code import SourceCodeCreateView, AppCompileEnvView
from console.views.app_event import AppEventView, AppEventLogView, AppLogView, AppLogInstanceView, AppHistoryLogView
from console.views.app_manage import ReStartAppView, StopAppView, StartAppView, DeployAppView, BatchActionView, \
    RollBackAppView, HorizontalExtendAppView, VerticalExtendAppView, DeleteAppView
from console.views.app_monitor import AppMonitorQueryRangeView, AppMonitorQueryView
from console.views.app_overview import AppDetailView, AppStatusView, AppPodsView, AppVisitView, AppBriefView, \
    AppPluginsBriefView, AppGroupView, AppAnalyzePluginView
from console.views.center_pool.apps import CenterAppListView
from console.views.center_pool.apps import CenterAppView
from console.views.code_repo import GithubCodeRepoView, GitlabCodeRepoView, ServiceCodeBranch, GithubCallBackView, \
    GitLabUserRegisterView, CodeBranchView
from console.views.file_upload import ConsoleUploadFileView
from console.views.group import TenantGroupView, TenantGroupOperationView
from console.views.jwt_token_view import JWTTokenView
from console.views.logos import ConfigInfoView, AnnouncementView
from console.views.plugin.plugin_config import ConfigPluginManageView, ConfigPreviewView
from console.views.plugin.plugin_create import PluginCreateView
from console.views.plugin.plugin_info import PluginBaseInfoView, PluginEventLogView, AllPluginVersionInfoView, \
    PluginVersionInfoView, AllPluginBaseInfoView, PluginUsedServiceView
from console.views.plugin.plugin_manage import PluginBuildView, CreatePluginVersionView, PluginBuildStatusView
from console.views.public_areas import TeamOverView, ServiceGroupView, GroupServiceView, AllServiceInfo, \
    ServiceEventsView, TeamServiceOverViewView, TopologicalGraphView, GroupServiceDetView, TopologicalInternetView
from console.views.region import RegQuyView, RegSimQuyView, RegUnopenView, OpenRegionView, QyeryRegionView, \
    GetRegionPublicKeyView, PublicRegionListView, RegionResourceDetailView
from console.views.service_docker import DockerContainerView
from console.views.service_share import ServiceShareInfoView, ServiceShareDeleteView, ServiceShareEventList, ServiceShareEventPost, \
    ServiceShareCompleteView, ServiceShareRecordView
from console.views.team import TeamNameModView, TeamDelView, TeamInvView, TeamUserDetaislView, AddTeamView, \
    UserAllTeamView, TeamUserView, UserDelView, UserFuzSerView, TeamUserAddView, TeamExitView
from console.views.user import CheckSourceView, UserLogoutView, UserAddPemView, UserPemTraView, UserPemView
from console.views.user_operation import TenantServiceView, SendResetEmail, PasswordResetBegin, ChangeLoginPassword, \
    UserDetailsView
from console.views.app_config.app_plugin import APPPluginsView, APPPluginInstallView, APPPluginOpenView, APPPluginConfigView    
urlpatterns = patterns(
    '',
    # 获取云帮Logo、标题、github、gitlab配置信息
    url(r'^config/info$', ConfigInfoView.as_view()),
    # 站内消息
    url(r'^announcement$', AnnouncementView.as_view()),

    # 判断是sso还是私有云
    url(r'^checksource$', CheckSourceView.as_view()),
    # 处理SSO登录
    url(r'^sso/callback$', GoorainSsoCallBack.as_view()),
    url(r'^sso/notify$', csrf_exempt(GoodrainSsoNotify.as_view())),
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
    # 添加新用户
    url(r'^teams/(?P<team_name>[\w\-]+)/add-user$', TeamUserAddView.as_view()),
    # 删除团队成员
    url(r'^teams/(?P<team_name>[\w\-]+)/users/batch/delete', UserDelView.as_view()),
    # 修改团队名称
    url(r'^teams/(?P<team_name>[\w\-]+)/modifyname$', TeamNameModView.as_view()),
    # 删除当前团队
    url(r'^teams/(?P<team_name>[\w\-]+)/delete$', TeamDelView.as_view()),
    # 退出当前团队
    url(r'^teams/(?P<team_name>[\w\-]+)/exit$', TeamExitView.as_view()),
    # 邀请注册
    url(r'^teams/(?P<team_name>[\w\-]+)/invitation$', TeamInvView.as_view()),

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

    # 团队应用信息
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/service/over$', TeamServiceOverViewView.as_view()),

    # 应用事件动态
    url(r'teams/(?P<team_name>[\w\-]+)/services/event$', ServiceEventsView.as_view()),

    # 应用组列表
    url(r'^teams/(?P<team_name>[\w\-]+)/overview/groups$', ServiceGroupView.as_view()),
    # 应用组应用列表、状态展示
    url(r'^teams/(?P<team_name>[\w\-]+)/service/group$', GroupServiceView.as_view()),

    # 应用组拓扑图
    # url(r'^teams/(?P<team_name>[\w\-]+)/topological/services', TopologicalGraphView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/topological$', TopologicalGraphView.as_view()),
    # 拓扑图中应用详情
    url(r'^teams/(?P<team_name>[\w\-]+)/topological/services/(?P<serviceAlias>[\w\-]+)$', GroupServiceDetView.as_view()),
    # Internet 拓扑详情
    url(r'^teams/(?P<team_name>[\w\-]+)/(?P<group_id>\d+)/outer-service$', TopologicalInternetView.as_view()),

    # 云市分享应用
    url(r'^teams/(?P<team_name>[\w\-]+)/groups/(?P<group_id>[\w\-]+)/share/record$', ServiceShareRecordView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/info$', ServiceShareInfoView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/giveup$', ServiceShareDeleteView.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events$', ServiceShareEventList.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/events/(?P<event_id>[\w\-]+)', ServiceShareEventPost.as_view()),
    url(r'^teams/(?P<team_name>[\w\-]+)/share/(?P<share_id>[\w\-]+)/complete$', ServiceShareCompleteView.as_view()),

    # 安装应用
    # url(r'^teams/(?P<team_name>[\w\-]+)/service/install$', InstallServiceView.as_view()),

    # 账户与费用相关
    url(r'^enterprise/(?P<team_name>[\w\-]+)/account/info$', EnterpriseAccountInfoView.as_view()),
    url(r'^enterprise/(?P<team_name>[\w\-]+)/team/fee', EnterpriseTeamFeeView.as_view()),
    # 数据中心相关
    url(r'^enterprise/(?P<team_name>[\w\-]+)/regions$', PublicRegionListView.as_view()),
    url(r'^enterprise/(?P<team_name>[\w\-]+)/region/resource$', RegionResourceDetailView.as_view()),

    # 租户数据中心组信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups$', TenantGroupView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/groups/(?P<group_id>[\w\-]+)$',
        TenantGroupOperationView.as_view()),
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
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/status', AppStatusView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins$', AppPluginsBriefView.as_view()),
    # 应用组信息修改
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/group', AppGroupView.as_view()),
    # 应用pod信息
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/pods', AppPodsView.as_view()),
    # 应用进入容器页面
    # url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/docker', AppDockerView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/docker_console', DockerContainerView.as_view()),
    # 应用访问
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/visit', AppVisitView.as_view()),
    ## 应用配置
    # 环境变量配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/envs$', AppEnvView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/envs/(?P<attr_name>[\w\-]+)$',
        AppEnvManageView.as_view()),
    # 端口配置
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/ports$',
        AppPortView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/ports/(?P<port>[\w\-]+)$',
        AppPortManageView.as_view()),
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
    url(r'^teams/(?P<tenantName>[\w\-]+)/domain$', DomainView.as_view()),
    # 服务操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/start$', StartAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/stop$', StopAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/restart$', ReStartAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/deploy$', DeployAppView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/rollback$', RollBackAppView.as_view()),
    # 批量操作
    url(r'^teams/(?P<tenantName>[\w\-]+)/batch_actions$', BatchActionView.as_view()),

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
    # 代码仓库
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/code/branch$', ServiceCodeBranch.as_view()),

    # 服务监控
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/monitor/query_range$',
        AppMonitorQueryRangeView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/monitor/query$',
        AppMonitorQueryView.as_view()),
    # 服务标签
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/labels$', AppLabelView.as_view()),
    # 应用权限
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/perms$', ServicePermView.as_view()),
    # 获取当前可用全部数据中心
    url(r'^regions$', QyeryRegionView.as_view()),

    # 获取数据中心builder PublicKey
    url(r'^teams/(?P<tenantName>[\w\-]+)/regions/(?P<region_name>[\w\-]+)/publickey$', GetRegionPublicKeyView.as_view()),

    # 插件
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins$', PluginCreateView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/all$', AllPluginBaseInfoView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)$', PluginBaseInfoView.as_view()),
    # 查询当前插件被使用的应用
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/used_services$',
        PluginUsedServiceView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/build-history$',
        AllPluginVersionInfoView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/new-version$',
        CreatePluginVersionView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/event-log$',
        PluginEventLogView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)$',
        PluginVersionInfoView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/config$',
        ConfigPluginManageView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/preview$',
        ConfigPreviewView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/build$',
        PluginBuildView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/version/(?P<build_version>[\w\-]+)/status$',
        PluginBuildStatusView.as_view()),

    # 插件与应用相关API
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/pluginlist$', APPPluginsView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/install$', APPPluginInstallView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/open$', APPPluginOpenView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/(?P<serviceAlias>[\w\-]+)/plugins/(?P<plugin_id>[\w\-]+)/configs$', APPPluginConfigView.as_view()),

    # 内部云市应用相关
    url(r'^apps$', CenterAppListView.as_view()),
    url(r'^teams/(?P<tenantName>[\w\-]+)/apps/market_create', CenterAppView.as_view()),

    # 文件上传
    url(r'^files/upload$', ConsoleUploadFileView.as_view()),
)




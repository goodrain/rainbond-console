# -*- coding: utf8 -*-
from django.conf.urls import patterns, url, include

from backends.views.account import AccountCreateView, TenantEnterpriseView, \
    AuthAccessTokenView, EnterpriseFuzzyQueryView
from backends.views.announcement import AllAnnouncementView, AnnouncementView
from backends.views.config import *
from backends.views.event import ServiceOperateView, ServiceOperationDetailView
from backends.views.resource.clusters import *
from backends.views.resource.nodes import *
from backends.views.resource.region import *
from backends.views.tenants import *
from backends.views.users import *
from backends.views.team import *
from backends.views.labels import *
urlpatterns = patterns(
    '',
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # url(r'^api-token-auth', views.obtain_auth_token),
    # url(r'^api-token-auth/', 'rest_framework_jwt.views.obtain_jwt_token'),
    # url(r'^api-token-auth/', ObtainJSONWebToken.as_view(serializer_class=CustomJWTSerializer)),

    url(r'^docs/', include('rest_framework_swagger.urls')),
    # url(r'^oauth2/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    url(r'^v1/tenants/query', TenantsView.as_view()),
    url(r'^v1/users$', AllUserView.as_view()),
    url(r'^v1/users/query$', UserQueryView.as_view()),
    url(r'^v1/tenants/(?P<tenant_name>[\w\-]+)/users/batch/delete', UserBatchDeleteView.as_view()),
    url(r'^v1/tenants/(?P<tenant_name>[\w\-]+)/users$', TenantUserView.as_view()),
    url(r'^v1/tenants/(?P<tenant_name>[\w\-]+)/users/(?P<user_id>[\w\-]+)$', UserView.as_view()),
    # 配置路径
    url(r'^v1/config/logo$', LogoView.as_view()),
    url(r'^v1/config/title$', TitleView.as_view()),
    url(r'^v1/config/safety$', SafetyView.as_view()),
    url(r'^v1/config/safety/regist$', SafetyRegistView.as_view()),
    url(r'^v1/config/safety/tenants$', SafetyTenantView.as_view()),
    url(r'^v1/config/license$', AuthorizationAView.as_view()),
    url(r'^v1/config/github', ConfigGithubView.as_view()),
    url(r'^v1/config/gitlab', ConfigGitlabView.as_view()),
    url(r'^v1/config/hub-config', HubConfigView.as_view()),
    url(r'^v1/config/ftp-config', FtpConfigView.as_view()),
    url(r'^v1/config/code/link$', ConfigCodeView.as_view()),
    url(r'^v1/config/manage$', ConfigManageView.as_view()),

    # 数据中心路径
    url(r'^v1/regions$', RegionView.as_view()),
    url(r'^v1/regions/(?P<region_id>[\w\-]+)$', RegionDetailView.as_view()),
    url(r'^v1/regions/(?P<region_id>[\w\-]+)/status$', RegionStatusView.as_view()),
    # # url(r'^v1/regions/(?P<region_id>[\w\-]+)/tenants/(?P<tenant_name>[\w\-]+)', TenantRegionResourceView.as_view()),
    # # url(r'^v1/regions/resources/manage$', RegionResourceView.as_view()),
    # url(r'^v1/regions/tenants/resources$', TenantRegionResourceView.as_view()),
    # url(r'^v1/regions/tenants/resources/real$', TenantRegionRealResourceView.as_view()),
    # # 数据中心下集群
    url(r'^v1/regions/(?P<region_id>[\w\-]+)/clusters$', ClusterView.as_view()),
    # url(r'^v1/regions/(?P<region_id>[\w\-]+)/clusters/resources$', ClusterResourceView.as_view()),
    # # 数据中心下所有节点
    # url(r'^v1/regions/(?P<region_id>[\w\-]+)/nodes$', RegionNodesView.as_view()),
    # # 所有集群
    # url(r'^v1/clusters$', AllClusterView.as_view()),
    #
    # # 数据中心集群下节点
    # url(r'^v1/regions/(?P<region_id>[\w\-]+)/clusters/(?P<cluster_id>[\w\-]+)/nodes$', NodesView.as_view()),
    # url(r'^v1/regions/(?P<region_id>[\w\-]+)/clusters/(?P<cluster_id>[\w\-]+)/nodes/(?P<node_uuid>[\w\-]+)$',
    #     NodeInfoView.as_view()),
    # url(r'^v1/regions/(?P<region_id>[\w\-]+)/clusters/(?P<cluster_id>[\w\-]+)/nodes/(?P<node_uuid>[\w\-]+)/operate$',
    #     NodeOperateView.as_view()),
    # url(r'^v1/regions/(?P<region_id>[\w\-]+)/clusters/(?P<cluster_id>[\w\-]+)/nodes/(?P<node_uuid>[\w\-]+)/brief$',
    #     NodeBriefInfoView.as_view()),
    # url(r'^v1/regions/(?P<region_id>[\w\-]+)/clusters/(?P<cluster_id>[\w\-]+)/nodes/(?P<node_uuid>(\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)|[\w\-]+)/labels$',
    #     NodeLabelsView.as_view()),

    # 所有节点
    # url(r'^v1/nodes$', AllNodesView.as_view()),

    # 团队路径
    url(r'^v1/teams$', AllTeamView.as_view()),
    url(r'^v1/teams/(?P<tenant_name>[\w\-]+)$', TeamView.as_view()),
    url(r'^v1/teams/(?P<tenant_name>[\w\-]+)/users/(?P<user_name>[\w\-]+)$', TeamUserView.as_view()),
    url(r'^v1/teams/(?P<tenant_name>[\w\-]+)/add-user$', AddTeamUserView.as_view()),
    url(r'^v1/teams/(?P<tenant_name>[\w\-]+)/regions$', TeamUsableRegionView.as_view()),
    # 标签路径
    url(r'^v1/labels$', AllLabelsView.as_view()),
    url(r'^v1/query/label', QueryLabelView.as_view()),
    url(r'^v1/labels/(?P<label_id>[\w\-]+)$', LabelView.as_view()),
    # 公告路径
    url(r'^v1/announcement$', AllAnnouncementView.as_view()),
    url(r'^v1/announcement/(?P<announcement_id>[\w\-]+)$', AnnouncementView.as_view()),
    # 管理后台初始化云帮

    url(r'^v1/account/create$', AccountCreateView.as_view()),
    url(r'^v1/account/auth-user-token$', AuthAccessTokenView.as_view()),

    url(r'^v1/enterprise/fuzzy_query$', EnterpriseFuzzyQueryView.as_view()),
    url(r'^v1/enterprise/(?P<enterprise_id>[\w\-]+)$', TenantEnterpriseView.as_view()),

    # 操作汇总
    url(r'^v1/events$', ServiceOperateView.as_view()),
    url(r'^v1/events/detail$', ServiceOperationDetailView.as_view()),
)


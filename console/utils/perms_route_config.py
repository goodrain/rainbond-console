# -*- coding: utf-8 -*-
import copy
from collections import Counter
"""
- enterprise 100
    sub1 -- 101
    sub2 -- 102
    ...
- team 200
- app 300
- component 400
- accessStrategy 500
- certificate 600
- plugin 700
"""

ENTERPRISE = {
    "perms": []
}

TEAM = {
    "perms": [
        ["describe", u"获取", 200001],
        ["region_describe", u"获取集群", 200002],
        ["region_install", u"挂载集群", 200003],
        ["region_uninstall", u"卸载集群", 200004],

        ["member_describe", u"获取成员", 200005],
        ["member_create", u"创建成员", 200006],
        ["member_edit", u"编辑成员", 200007],
        ["member_delete", u"删除成员", 200008],

        ["dynamic_describe", u"获取动态", 200009],

        ["rule_describe", u"获取角色", 200010],
        ["rule_create", u"创建角色", 200011],
        ["rule_edit", u"编辑角色", 200012],
        ["rule_delete", u"删除角色", 200013],

    ],
    "app": {
        "perms": [
            ["describe", u"获取", 300001],
            ["create", u"创建", 300002],
            ["edit", u"编辑", 300003],
            ["delete", u"删除", 300004],

            ["start", u"启动", 300005],
            ["stop", u"停用", 300006],
            ["update", u"更新", 300007],
            ["construct", u"构建", 300008],


            ["backup", u"备份", 300009],
            ["migrate",  u"迁移", 300010],
            ["restore",  u"恢复", 300011],
            ["share",  u"发布", 300012],
            ["upgrade",  u"升级", 300013],
            ["copy", u"复制", 300014],
        ]
    },
    "component": {
        "perms": [
            ["describe", u"获取", 400001],
            ["create", u"创建", 400002],
            ["edit", u"编辑", 400003],
            ["delete", u"删除", 400004],
            ["visit_web_terminal", u"访问web终端", 400005],

            ["start", u"启动", 400006],
            ["restart", u"重启", 400007],
            ["stop", u"关闭", 400008],
            ["update", u"更新", 400009],
            ["construct", u"构建", 400010],
            ["rollback", u"回滚", 400011],

            ["telescopic", u"伸缩管理", 400012],
            ["env", u"环境管理", 400013],
            ["rely", u"依赖管理", 400014],
            ["storage", u"存储管理", 400015],
            ["port", u"端口管理", 400016],
            ["plugin", u"插件管理", 400017],
            ["source", u"构建源管理", 400018],
            ["deploy_type", u"部署类型", 400019],
            ["characteristic", u"特性", 400020],
            ["health", u"健康检测", 400021],
        ]
    },
    "gatewayRule": {
        "perms": [
            ["describe", u"获取", 500001],
            ["create", u"创建", 500002],
            ["edit", u"编辑", 500003],
            ["delete", u"删除", 500004],
        ]

    },
    "certificate": {
        "perms": [
            ["describe", u"获取", 600001],
            ["create", u"创建", 600002],
            ["edit", u"编辑", 600003],
            ["delete", u"删除", 600004],
        ]
    },
    "plugin": {
        "perms": [
            ["get", u"获取", 700001],
            ["create", u"创建", 700002],
            ["edit", u"编辑", 700003],
            ["delete", u"删除", 700004],
        ]
    }
}

DEFAULT_ENTERPRISE_ROLE_PERMS = {
    "admin": [],
    "developer": [],
    "viewer": [],
}

DEFAULT_TEAM_ROLE_PERMS = {
    "admin": [200001, 200002, 200003, 200004, 200005, 200006, 200007, 200008, 200009, 200010,
              200011, 200012, 200013, 300001, 300002, 300003, 300004, 300005, 300006, 300007,
              300008, 300009, 300010, 300011, 300012, 300013, 300014, 400001, 400002, 400003,
              400004, 400005, 400006, 400007, 400008, 400009, 400010, 400011, 400012, 400013,
              400014, 400015, 400016, 400017, 400018, 400019, 400020, 400021, 500001, 500002,
              500003, 500004, 600001, 600002, 600003, 600004, 700001, 700002, 700003, 700004],
    "developer": [200001, 200002, 200005, 200009, 200010, 300001, 300002, 300003, 300005, 300006,
                  300007, 300008, 300009, 300010, 300011, 300012, 300013, 300014, 400001, 400002,
                  400003, 400005, 400006, 400007, 400008, 400009, 400010, 400011, 400012, 400013,
                  400014, 400015, 400016, 400017, 400018, 400019, 400020, 400021, 500001, 500002,
                  500003, 600001, 600002, 600003, 700001, 700002, 700003],
    "viewer": [200001, 200002, 200005, 200009, 200010, 300001, 400001, 500001, 600001, 700001],
}

OauthConfig = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [100000]},
        "delete": {"perms": []}
    }
}

OauthService = {
    "__message":{
        "get": {"perms": [100000]},
        "post": {"perms": [100000]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

OauthServiceInfo = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [100000]}
    }
}

TeamRolesPermsLView = {
    "__message":{
        "get": {"perms": [200001, 200010]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamRolePermsRUDView = {
    "__message":{
        "get": {"perms": [200001, 200010]},
        "post": {"perms": []},
        "put": {"perms": [200010, 200012]},
        "delete": {"perms": []}
    }
}

TeamRolesLCView = {
    "__message":{
        "get": {"perms": [200001, 200010]},
        "post": {"perms": [200010, 200011]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamRolesRUDView = {
    "__message":{
        "get": {"perms": [200001, 200010]},
        "post": {"perms": []},
        "put": {"perms": [200010, 200012]},
        "delete": {"perms": [200013]}
    }
}

TeamUsersRolesLView = {
    "__message":{
        "get": {"perms": [200001, 200005, 200010]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamUserRolesRUDView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [200007, 200010]},
        "delete": {"perms": [200008]}
    }
}

TeamUserPermsLView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [200011]},
        "put": {"perms": [200012]},
        "delete": {"perms": [200013]}
    }
}

UserPemTraView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [200000]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AddTeamView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [100000]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamUserView = {
    "__message":{
        "get": {"perms": [200001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

NotJoinTeamUserView = {
    "__message":{
        "get": {"perms": [200001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

UserDelView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [200008]}
    }
}

TeamNameModView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [200000]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamDelView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [100000]}
    }
}

AppGroupVisitView = {
    "__message":{
        "get": {"perms": [400001, 300001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamSortDomainQueryView = {
    "__message":{
        "get": {"perms": [200001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamSortServiceQueryView = {
    "__message":{
        "get": {"perms": [200001, 400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

RegQuyView = {
    "__message":{
        "get": {"perms": [200001, 200002]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

RegUnopenView = {
    "__message":{
        "get": {"perms": [200001, 200002]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

OpenRegionView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [200003]},
        "put": {"perms": []},
        "patch": {"perms": [200003]},
        "delete": {"perms": [200004]}
    }
}

TeamOverView = {
    "__message":{
        "get": {"perms": [200001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AllServiceInfo = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [200001, 300001, 400001]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamAppSortViewView = {
    "__message":{
        "get": {"perms": [200001, 300001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamServiceOverViewView = {
    "__message":{
        "get": {"perms": [200001, 300001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ServiceEventsView = {
    "__message":{
        "get": {"perms": [200009]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TenantServiceEnvsView = {
    "__message":{
        "get": {"perms": [400013]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ServiceGroupView = {
    "__message":{
        "get": {"perms": [300001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GroupServiceView = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TopologicalGraphView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GroupServiceDetView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TopologicalInternetView = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ServiceShareRecordView = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

ServiceShareRecordInfoView = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

ShareRecordView = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

ServiceGroupSharedApps = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

ShareRecordHistoryView = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

ServiceShareInfoView = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

ServiceShareDeleteView = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

ServiceShareEventList = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

ServiceShareEventPost = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

ServicePluginShareEventPost = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

ServiceShareCompleteView = {
    "__message":{
        "get": {"perms": [300012]},
        "post": {"perms": [300012]},
        "put": {"perms": [300012]},
        "delete": {"perms": [300012]}
    }
}

TenantGroupView = {
    "__message":{
        "get": {"perms": [300001]},
        "post": {"perms": [300002]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TenantGroupOperationView = {
    "__message":{
        "get": {"perms": [300001]},
        "post": {"perms": []},
        "put": {"perms": [300003]},
        "delete": {"perms": [300004]}
    }
}

GroupStatusView = {
    "__message":{
        "get": {"perms": [300001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}
# 权限在内部验证
TenantGroupCommonOperationView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

SourceCodeCreateView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [300001, 300002, 300005, 300007, 300008, 400001, 400002, 400003, 400006, 400009, 400010]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ThirdPartyServiceCreateView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [300001, 300002, 400001, 400002]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ThirdPartyServiceApiView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [300001, 300002, 400001, 400002]},
        "put": {"perms": [300001, 300002, 400001, 400002]},
        "delete": {"perms": [300001, 300002, 400001, 400002]}
    }
}

ThirdPartyUpdateSecretKeyView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [400001, 400003]},
        "delete": {"perms": []}
    }
}

ThirdPartyHealthzView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": [400001, 400021]},
        "delete": {"perms": []}
    }
}

DockerRunCreateView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [300001, 300002, 300005, 300007, 300008, 400001, 400002, 400003, 400006, 400009, 400010]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

DockerComposeCreateView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [300001, 300002, 300005, 300007, 300008, 400001, 400002, 400003, 400006, 400009, 400010]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppCheck = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": [300001, 400001]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GetCheckUUID = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

MultiAppCheckView = {
    "__message":{
        "get": {"perms": [300001, 300002, 400001, 400002]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

MultiAppCreateView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [300001, 300002, 300005, 300007, 300008, 400001, 400002, 400003, 400006, 400009, 400010]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppCheckUpdate = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [300001, 300002, 400001, 400002]},
        "delete": {"perms": []}
    }
}

ComposeCheckUpdate = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [300001, 300002, 400001, 400002]},
        "delete": {"perms": []}
    }
}

ComposeCheckView = {
    "__message":{
        "get": {"perms": [300001, 300002, 400001, 400002]},
        "post": {"perms": [300001, 300002, 400001, 400002]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GetComposeCheckUUID = {
    "__message":{
        "get": {"perms": [300001, 300002, 400001, 400002]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ComposeBuildView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [300001, 300002, 300008, 400001, 400002, 400009, 400010]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ComposeDeleteView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [300001, 300002, 300004, 400001, 400002, 400004]}
    }
}

ComposeServicesView = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ComposeContentView = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppBuild = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [400001, 400009, 400010]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppCompileEnvView = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": []},
        "put": {"perms": [300001, 300002, 300003, 300005, 300007, 300008, 400001, 400002, 400003, 400006, 400009, 400010]},
        "delete": {"perms": []}
    }
}

DeleteAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [300004, 400004]}
    }
}

AppDetailView = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppAnalyzePluginView = {
    "__message":{
        "get": {"perms": [300001, 400001, 400017, 700001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppBriefView = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": []},
        "put": {"perms": [300001, 300003, 400001]},
        "delete": {"perms": []}
    }
}

AppKeywordView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [300001, 400001, 400003, 400018]},
        "delete": {"perms": []}
    }
}

AppStatusView = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppPluginsBriefView = {
    "__message":{
        "get": {"perms": [300001, 400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppGroupView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [300001, 300003, 400001, 400003]},
        "delete": {"perms": []}
    }
}

ListAppPodsView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": [400001, 400005]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppPodsView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ThirdPartyAppPodsView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": [400003]},
        "put": {"perms": [400003]},
        "delete": {"perms": [400003]}
    }
}

DockerContainerView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppVisitView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppEnvView = {
    "__message":{
        "get": {"perms": [400001, 400013]},
        "post": {"perms": [400013]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppEnvManageView = {
    "__message":{
        "get": {"perms": [400001, 400013]},
        "post": {"perms": [400013]},
        "put": {"perms": [400013]},
        "patch": {"perms": [400013]},
        "delete": {"perms": [400013]}
    }
}

AppBuildEnvView = {
    "__message":{
        "get": {"perms": [400001, 400013]},
        "post": {"perms": []},
        "put": {"perms": [400013]},
        "delete": {"perms": []}
    }
}

AppPortView = {
    "__message":{
        "get": {"perms": [400001, 400016]},
        "post": {"perms": [400016]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppPortManageView = {
    "__message":{
        "get": {"perms": [400001, 400016]},
        "post": {"perms": [400016]},
        "put": {"perms": [400016]},
        "delete": {"perms": [400016]}
    }
}

TopologicalPortView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [400001, 400016]},
        "delete": {"perms": []}
    }
}

AppTcpOuterManageView = {
    "__message":{
        "get": {"perms": [400001, 400016]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppVolumeOptionsView = {
    "__message":{
        "get": {"perms": [400001, 400015]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppVolumeView = {
    "__message":{
        "get": {"perms": [400001, 400015]},
        "post": {"perms": [400015]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppVolumeManageView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [400015]},
        "delete": {"perms": [400015]}
    }
}

AppDependencyView = {
    "__message":{
        "get": {"perms": [400001, 400014]},
        "post": {"perms": [400014]},
        "put": {"perms": []},
        "patch": {"perms": [400014]},
        "delete": {"perms": []}
    }
}

AppDependencyManageView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [400014]}
    }
}

AppNotDependencyView = {
    "__message":{
        "get": {"perms": [400014]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppMntView = {
    "__message":{
        "get": {"perms": [400001, 400014]},
        "post": {"perms": [400014]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppMntManageView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [400014]}
    }
}

TenantCertificateView = {
    "__message":{
        "get": {"perms": [400001, 600001]},
        "post": {"perms": [400001, 400003, 600001, 600002]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TenantCertificateManageView = {
    "__message":{
        "get": {"perms": [400001, 600001]},
        "post": {"perms": []},
        "put": {"perms": [400001, 400003, 600003]},
        "delete": {"perms": [400001, 400003, 600004]}
    }
}

ServiceDomainView = {
    "__message":{
        "get": {"perms": [400001, 400016, 600001]},
        "post": {"perms": [400001, 400003, 400016, 600001]},
        "put": {"perms": []},
        "delete": {"perms": [400001, 400003, 400016, 600004]}
    }
}

SecondLevelDomainView = {
    "__message":{
        "get": {"perms": [400001, 400016, 600001]},
        "post": {"perms": []},
        "put": {"perms": [400001, 400003, 400016, 600001, 600003]},
        "delete": {"perms": []}
    }
}

DomainView = {
    "__message":{
        "get": {"perms": [400001, 400016, 600001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

DomainQueryView = {
    "__message":{
        "get": {"perms": [400001, 400016, 600001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

HttpStrategyView = {
    "__message":{
        "get": {"perms": [400001, 400016, 500001]},
        "post": {"perms": [400001, 400003, 400016, 500002]},
        "put": {"perms": [400001, 400003, 400016, 500003]},
        "delete": {"perms": [400001, 400003, 400016, 500004]}
    }
}

GetSeniorUrlView = {
    "__message":{
        "get": {"perms": [400001, 400016, 500001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ServiceTcpDomainQueryView = {
    "__message":{
        "get": {"perms": [400001, 400016, 500001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GetPortView = {
    "__message":{
        "get": {"perms": [400001, 400016, 500001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ServiceTcpDomainView = {
    "__message":{
        "get": {"perms": [400001, 400016, 500001]},
        "post": {"perms": [400016, 500002]},
        "put": {"perms": [400016, 500003]},
        "delete": {"perms": [400016, 500004]}
    }
}

AppServiceTcpDomainQueryView = {
    "__message":{
        "get": {"perms": [400001, 400016, 500001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppServiceDomainQueryView = {
    "__message":{
        "get": {"perms": [400001, 400016, 500001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GatewayCustomConfigurationView = {
    "__message":{
        "get": {"perms": [400001, 400016, 500001]},
        "post": {"perms": []},
        "put": {"perms": [400016, 500003]},
        "delete": {"perms": []}
    }
}

StartAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [400006]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

StopAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [400008]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ReStartAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [400007]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

DeployAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [400010, 400009]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

RollBackAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [400011]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

UpgradeAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [400009]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ChangeServiceUpgradeView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [400010, 400009]},
        "delete": {"perms": []}
    }
}

MarketServiceUpgradeView = {
    "__message":{
        "get": {"perms": [400001, 400009]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

BatchActionView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

BatchDelete = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [400004]}
    }
}

AgainDelete = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [400004]}
    }
}

AppEventView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppLogView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppEventLogView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppLogInstanceView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppHistoryLogView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppProbeView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": [400003]},
        "put": {"perms": [400003]},
        "delete": {"perms": [400003]}
    }
}

HorizontalExtendAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [400003, 400012]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

VerticalExtendAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [400003, 400012]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppExtendView = {
    "__message":{
        "get": {"perms": [400001, 400012]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ListAppAutoscalerView = {
    "__message":{
        "get": {"perms": [400001, 400012]},
        "post": {"perms": [400003, 400012]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppAutoscalerView = {
    "__message":{
        "get": {"perms": [400001, 400012]},
        "post": {"perms": []},
        "put": {"perms": [400003, 400012]},
        "delete": {"perms": []}
    }
}

AppScalingRecords = {
    "__message":{
        "get": {"perms": [400001, 400012]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ChangeServiceTypeView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [400019]},
        "delete": {"perms": []}
    }
}

ChangeServiceNameView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [400003]},
        "delete": {"perms": []}
    }
}

ServiceCodeBranch = {
    "__message":{
        "get": {"perms": [400001, 400018]},
        "post": {"perms": []},
        "put": {"perms": [400018]},
        "delete": {"perms": []}
    }
}

AppMonitorQueryRangeView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppMonitorQueryView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

BatchAppMonitorQueryView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppLabelView = {
    "__message":{
        "get": {"perms": [400001, 400020]},
        "post": {"perms": [400020]},
        "put": {"perms": []},
        "delete": {"perms": [400020]}
    }
}

AppLabelAvailableView = {
    "__message":{
        "get": {"perms": [400001, 400020]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppResourceQueryView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GetRegionPublicKeyView = {
    "__message":{
        "get": {"perms": [200001, 200002]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

PluginCreateView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700004]}
    }
}

DefaultPluginCreateView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700004]}
    }
}

AllPluginBaseInfoView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700004]}
    }
}

PluginBaseInfoView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700004]}
    }
}

PluginUsedServiceView = {
    "__message":{
        "get": {"perms": [400017, 700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700004]}
    }
}

AllPluginVersionInfoView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700004]}
    }
}

CreatePluginVersionView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700004]}
    }
}

PluginEventLogView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700004]}
    }
}

PluginVersionInfoView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700004]}
    }
}

ConfigPluginManageView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

ConfigPreviewView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

PluginBuildView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

PluginBuildStatusView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700002]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

ServicePluginsView = {
    "__message":{
        "get": {"perms": [400017, 700001]},
        "post": {"perms": [400017, 700001]},
        "put": {"perms": [400017, 700001]},
        "delete": {"perms": [400017, 700001]}
    }
}

ServicePluginInstallView = {
    "__message":{
        "get": {"perms": [400017, 700001]},
        "post": {"perms": [400017, 700001]},
        "put": {"perms": [400017, 700001]},
        "delete": {"perms": [400017, 700001]}
    }
}

ServicePluginOperationView = {
    "__message":{
        "get": {"perms": [400017, 700001]},
        "post": {"perms": [400017, 700001]},
        "put": {"perms": [400017, 700001]},
        "delete": {"perms": [400017, 700001]}
    }
}

ServicePluginConfigView = {
    "__message":{
        "get": {"perms": [400017, 700001]},
        "post": {"perms": [400017, 700001]},
        "put": {"perms": [400017, 700001]},
        "delete": {"perms": [400017, 700001]}
    }
}

PluginShareRecordView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

PluginShareInfoView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

PluginShareEventsView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

PluginShareEventView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

PluginShareCompletionView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

MarketPluginsView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

SyncMarketPluginsView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

SyncMarketPluginTemplatesView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

UninstallPluginTemplateView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

InstallMarketPlugin = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

InternalMarketPluginsView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

InstallableInteralPluginsView = {
    "__message":{
        "get": {"perms": [700001]},
        "post": {"perms": [700003]},
        "put": {"perms": [700003]},
        "delete": {"perms": [700003]}
    }
}

CenterAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [300001, 300002, 300005, 300007, 300008, 400001, 400002, 400006, 400009, 400010]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

RegionProtocolView = {
    "__message":{
        "get": {"perms": [200001, 200002]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

CenterAppUploadView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [300015]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ImportingRecordView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [300015]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

CenterAppImportingAppsView = {
    "__message":{
        "get": {"perms": [300015]},
        "post": {"perms": [300015]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

CenterAppImportView = {
    "__message":{
        "get": {"perms": [300015]},
        "post": {"perms": [300015]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

ExportFileDownLoadView = {
    "__message":{
        "get": {"perms": [300016]},
        "post": {"perms": [300016]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamAddUserView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [200006, 200010]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GroupAppsBackupView = {
    "__message":{
        "get": {"perms": [300001, 300009]},
        "post": {"perms": [300009]},
        "put": {"perms": [300009]},
        "delete": {"perms": [300009]}
    }
}

GroupAppsBackupStatusView = {
    "__message":{
        "get": {"perms": [300001, 300009]},
        "post": {"perms": [300009]},
        "put": {"perms": [300009]},
        "delete": {"perms": [300009]}
    }
}

GroupAppsBackupExportView = {
    "__message":{
        "get": {"perms": [300001, 300009]},
        "post": {"perms": [300009]},
        "put": {"perms": [300009]},
        "delete": {"perms": [300009]}
    }
}

GroupAppsBackupImportView = {
    "__message":{
        "get": {"perms": [300001, 300009]},
        "post": {"perms": [300009]},
        "put": {"perms": [300009]},
        "delete": {"perms": [300009]}
    }
}

TeamGroupAppsBackupView = {
    "__message":{
        "get": {"perms": [300001, 300009]},
        "post": {"perms": [300009]},
        "put": {"perms": [300009]},
        "delete": {"perms": [300009]}
    }
}

GroupAppsCopyView = {
    "__message":{
        "get": {"perms": [300001, 300014]},
        "post": {"perms": [300014]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AllTeamGroupAppsBackupView = {
    "__message":{
        "get": {"perms": [300001, 300009]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GroupAppsMigrateView = {
    "__message":{
        "get": {"perms": [300001, 300010]},
        "post": {"perms": [300010]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

MigrateRecordView = {
    "__message":{
        "get": {"perms": [300001, 300009, 300010]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GroupAppsView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [300004]}
    }
}

AppVersionsView = {
    "__message":{
        "get": {"perms": [300001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppVersionManageView = {
    "__message":{
        "get": {"perms": [300001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [300004]}
    }
}

ApplicantsView = {
    "__message":{
        "get": {"perms": [300001, 200009]},
        "post": {"perms": [200006, 200010]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AdminAddUserView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [100000]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

UpdateSecretKey = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [400003]},
        "delete": {"perms": []}
    }
}

ImageAppView = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [400018]},
        "delete": {"perms": []}
    }
}

BuildSourceinfo = {
    "__message":{
        "get": {"perms": [400001, 400018]},
        "post": {"perms": []},
        "put": {"perms": [400018]},
        "delete": {"perms": []}
    }
}

AppEventsView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AppEventsLogView = {
    "__message":{
        "get": {"perms": [400001]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

GroupAppView = {
    "__message":{
        "get": {"perms": [300001, 400001, 300013]},
        "post": {"perms": [300013]},
        "put": {"perms": [300013]},
        "delete": {"perms": [300013]}
    }
}

AppUpgradeVersion = {
    "__message":{
        "get": {"perms": [300001, 400001, 300013]},
        "post": {"perms": [300013]},
        "put": {"perms": [300013]},
        "delete": {"perms": [300013]}
    }
}

AppUpgradeRecordsView = {
    "__message":{
        "get": {"perms": [300001, 400001, 300013]},
        "post": {"perms": [300013]},
        "put": {"perms": [300013]},
        "delete": {"perms": [300013]}
    }
}

AppUpgradeRecordView = {
    "__message":{
        "get": {"perms": [300001, 400001, 300013]},
        "post": {"perms": [300013]},
        "put": {"perms": [300013]},
        "delete": {"perms": [300013]}
    }
}

AppUpgradeInfoView = {
    "__message":{
        "get": {"perms": [300001, 400001, 300013]},
        "post": {"perms": [300013]},
        "put": {"perms": [300013]},
        "delete": {"perms": [300013]}
    }
}

AppUpgradeTaskView = {
    "__message":{
        "get": {"perms": [300001, 400001, 300013]},
        "post": {"perms": [300013]},
        "put": {"perms": [300013]},
        "delete": {"perms": [300013]}
    }
}

AppUpgradeRollbackView = {
    "__message":{
        "get": {"perms": [300001, 400001, 300013]},
        "post": {"perms": [300013]},
        "put": {"perms": [300013]},
        "delete": {"perms": [300013]}
    }
}











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

OauthConfigPerms = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": [100000]},
        "delete": {"perms": []}
    }
}

OauthServicePerms = {
    "__message":{
        "get": {"perms": [100000]},
        "post": {"perms": [100000]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

OauthServiceInfoPerms = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": [100000]}
    }
}

TeamRolesPermsLViewPerms = {
    "__message":{
        "get": {"perms": [200001, 200010]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamRolePermsRUDViewPerms = {
    "__message":{
        "get": {"perms": [200001, 200010]},
        "post": {"perms": []},
        "put": {"perms": [200010, 200012]},
        "delete": {"perms": []}
    }
}

TeamRolesLCViewPerms = {
    "__message":{
        "get": {"perms": [200001, 200010]},
        "post": {"perms": [200010, 200011]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamRolesRUDViewPerms = {
    "__message":{
        "get": {"perms": [200001, 200010]},
        "post": {"perms": []},
        "put": {"perms": [200010, 200012]},
        "delete": {"perms": [200013]}
    }
}

TeamUsersRolesLViewPerms = {
    "__message":{
        "get": {"perms": [200001, 200005, 200010]},
        "post": {"perms": []},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamUserRolesRUDViewPerms = {
    "__message":{
        "get": {"perms": [200001, 200005, 200010]},
        "post": {"perms": []},
        "put": {"perms": [200007, 200010]},
        "delete": {"perms": [200008]}
    }
}

TeamUserPermsLViewPerms = {
    "__message":{
        "get": {"perms": [200001, 200010]},
        "post": {"perms": [200011]},
        "put": {"perms": [200012]},
        "delete": {"perms": [200013]}
    }
}

UserPemTraViewPerms = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [200000]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

AddTeamViewPerms = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [100000]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}

TeamUserViewPerms = {
    "__message":{
        "get": {"perms": []},
        "post": {"perms": [100000]},
        "put": {"perms": []},
        "delete": {"perms": []}
    }
}
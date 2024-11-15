# -*- coding: utf-8 -*-
import copy
from collections import Counter

from console.enum.enterprise_enum import EnterpriseRolesEnum
from www.models.main import ServiceGroup
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

# 100000 ~ 199999 for team
ENTERPRISE = {
    "admin": {
        "perms": [
            ["enterprise_info", "企业视图的功能", 100000],
            ["team_info", "团队相关操作", 100001],
            ["users", "企业用户查询和创建", 100002],
            ["query", "用户模糊查询", 100003],
            ["upload", "上传", 100004],
        ]
    },
    "app_store": {
        "perms": [
            ["create_app", "创建应用模板", 110000],
            ["edit_app", "编辑应用模板", 110001],
            ["delete_app", "删除应用模板", 110002],
            ["import_app", "导入应用模板", 110003],
            ["export_app", "导出应用模板", 110004],
            ["create_app_store", "添加应用商店", 110005],
            ["get_app_store", "获取应用商店", 110006],  # Can find access_key
            ["edit_app_store", "编辑应用商店", 110007],
            ["delete_app_store", "删除应用商店", 110008],
            ["edit_app_version", "编辑应用版本", 110009],
            ["delete_app_version", "删除应用版本", 110010],
        ]
    },
}

common_perms = [
    ["create_app", "创建应用模板", 110000],
    ["edit_app", "编辑应用模板", 110001],
    ["delete_app", "删除应用模板", 110002],
    ["import_app", "导入应用模板", 110003],
    ["get_app_store", "获取应用商店", 110006],  # Can find access_key
    # 120000 ~ 129999 enterprise teams
    ["get_ent_teams", "获取企业的团队列表", 120000],
]

APP = {
    "perms": [],
    "app_overview": {
        "perms": [
            ["describe", "查看", 300002],
            ["edit", "编辑", 300003],
            ["delete", "删除", 300004],
            ["start", "启动", 300005],
            ["stop", "停用", 300006],
            ["update", "更新", 300007],
            ["construct", "构建", 300008],
            ["restart", "重启", 300012],
            ["create", "组件创建", 300013],
            ["copy", "快速复制", 300009],
            ["visit_web_terminal", "组件访问web终端", 300010],
            ["service_monitor", "组件监控", 300025],
            ["telescopic", "组件伸缩", 300011],
            ["env", "组件环境配置", 300016],
            ["rely", "组件依赖", 300017],
            ["storage", "组件存储", 300018],
            ["port", "组件端口", 300019],
            ["plugin", "组件插件", 300020],
            ["source", "组件构建源", 300021],
            ["safety", "组件安全", 300027],
            ["other_setting", "组件其他设置", 300022],
        ]
    },
    "app_release": {
        "perms": [
            ["describe", "查看", 310004],
            ["share", "发布", 310001],
            ["export", "导出", 310002],
            ["delete", "删除", 310003],
        ]
    },
    "app_gateway_manage": {
        "perms": [],
        "app_gateway_monitor": {
            "perms": [
                ["describe", "查看", 320001],
            ],
        },
        "app_route_manage": {
            "perms": [
                ["describe", "查看", 321001],
                ["create", "创建", 321002],
                ["edit", "编辑", 321003],
                ["delete", "删除", 321004],
            ],
        },
        "app_target_services": {
            "perms": [
                ["describe", "查看", 322001],
                ["create", "创建", 322002],
                ["edit", "编辑", 322003],
                ["delete", "删除", 322004],
            ],
        },
        "app_certificate": {
            "perms": [
                ["describe", "查看", 323001],
                ["create", "创建", 323002],
                ["edit", "编辑", 323003],
                ["delete", "删除", 323004],
            ]
        },
    },
    "app_upgrade": {
        "perms": [
            ["app_model_list", "应用模型列表", 330001],
            ["upgrade_record", "升级记录", 330002],
            ["upgrade", "升级", 330003],
            ["rollback", "回滚", 330004],
        ]
    },
    "app_resources": {
        "perms": [
            ["describe", "查看", 340001],
            ["create", "创建", 340002],
            ["edit", "编辑", 340003],
            ["delete", "删除", 340004],
        ],
    },
    "app_backup": {
        "perms": [
            ["describe", "查看", 350007],
            ["add", "新增备份", 350001],
            ["import", "导入备份", 350002],
            ["recover", "恢复", 350003],
            ["move", "迁移", 350004],
            ["export", "导出", 350005],
            ["delete", "删除", 350006],
        ]
    },
    "app_config_group": {
        "perms": [
            ["describe", "查看", 360001],
            ["create", "创建", 360002],
            ["edit", "编辑", 360003],
            ["delete", "删除", 360004],
        ]
    }
}
'''
注意：以下注释部分是企业版功能，新增权限的时候需要避免冲突！
'''
TEAM = {
    "perms": [],
    "team_overview": {
        "perms": [
            ["describe", "查看团队信息", 200001],
            ["app_list", "查看应用信息", 200002],
            ["resource_limit", "申请资源限额", 200003],
        ],
    },
    "team_app_create": {
        "perms": [
            ["describe", "新建应用", 300001],
        ],
    },
    "team_app_manage": {
        "perms": [],
        "app_overview": {
            "perms": [
                ["describe", "查看", 300002],
                ["edit", "编辑", 300003],
                ["delete", "删除", 300004],
                ["start", "启动", 300005],
                ["stop", "停用", 300006],
                ["update", "更新", 300007],
                ["construct", "构建", 300008],
                ["restart", "重启", 300012],
                ["create", "组件创建", 300013],
                ["copy", "快速复制", 300009],
                ["visit_web_terminal", "组件访问web终端", 300010],
                ["service_monitor", "组件监控", 300025],
                ["telescopic", "组件伸缩", 300011],
                ["env", "组件环境配置", 300016],
                ["rely", "组件依赖", 300017],
                ["storage", "组件存储", 300018],
                ["port", "组件端口", 300019],
                ["plugin", "组件插件", 300020],
                ["source", "组件构建源", 300021],
                ["safety", "组件安全", 300027],
                ["other_setting", "组件其他设置", 300022],
            ]
        },
        "app_release": {
            "perms": [
                ["describe", "查看", 310004],
                ["share", "发布", 310001],
                ["export", "导出", 310002],
                ["delete", "删除", 310003],
            ]
        },
        "app_gateway_manage": {
            "perms": [],
            "app_gateway_monitor": {
                "perms": [
                    ["describe", "查看", 320001],
                ],
            },
            "app_route_manage": {
                "perms": [
                    ["describe", "查看", 321001],
                    ["create", "创建", 321002],
                    ["edit", "编辑", 321003],
                    ["delete", "删除", 321004],
                ],
            },
            "app_target_services": {
                "perms": [
                    ["describe", "查看", 322001],
                    ["create", "创建", 322002],
                    ["edit", "编辑", 322003],
                    ["delete", "删除", 322004],
                ],
            },
            "app_certificate": {
                "perms": [
                    ["describe", "查看", 323001],
                    ["create", "创建", 323002],
                    ["edit", "编辑", 323003],
                    ["delete", "删除", 323004],
                ]
            },
        },
        "app_upgrade": {
            "perms": [
                ["app_model_list", "应用模型列表", 330001],
                ["upgrade_record", "升级记录", 330002],
                ["upgrade", "升级", 330003],
                ["rollback", "回滚", 330004],
            ]
        },
        "app_resources": {
            "perms": [
                ["describe", "查看", 340001],
                ["create", "创建", 340002],
                ["edit", "编辑", 340003],
                ["delete", "删除", 340004],
            ],
        },
        "app_backup": {
            "perms": [
                ["describe", "查看", 350007],
                ["add", "新增备份", 350001],
                ["import", "导入备份", 350002],
                ["recover", "恢复", 350003],
                ["move", "迁移", 350004],
                ["export", "导出", 350005],
                ["delete", "删除", 350006],
            ]
        },
        "app_config_group": {
            "perms": [
                ["describe", "查看", 360001],
                ["create", "创建", 360002],
                ["edit", "编辑", 360003],
                ["delete", "删除", 360004],
            ]
        }
    },
    "team_gateway_manage": {
        "perms": [],
        "team_gateway_monitor": {
            "perms": [
                ["describe", "查看", 400001],
            ],
        },
        "team_route_manage": {
            "perms": [
                ["describe", "查看", 410001],
                ["create", "创建", 410002],
                ["edit", "编辑", 410003],
                ["delete", "删除", 410004],
            ],
        },
        "team_target_services": {
            "perms": [
                ["describe", "查看", 420001],
                ["create", "创建", 420002],
                ["edit", "编辑", 420003],
                ["delete", "删除", 420004],
            ],
        },
        "team_certificate": {
            "perms": [
                ["describe", "查看", 430001],
                ["create", "创建", 430002],
                ["edit", "编辑", 430003],
                ["delete", "删除", 430004],
            ]
        },
    },
    "team_plugin_manage": {
        "perms": [
            ["describe", "查看", 500001],
            ["create", "创建", 500002],
            ["edit", "编辑", 500003],
            ["delete", "删除", 500004],
        ],
    },
    "team_manage": {
        "perms": [],
        "team_dynamic": {
            "perms": [
                ["describe", "查看", 600001],
            ]
        },
        "team_member": {
            "perms": [
                ["describe", "查看", 610001],
                ["create", "创建", 610002],
                ["edit", "编辑", 610003],
                ["delete", "删除", 610004],
            ]
        },
        "team_region": {
            "perms": [
                ["describe", "查看", 620001],
                ["install", "开通", 620002],
                ["uninstall", "卸载", 620003],
            ]
        },
        "team_role": {
            "perms": [
                ["describe", "查看", 630001],
                ["create", "创建", 630002],
                ["edit", "编辑", 630003],
                ["delete", "删除", 630004],
            ]
        },
        "team_registry_auth": {
            "perms": [
                ["describe", "查看", 640001],
                ["create", "创建", 640002],
                ["edit", "编辑", 640003],
                ["delete", "删除", 640004],
            ]
        },
    },
    "listed_manage": {
        "perms": [
            ["describe", "查看", 700001],
            ["create", "创建", 700002],
            ["edit", "编辑", 700003],
            ["delete", "删除", 700004],
        ],
    },
    "application_records": {
        "perms": [
            ["describe", "查看", 800001],
        ],
    },
}

DEFAULT_TEAM_ROLE_PERMS = {
    "管理员": [
        200001, 200002, 300001, 300002, 300003, 300004, 300005, 300006, 300007, 300008, 300009, 300010, 300011, 300012, 300013,
        300014, 300015, 300016, 300017, 300018, 300019, 300020, 300021, 300022, 300023, 300024, 300025, 300026, 310001, 310002,
        310003, 320001, 321001, 321002, 321003, 321004, 322001, 322002, 322003, 322004, 323001, 323002, 323003, 323004, 330001,
        330002, 330003, 330004, 340001, 340002, 340003, 340004, 350001, 350002, 350003, 350004, 350005, 350006, 360001, 360002,
        360003, 360004, 400001, 410001, 410002, 410003, 410004, 420001, 420002, 420003, 420004, 430001, 430002, 430003, 430004,
        500001, 500002, 500003, 500004, 600001, 610001, 610002, 610003, 610004, 620001, 620002, 620003, 620004, 630001, 630002,
        630003, 630004, 640001, 640002, 640003, 640004, 700001, 700002, 700003, 700004, 800001
    ],
    "开发者": [
        200001, 200002, 200003, 300001, 300002, 300003, 300005, 300006, 300007,
        300008, 300013, 300009, 300010, 300025, 300011, 300012, 300016, 300017,
        300018, 300019, 300020, 300021, 300027, 300022, 310004, 310001, 310002,
        320001, 321001, 321002, 321003, 322001, 322002, 322003, 323001, 323002,
        323003, 330001, 330002, 330003, 330004, 340001, 340002, 340003, 350001,
        350002, 350003, 350004, 350005, 360001, 360002, 360003, 400001, 410001,
        410002, 410003, 420001, 420002, 420003, 430001, 430002, 430003, 500001,
        500002, 500003, 600001, 610001, 610002, 610003, 620001, 620002, 630001,
        630002, 630003, 640001, 640002, 640003, 700001, 700002, 700003, 800001
    ],
    "观察者": [
        200001, 200002, 300002, 300025, 300022, 310004, 320001,
        321001, 322001, 323001, 330001, 340001, 360001, 400001, 410001, 420001,
        430001, 500001, 600001, 610001, 620001, 630001, 640001, 700001, 800001
    ],
}


def get_structure(kind, kind_name):
    structure = {
        kind_name: {
            "sub_models": [],
            "perms": [{
                "name": x[0],
                "desc": x[1],
                "code": x[2]
            } for x in kind.get("perms", [])]
        }
    }
    subs = list(kind.keys())
    try:
        subs.remove("perms")
    except ValueError:
        pass
    if subs:
        for sub in subs:
            sub_structure = get_structure(kind[sub], sub)
            structure[kind_name]["sub_models"].append(sub_structure)
    return structure


def get_model(kind, kind_name):
    structure = {kind_name: {"sub_models": [], "perms": [{x[0]: False, "code": x[2]} for x in kind["perms"]]}}
    subs = list(kind.keys())
    if "perms" in subs:
        subs.remove("perms")
    if subs:
        for sub in subs:
            sub_structure = get_model(kind[sub], sub)
            structure[kind_name]["sub_models"].append(sub_structure)
    return structure


def get_team_perms_model():
    return get_model(copy.deepcopy(TEAM), "team")


def get_app_perms_model():
    return get_model(copy.deepcopy(APP), "app")


def get_perms_model():
    perms_model = {}
    team = get_model(copy.deepcopy(TEAM), "team")
    enterprise = get_model(copy.deepcopy(ENTERPRISE), "enterprise")
    perms_model.update(team)
    perms_model.update(enterprise)
    return perms_model


def get_perms_structure(tenant_id):
    perms_structure = {}
    app_ids = ServiceGroup.objects.filter(tenant_id=tenant_id).values_list("ID", flat=True)
    if not app_ids:
        app_ids = []
    team = copy.deepcopy(TEAM)
    removed_value = team.get("team_app_manage")
    app_perms = dict()
    for app_id in app_ids:
        key = "app_" + str(app_id)
        app_perms[key] = removed_value
    team = get_structure(team, "team")
    enterprise = get_structure(copy.deepcopy(ENTERPRISE), "enterprise")
    app = get_structure(app_perms, "app")
    team.get("team").get("sub_models")[2]["team_app_manage"] = app.get("app")
    perms_structure.update(team)
    perms_structure.update(enterprise)
    # perms_structure.update(app)
    return perms_structure


def assemble_perms(perm, group, kind_name):
    perm[0] = '_'.join([group, perm[0]])
    perm.extend([group, kind_name])
    return tuple(perm)


def get_perms(kind, group, kind_name):
    if isinstance(kind, dict) and kind:
        perms_list = []
        if kind.get("perms"):
            perms_list.extend(
                list(map(assemble_perms, kind["perms"], [group] * len(kind["perms"]), [kind_name] * len(kind["perms"]))))
        kind_elements = list(kind.keys())
        if "perms" in kind_elements:
            kind_elements.remove("perms")
        if kind_elements:
            for kind_element in kind_elements:
                kid_perms_list = get_perms(kind[kind_element], kind_element, kind_name)
                if kid_perms_list:
                    perms_list.extend(kid_perms_list)
        return perms_list
    return []


def get_perms_metadata():
    from console.exception.main import ServiceHandleException
    perms = []
    team_perms = get_perms(copy.deepcopy(TEAM), "team", "team")
    enterprise_perms = get_perms(copy.deepcopy(ENTERPRISE), "enterprise", "enterprise")
    perms.extend(team_perms)
    perms.extend(enterprise_perms)
    name = [z[0] for z in [y for y in list(Counter([x[0] for x in perms]).items()) if y[-1] > 1]]
    code = [z[0] for z in [y for y in list(Counter([x[2] for x in perms]).items()) if y[-1] > 1]]
    if name:
        raise ServiceHandleException(msg="init perms error", msg_show="初始化权限列表失败，权限列表存在重复名称: {}".format(','.join(name)))
    if code:
        raise ServiceHandleException(msg="init perms error", msg_show="初始化权限列表失败，权限列表存在重复编码: {}".format(','.join(code)))
    return perms


def check_perms_metadata():
    perms = []
    team_perms = get_perms(copy.deepcopy(TEAM), "team", "team")
    enterprise_perms = get_perms(copy.deepcopy(ENTERPRISE), "enterprise", "enterprise")
    perms.extend(team_perms)
    perms.extend(enterprise_perms)
    name = [z[0] for z in [y for y in list(Counter([x[0] for x in perms]).items()) if y[-1] > 1]]
    code = [z[0] for z in [y for y in list(Counter([x[2] for x in perms]).items()) if y[-1] > 1]]
    if name:
        print(("初始化权限列表失败，权限列表存在重复名称: {}".format(', '.join(name))))
    if code:
        code = [str(x) for x in code]
        print(("初始化权限列表失败，权限列表存在重复编码: {}".format(', '.join(code))))
    return perms


def get_perms_name_code(perms_model, kind_name):
    perms = {}
    sub_models = list(perms_model.keys())
    if "perms" in sub_models:
        sub_models.remove("perms")
    for perm in perms_model.get("perms", []):
        perms.update({'_'.join([kind_name, perm[0]]): perm[2]})
    if sub_models:
        for sub_model in sub_models:
            perms.update(get_perms_name_code(perms_model[sub_model], sub_model))
    return perms


def get_perms_name_code_kv():
    perms = {}
    perms.update(get_perms_name_code(copy.deepcopy(TEAM), "team"))
    perms.update(get_perms_name_code(copy.deepcopy(ENTERPRISE), "enterprise"))
    return perms


def get_perm_code(obj):
    codes = []
    for key in obj:
        if key == "perms":
            for item in obj["perms"]:
                codes.append(item[2])
        if isinstance(obj[key], dict):
            codes.extend(get_perm_code(obj[key]))
    return codes


def get_enterprise_adminer_codes():
    codes = set()
    codes.update(get_perm_code(TEAM))
    codes.update(get_perm_code(ENTERPRISE))
    return codes


def list_enterprise_perm_codes_by_role(role):
    if role == EnterpriseRolesEnum.admin.name:
        return get_enterprise_adminer_codes()

    perms = ENTERPRISE.get(role, [])
    codes = set()
    codes.update([perm[2] for perm in perms["perms"]])
    codes.update([perm[2] for perm in common_perms])
    return codes


def list_enterprise_perm_codes_by_roles(roles):
    codes = set()
    for role in roles:
        codes.update(list_enterprise_perm_codes_by_role(role))
    codes.update([perm[2] for perm in common_perms])
    return codes


def list_enterprise_perms_by_role(role):
    if role == EnterpriseRolesEnum.admin.name:
        perms = set()
        for r in ENTERPRISE:
            if r == "admin":
                # Special handling for admin role.
                # No permissions have been set for admin before.
                continue
            perms.update([r + "." + perm[0] for perm in ENTERPRISE[r]["perms"]])
        return perms

    perms = ENTERPRISE.get(role, [])
    return set([role + "." + perm[0] for perm in perms["perms"]])


def list_enterprise_perms_by_roles(roles):
    perms = set()
    for role in roles:
        perms.update(list_enterprise_perms_by_role(role))
    perms.update(set(["app_store." + perm[0] for perm in common_perms]))
    return perms


if __name__ == '__main__':
    # 检测权限命名和权限编码是否重复
    check_perms_metadata()
    print((get_enterprise_adminer_codes()))
    # print get_perms_structure()
    # print get_perms_model()
    # print get_perms_name_code_kv()

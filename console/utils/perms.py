# -*- coding: utf-8 -*-
import copy
from collections import Counter
from console.enum.enterprise_enum import EnterpriseRolesEnum
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
            # what is What is 10000 and 20000?
            ["", "", 100000],
            ["", "", 200000],
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
    }
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

TEAM = {
    "perms": [
        ["describe", "查看团队信息", 200001],
        ["dynamic_describe", "查看团队动态", 200009],
        ["maven_setting", "管理Maven配置", 200014],
    ],
    "teamRegion": {
        "perms": [["describe", "查看", 200002], ["install", "开通", 200003], ["uninstall", "卸载", 200004]]
    },
    "teamMember": {
        "perms": [
            ["describe", "查看", 200005],
            ["create", "创建", 200006],
            ["edit", "编辑", 200007],
            ["delete", "删除", 200008],
        ]
    },
    "teamRole": {
        "perms": [
            ["describe", "查看", 200010],
            ["create", "创建", 200011],
            ["edit", "编辑", 200012],
            ["delete", "删除", 200013],
        ]
    },
    "app": {
        "perms": [
            ["describe", "查看", 300001],
            ["create", "创建", 300002],
            ["edit", "编辑", 300003],
            ["delete", "删除", 300004],
            ["start", "启动", 300005],
            ["stop", "停用", 300006],
            ["update", "更新", 300007],
            ["construct", "构建", 300008],
            ["backup", "备份", 300009],
            ["migrate", "迁移", 300010],
            ["share", "发布", 300012],
            ["upgrade", "升级", 300013],
            ["copy", "复制", 300014],
            ["import", "导入", 300015],
            ["export", "导出", 300016],
        ]
    },
    "app_config_group": {
        "perms": [
            ["describe", "查看", 300017],
            ["create", "创建", 300018],
            ["edit", "编辑", 300019],
            ["delete", "删除", 300020],
        ]
    },
    "component": {
        "perms": [
            ["describe", "查看", 400001],
            ["create", "创建", 400002],
            ["edit", "编辑", 400003],
            ["delete", "删除", 400004],
            ["visit_web_terminal", "访问web终端", 400005],
            ["start", "启动", 400006],
            ["restart", "重启", 400007],
            ["stop", "关闭", 400008],
            ["update", "更新", 400009],
            ["construct", "构建", 400010],
            ["rollback", "回滚", 400011],
            ["telescopic", "伸缩管理", 400012],
            ["env", "环境管理", 400013],
            ["rely", "依赖管理", 400014],
            ["storage", "存储管理", 400015],
            ["port", "端口管理", 400016],
            ["plugin", "插件管理", 400017],
            ["source", "构建源管理", 400018],
            ["deploy_type", "部署类型", 400019],
            ["characteristic", "特性", 400020],
            ["health", "健康检测", 400021],
            ["service_monitor", "业务监控管理", 400022],
        ]
    },
    "gatewayRule": {
        "perms": [
            ["describe", "查看", 500001],
            ["create", "创建", 500002],
            ["edit", "编辑", 500003],
            ["delete", "删除", 500004],
        ]
    },
    "certificate": {
        "perms": [
            ["describe", "查看", 600001],
            ["create", "创建", 600002],
            ["edit", "编辑", 600003],
            ["delete", "删除", 600004],
        ]
    },
    "plugin": {
        "perms": [
            ["describe", "查看", 700001],
            ["create", "创建", 700002],
            ["edit", "编辑", 700003],
            ["delete", "删除", 700004],
        ]
    }
}

DEFAULT_ENTERPRISE_ROLE_PERMS = {
    "管理员": [],
    "开发者": [],
    "观察者": [],
}

DEFAULT_TEAM_ROLE_PERMS = {
    "管理员": [
        200001, 200002, 200003, 200004, 200005, 200006, 200007, 200008, 200009, 200010, 200011, 200012, 200013, 300001, 300002,
        300003, 300004, 300005, 300006, 300007, 300008, 300009, 300010, 300011, 300012, 300013, 300014, 300017, 300018, 300019,
        300020, 400001, 400002, 400003, 400004, 400005, 400006, 400007, 400008, 400009, 400010, 400011, 400012, 400013, 400014,
        400015, 400016, 400017, 400018, 400019, 400020, 400021, 400022, 500001, 500002, 500003, 500004, 600001, 600002, 600003,
        600004, 700001, 700002, 700003, 700004
    ],
    "开发者": [
        200001, 200002, 200005, 200009, 200010, 300001, 300002, 300003, 300005, 300006, 300007, 300008, 300009, 300010, 300011,
        300012, 300013, 300014, 300017, 300018, 300019, 300020, 400001, 400002, 400003, 400005, 400006, 400007, 400008, 400009,
        400010, 400011, 400012, 400013, 400014, 400015, 400016, 400017, 400022, 400018, 400019, 400020, 400021, 500001, 500002,
        500003, 600001, 600002, 600003, 700001, 700002, 700003
    ],
    "观察者": [200001, 200002, 200005, 200009, 200010, 300001, 400001, 500001, 600001, 700001],
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


def get_enterprise_perms_model():
    return get_model(copy.deepcopy(ENTERPRISE), "enterprise")


def get_perms_model():
    perms_model = {}
    team = get_model(copy.deepcopy(TEAM), "team")
    enterprise = get_model(copy.deepcopy(ENTERPRISE), "enterprise")
    perms_model.update(team)
    perms_model.update(enterprise)
    return perms_model


def get_perms_structure():
    perms_structure = {}
    team = get_structure(copy.deepcopy(TEAM), "team")
    enterprise = get_structure(copy.deepcopy(ENTERPRISE), "enterprise")
    perms_structure.update(team)
    perms_structure.update(enterprise)
    return perms_structure


def assemble_perms(perm, group, kind_name):
    perm[0] = '_'.join([group, perm[0]])
    perm.extend([group, kind_name])
    return tuple(perm)


def get_perms(kind, group, kind_name):
    if isinstance(kind, dict) and kind and kind.get("perms"):
        perms_list = []
        perms_list.extend(list(map(assemble_perms, kind["perms"], [group] * len(kind["perms"]), [kind_name] * len(kind["perms"]))))
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

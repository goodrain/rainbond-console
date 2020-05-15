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


def get_structure(kind, kind_name):
    structure = {kind_name: {"sub_models": [], "perms": map(lambda x: {"name": x[0], "desc": x[1], "code": x[2]}, kind["perms"])}}
    subs = kind.keys()
    subs.remove("perms")
    if subs:
        for sub in subs:
            sub_structure = get_structure(kind[sub], sub)
            structure[kind_name]["sub_models"].append(sub_structure)
    return structure

def get_model(kind, kind_name):
    structure = {kind_name:{"sub_models": [], "perms": map(lambda x: {x[0]: False, "code": x[2]}, kind["perms"])}}
    subs = kind.keys()
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
    if isinstance(kind, dict) and kind:
        perms_list = []
        perms_list.extend(map(assemble_perms, kind["perms"], [group] * len(kind["perms"]), [kind_name] * len(kind["perms"])))
        kind_elements = kind.keys()
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
    name = map(lambda z: z[0], filter(lambda y: y[-1] > 1, Counter(map(lambda x: x[0], perms)).items()))
    code = map(lambda z: z[0], filter(lambda y: y[-1] > 1, Counter(map(lambda x: x[2], perms)).items()))
    if name:
        raise ServiceHandleException(
            msg="init perms error", msg_show="初始化权限列表失败，权限列表存在重复名称: {}".format(','.join(name)))
    if code:
        raise ServiceHandleException(
            msg="init perms error", msg_show="初始化权限列表失败，权限列表存在重复编码: {}".format(','.join(code)))
    return perms


def check_perms_metadata():
    perms = []
    team_perms = get_perms(copy.deepcopy(TEAM), "team", "team")
    enterprise_perms = get_perms(copy.deepcopy(ENTERPRISE), "enterprise", "enterprise")
    perms.extend(team_perms)
    perms.extend(enterprise_perms)
    name = map(lambda z: z[0], filter(lambda y: y[-1] > 1, Counter(map(lambda x: x[0], perms)).items()))
    code = map(lambda z: z[0], filter(lambda y: y[-1] > 1, Counter(map(lambda x: x[2], perms)).items()))
    if name:
        print "初始化权限列表失败，权限列表存在重复名称: {}".format(', '.join(name))
    if code:
        code = map(lambda x: str(x), code)
        print "初始化权限列表失败，权限列表存在重复编码: {}".format(', '.join(code))
    return perms

def get_perms_name_code(perms_model, kind_name):
    perms = {}
    sub_models = perms_model.keys()
    sub_models.remove("perms")
    for perm in perms_model["perms"]:
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

if __name__ == '__main__':
    # 检测权限命名和权限编码是否重复
    check_perms_metadata()
    # print get_perms_structure()
    # print get_perms_model()
    # print get_perms_name_code_kv()

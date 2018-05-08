# -*- coding: utf8 -*-

import logging

logger = logging.getLogger('default')


def status_map():
    status_map = {}
    # 运行中
    status_map["running"] = {
        "status_cn": "运行中",
        "disabledAction": ["restart"],
        "activeAction": ['stop', 'deploy', 'visit', 'manage_container', 'reboot'],
    }
    # region
    status_map["starting"] = {
        "status_cn": "启动中",
        "disabledAction": ['restart', 'visit', 'manage_container'],
        "activeAction": ['deploy', 'stop', 'reboot'],
    }
    # region
    status_map["checking"] = {
        "status_cn": "检测中",
        "disabledAction": ['deploy', 'restart', 'visit', 'manage_container'],
        "activeAction": ["stop", 'reboot'],
    }
    # region
    status_map["stoping"] = {
        "status_cn": "关闭中",
        "disabledAction": ['deploy', 'restart', 'stop', 'visit', 'manage_container','reboot'],
        "activeAction": [],
    }
    # region
    status_map["unusual"] = {
        "status_cn": "运行异常",
        "disabledAction": ['visit', 'restart', 'manage_container'],
        "activeAction": ['stop', 'deploy', 'reboot'],
    }
    # region
    status_map["closed"] = {
        "status_cn": "已关闭",
        "disabledAction": ['visit', "stop", 'manage_container', 'reboot'],
        "activeAction": ['restart', 'deploy'],
    }
    # console
    status_map["owed"] = {
        "status_cn": "余额不足已关闭",
        "disabledAction": ['deploy', 'visit', 'restart', 'stop', 'manage_container', 'reboot'],
        "activeAction": ['pay'],
    }
    # console
    status_map["Owed"] = {
        "status_cn": "余额不足已关闭",
        "disabledAction": ['deploy', 'visit', 'restart', 'stop', 'manage_container', 'reboot'],
        "activeAction": ['pay'],
    }
    # console
    status_map["expired"] = {
        "status_cn": "试用已到期",
        "disabledAction": ['visit', 'restart', 'deploy', 'stop', 'manage_container', 'reboot'],
        "activeAction": ['pay'],
    }
    # console/region
    status_map["undeploy"] = {
        "status_cn": "未部署",
        "disabledAction": ['restart', 'stop', 'visit', 'manage_container', 'reboot'],
        "activeAction": ['deploy'],
    }
    # console
    status_map["unKnow"] = {
        "status_cn": "未知",
        "disabledAction": ['deploy', 'restart', 'visit', 'manage_container'],
        "activeAction": ['stop', 'reboot'],
    }
    # console
    status_map["deployed"] = "已部署"
    status_map["abnormal"] = {
        "status_cn": "运行异常",
        "disabledAction": ['visit', 'restart', 'manage_container'],
        "activeAction": ['stop', 'deploy', 'reboot'],
    }
    # console/region
    status_map["failure"] = {
        "status_cn": "未知",
        "disabledAction": ['deploy', 'restart', 'visit', 'manage_container'],
        "activeAction": ['stop', 'reboot'],
    }
    # region
    status_map["upgrade"] = {
        "status_cn": "升级中",
        "disabledAction": [ 'manage_container'],
        "activeAction": ['stop','visit', 'deploy', 'restart', 'reboot'],
    }
    # region
    status_map["stopping"] = {
        "status_cn": "关闭中",
        "disabledAction": ['deploy', 'restart', 'stop', 'visit', 'manage_container','reboot'],
        "activeAction": [],
    }
    # console
    status_map["uncreate"] = {
        "status_cn": "未部署",
        "disabledAction": [],
        "activeAction": [],
    }
    # console
    status_map["creating"] = {
        "status_cn": "创建中",
        "disabledAction": ['restart', 'stop', 'visit', 'manage_container', 'reboot'],
        "activeAction": ['deploy'],
    }
    return status_map


def get_status_info_map(status):
    status_info_map = status_map().get(status, None)
    rt_map = {}
    if status_info_map:
        rt_map["status"] = status
        rt_map["status_cn"] = status_info_map["status_cn"]
        rt_map["disabledAction"] = status_info_map["disabledAction"]
        rt_map["activeAction"] = status_info_map["activeAction"]
    else:
        rt_map["status"] = status
        rt_map["status_cn"] = "未知"
        rt_map["disabledAction"] = []
        rt_map["activeAction"] = []
    return rt_map

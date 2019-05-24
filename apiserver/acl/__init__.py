# coding: utf-8
"""acl 配置模块
client.yaml 里配置允许访问的客户端 key
policy.csv 里配置 客户端允许访问的资源
"""

__all__ = ["acl", "CLIENTS"]

import os
import yaml
import casbin

ACL_DIR = os.path.dirname(os.path.abspath(__file__))

acl = casbin.Enforcer("{}/model.conf".format(ACL_DIR), "{}/policy.csv".format(ACL_DIR))

# 客户端设置
with open("{}/client.yaml".format(ACL_DIR)) as f:
    clients = yaml.load(f).get('clients')
    if not (clients and isinstance(clients, list)):
        raise ValueError("没有客户端 token")

CLIENTS = set(clients)

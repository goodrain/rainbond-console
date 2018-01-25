# -*- coding: utf8 -*-
import json
import logging

from backends.models.main import RegionConfig, RegionClusterInfo, NodeInstallInfo
from backends.services.clusterservice import cluster_service
from backends.services.exceptions import *
from backends.services.httpclient import HttpInvokeApi
from backends.services.regionservice import region_service
from www.apiclient.regionapi import RegionInvokeApi
from www.models import Tenants, TenantServiceInfo
from www.models.label import *
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")

STATUS_MAP = {"running": "运行中",
              "offline": "离线",
              "online": "在线",
              "installing": "安装中",
              "failed": "失败",
              "unschedulable":"不可调度",
              }

class NodeService(object):
    url = "http://test.goodrain.com:6200"
    default_headers = {
        'Connection': 'keep-alive',
        'Content-Type': 'application/json'
    }
    http_client = HttpInvokeApi()
    region_api = RegionInvokeApi()

    def wapper_node_info(self, node_list, region, cluster):
        for node in node_list:
            status = node["status"]
            node["status_cn"] = STATUS_MAP.get(status, "未知")
            node['region_alias'] = region.region_alias
            node['cluster_alias'] = cluster.cluster_alias
            node['cluster_name'] = cluster.cluster_name
            node["region_name"] = region.region_name
            node["region_id"] = region.region_id
            node["cluster_id"] = cluster.ID
        return node_list

    def get_nodes(self, region_id, cluster_id):
        region = RegionConfig.objects.get(region_id=region_id)
        cluster = RegionClusterInfo.objects.get(ID=cluster_id)
        # 更新请求发送客户端
        list = []
        try:
            self.http_client.update_client(region)

            res, body = self.http_client.get_region_nodes(body=None)
            if 400 <= res.status <= 600:
                return body["code"], body["body"]
            list = body["body"]["list"]
        except Exception as e:
            logger.exception(e)
        node_list = self.wapper_node_info(list, region, cluster)
        return 200, node_list

    # def add_node(self, region_id, cluster_id, **kwargs):
    #     # 此方法已废弃
    #     region = RegionConfig.objects.get(region_id=region_id)
    #     cluster = RegionClusterInfo.objects.get(ID=cluster_id)
    #     self.http_client.update_client(region)
    #
    #     body = kwargs
    #     labels = json.loads(body["labels"])
    #     body["labels"] = labels
    #     uuid = make_uuid()
    #     body["uuid"] = uuid
    #     res, body = self.http_client.add_node(json.dumps(body))
    #     # 为节点记录标签
    #     if 200 <= body["code"] < 300:
    #         all_labels = Labels.objects.all()
    #         # 标签ID和标签英文名称字符串
    #         label_map = {l.label_name: l.label_id for l in all_labels}
    #         node_labels = []
    #         for label_name in labels.keys():
    #             label_id = label_map.get(label_name, None)
    #             if label_id:
    #                 node_label = NodeLabels(
    #                     region_id=region_id,
    #                     cluster_id=cluster_id,
    #                     node_uuid=uuid,
    #                     label_id=label_id,
    #                 )
    #                 node_labels.append(node_label)
    #         NodeLabels.objects.bulk_create(node_labels)
    #     return body["code"], body["body"]

    def get_node_brief_info(self, region_id, cluster_id, node_uuid):
        region = RegionConfig.objects.get(region_id=region_id)
        cluster = RegionClusterInfo.objects.get(ID=cluster_id)
        self.http_client.update_client(region)
        res, body = self.http_client.get_node_brief_info(node_uuid, None)

        result = body["body"]
        result["bean"]["region_id"] = region_id
        result["bean"]["cluster_id"] = cluster_id
        result["bean"]["region_name"] = region.region_name
        result["bean"]["cluster_name"] = cluster.cluster_name
        result["bean"]["region_alias"] = region.region_alias
        result["bean"]["cluster_alias"] = cluster.cluster_alias
        return body["code"], result

    def format_memory(self, memorystr):
        if memorystr.endswith("m".upper()) or memorystr.endswith("m"):
            memory = memorystr[:-1]
            return int(memory.strip())
        else:
            return int(memorystr.strip())

    def get_node_service_details(self, nonterminatedpods):
        tenant_ids = []
        service_alias_list = []
        for info in nonterminatedpods:
            tenant_ids.append(info["namespace"])
            service_alias_list.append(info["id"])
        tenants = Tenants.objects.filter(tenant_id__in=tenant_ids).values("tenant_id", "tenant_name")
        services = TenantServiceInfo.objects.filter(service_alias__in=service_alias_list).values("service_alias",
                                                                                                 "service_cname")
        tenant_id_name_map = {tenant["tenant_id"]: tenant["tenant_name"] for tenant in tenants}
        service_alias_name_map = {service["service_alias"]: service["service_cname"] for service in services}
        for info in nonterminatedpods:
            info["tenant_name"] = tenant_id_name_map.get(info["namespace"], "")
            info["service_cname"] = service_alias_name_map.get(info["id"], "")
        pod_list = sorted(nonterminatedpods, key=lambda pod: (
            self.format_memory(pod["memoryrequests"]), self.format_memory(pod["cpurequest"])),
                          reverse=True)
        return pod_list

    def wapper_node_labels(self, labels):
        all_labels = Labels.objects.all()
        # 标签中文和标签英文名称字符串
        label_map = {l.label_name: l.label_alias for l in all_labels}
        rt_label = {}
        if labels:
            for k in labels.iterkeys():
                val = label_map.get(k, None)
                if val:
                    rt_label[k] = val
        return rt_label

    def get_node_info(self, region_id, cluster_id, node_uuid):
        region = RegionConfig.objects.get(region_id=region_id)
        cluster = RegionClusterInfo.objects.get(ID=cluster_id)
        self.http_client.update_client(region)

        res, body = self.http_client.get_node_info(node_uuid, None)
        if 400 <= res.status <= 600:
            return body["code"], body
        result = body["body"]
        nonterminatedpods = result["bean"].get("nonterminatedpods")
        nonterminatedpods = self.get_node_service_details(nonterminatedpods)
        labels = result["bean"].get("labels")
        labels = self.wapper_node_labels(labels)

        status = result["bean"].get("status")
        result["bean"]["status_cn"] = STATUS_MAP.get(status, "未知")
        result["bean"]["nonterminatedpods"] = nonterminatedpods
        result["bean"]["labels"] = labels
        result["bean"]["region_id"] = region_id
        result["bean"]["cluster_id"] = cluster_id
        result["bean"]["region_name"] = region.region_name
        result["bean"]["cluster_name"] = cluster.cluster_name
        result["bean"]["region_alias"] = region.region_alias
        result["bean"]["cluster_alias"] = cluster.cluster_alias
        return body["code"], result

    def update_node_info(self, region_id, cluster_id, node_uuid, **kwargs):
        # 此方法已废弃
        region = RegionConfig.objects.get(region_id=region_id)
        cluster = RegionClusterInfo.objects.get(ID=cluster_id)
        self.http_client.update_client(region)
        body = kwargs
        labels = json.loads(body["labels"])
        body["labels"] = labels
        res, body = self.http_client.update_node_info(node_uuid, json.dumps(body))
        # 更新节点标签
        if 200 <= body["code"] < 300:
            all_labels = Labels.objects.all()
            # 标签ID和标签英文名称字符串
            label_map = {l.label_name: l.label_id for l in all_labels}
            # 删除原有标签
            NodeLabels.objects.filter(node_uuid=node_uuid).delete()
            node_labels = []
            for label_name in labels.keys():
                label_id = label_map.get(label_name, None)
                if label_id:
                    node_label = NodeLabels(
                        region_id=region_id,
                        cluster_id=cluster_id,
                        node_uuid=node_uuid,
                        label_id=label_id,
                    )
                    node_labels.append(node_label)
            NodeLabels.objects.bulk_create(node_labels)

        return body["code"], body["body"]

    def delete_node(self, region_id, cluster_id, node_uuid):
        """删除节点"""
        region = RegionConfig.objects.get(region_id=region_id)
        cluster = RegionClusterInfo.objects.get(ID=cluster_id)
        self.http_client.update_client(region)
        res, body = self.http_client.delete_node(node_uuid, None)
        result = body["body"]
        return body["code"], result

    def get_all_region_nodes(self):
        regions = region_service.get_all_regions(True)
        # 对每个数据中心下的每个集群查询节点信息
        node_list = []
        for region in regions:

            cluster_list = cluster_service.get_cluster_by_region(region.region_id)
            for cluster in cluster_list:
                status, nodes = self.get_nodes(region.region_id, cluster.ID)
                if status == 200:
                    for node in nodes:
                        node["region_id"] = region.region_id
                        node["cluster_id"] = cluster.ID
                        node["region_alias"] = region.region_alias
                        node["cluster_alias"] = cluster.cluster_alias
                        node_list.append(node)

        sorted_nodes = sorted(node_list, key=lambda node: node["host_name"])
        return sorted_nodes

    def manage_node(self, region_id, cluster_id, node_uuid, action):
        """节点操作"""

        if not action:
            raise ParamsError("未识别操作")
        region = RegionConfig.objects.get(region_id=region_id)
        cluster = RegionClusterInfo.objects.get(ID=cluster_id)
        self.http_client.update_client(region)
        if action == "online":
            res, body = self.http_client.online_node(node_uuid, None)
        elif action == "offline":
            res, body = self.http_client.offline_node(node_uuid, None)
        elif action == "reschedulable":
            res, body = self.http_client.schedulable_node(node_uuid, None)
        elif action == "unschedulable":
            res, body = self.http_client.unschedulable_node(node_uuid, None)
        else:
            raise ParamsError("未识别操作")
        result = body["body"]
        return body["code"], result

    def node_check(self, region_id, data):
        region = RegionConfig.objects.get(region_id=region_id)
        params = {}
        cluster = RegionClusterInfo.objects.get(region_id=region_id)
        host = data.get("host")
        port = data.get("port", 22)
        params["hostport"] = host + ":" + str(port)
        node_type = data.get("node_type")
        params["hosttype"] = node_type
        login_type = data.get("login_type")
        params["pwd"] = None
        params["type"] = False
        if login_type == "root":
            params["type"] = True
            root_pwd = data.get("root_pwd")
            params["pwd"] = root_pwd

        self.http_client.update_client(region)
        res, body = self.http_client.node_login_check(json.dumps(params))
        if 200 <= res.status < 400:
            bean = body["bean"]
            return 200, bean
        else:
            return res.status, body["msg"]

    def node_init(self, region_id, data):
        region = RegionConfig.objects.get(region_id=region_id)
        params = {}
        cluster = RegionClusterInfo.objects.get(region_id=region_id)
        node_ip = data.get("node_ip")
        params["ip"] = node_ip
        self.http_client.update_client(region)
        res, body = self.http_client.node_component_init(node_ip, json.dumps(params))
        logger.debug("res {0} ,body {1}".format(res, body))
        if 200 <= res.status < 400:
            return 200, body["bean"]
        else:
            return int(res.status), body["msg"]

    def node_install(self, region_id, node_ip):
        """节点组件安装"""
        region = RegionConfig.objects.get(region_id=region_id)
        cluster = RegionClusterInfo.objects.get(region_id=region_id)
        self.http_client.update_client(region)
        res, body = self.http_client.node_component_install(node_ip, None)
        if 200 <= res.status < 400:
            return 200, body["bean"]
        else:
            return int(res.status), body["msg"]

    def is_init(self, region_id, node_ip):
        """判断节点是否初始化"""
        nodes = NodeInstallInfo.objects.filter(region_id=region_id, node_ip=node_ip)
        flag = True
        if nodes:
            node = nodes[0]
            if node.init_status == "uninit":
                flag = False
        else:
            NodeInstallInfo.objects.create(region_id=region_id, node_ip=node_ip, init_status="uninit")
            flag = False
        return flag

    def check_init_status(self, region_id, node_ip):
        """检测节点初始化状态"""
        region = RegionConfig.objects.get(region_id=region_id)
        # if not self.is_init(region_id, node_ip):
        #     code, result = self.node_init(region_id, {"node_ip": node_ip})
        #     if code != 200:
        #         body = {}
        #         body["msg_show"] = "初始化指令发送失败"
        #         return code, body
        #     else:
        #         # 表示初始化中
        #         NodeInstallInfo.objects.filter(region_id=region_id, node_ip=node_ip).update(init_status="initing")
        self.http_client.update_client(region)
        res, body = self.http_client.node_init_status(node_ip, None)
        rt_body = {}
        if 200 <= res.status < 400:
            result = body["bean"]
            status = result["status"]
            if status == "failed":
                msg = "初始化失败{0}".format(result["msg"])
            elif status == "success":
                msg = "初始化成功"
            elif status == "uninit":
                # 未初始化进行初始化
                code, result = self.node_init(region_id, {"node_ip": node_ip})
                msg = "未初始化"
                logger.debug("init node status {0}, result is {1}".format(code, result))
            elif status == "initing":
                msg = "初始化中"
            else:
                msg = "正在初始化节点..."
            rt_body["status"] = status
            rt_body["msg"] = msg
        else:
            rt_body["status"] = "failed"
            rt_body["msg"] = "初始化失败"
        return rt_body

    def node_install_status(self, region_id, node_ip):
        """查询节点安装状态"""
        region = RegionConfig.objects.get(region_id=region_id)
        cluster = RegionClusterInfo.objects.get(region_id=region_id)

        self.http_client.update_client(region)
        res, body = self.http_client.node_component_status(node_ip, None)
        if 200 <= res.status < 400:
            return 200, body["bean"]
        else:
            return int(res.status), body["msg"] if body["msg"] else "安装状态查询异常"

    def update_node_labels(self, region_id, cluster_id, node_uuid, labels_map):
        """添加节点的标签"""
        region = RegionConfig.objects.get(region_id=region_id)
        labels_map = json.loads(labels_map)
        all_labels = Labels.objects.all()
        label_id_map = {l.label_name: l.label_id for l in all_labels}
        node_labels = []
        for k, v in labels_map.iteritems():
            # 对于用户自定义的标签进行操作
            if v == "selfdefine":
                label_id = label_id_map.get(k, None)
                if label_id:
                    node_label = NodeLabels(region_id=region_id,
                                            cluster_id=cluster_id,
                                            node_uuid=node_uuid,
                                            label_id=label_id)
                    node_labels.append(node_label)

        res, body = self.http_client.update_node_labels(region, node_uuid, json.dumps(labels_map))
        NodeLabels.objects.filter(region_id=region_id, node_uuid=node_uuid).delete()
        NodeLabels.objects.bulk_create(node_labels)
        return res, body

    def get_ws_url(self, request, default_url, ws_type):
        if default_url != "auto":
            return "{0}/{1}".format(default_url, ws_type)
        logger.debug(request.META)
        host = request.META.get('REMOTE_ADDR').split(':')[0]
        return "ws://{0}:6060/{1}".format(host, ws_type)


node_service = NodeService()

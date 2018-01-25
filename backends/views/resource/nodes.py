# -*- coding: utf8 -*-


import logging

from rest_framework.response import Response
from django.conf import settings
from backends.models.main import RegionClusterInfo, RegionConfig
from backends.serializers import NodeSerilizer, NodeUpdateSerilizer
from backends.services.nodeservice import node_service
from backends.services.resultservice import *
from backends.views.base import BaseAPIView

logger = logging.getLogger("default")


class NodesView(BaseAPIView):
    def get(self, request, region_id, cluster_id, *args, **kwargs):
        """
        获取数据中心下的某集群下的节点信息
        ---

        """
        try:
            status, nodes_info = node_service.get_nodes(region_id, cluster_id)
            result = generate_result(
                "0000", "success", "查询成功", list=nodes_info
            )
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    # def post(self, request, region_id, cluster_id, *args, **kwargs):
    #     """
    #
    #     添加节点
    #     ---
    #     serializer: NodeSerilizer
    #     """
    #     try:
    #         data = request.data
    #         serializer = NodeSerilizer(data=request.data)
    #         if not serializer.is_valid():
    #             result = generate_result(
    #                 "1003", "params error", "参数错误")
    #             return Response(result)
    #         code, res = node_service.add_node(region_id, cluster_id, **serializer.data)
    #         if code != 200 and code != 201:
    #             result = generate_result(
    #                 "3001", res.get("msg"), res.get("msgcn"))
    #         else:
    #             result = generate_result(
    #                 "0000", "success", "添加成功")
    #     except Exception as e:
    #         logger.exception(e)
    #         result = generate_error_result()
    #     return Response(result)


class NodeInfoView(BaseAPIView):
    def get(self, request, region_id, cluster_id, node_uuid, *args, **kwargs):
        """
         获取某个节点详细信息
        """
        try:
            logger.debug("get node {}".format(node_uuid))
            code, res = node_service.get_node_info(region_id, cluster_id, node_uuid)
            logger.debug("result code is {}".format(code))
            logger.debug("result content is {}".format(res))

            if code != 200 and code != 201:
                result = generate_result("3002", res.get("msg"), res.get("msgcn"))
            else:
                result = generate_result(
                    "0000", "success", "查询成功", bean=res.get("bean", None))
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def put(self, request, region_id, cluster_id, node_uuid, *args, **kwargs):
        """
        修改节点
        ---
        serializer: NodeUpdateSerilizer
        """
        try:
            logger.debug("update node {}".format(node_uuid))
            data = request.data
            serializer = NodeUpdateSerilizer(data=data)
            if not serializer.is_valid():
                logger.error("params error")
                result = generate_result(
                    "1003", "params error", "参数错误")
                return Response(result)

            code, res = node_service.update_node_info(region_id, cluster_id, node_uuid, **serializer.data)
            if code != 200 and code != 201:
                result = generate_result(
                    str(code), res.get("msg"), res.get("msgcn"))
            else:
                result = generate_result(
                    "0000", "success", "修改成功")

        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def delete(self, request, region_id, cluster_id, node_uuid, *args, **kwargs):
        """
        删除节点
        """
        try:
            logger.debug("delete node {}".format(node_uuid))
            code, res = node_service.delete_node(region_id, cluster_id, node_uuid)
            if code != 200 and code != 201:
                result = generate_result("3002", res.get("msg"), res.get("msgcn"))
            else:
                result = generate_result(
                    "0000", "success", "删除成功", bean=res.get("bean", None))
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class NodeBriefInfoView(BaseAPIView):
    def get(self, request, region_id, cluster_id, node_uuid, *args, **kwargs):
        """
         获取某个节点概要信息
        """
        try:
            logger.debug("get node brief info {}".format(node_uuid))
            code, res = node_service.get_node_brief_info(region_id, cluster_id, node_uuid)
            logger.debug("result code is {}".format(code))
            if code != 200 and code != 201:
                result = generate_result("3002", res.get("msg"), res.get("msgcn"))
            else:
                result = generate_result(
                    "0000", "success", "查询成功", bean=res.get("bean", None))
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class AllNodesView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取所有节点的信息
        ---
        parameters:
            - name: page_num
              description: 页码
              required: false
              type: string
              paramType: query
            - name: page_size
              description: 每页数量
              required: false
              type: string
              paramType: query
        """

        try:
            page = request.GET.get("page_num", 1)
            page_size = request.GET.get("page_size", 20)
            nodes = node_service.get_all_region_nodes()
            start = int(page_size) * (int(page) - 1)
            end = int(page_size) * int(page)
            rt_nodes = nodes[start: end]
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, list=rt_nodes, total=len(nodes))
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class NodeOperateView(BaseAPIView):
    def post(self, request, region_id, cluster_id, node_uuid, *args, **kwargs):
        """
        节点操作
        ---
        parameters:
            - name: action
              description: 操作类型 (online,offline,reschedulable 可调度,unschedulable 不可调度)
              required: true
              type: string
              paramType: form

        """
        try:
            action = request.data.get("action", None)
            code, res = node_service.manage_node(region_id, cluster_id, node_uuid, action)
            if code != 200 and code != 201:
                result = generate_result("3002", res.get("msg"), res.get("msgcn"))
            else:

                result = generate_result(
                    "0000", "success", "操作成功", bean=res.get("bean", None))
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class RegionNodesView(BaseAPIView):
    def get(self, request, region_id, *args, **kwargs):
        """
        查询数据中心下的所有节点信息
        """
        try:
            cluster_list = RegionClusterInfo.objects.filter(region_id=region_id)
            all_nodes = []
            for cluster in cluster_list:
                code, node = node_service.get_nodes(region_id, cluster.ID)
                all_nodes[0:0] = node
            result = generate_result(
                "0000", "success", "查询成功", list=all_nodes
            )
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


# class NodeInstallCheckView(BaseAPIView):
#     """检测节点是否可安装"""
#
#     def post(self, request,region_id, *args, **kwargs):
#         """
#         检测节点是否可用
#         ---
#         parameters:
#             - name: region_id
#               description: 数据中心ID
#               required: true
#               type: string
#               paramType: path
#             - name: host
#               description: 节点IP
#               required: true
#               type: string
#               paramType: form
#             - name: port
#               description: 连接节点的端口
#               required: true
#               type: string
#               paramType: form
#             - name: node_type
#               description: 节点类型(tree 或 rain)
#               required: true
#               type: string
#               paramType: form
#             - name: login_type
#               description: 登录类型(ssh 或 root)
#               required: true
#               type: string
#               paramType: form
#             - name: root_pwd
#               description: root登录密码
#               required: false
#               type: string
#               paramType: form
#         """
#         try:
#             data = request.data
#             status, body = node_service.node_check(region_id, data)
#             if status == 200:
#                 bean = body
#                 bean["region_id"] = region_id
#                 bean["host"] = data.get("host")
#                 bean["port"] = data.get("port", 22)
#                 result = generate_result(
#                     "0000", "success", "操作成功", bean=body)
#             elif status == 400:
#                 result = generate_result("3005", msg=body, msg_show="服务器已在使用中")
#             else:
#                 result = generate_result("3004", msg=body, msg_show="无法连接服务器")
#         except Exception as e:
#             logger.exception(e)
#             result = generate_error_result()
#         return Response(result)
#
#
# class NodeInitStatusView(BaseAPIView):
#     """节点初始化状态"""
#
#     def get(self, request, region_id, *args, **kwargs):
#         """
#         查询节点初始化状态
#         ---
#         parameters:
#             - name: region_id
#               description: 数据中心ID
#               required: true
#               type: string
#               paramType: path
#             - name: node_ip
#               description: 节点ip
#               required: true
#               type: string
#               paramType: query
#         """
#         try:
#             node_ip = request.GET.get("node_ip")
#             rt_body = node_service.check_init_status(region_id, node_ip)
#             region = RegionConfig.objects.get(region_id=region_id)
#             bean = {}
#             web_socket_url = node_service.get_ws_url(request, settings.EVENT_WEBSOCKET_URL[region.region_name],
#                                                      "event_log")
#             bean["web_socket_url"] = web_socket_url
#             bean.update(rt_body)
#             result = generate_result("0000", "success", "操作成功",bean=bean)
#         except Exception as e:
#             logger.exception(e)
#             result = generate_error_result()
#         return Response(result)
#
#
# class NodeInstallStatusView(BaseAPIView):
#     """节点安装状态"""
#
#     def get(self, request, region_id, *args, **kwargs):
#         """
#         节点组件安装状态
#         ---
#         parameters:
#             - name: region_id
#               description: 数据中心ID
#               required: true
#               type: string
#               paramType: path
#             - name: node_ip
#               description: 节点ip
#               required: true
#               type: string
#               paramType: query
#
#         """
#         try:
#             node_ip = request.GET.get("node_ip")
#             status, body = node_service.node_install_status(region_id, node_ip)
#             if status == 200:
#                 task_list = body["List"]
#                 all_complete = body["Result"]
#                 status = body["Status"]
#                 region = RegionConfig.objects.get(region_id=region_id)
#                 bean = {}
#                 web_socket_url = node_service.get_ws_url(request, settings.EVENT_WEBSOCKET_URL[region.region_name],
#                                                          "event_log")
#                 bean["web_socket_url"] = web_socket_url
#                 result = generate_result(
#                     "0000", "success", "操作成功", bean=bean, list=task_list, all_complete=all_complete,status=status)
#             else:
#                 result = generate_result("3004", msg=body, msg_show=body["msg_show"])
#         except Exception as e:
#             logger.exception(e)
#             result = generate_error_result()
#         return Response(result)
#
#
# class NodeInstallView(BaseAPIView):
#     """节点组件安装"""
#
#     def post(self, request, region_id, *args, **kwargs):
#         """
#         节点组件安装
#         ---
#         parameters:
#             - name: region_id
#               description: 数据中心ID
#               required: true
#               type: string
#               paramType: path
#             - name: node_ip
#               description: 节点ip
#               required: true
#               type: string
#               paramType: form
#
#         """
#         try:
#             node_ip = request.data.get("node_ip")
#             status, body = node_service.node_install(region_id, node_ip)
#             if status == 200:
#                 task_list = body["List"]
#                 all_complete = body["Result"]
#                 region = RegionConfig.objects.get(region_id=region_id)
#                 bean = {}
#                 web_socket_url = node_service.get_ws_url(request, settings.EVENT_WEBSOCKET_URL[region.region_name],
#                                                          "event_log")
#                 bean["web_socket_url"] = web_socket_url
#                 result = generate_result(
#                     "0000", "success", "操作成功",bean=bean, list=task_list, all_complete=all_complete)
#             else:
#                 result = generate_result("3004", msg=body, msg_show=body)
#         except Exception as e:
#             logger.exception(e)
#             result = generate_error_result()
#         return Response(result)


class NodeLabelsView(BaseAPIView):
    """节点标签"""

    def post(self, request, region_id, cluster_id, node_uuid, *args, **kwargs):
        """
        节点标签添加
        ---
        parameters:
            - name: region_id
              description: 数据中心ID
              required: true
              type: string
              paramType: path
            - name: cluster_id
              description: 集群ID
              required: true
              type: string
              paramType: path
            - name: node_uuid
              description: 节点ID
              required: true
              type: string
              paramType: path
            - name: labels
              description: 标签 {labels:["label1","label2"]}
              required: true
              type: string
              paramType: form

        """
        try:
            labels = request.data.get("labels")
            logger.debug("===========> labels {0}".format(labels))
            node_service.update_node_labels(region_id, cluster_id, node_uuid, labels)

            result = generate_result(
                "0000", "success", "节点标签更新成功")
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)
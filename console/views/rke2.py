# -*- coding: utf-8 -*-
import logging
import time
import json

import yaml
from django.db import IntegrityError
from django.http import StreamingHttpResponse
from rest_framework.response import Response
from console.repositories.init_cluster import rke_cluster, rke_cluster_node
from console.utils.k8s_cli import K8sClient
from console.views.base import AlowAnyApiView
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class BaseClusterView(AlowAnyApiView):
    def handle_exception(self, e, message="Operation failed", message_cn="操作失败"):
        logger.error(f"{message}: {str(e)}")
        result = general_message(500, message, message_cn, bean={})
        return Response(result, status=500)


# 获取集群部署状态的接口
class ClusterRKE(BaseClusterView):
    # get 接口用于获取集群安装状态以及初始化安装集群。
    def get(self, request):
        try:
            cluster_id = request.GET.get("cluster_id", "")
            cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
            result = general_message(200, "Get cluster successful.", "获取集群成功", bean={
                "event_id": cluster.event_id,
                "create_status": cluster.create_status,
                "cluster_name": cluster.cluster_name,
                "cluster_id": cluster.cluster_id,
                "server_host": cluster.server_host,
            })
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to get cluster", "获取集群失败")

    # 更新集群名称和集群ID
    def post(self, request):
        try:
            cluster_name = request.data.get("cluster_name")
            cluster_id = request.data.get("cluster_id")
            server_host = request.data.get("server_host")
            if not cluster_name or not cluster_id or not server_host:
                result = general_message(400, "Cluster name, ID and server host are required.", "集群名称、ID和服务器地址是必需的")
                return Response(result, status=400)

            cluster = rke_cluster.update_cluster(
                cluster_name=cluster_name,
                cluster_id=cluster_id
            )
            result = general_message(200, "Cluster created successfully.", "集群创建成功", bean={
                "cluster_id": cluster.cluster_id,
                "cluster_name": cluster.cluster_name,
                "server_host": cluster.server_host,
            })
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to create cluster", "创建集群失败")


# 安装 RKE 集群
class InstallRKECluster(BaseClusterView):
    def post(self, request):
        try:
            cluster_id = request.data.get("cluster_id", "")
            cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
            
            # 这里应该有实际的集群安装逻辑
            cluster = rke_cluster.update_cluster(create_status="installing")
            
            result = general_message(200, "Cluster installation started.", "集群安装已开始", bean={
                "cluster_id": cluster.cluster_id,
                "status": cluster.create_status,
            })
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to install cluster", "安装集群失败")


# 集群节点管理
class ClusterRKENode(BaseClusterView):
    def get(self, request):
        try:
            cluster_id = request.GET.get("cluster_id", "")
            nodes = rke_cluster_node.get_cluster_nodes(cluster_id=cluster_id)
            node_list = [{"cluster_id": node.cluster_id, "node_name": node.node_name, "node_ip": node.node_ip, "node_role": node.node_role, "is_server": node.is_server} for node in nodes]
            
            result = general_message(200, "Get cluster nodes successful.", "获取集群节点成功", bean=node_list)
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to get cluster nodes", "获取集群节点失败")

    def post(self, request):
        try:
            cluster_id = request.data.get("cluster_id")
            node_ip = request.data.get("node_ip")
            node_role = request.data.get("node_role", "worker")
            node_name = request.data.get("node_name", node_ip)
            is_server = request.data.get("is_server", False)
            
            if not cluster_id or not node_ip:
                result = general_message(400, "Cluster ID and node IP are required.", "集群ID和节点IP是必需的")
                return Response(result, status=400)

            node = rke_cluster_node.create_node(
                cluster_id=cluster_id,
                node_name=node_name,
                node_role=node_role,
                node_ip=node_ip,
                is_server=is_server
            )
            
            result = general_message(200, "Node added successfully.", "节点添加成功", bean={
                "cluster_id": node.cluster_id,
                "node_name": node.node_name,
                "node_ip": node.node_ip,
                "node_role": node.node_role,
                "is_server": node.is_server
            })
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to add node", "添加节点失败")


# 获取节点 IP
class ClusterNodeIP(BaseClusterView):
    def get(self, request):
        try:
            cluster_id = request.GET.get("cluster_id", "")
            nodes = rke_cluster_node.get_cluster_nodes(cluster_id=cluster_id)
            node_ips = [node.node_ip for node in nodes] if nodes else []
            
            result = general_message(200, "Get node IPs successful.", "获取节点IP成功", bean=node_ips)
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to get node IPs", "获取节点IP失败")


# 安装 Rainbond
class ClusterRKEInstallRB(BaseClusterView):
    def post(self, request):
        try:
            cluster_id = request.data.get("cluster_id", "")
            cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
            
            # 这里应该有实际的 Rainbond 安装逻辑
            cluster = rke_cluster.update_cluster(create_status="installing_rainbond")
            
            result = general_message(200, "Rainbond installation started.", "Rainbond安装已开始", bean={
                "cluster_id": cluster.cluster_id,
                "status": cluster.create_status,
            })
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to install Rainbond", "安装Rainbond失败")


# 卸载 Rainbond
class ClusterRKEUNInstallInstallRB(BaseClusterView):
    def post(self, request):
        try:
            cluster_id = request.data.get("cluster_id", "")
            cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
            
            # 这里应该有实际的 Rainbond 卸载逻辑
            cluster = rke_cluster.update_cluster(create_status="uninstalling_rainbond")
            
            result = general_message(200, "Rainbond uninstallation started.", "Rainbond卸载已开始", bean={
                "cluster_id": cluster.cluster_id,
                "status": cluster.create_status,
            })
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to uninstall Rainbond", "卸载Rainbond失败")


# 获取 Rainbond 安装状态
class ClusterRKERBStatus(BaseClusterView):
    def get(self, request):
        try:
            cluster_id = request.GET.get("cluster_id", "")
            cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
            if not cluster or not cluster.config:
                result = general_message(200, "No cluster config available.", "无可用的集群配置", bean=[])
                return Response(result, status=200)
            k8s_api = K8sClient(cluster.config)
            rb_components_status, rb_installed = k8s_api.rb_components_status(cluster.third_db, cluster.third_hub)
            if rb_installed:
                cluster = rke_cluster.update_cluster(create_status="integrated")
            result = general_message(200, "get rb components status successfully.", "组件状态获取成功",
                                     bean=rb_components_status)
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to get cluster", "获取组件状态失败")


# 获取 Rainbond 组件的详细事件信息
class ClusterRKERBEvent(BaseClusterView):
    def get(self, request):
        try:
            cluster_id = request.GET.get("cluster_id", "")
            pod_name = request.GET.get('pod_name')
            cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
            if not cluster or not cluster.config:
                result = general_message(200, "No cluster config available.", "无可用的集群配置", bean=[])
                return Response(result, status=200)
            k8s_api = K8sClient(cluster.config)
            rb_components_status = k8s_api.rb_component_event(pod_name)
            result = general_message(200, "get rb components status successfully.", "组件状态获取成功",
                                     bean=rb_components_status)
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to get cluster", "获取组件状态失败")


# SSE 实时获取 Rainbond 组件日志
class ClusterRBComponentLogSSE(BaseClusterView):
    def get(self, request):
        """
        SSE 接口，实时获取 Rainbond 组件运行日志
        参数:
        - cluster_id: 集群ID (可选，默认使用当前集群)
        - pod_name: Pod名称
        - container_name: 容器名称 (可选，默认为主容器)
        - follow: 是否跟随日志 (默认 true)
        - tail_lines: 显示最近多少行 (默认 100)
        """
        try:
            cluster_id = request.GET.get("cluster_id", "")
            pod_name = request.GET.get('pod_name')
            container_name = request.GET.get('container_name', '')
            follow = request.GET.get('follow', 'true').lower() == 'true'
            tail_lines = int(request.GET.get('tail_lines', '100'))
            
            if not pod_name:
                return self._sse_error("pod_name is required", "Pod名称是必需的")
            
            # 获取集群配置
            if cluster_id:
                cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
            else:
                cluster = rke_cluster.get_rke_cluster_exclude_integrated()
            
            if not cluster or not cluster.config:
                return self._sse_error("No cluster config available", "无可用的集群配置")
            
            k8s_api = K8sClient(cluster.config)
            
            def generate_log_stream():
                log_stream = None
                try:
                    # 发送连接成功消息
                    yield self._format_sse_message({
                        "type": "connected",
                        "message": f"Connected to {pod_name} logs",
                        "timestamp": time.time()
                    })
                    
                    # 获取日志流
                    log_stream = k8s_api.get_pod_logs_stream(
                        pod_name=pod_name,
                        namespace="rbd-system",
                        container_name=container_name,
                        follow=follow,
                        tail_lines=tail_lines
                    )
                    
                    log_count = 0
                    for log_line in log_stream:
                        if log_line.strip():
                            # 检查是否是错误消息
                            if log_line.startswith("错误:") or log_line.startswith("Error:") or log_line.startswith("获取日志失败:"):
                                yield self._format_sse_message({
                                    "type": "error",
                                    "message": log_line.strip(),
                                    "timestamp": time.time()
                                })
                                break  # 遇到错误时停止流
                            else:
                                yield self._format_sse_message({
                                    "type": "log",
                                    "data": log_line.strip(),
                                    "pod_name": pod_name,
                                    "container_name": container_name,
                                    "timestamp": time.time()
                                })
                                log_count += 1
                                
                                # 防止无限制的日志输出，每1000行发送一次心跳
                                if log_count % 1000 == 0:
                                    yield self._format_sse_message({
                                        "type": "heartbeat",
                                        "message": f"Received {log_count} log lines",
                                        "timestamp": time.time()
                                    })
                        
                except GeneratorExit:
                    # 客户端断开连接
                    logger.info(f"Client disconnected from log stream for pod {pod_name}")
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error in log stream for pod {pod_name}: {error_msg}")
                    
                    # 发送具体的错误信息
                    if "不存在" in error_msg or "not found" in error_msg.lower():
                        yield self._format_sse_message({
                            "type": "error",
                            "message": f"Pod或容器不存在: {error_msg}",
                            "message_cn": "请检查Pod名称和容器名称是否正确",
                            "timestamp": time.time()
                        })
                    else:
                        yield self._format_sse_message({
                            "type": "error",
                            "message": error_msg,
                            "timestamp": time.time()
                        })
                finally:
                    # 确保资源清理
                    if log_stream:
                        try:
                            if hasattr(log_stream, 'close'):
                                log_stream.close()
                        except Exception as cleanup_e:
                            logger.warning(f"Failed to cleanup log stream for pod {pod_name}: {str(cleanup_e)}")
                    
                    yield self._format_sse_message({
                        "type": "disconnected",
                        "message": "Log stream ended",
                        "timestamp": time.time()
                    })
            
            response = StreamingHttpResponse(
                generate_log_stream(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['Connection'] = 'keep-alive'
            response['Content-Encoding'] = 'identity'
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'Cache-Control'
            
            return response
            
        except Exception as e:
            return self._sse_error(f"Failed to start log stream: {str(e)}", "启动日志流失败")
    
    def _format_sse_message(self, data):
        """格式化 SSE 消息"""
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    
    def _sse_error(self, error_message, error_message_cn):
        """返回 SSE 错误响应"""
        def error_stream():
            yield self._format_sse_message({
                "type": "error",
                "message": error_message,
                "message_cn": error_message_cn,
                "timestamp": time.time()
            })
        
        response = StreamingHttpResponse(
            error_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive'
        response['Content-Encoding'] = 'identity'
        return response


# 获取 Rainbond 集群信息
class RKERegionConfig(BaseClusterView):
    def get(self, request):
        try:
            cluster = rke_cluster.get_rke_cluster_exclude_integrated()
            if not cluster or not cluster.config:
                result = general_message(200, "No cluster config available.", "无可用的集群配置", bean=[])
                return Response(result, status=200)
            k8s_api = K8sClient(cluster.config)
            region_config = k8s_api.rb_region_config()
            result = general_message(200, "get region config successfully.", "获取集群配置成功",
                                     bean=region_config)
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to get region config", "获取集群配置失败")
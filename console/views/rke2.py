# -*- coding: utf-8 -*-
import json
import logging
import time

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
        result = general_message(500, message, message_cn, bean={"error": str(e)})
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
            cluster_name = request.data.get('cluster_name')
            cluster_id = request.data.get('cluster_id')
            cluster = rke_cluster.update_cluster(create_status="initialized", cluster_name=cluster_name, cluster_id=cluster_id)
            result = general_message(200, "Get cluster successful.", "获取集群成功", bean={
                "event_id": cluster.event_id,
                "create_status": cluster.create_status,
            })
            return Response(result, status=200)
        except IntegrityError as e:
            # 检查是否是 UNIQUE 约束错误
            if "UNIQUE constraint failed" in str(e):
                result = general_message(400, "Cluster ID already exists.", "集群 ID 已存在")
                return Response(result, status=400)
            else:
                # 处理其他类型的 IntegrityError
                return self.handle_exception(e, "Failed to get cluster", "创建集群失败: {}".format(e))
        except Exception as e:
            return self.handle_exception(e, "Failed to get cluster", "创建集群失败: {}".format(e))

    # put 接口用于更新集群的配置文件，脚本执行完成后调用。
    def put(self, request):
        kubeconfig_file = request.FILES.get('kubeconfig')
        if not kubeconfig_file:
            result = general_message(400, "No kubeconfig file provided.", "未提供kubeconfig文件")
            return Response(result, status=400)

        try:
            kubeconfig_content = kubeconfig_file.read().decode('utf-8')
            cluster = rke_cluster.get_rke_cluster_exclude_integrated()
            server_node = rke_cluster_node.get_server_node(cluster.cluster_id)
            kubeconfig_content = kubeconfig_content.replace("127.0.0.1", server_node.node_name)
            cluster.config = kubeconfig_content
            cluster.save()
            result = general_message(200, "Cluster updated successfully.", "集群更新成功")
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to update cluster", "集群更新失败")


# 节点注册接口
class InstallRKECluster(BaseClusterView):
    def get(self, request):
        try:
            node_ip = request.GET.get("node_ip", "")
            node_role = request.GET.get("node_role", "")
            node_name = request.GET.get("node_name", "")
            event_id = request.GET.get("event_id", "")
            node_role_list = node_role.split(",")
            is_server = False
            if "control-plane" in node_role_list:
                cluster, is_server = rke_cluster.only_server(node_ip, event_id)
            else:
                cluster = rke_cluster.get_rke_cluster(event_id=event_id)
            if cluster.server_host:
                node = rke_cluster_node.create_node(cluster.cluster_id, node_name, node_role, node_ip, is_server)
                if cluster.config:
                    k8s_api = K8sClient(cluster.config)
                    k8s_api.nodes_add_worker_rule([node])
            result = general_message(200, "Nodes init successfully.", "节点注册成功",
                                     bean={"server_ip": cluster.server_host, "is_server": is_server})
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to retrieve nodes", "节点注册失败")


# 获取节点信息接口
class ClusterRKENode(BaseClusterView):
    def get(self, request):
        try:
            cluster_id = request.GET.get("cluster_id", "")
            cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
            nodes_dict = {}
            if cluster.config:
                k8s_api = K8sClient(cluster.config)
                nodes_dict = k8s_api.get_nodes()

            nodes = rke_cluster_node.get_cluster_nodes(cluster.cluster_id)
            nodes_info = []
            for node in nodes:
                node_info = nodes_dict.get(node.node_name)
                if node_info:
                    rke_node_rule = node_info.get("roles").split(",")
                    node_rule = node.node_role.split(",")
                    # 输出结果
                    if "worker" in node_rule and "worker" not in rke_node_rule:
                        k8s_api = K8sClient(cluster.config)
                        k8s_api.nodes_add_worker_rule([node])
                    nodes_info.append(node_info)
                else:
                    nodes_info.append(
                        {
                            'status': "Registering",
                            'name': node.node_name,
                            'internal_ip': node.node_ip,
                            'external_ip': "" if node.node_name == node.node_ip else node.node_name,
                            'os_image': "",
                            'roles': node.node_role,
                            'uptime': "",
                            'installation_status': "wait for the node to start"
                        }
                    )
            node_ready = all(node.get("status") == "Ready" for node in nodes_info)
            if cluster_id == "":
                if node_ready and nodes_info:
                    rke_cluster.update_cluster(create_status="installed")
                else:
                    rke_cluster.update_cluster(create_status="installing")
            result = general_message(200, "Nodes retrieved successfully.", "节点获取成功", list=nodes_info)
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to retrieve nodes", "获取节点失败")

    def delete(self, request):
        try:
            cluster_id = request.data.get('cluster_id')
            node_name = request.data.get('node_name')
            cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
            rke_cluster_node.delete_cluster_nodes(cluster.cluster_id, node_name)
            if not rke_cluster_node.get_cluster_nodes(cluster.cluster_id):
                cluster.server_host = ""
                cluster.save()
            result = general_message(200, "node delete successfully.", "节点删除成功")
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "failed to delete nodes", "节点删除失败")


# 获取节点IP接口
class ClusterNodeIP(BaseClusterView):
    def get(self, request):
        try:

            cluster = rke_cluster.get_rke_cluster()
            if not cluster.config:
                result = general_message(200, "No cluster config available.", "无可用的集群配置", bean=[])
                return Response(result, status=200)
            nodes = rke_cluster_node.get_cluster_nodes(cluster.cluster_id)
            ips = [node.node_name for node in nodes]
            result = general_message(200, "Nodes retrieved successfully.", "节点 ip 获取成功", list=ips)
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to retrieve nodes", "获取节点失败")


# 安装 Rainbond
class ClusterRKEInstallRB(BaseClusterView):
    def post(self, request):
        try:
            # 从请求体中获取 values.yaml 内容
            third_db = request.data.get('third_db')
            third_hub = request.data.get('third_hub')
            values_content = request.data.get('value_yaml')
            if not values_content:
                result = general_message(400, "No values.yaml content provided.", "未提供 values.yaml 内容", bean=[])
                return Response(result, status=400)

            cluster = rke_cluster.get_rke_cluster_exclude_integrated()
            if not cluster.config:
                result = general_message(200, "No cluster config available.", "无可用的集群配置", bean=[])
                return Response(result, status=200)

            k8s_api = K8sClient(cluster.config)
            error_message = k8s_api.install_rainbond(values_content)
            if error_message:
                return self.handle_exception(error_message, "Failed to install Rainbond", "安装Rainbond失败")
            cluster.create_status = "integrating"
            cluster.third_db = third_db
            cluster.third_hub = third_hub
            cluster.save()
            result = general_message(200, "Rainbond installed successfully.", "Rainbond安装成功", bean={})
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to install Rainbond", "安装Rainbond失败")


# 卸载 Rainbond
class ClusterRKEUNInstallInstallRB(BaseClusterView):
    def post(self, request):
        try:
            cluster = rke_cluster.get_rke_cluster_exclude_integrated()
            if not cluster.config:
                result = general_message(200, "No cluster config available.", "无可用的集群配置", bean=[])
                return Response(result, status=200)

            k8s_api = K8sClient(cluster.config)
            error_message = k8s_api.uninstall_rainbond()
            if error_message:
                return self.handle_exception(error_message, "Failed to uninstall Rainbond", "卸载Rainbond失败")
            cluster.create_status = "installed"
            cluster.save()
            result = general_message(200, "Rainbond uninstalled successfully.", "Rainbond卸载成功", bean={})
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to install Rainbond", "安装Rainbond失败")


# 获取 Rainbond 安装状态
class ClusterRKERBStatus(BaseClusterView):
    def get(self, request):
        try:
            cluster_id = request.GET.get("cluster_id", "")
            cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
            if not cluster.config:
                result = general_message(200, "No cluster config available.", "无可用的集群配置", bean=[])
                return Response(result, status=200)
            k8s_api = K8sClient(cluster.config)
            rb_components_status, rb_installed = k8s_api.rb_components_status(cluster.third_db, cluster.third_hub)
            if rb_installed:
                cluster.create_status = "integrated"
                cluster.save()
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
            if not cluster.config:
                result = general_message(200, "No cluster config available.", "无可用的集群配置", bean=[])
                return Response(result, status=200)
            k8s_api = K8sClient(cluster.config)
            rb_components_status = k8s_api.rb_component_event(pod_name)
            result = general_message(200, "get rb components status successfully.", "组件状态获取成功",
                                     bean=rb_components_status)
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to get cluster", "获取组件状态失败")


# 获取 Rainbond 集群信息
class RKERegionConfig(BaseClusterView):
    def get(self, request):
        try:
            cluster = rke_cluster.get_rke_cluster_exclude_integrated()
            if not cluster.config:
                result = general_message(200, "No cluster config available.", "无可用的集群配置", bean=[])
                return Response(result, status=200)
            k8s_api = K8sClient(cluster.config)
            region_config = k8s_api.rb_region_config()
            region_config_yaml = yaml.dump(region_config, default_flow_style=False, allow_unicode=True)
            result = general_message(200, "get rb region config successfully.", "集群配置信息获取成功",
                                     bean={"configs": region_config, "configs_yaml": region_config_yaml})
            return Response(result, status=200)
        except Exception as e:
            return self.handle_exception(e, "Failed to get region config", "集群配置信息获取失败")


# SSE 实时获取 Rainbond 组件日志
class ClusterRBComponentLogSSE(BaseClusterView):
    def get(self, request):
        """
        SSE 接口，实时获取 Rainbond 组件运行日志
        参数:
        - cluster_id: 集群ID (必填)
        - pod_name: Pod名称 (必填)
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
            
            if not cluster_id:
                return self._sse_error("cluster_id is required", "集群ID是必需的")
            
            if not pod_name:
                return self._sse_error("pod_name is required", "Pod名称是必需的")
            
            # 获取集群配置
            cluster = rke_cluster.get_rke_cluster(cluster_id=cluster_id)
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
                    
                    logger.info(f"Starting SSE log stream for pod {pod_name}, container: {container_name}, follow: {follow}")
                    
                    # 获取日志流
                    log_stream = k8s_api.get_pod_logs_stream(
                        pod_name=pod_name,
                        namespace="rbd-system",
                        container_name=container_name,
                        follow=follow,
                        tail_lines=tail_lines
                    )
                    
                    log_count = 0
                    last_heartbeat = time.time()
                    
                    for log_line in log_stream:
                        if log_line and log_line.strip():
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
                                    last_heartbeat = time.time()
                        else:
                            # 即使没有新日志，也定期发送心跳保持连接
                            current_time = time.time()
                            if current_time - last_heartbeat > 30:  # 30秒发送一次心跳
                                yield self._format_sse_message({
                                    "type": "heartbeat",
                                    "message": f"Connection alive, {log_count} lines received",
                                    "timestamp": current_time
                                })
                                last_heartbeat = current_time
                        
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

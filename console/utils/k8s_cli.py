# -*- coding: utf-8 -*-
import base64
import logging
import tempfile
import os
from kubernetes import client, config

logger = logging.getLogger('default')


class K8sClient:
    def __init__(self, kubeconfig_content):
        # 从 kubeconfig 字符串内容加载配置
        try:
            # 创建临时文件保存 kubeconfig
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
                f.write(kubeconfig_content)
                kubeconfig_path = f.name
            
            # 加载 kubeconfig
            config.load_kube_config(config_file=kubeconfig_path)
            
            # 初始化 API 客户端
            self.core_v1_api = client.CoreV1Api()
            
            # 清理临时文件
            os.unlink(kubeconfig_path)
            
        except Exception as e:
            logger.error(f"Failed to initialize K8s client: {str(e)}")
            raise e

    def _get_pod_status(self, pod):
        """获取 Pod 状态"""
        if not pod.status:
            return "Unknown"
        
        if pod.status.phase:
            return pod.status.phase
        
        return "Unknown"

    def _get_container_info(self, container_status):
        """获取容器信息"""
        container_info = {
            "name": container_status.name,
            "image": container_status.image,
            "ready": container_status.ready,
            "restart_count": container_status.restart_count,
        }
        
        if container_status.state:
            if container_status.state.running:
                container_info["state"] = "Running"
                container_info["started_at"] = str(container_status.state.running.started_at) if container_status.state.running.started_at else ""
            elif container_status.state.waiting:
                container_info["state"] = "Waiting"
                container_info["reason"] = container_status.state.waiting.reason or ""
                container_info["message"] = container_status.state.waiting.message or ""
            elif container_status.state.terminated:
                container_info["state"] = "Terminated"
                container_info["reason"] = container_status.state.terminated.reason or ""
                container_info["exit_code"] = container_status.state.terminated.exit_code
            else:
                container_info["state"] = "Unknown"
        else:
            container_info["state"] = "Unknown"
            
        return container_info

    def _get_event_info(self, event):
        """获取事件信息"""
        return {
            "type": event.type,
            "reason": event.reason,
            "message": event.message,
            "first_timestamp": str(event.first_timestamp) if event.first_timestamp else "",
            "last_timestamp": str(event.last_timestamp) if event.last_timestamp else "",
            "count": event.count,
            "source_component": event.source.component if event.source else "",
            "source_host": event.source.host if event.source else "",
        }

    def rb_components_status(self, third_db=False, third_hub=False):
        """获取 Rainbond 组件状态"""
        try:
            namespace = "rbd-system"
            pods = self.core_v1_api.list_namespaced_pod(namespace=namespace)
            
            components_status = []
            rb_installed = False
            
            for pod in pods.items:
                # 检查是否是 Rainbond 组件
                if not pod.metadata.name.startswith('rbd-'):
                    continue
                    
                rb_installed = True
                
                containers_info = []
                if pod.status.container_statuses:
                    containers_info = [self._get_container_info(container_status) 
                                     for container_status in pod.status.container_statuses]

                component_status = {
                    "name": pod.metadata.name,
                    "status": self._get_pod_status(pod),
                    "ready": self._is_pod_ready(pod),
                    "node_name": pod.spec.node_name,
                    "start_time": str(pod.status.start_time) if pod.status.start_time else "",
                    "pod_ip": pod.status.pod_ip,
                    "host_ip": pod.status.host_ip,
                    "containers": containers_info,
                    "namespace": namespace,
                    "labels": pod.metadata.labels or {},
                    "image": containers_info[0]["image"] if containers_info else "",
                    "image_status": "存在" if containers_info else "不存在"
                }
                components_status.append(component_status)
            
            return components_status, rb_installed
            
        except Exception as e:
            logger.error(f"Failed to get Rainbond components status: {str(e)}")
            return [], False

    def rb_component_event(self, component_name):
        """获取单个服务的状态和事件信息"""
        try:
            pod = self.core_v1_api.read_namespaced_pod(name=component_name, namespace="rbd-system")
            containers_info = [self._get_container_info(container_status) for container_status in
                               pod.status.container_statuses]

            pod_status_info = {
                "pod_name": pod.metadata.name,
                "status": self._get_pod_status(pod),
                "node_name": pod.spec.node_name,
                "start_time": str(pod.status.start_time) if pod.status.start_time else "",
                "pod_ip": pod.status.pod_ip,
                "host_ip": pod.status.host_ip,
                "containers": containers_info,
                "namespace": "rbd-system",
            }

            event_list = self.core_v1_api.list_namespaced_event(
                namespace="rbd-system",
                field_selector=f"involvedObject.name={component_name}"
            )

            events_info = [self._get_event_info(event) for event in event_list.items]

            return {
                "pod_status": pod_status_info,
                "events": events_info
            }

        except Exception as e:
            logger.error(f"Failed to retrieve status for component {component_name}: {str(e)}")
            return {"error": str(e)}

    def get_pod_logs_stream(self, pod_name, namespace="rbd-system", container_name="", follow=True, tail_lines=100):
        """
        获取 Pod 日志流
        :param pod_name: Pod 名称
        :param namespace: 命名空间，默认为 rbd-system
        :param container_name: 容器名称，为空时获取主容器日志
        :param follow: 是否跟随日志
        :param tail_lines: 显示最近多少行
        """
        log_response = None
        try:
            # 首先检查 Pod 是否存在
            try:
                pod = self.core_v1_api.read_namespaced_pod(name=pod_name, namespace=namespace)
                if not pod:
                    raise Exception(f"Pod {pod_name} not found in namespace {namespace}")
            except Exception as e:
                if "404" in str(e) or "NotFound" in str(e):
                    raise Exception(f"Pod '{pod_name}' 不存在于命名空间 '{namespace}' 中")
                else:
                    raise e
            
            # 构建日志查询参数
            kwargs = {
                'name': pod_name,
                'namespace': namespace,
                'follow': follow,
                'tail_lines': tail_lines,
                '_preload_content': False
            }
            
            # 如果指定了容器名称，则添加到参数中
            if container_name:
                # 验证容器是否存在
                container_found = False
                for container_status in pod.status.container_statuses or []:
                    if container_status.name == container_name:
                        container_found = True
                        break
                
                if not container_found:
                    raise Exception(f"容器 '{container_name}' 不存在于 Pod '{pod_name}' 中")
                
                kwargs['container'] = container_name
            
            # 获取日志流
            log_response = self.core_v1_api.read_namespaced_pod_log(**kwargs)
            
            # 逐行读取日志
            try:
                for line in log_response.stream():
                    if line:
                        yield line.decode('utf-8')
            except Exception as stream_e:
                logger.error(f"Error reading log stream for pod {pod_name}: {str(stream_e)}")
                yield f"日志流读取错误: {str(stream_e)}\n"
                    
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to get logs for pod {pod_name}: {error_msg}")
            
            # 更友好的错误信息
            if "404" in error_msg or "NotFound" in error_msg:
                yield f"错误: Pod '{pod_name}' 不存在\n"
            elif "container" in error_msg.lower():
                yield f"错误: {error_msg}\n"
            else:
                yield f"获取日志失败: {error_msg}\n"
        finally:
            # 确保关闭日志流以释放资源
            if log_response:
                try:
                    if hasattr(log_response, 'close'):
                        log_response.close()
                    elif hasattr(log_response, 'release_conn'):
                        log_response.release_conn()
                except Exception as cleanup_e:
                    logger.warning(f"Failed to cleanup log response for pod {pod_name}: {str(cleanup_e)}")

    def _is_pod_ready(self, pod):
        """检查 Pod 是否就绪"""
        if not pod.status.conditions:
            return False
        
        for condition in pod.status.conditions:
            if condition.type == "Ready":
                return condition.status == "True"
        return False

    def rb_region_config(self):
        """获取 region 配置信息"""
        try:
            region_config_dict = dict()
            region_config = self.core_v1_api.read_namespaced_config_map(name="region-config", namespace="rbd-system")
            if region_config:
                client_pem_str = region_config.binary_data.get("client.pem", "")
                client_pem_bytes = base64.b64decode(client_pem_str)
                client_pem = client_pem_bytes.decode('utf-8')

                client_key_pem_str = region_config.binary_data.get("client.key.pem", "")
                client_key_pem_bytes = base64.b64decode(client_key_pem_str)
                client_key_pem = client_key_pem_bytes.decode('utf-8')

                ca_pem_str = region_config.binary_data.get("ca.pem", "")
                ca_pem_bytes = base64.b64decode(ca_pem_str)
                ca_pem = ca_pem_bytes.decode('utf-8')

                region_config_dict = {
                    "client.pem": client_pem,
                    "client.key.pem": client_key_pem,
                    "ca.pem": ca_pem,
                    "apiAddress": region_config.data.get("apiAddress", ""),
                    "websocketAddress": region_config.data.get("websocketAddress", ""),
                    "defaultDomainSuffix": region_config.data.get("defaultDomainSuffix", ""),
                    "defaultTCPHost": region_config.data.get("defaultTCPHost", "")
                }
            return region_config_dict
        except Exception as e:
            logger.error(f"Failed to get region config: {str(e)}")
            return {}
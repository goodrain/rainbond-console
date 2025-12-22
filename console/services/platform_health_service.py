# -*- coding: utf-8 -*-
import logging
import os
import requests

logger = logging.getLogger("default")


class PlatformHealthService(object):
    """
    平台健康检测服务
    基于Prometheus监控数据检测平台基础设施和关键资源的健康状态
    """

    def __init__(self):
        self.prometheus_url = os.environ.get("PROMETHEUS_URL", "http://rbd-monitor:9999")

    def get_platform_health(self):
        """
        获取平台整体健康状态
        返回格式：
        {
            "status": "healthy|warning|unhealthy",
            "total_issues": 0,
            "issues": []
        }
        """
        issues = []

        # 优先检查 Prometheus 监控服务是否可用
        monitor_issue = self._check_prometheus_connectivity()
        if monitor_issue:
            # 如果监控服务不可用，直接返回错误，不再检查其他指标
            return {
                "status": "unhealthy",
                "total_issues": 1,
                "issues": [monitor_issue]
            }

        # P0 级别检查 - 平台依赖基础设施
        issues.extend(self._check_p0_infrastructure())

        # P1 级别检查 - 平台关键资源
        issues.extend(self._check_p1_resources())

        # 统计问题数量
        p0_count = len([i for i in issues if i['priority'] == 'P0'])
        p1_count = len([i for i in issues if i['priority'] == 'P1'])

        # 确定整体状态
        if p0_count > 0:
            overall_status = "unhealthy"
        elif p1_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "total_issues": len(issues),
            "issues": issues
        }

    def _check_prometheus_connectivity(self):
        """
        检查 Prometheus 监控服务连接性
        如果监控服务不可用，返回 P0 级别错误
        """
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": "up"},
                timeout=5
            )
            result = response.json()

            if result.get('status') != 'success':
                logger.error(f"Prometheus响应异常: {result}")
                return {
                    "priority": "P0",
                    "category": "monitor",
                    "name": "监控服务",
                    "instance": self.prometheus_url,
                    "status": "down",
                    "message": "Prometheus监控服务不可用，无法获取平台健康状态",
                    "metric": "prometheus_up",
                    "value": 0
                }
            return None
        except Exception as e:
            logger.error(f"无法连接到Prometheus监控服务: {e}")
            return {
                "priority": "P0",
                "category": "monitor",
                "name": "监控服务",
                "instance": self.prometheus_url,
                "status": "down",
                "message": f"Prometheus监控服务连接失败: {str(e)}",
                "metric": "prometheus_up",
                "value": 0
            }

    def _check_p0_infrastructure(self):
        """
        P0级别检查：平台依赖基础设施（致命）
        包括：数据库、Kubernetes集群、镜像仓库、对象存储
        """
        issues = []

        # 1.1 数据库检查
        issues.extend(self._check_mysql())

        # 1.2 Kubernetes 集群检查
        issues.extend(self._check_kubernetes())

        # 1.3 镜像仓库检查
        issues.extend(self._check_registry())

        # 1.4 对象存储检查
        issues.extend(self._check_minio())

        return issues

    def _check_p1_resources(self):
        """
        P1级别检查：平台关键资源（严重）
        包括：磁盘空间、计算资源、节点状态
        """
        issues = []

        # 2.1 磁盘空间检查
        issues.extend(self._check_disk_space())

        # 2.2 计算资源检查
        issues.extend(self._check_compute_resources())

        # 2.3 节点状态检查
        issues.extend(self._check_node_status())

        return issues

    def _check_mysql(self):
        """检查MySQL数据库状态"""
        issues = []
        try:
            query = 'mysql_up == 0'
            result = self._query_prometheus(query)

            if result and len(result) > 0:
                for item in result:
                    metric = item.get('metric', {})
                    instance = metric.get('instance', 'unknown')
                    host = metric.get('host', instance)  # 优先使用 host 字段，否则用 instance

                    issue = {
                        "priority": "P0",
                        "category": "database",
                        "name": "MySQL数据库",
                        "instance": instance,
                        "status": "down",
                        "message": f"数据库不可达 ({host})",
                        "metric": "mysql_up",
                        "value": 0
                    }
                    issues.append(issue)
        except Exception as e:
            logger.error(f"检查MySQL状态失败: {e}")

        return issues

    def _check_kubernetes(self):
        """检查Kubernetes集群核心组件"""
        issues = []

        # API Server
        issues.extend(self._check_component('kubernetes_apiserver_up', 'P0', 'kubernetes',
                                           'API Server', 'K8s API不可用'))

        # CoreDNS
        issues.extend(self._check_component('coredns_up', 'P0', 'kubernetes',
                                           'CoreDNS', '集群内部域名解析异常'))

        # Etcd
        issues.extend(self._check_component('etcd_up', 'P0', 'kubernetes',
                                           'Etcd', 'K8s存储后端故障'))

        # 存储类
        issues.extend(self._check_storage_class())

        return issues

    def _check_storage_class(self):
        """检查存储类可用性"""
        issues = []
        try:
            query = 'cluster_storage_up == 0'
            result = self._query_prometheus(query)

            if result and len(result) > 0:
                for item in result:
                    storage_class = item.get('metric', {}).get('storage_class', 'unknown')
                    issues.append({
                        "priority": "P0",
                        "category": "kubernetes",
                        "name": "集群存储",
                        "instance": storage_class,
                        "status": "down",
                        "message": "外部存储类不可用，无法创建PVC",
                        "metric": "cluster_storage_up",
                        "value": 0
                    })
        except Exception as e:
            logger.error(f"检查存储类状态失败: {e}")

        return issues

    def _check_registry(self):
        """检查容器镜像仓库"""
        issues = []
        try:
            query = 'registry_up == 0'
            result = self._query_prometheus(query)

            if result and len(result) > 0:
                for item in result:
                    metric = item.get('metric', {})
                    instance = metric.get('instance', 'unknown')
                    url = metric.get('url', '')  # 提取 url 字段
                    error_reason = metric.get('error_reason', '')  # 提取 error_reason 字段

                    # 构建 message，将 url 和 error_reason 融入
                    message = "镜像仓库不可达"
                    if url:
                        message += f" ({url})"
                    if error_reason:
                        message += f": {error_reason}"

                    issue = {
                        "priority": "P0",
                        "category": "registry",
                        "name": "容器镜像仓库",
                        "instance": instance,
                        "status": "down",
                        "message": message,
                        "metric": "registry_up",
                        "value": 0
                    }

                    issues.append(issue)
        except Exception as e:
            logger.error(f"检查容器镜像仓库状态失败: {e}")

        return issues

    def _check_minio(self):
        """检查MinIO对象存储"""
        return self._check_component('minio_up', 'P0', 'storage',
                                     'MinIO对象存储', '对象存储不可用')

    def _check_disk_space(self):
        """检查磁盘空间"""
        issues = []

        # /grdata 目录检查（剩余空间 < 10%）
        try:
            query = '(1 - node_filesystem_avail_bytes{mountpoint="/grdata"} / node_filesystem_size_bytes{mountpoint="/grdata"}) * 100 > 90'
            result = self._query_prometheus(query)

            if result and len(result) > 0:
                for item in result:
                    node = item.get('metric', {}).get('node', 'unknown')
                    usage = float(item.get('value', [0, 0])[1])
                    issues.append({
                        "priority": "P1",
                        "category": "disk",
                        "name": "/grdata目录",
                        "instance": node,
                        "status": "warning",
                        "message": "构建/日志目录空间不足",
                        "metric": "node_filesystem_usage",
                        "value": round(usage, 2)
                    })
        except Exception as e:
            logger.warning(f"检查/grdata目录空间失败: {e}")

        # 节点磁盘检查（使用率 > 80%）
        try:
            query = '(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 > 80'
            result = self._query_prometheus(query)

            if result and len(result) > 0:
                for item in result:
                    node = item.get('metric', {}).get('node', 'unknown')
                    usage = float(item.get('value', [0, 0])[1])
                    issues.append({
                        "priority": "P1",
                        "category": "disk",
                        "name": "节点磁盘",
                        "instance": node,
                        "status": "warning",
                        "message": "节点磁盘空间紧张",
                        "metric": "node_filesystem_usage",
                        "value": round(usage, 2)
                    })
        except Exception as e:
            logger.warning(f"检查节点磁盘空间失败: {e}")

        return issues

    def _check_compute_resources(self):
        """检查计算资源"""
        issues = []

        # 集群内存检查（可用内存 < 10%）
        try:
            query = '(1 - sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes)) * 100 > 90'
            result = self._query_prometheus(query)

            if result and len(result) > 0:
                for item in result:
                    usage = float(item.get('value', [0, 0])[1])
                    issues.append({
                        "priority": "P1",
                        "category": "compute",
                        "name": "集群内存",
                        "instance": "cluster",
                        "status": "warning",
                        "message": "集群内存即将耗尽",
                        "metric": "cluster_memory_usage",
                        "value": round(usage, 2)
                    })
        except Exception as e:
            logger.warning(f"检查集群内存失败: {e}")

        # 集群CPU检查（可用CPU < 10%）
        try:
            query = '(1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))) * 100 > 90'
            result = self._query_prometheus(query)

            if result and len(result) > 0:
                for item in result:
                    usage = float(item.get('value', [0, 0])[1])
                    issues.append({
                        "priority": "P1",
                        "category": "compute",
                        "name": "集群CPU",
                        "instance": "cluster",
                        "status": "warning",
                        "message": "集群CPU资源即将耗尽",
                        "metric": "cluster_cpu_usage",
                        "value": round(usage, 2)
                    })
        except Exception as e:
            logger.warning(f"检查集群CPU失败: {e}")

        return issues

    def _check_node_status(self):
        """检查节点状态"""
        issues = []

        # 节点可用性检查（NotReady状态）
        try:
            query = 'kube_node_status_condition{condition="Ready",status="true"} == 0'
            result = self._query_prometheus(query)

            if result and len(result) > 0:
                for item in result:
                    node = item.get('metric', {}).get('node', 'unknown')
                    issues.append({
                        "priority": "P1",
                        "category": "node",
                        "name": "节点可用性",
                        "instance": node,
                        "status": "down",
                        "message": "节点状态为NotReady，节点宕机或不可用",
                        "metric": "kube_node_status_condition",
                        "value": 0
                    })
        except Exception as e:
            logger.warning(f"检查节点可用性失败: {e}")

        # 节点高负载检查（load average > CPU核心数）
        try:
            query = 'node_load15 / count(node_cpu_seconds_total{mode="idle"}) by (instance) > 1'
            result = self._query_prometheus(query)

            if result and len(result) > 0:
                for item in result:
                    node = item.get('metric', {}).get('instance', 'unknown')
                    load = float(item.get('value', [0, 0])[1])
                    issues.append({
                        "priority": "P1",
                        "category": "node",
                        "name": "节点负载",
                        "instance": node,
                        "status": "warning",
                        "message": "节点负载过高",
                        "metric": "node_load15",
                        "value": round(load, 2)
                    })
        except Exception as e:
            logger.warning(f"检查节点负载失败: {e}")

        return issues

    def _check_component(self, metric_name, priority, category, component_name, error_message):
        """
        通用组件检查方法
        :param metric_name: Prometheus指标名称
        :param priority: 优先级 (P0/P1)
        :param category: 类别
        :param component_name: 组件名称
        :param error_message: 错误描述
        """
        issues = []
        try:
            query = f'{metric_name} == 0'
            result = self._query_prometheus(query)

            if result and len(result) > 0:
                for item in result:
                    instance = item.get('metric', {}).get('instance', 'unknown')
                    issues.append({
                        "priority": priority,
                        "category": category,
                        "name": component_name,
                        "instance": instance,
                        "status": "down",
                        "message": error_message,
                        "metric": metric_name,
                        "value": 0
                    })
        except Exception as e:
            logger.error(f"检查{component_name}状态失败: {e}")

        return issues

    def _query_prometheus(self, query):
        """
        查询Prometheus
        :param query: PromQL查询语句
        :return: 查询结果列表
        """
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=10
            )
            result = response.json()

            if result.get('status') == 'success':
                return result.get('data', {}).get('result', [])
            else:
                logger.error(f"Prometheus查询失败: {result.get('error', 'unknown error')}")
                return []
        except Exception as e:
            logger.error(f"查询Prometheus异常: {e}")
            return []


platform_health_service = PlatformHealthService()

import datetime
import uuid

from django.db import transaction

from console.models.main import RKECluster, RKEClusterNode


class Cluster(object):
    def get_rke_cluster_exclude_integrated(self):
        clusters = RKECluster.objects.exclude(create_status="interconnected")
        if clusters.exists():
            return clusters[0]
        return self.init_cluster()

    def only_server(self, node_ip):
        with transaction.atomic():
            cluster = self.get_rke_cluster_exclude_integrated()
            if not cluster.server_host:
                cluster.server_host = node_ip
                cluster.save()
                return cluster, True
            if cluster.server_host == node_ip:
                return cluster, True
            return cluster, False

    def init_cluster(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        # 生成一个随机的UUID
        random_uuid = uuid.uuid4().hex[:8]  # 截取UUID的前8位
        # 合并时间戳和随机UUID作为名称
        cluster_name = f"{timestamp}-{random_uuid}"
        event_id = uuid.uuid4().hex
        cluster = RKECluster.objects.create(
            event_id=event_id,
            cluster_name=cluster_name,
            create_status="initialized",
            server_host="",
        )
        return cluster

    def update_cluster(self, config, create_status):
        cluster = self.get_rke_cluster_exclude_integrated()
        if config:
            cluster.config = config
        if create_status:
            cluster.create_status = create_status
        cluster.save()
        return cluster


class ClusterNode(object):
    def create_node(self, cluster_name, node_name, node_role, node_ip, is_server):
        node = RKEClusterNode.objects.filter(cluster_name=cluster_name, node_name=node_name)
        if node.exists():
            return node[0]
        cluster_node = RKEClusterNode.objects.create(
            cluster_name=cluster_name,
            node_name=node_name,
            node_role=node_role,
            node_ip=node_ip,
            is_server=is_server,
        )
        return cluster_node

    def get_worker_node(self, cluster_name):
        cluster_node = RKEClusterNode.objects.filter(
            cluster_name=cluster_name,
            node_role__contains="worker",
        )
        return cluster_node

    def get_server_node(self, cluster_name):
        cluster_node = RKEClusterNode.objects.filter(
            cluster_name=cluster_name,
            is_server=True,
        ).first()
        return cluster_node

    def get_cluster_nodes(self, cluster_name):
        cluster_nodes = RKEClusterNode.objects.filter(
            cluster_name=cluster_name,
        )
        return cluster_nodes


rke_cluster = Cluster()
rke_cluster_node = ClusterNode()

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

    def get_rke_cluster(self, event_id="", cluster_id="", cluster_name=""):
        if event_id:
            return RKECluster.objects.filter(event_id=event_id).first()
        if cluster_id:
            return RKECluster.objects.filter(cluster_id=cluster_id).first()
        if cluster_name:
            return RKECluster.objects.filter(cluster_name=cluster_name).first()
        return self.get_rke_cluster_exclude_integrated()

    def only_server(self, node_ip, event_id):
        with transaction.atomic():
            cluster = self.get_rke_cluster(event_id=event_id)
            if not cluster.server_host:
                cluster.server_host = node_ip
                cluster.save()
                return cluster, True
            if cluster.server_host == node_ip:
                return cluster, True
            return cluster, False

    def init_cluster(self):
        # 合并时间戳和随机UUID作为名称
        event_id = uuid.uuid4().hex
        cluster = RKECluster.objects.create(
            event_id=event_id,
            create_status="initializing",
            server_host="",
        )
        return cluster

    def update_cluster(self, create_status="", cluster_name="", cluster_id=""):
        cluster = self.get_rke_cluster_exclude_integrated()
        if create_status:
            cluster.create_status = create_status
        # 只有在 cluster_name 为空时才允许更新
        if cluster_name and not cluster.cluster_name:
            cluster.cluster_name = cluster_name
        # 只有在 cluster_id 为空时才允许更新
        if cluster_id and not cluster.cluster_id:
            cluster.cluster_id = cluster_id
        cluster.save()
        return cluster

    def delete_cluster(self, cluster_name="", cluster_id=""):
        if cluster_name:
            clusters = RKECluster.objects.filter(cluster_name=cluster_name)
            if clusters:
                cluster = clusters[0]
                RKEClusterNode.objects.filter(cluster_id=cluster.cluster_id).delete()
            clusters.delete()
        if cluster_id:
            RKECluster.objects.filter(cluster_id=cluster_id).delete()
            RKEClusterNode.objects.filter(cluster_id=cluster_id).delete()


class ClusterNode(object):
    def create_node(self, cluster_id, node_name, node_role, node_ip, is_server):
        node = RKEClusterNode.objects.filter(cluster_id=cluster_id, node_name=node_name)
        if node.exists():
            return node[0]
        cluster_node = RKEClusterNode.objects.create(
            cluster_id=cluster_id,
            node_name=node_name,
            node_role=node_role,
            node_ip=node_ip,
            is_server=is_server,
        )
        return cluster_node

    def get_server_node(self, cluster_id):
        cluster_node = RKEClusterNode.objects.filter(
            cluster_id=cluster_id,
            is_server=True,
        ).first()
        return cluster_node

    def get_cluster_nodes(self, cluster_id):
        cluster_nodes = RKEClusterNode.objects.filter(
            cluster_id=cluster_id,
        )
        return cluster_nodes

    def delete_cluster_nodes(self, cluster_id, node_name):
        RKEClusterNode.objects.filter(cluster_id=cluster_id, node_name=node_name).delete()


rke_cluster = Cluster()
rke_cluster_node = ClusterNode()

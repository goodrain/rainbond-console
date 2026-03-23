from unittest import TestCase
from unittest.mock import MagicMock, patch

from console.repositories.init_cluster import Cluster


class ClusterRepositoryTests(TestCase):
    @patch("console.repositories.init_cluster.RKEClusterNode.objects")
    @patch("console.repositories.init_cluster.uuid")
    @patch("console.repositories.init_cluster.RKECluster.objects")
    def test_get_rke_cluster_exclude_integrated_recycles_blank_cluster(self, mock_cluster_objects, mock_uuid, mock_node_objects):
        pending_queryset = MagicMock()
        pending_queryset.order_by.return_value.first.return_value = None
        mock_cluster_objects.exclude.return_value = pending_queryset

        reusable_cluster = MagicMock()
        reusable_cluster.cluster_id = ""
        reusable_cluster.cluster_name = ""
        reusable_cluster.create_status = "interconnected"
        reusable_cluster.server_host = "10.0.0.1"
        reusable_cluster.config = "old-config"
        reusable_cluster.third_db = True
        reusable_cluster.third_hub = True

        recyclable_queryset = MagicMock()
        recyclable_queryset.order_by.return_value.first.return_value = reusable_cluster
        mock_cluster_objects.filter.return_value = recyclable_queryset
        mock_uuid.uuid4.return_value.hex = "new-event-id"

        cluster = Cluster().get_rke_cluster_exclude_integrated()

        self.assertIs(cluster, reusable_cluster)
        self.assertEqual(cluster.event_id, "new-event-id")
        self.assertEqual(cluster.create_status, "initializing")
        self.assertEqual(cluster.server_host, "")
        self.assertEqual(cluster.config, "")
        self.assertFalse(cluster.third_db)
        self.assertFalse(cluster.third_hub)
        mock_cluster_objects.filter.assert_called_once_with(cluster_id="", cluster_name="")
        mock_node_objects.filter.assert_called_once_with(cluster_id="")
        mock_node_objects.filter.return_value.delete.assert_called_once_with()
        reusable_cluster.save.assert_called_once_with()

    @patch("console.repositories.init_cluster.RKECluster.objects")
    def test_get_rke_cluster_exclude_integrated_prefers_latest_pending_cluster(self, mock_cluster_objects):
        latest_cluster = MagicMock()
        pending_queryset = MagicMock()
        pending_queryset.order_by.return_value.first.return_value = latest_cluster
        mock_cluster_objects.exclude.return_value = pending_queryset

        cluster = Cluster().get_rke_cluster_exclude_integrated()

        self.assertIs(cluster, latest_cluster)
        mock_cluster_objects.filter.assert_not_called()

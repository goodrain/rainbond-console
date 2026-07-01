import sys
from types import ModuleType
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.conf import settings
import django

if not settings.configured:
    settings.configure(
        SECRET_KEY="test",
        DEFAULT_CHARSET="utf-8",
        ROOT_URLCONF=__name__,
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "rest_framework",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        REST_FRAMEWORK={
            "UNAUTHENTICATED_USER": None,
        },
        USE_TZ=True,
    )
django.setup()

from rest_framework.permissions import AllowAny  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402
from rest_framework.views import APIView  # noqa: E402


class TestAllowAnyApiView(APIView):
    permission_classes = (AllowAny, )
    authentication_classes = ()


base_module = ModuleType("console.views.base")
base_module.AlowAnyApiView = TestAllowAnyApiView
sys.modules.setdefault("console.views.base", base_module)

init_cluster_module = ModuleType("console.repositories.init_cluster")
init_cluster_module.rke_cluster = MagicMock()
init_cluster_module.rke_cluster_node = MagicMock()
sys.modules.setdefault("console.repositories.init_cluster", init_cluster_module)

from console.utils.k8s_cli import K8sClient  # noqa: E402
from console.views.rke2 import ClusterRKE, ClusterRKEInstallRB  # noqa: E402


class ClusterRKEErrorTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("console.views.rke2.rke_cluster")
    # capability_id: console.rke2.cluster-missing-metadata-404
    def test_cluster_get_returns_structured_404_when_cluster_metadata_missing(self, mock_rke_cluster):
        mock_rke_cluster.get_rke_cluster.return_value = None

        request = self.factory.get("/console/cluster", {"cluster_id": "missing-cluster"})
        response = ClusterRKE.as_view()(request)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], 404)
        self.assertEqual(response.data["msg"], "Cluster not found.")
        self.assertEqual(response.data["data"]["bean"]["cluster_id"], "missing-cluster")

    @patch("console.views.rke2.K8sClient")
    @patch("console.views.rke2.rke_cluster")
    # capability_id: console.rke2.cluster-install-structured-helm-error
    def test_cluster_install_returns_structured_helm_error_without_saving_integrating(self, mock_rke_cluster, mock_k8s_client):
        cluster = MagicMock()
        cluster.config = "apiVersion: v1"
        mock_rke_cluster.get_rke_cluster_exclude_integrated.return_value = cluster
        mock_k8s_client.return_value.install_rainbond.return_value = {
            "stage": "helm_install",
            "command": "helm install rainbond",
            "return_code": 1,
            "stderr": "release already exists",
            "stdout": "",
            "error": "helm command failed",
        }

        request = self.factory.post(
            "/console/cluster_install",
            {"value_yaml": "rainbond: {}", "third_db": False, "third_hub": False},
            format="json")
        response = ClusterRKEInstallRB.as_view()(request)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["code"], 500)
        error = response.data["data"]["bean"]["error"]
        self.assertEqual(error["stage"], "helm_install")
        self.assertEqual(error["stderr"], "release already exists")
        self.assertNotIn("--kubeconfig", str(error))
        self.assertNotIn("./rainbond-chart", str(error))
        cluster.save.assert_not_called()
        self.assertNotEqual(cluster.create_status, "integrating")

    @patch.object(K8sClient, "uninstall_rainbond")
    @patch.object(K8sClient, "_write_file")
    # capability_id: console.rke2.helm-subprocess-error-sanitized
    def test_install_rainbond_returns_sanitized_subprocess_error(self, mock_write_file, mock_uninstall):
        client = K8sClient.__new__(K8sClient)
        client.kube_config = "apiVersion: v1"

        with patch("console.utils.k8s_cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = b"installing\n"
            mock_run.return_value.stderr = b"Error: failed to install\n"

            error = client.install_rainbond("rainbond: {}")

        self.assertEqual(error["stage"], "helm_install")
        self.assertEqual(error["command"], "helm install rainbond")
        self.assertEqual(error["return_code"], 1)
        self.assertEqual(error["stdout"], "installing")
        self.assertEqual(error["stderr"], "Error: failed to install")
        self.assertNotIn("--kubeconfig", str(error))
        self.assertNotIn("kube.config", str(error))
        self.assertNotIn("./rainbond-chart", str(error))
        mock_uninstall.assert_called_once_with()

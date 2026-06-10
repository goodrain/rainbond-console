import collections
import os
import sys
from types import ModuleType
from types import SimpleNamespace
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
openapi_client = ModuleType("openapi_client")
openapi_client.ApiClient = mock.Mock()
openapi_client.MarketOpenapiApi = mock.Mock()
configuration_module = ModuleType("openapi_client.configuration")
configuration_module.Configuration = mock.Mock
rest_module = ModuleType("openapi_client.rest")
rest_module.ApiException = Exception
sys.modules.setdefault("openapi_client", openapi_client)
sys.modules.setdefault("openapi_client.configuration", configuration_module)
sys.modules.setdefault("openapi_client.rest", rest_module)

from console.exception.main import ServiceHandleException
from console.models import KubeBlocksBackupRepo
from console.services import kubeblocks_service as kubeblocks_module
from console.services.kubeblocks_service import KubeBlocksService
from django.test import TestCase


class KubeBlocksBackupRepoServiceTests(TestCase):
    def setUp(self):
        self.service = KubeBlocksService()
        self.tenant = SimpleNamespace(tenant_id="tenant-1", tenant_name="team-a", namespace="team-a-ns")
        self.other_tenant = SimpleNamespace(tenant_id="tenant-2", tenant_name="team-b", namespace="team-b-ns")
        self.user = SimpleNamespace(nick_name="alice")

    # capability_id: console.kubeblocks.backup-repo.team-create
    def test_create_backup_repo_prefixes_namespace_and_does_not_store_secret_values(self):
        region_api = mock.Mock()
        region_api.create_kubeblocks_backup_repo.return_value = ({"status": 200}, {"bean": {"name": "team-a-ns-prod"}})

        payload = {
            "name": "prod",
            "display_name": "生产仓库",
            "bucket": "rainbond-backup",
            "endpoint": "https://s3.example.com",
            "region": "cn-hangzhou",
            "access_key_id": "ak",
            "secret_access_key": "sk",
            "volume_capacity": "100Gi",
        }
        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            status, body = self.service.create_backup_repo(self.tenant, self.user, "region-a", payload)

        self.assertEqual(status, 200)
        repo = KubeBlocksBackupRepo.objects.get(repo_name="team-a-ns-prod")
        self.assertEqual(repo.tenant_id, "tenant-1")
        self.assertEqual(repo.namespace, "team-a-ns")
        self.assertEqual(repo.secret_name, "team-a-ns-prod-secret")
        self.assertEqual(repo.secret_namespace, "rbd-plugins")
        self.assertEqual(repo.bucket, "rainbond-backup")
        self.assertFalse(hasattr(repo, "access_key_id"))
        self.assertFalse(hasattr(repo, "secret_access_key"))
        self.assertNotIn("access_key_id", body["bean"])
        self.assertNotIn("secret_access_key", body["bean"])

        region_payload = region_api.create_kubeblocks_backup_repo.call_args[0][1]
        self.assertEqual(region_payload["name"], "team-a-ns-prod")
        self.assertEqual(region_payload["credential"]["namespace"], "rbd-plugins")
        self.assertEqual(region_payload["secrets"]["accessKeyId"], "ak")
        self.assertEqual(region_payload["secrets"]["secretAccessKey"], "sk")

    # capability_id: console.kubeblocks.backup-repo.team-list
    def test_list_backup_repos_merges_live_status_from_region(self):
        KubeBlocksBackupRepo.objects.create(
            tenant_id="tenant-1",
            team_name="team-a",
            region_name="region-a",
            namespace="team-a-ns",
            display_name="生产仓库",
            repo_name="team-a-ns-prod",
            secret_name="team-a-ns-prod-secret",
            secret_namespace="rbd-plugins",
            storage_provider="s3",
            bucket="rainbond-backup",
            endpoint="https://s3.example.com",
            region="cn-hangzhou",
        )
        region_api = mock.Mock()
        region_api.get_kubeblocks_backup_repos.return_value = ({
            "status": 200
        }, {
            "list": [{
                "name": "team-a-ns-prod",
                "phase": "Ready",
                "generatedStorageClassName": "sc-team-a-ns-prod",
            }]
        })

        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            status, body = self.service.get_team_backup_repos(self.tenant, "region-a")

        self.assertEqual(status, 200)
        self.assertEqual(len(body["list"]), 1)
        item = body["list"][0]
        self.assertEqual(item["name"], "team-a-ns-prod")
        self.assertEqual(item["displayName"], "生产仓库")
        self.assertEqual(item["phase"], "Ready")
        self.assertEqual(item["generatedStorageClassName"], "sc-team-a-ns-prod")

    # capability_id: console.kubeblocks.backup-repo.team-ownership
    def test_ensure_backup_repo_belongs_to_team_rejects_other_team_repo(self):
        KubeBlocksBackupRepo.objects.create(
            tenant_id="tenant-2",
            team_name="team-b",
            region_name="region-a",
            namespace="team-b-ns",
            display_name="其他仓库",
            repo_name="team-b-ns-prod",
            secret_name="team-b-ns-prod-secret",
            secret_namespace="rbd-plugins",
            storage_provider="s3",
            bucket="rainbond-backup",
            endpoint="https://s3.example.com",
        )

        with self.assertRaises(ServiceHandleException):
            self.service.ensure_backup_repo_belongs_to_team(self.tenant, "region-a", "team-b-ns-prod")

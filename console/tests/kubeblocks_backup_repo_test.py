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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from console.models import KubeBlocksBackupRepo  # noqa: E402
from console.services import kubeblocks_service as kubeblocks_module  # noqa: E402
from console.services.kubeblocks_service import KubeBlocksService  # noqa: E402
from django.test import TestCase  # noqa: E402


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
        self.assertEqual(region_payload["storageProviderRef"], "s3-compatible")
        self.assertEqual(region_payload["config"]["forcePathStyle"], "true")
        self.assertEqual(region_payload["credential"]["namespace"], "rbd-plugins")
        self.assertEqual(region_payload["secrets"]["accessKeyId"], "ak")
        self.assertEqual(region_payload["secrets"]["secretAccessKey"], "sk")

    # capability_id: console.kubeblocks.backup-repo.team-create
    def test_create_backup_repo_allows_virtual_hosted_style_access(self):
        region_api = mock.Mock()
        region_api.create_kubeblocks_backup_repo.return_value = ({"status": 200}, {"bean": {"name": "team-a-ns-oss"}})

        payload = {
            "name": "oss",
            "display_name": "阿里云 OSS",
            "bucket": "rainbond-backup",
            "endpoint": "oss-cn-beijing.aliyuncs.com",
            "region": "oss-cn-beijing",
            "force_path_style": False,
            "access_key_id": "ak",
            "secret_access_key": "sk",
            "volume_capacity": "100Gi",
        }
        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            status, body = self.service.create_backup_repo(self.tenant, self.user, "region-a", payload)

        self.assertEqual(status, 200)
        repo = KubeBlocksBackupRepo.objects.get(repo_name="team-a-ns-oss")
        self.assertFalse(repo.force_path_style)

        region_payload = region_api.create_kubeblocks_backup_repo.call_args[0][1]
        self.assertEqual(region_payload["config"]["forcePathStyle"], "false")
        self.assertEqual(body["bean"]["forcePathStyle"], False)

    # capability_id: console.kubeblocks.backup-repo.team-create
    def test_create_backup_repo_defaults_to_prechecking_when_region_phase_is_empty(self):
        region_api = mock.Mock()
        region_api.create_kubeblocks_backup_repo.return_value = ({"status": 200}, {"bean": {"name": "team-a-ns-prod"}})

        payload = {
            "name": "prod",
            "display_name": "生产仓库",
            "bucket": "rainbond-backup",
            "endpoint": "https://s3.example.com",
            "access_key_id": "ak",
            "secret_access_key": "sk",
        }
        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            status, body = self.service.create_backup_repo(self.tenant, self.user, "region-a", payload)

        self.assertEqual(status, 200)
        repo = KubeBlocksBackupRepo.objects.get(repo_name="team-a-ns-prod")
        self.assertEqual(repo.status, "PreChecking")
        self.assertEqual(body["bean"]["phase"], "PreChecking")
        self.assertEqual(body["bean"]["status"], "PreChecking")

    # capability_id: console.kubeblocks.backup-repo.team-create
    def test_create_backup_repo_reclaims_deleted_region_repo_name(self):
        old_record = KubeBlocksBackupRepo.objects.create(
            tenant_id="tenant-1",
            team_name="team-a",
            region_name="region-a",
            namespace="team-a-ns",
            display_name="旧仓库",
            repo_name="team-a-ns-prod",
            secret_name="team-a-ns-prod-secret",
            secret_namespace="rbd-plugins",
            storage_provider="s3-compatible",
            bucket="rainbond-backup",
            endpoint="https://s3.example.com",
            is_deleted=True,
        )
        region_api = mock.Mock()
        region_api.create_kubeblocks_backup_repo.return_value = ({"status": 200}, {"bean": {"name": "team-a-ns-prod"}})

        payload = {
            "name": "prod",
            "display_name": "生产仓库",
            "bucket": "rainbond-backup",
            "endpoint": "https://s3.example.com",
            "access_key_id": "ak",
            "secret_access_key": "sk",
        }
        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            status, body = self.service.create_backup_repo(self.tenant, self.user, "region-a", payload)

        self.assertEqual(status, 200)
        self.assertFalse(KubeBlocksBackupRepo.objects.filter(ID=old_record.ID).exists())
        repo = KubeBlocksBackupRepo.objects.get(repo_name="team-a-ns-prod")
        self.assertFalse(repo.is_deleted)
        self.assertEqual(repo.display_name, "生产仓库")
        region_api.create_kubeblocks_backup_repo.assert_called_once()

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

    # capability_id: console.kubeblocks.backup-repo.team-list
    def test_list_backup_repos_keeps_failed_live_status(self):
        KubeBlocksBackupRepo.objects.create(
            tenant_id="tenant-1",
            team_name="team-a",
            region_name="region-a",
            namespace="team-a-ns",
            display_name="生产仓库",
            repo_name="team-a-ns-prod",
            secret_name="team-a-ns-prod-secret",
            secret_namespace="rbd-plugins",
            storage_provider="s3-compatible",
            bucket="rainbond-backup",
            endpoint="http://minio-service.rbd-system.svc.cluster.local:9000",
        )
        region_api = mock.Mock()
        region_api.get_kubeblocks_backup_repos.return_value = ({
            "status": 200
        }, {
            "list": [{
                "name": "team-a-ns-prod",
                "phase": "Failed",
                "conditions": [{
                    "type": "PreCheckPassed",
                    "status": "False",
                    "reason": "PreCheckFailed",
                    "message": "lookup bucket.minio-service failed",
                }],
            }]
        })

        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            status, body = self.service.get_team_backup_repos(self.tenant, "region-a")

        self.assertEqual(status, 200)
        item = body["list"][0]
        self.assertEqual(item["phase"], "Failed")
        self.assertEqual(item["conditions"][0]["reason"], "PreCheckFailed")

    # capability_id: console.kubeblocks.backup-repo.team-list
    def test_list_backup_repos_marks_missing_when_region_resource_disappears(self):
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
            status="Ready",
        )
        region_api = mock.Mock()
        region_api.get_kubeblocks_backup_repos.return_value = ({
            "status": 200
        }, {
            "list": []
        })

        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            status, body = self.service.get_team_backup_repos(self.tenant, "region-a")

        self.assertEqual(status, 200)
        item = body["list"][0]
        self.assertEqual(item["phase"], "Missing")
        self.assertEqual(item["status"], "Missing")

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

    # capability_id: console.kubeblocks.backup-repo.ready-guard
    def test_ensure_backup_repo_ready_for_use_rejects_prechecking_repo(self):
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
            status="PreChecking",
        )
        region_api = mock.Mock()
        region_api.get_kubeblocks_backup_repos.return_value = ({
            "status": 200
        }, {
            "list": [{
                "name": "team-a-ns-prod",
                "phase": "PreChecking",
            }]
        })

        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            with self.assertRaises(ServiceHandleException) as context:
                self.service.ensure_backup_repo_ready_for_use(self.tenant, "region-a", "team-a-ns-prod")

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "备份仓库正在检测中，请检测通过后再使用")

    # capability_id: console.kubeblocks.backup-repo.ready-guard
    def test_ensure_backup_repo_ready_for_use_accepts_ready_repo(self):
        record = KubeBlocksBackupRepo.objects.create(
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
            status="PreChecking",
        )
        region_api = mock.Mock()
        region_api.get_kubeblocks_backup_repos.return_value = ({
            "status": 200
        }, {
            "list": [{
                "name": "team-a-ns-prod",
                "phase": "Ready",
            }]
        })

        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            checked = self.service.ensure_backup_repo_ready_for_use(self.tenant, "region-a", "team-a-ns-prod")

        self.assertEqual(checked.ID, record.ID)

    # capability_id: console.kubeblocks.backup-repo.ready-guard
    def test_ensure_backup_repo_ready_for_use_rejects_missing_live_repo(self):
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
            status="Ready",
        )
        region_api = mock.Mock()
        region_api.get_kubeblocks_backup_repos.return_value = ({
            "status": 200
        }, {
            "list": []
        })

        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            with self.assertRaises(ServiceHandleException) as context:
                self.service.ensure_backup_repo_ready_for_use(self.tenant, "region-a", "team-a-ns-prod")

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "备份仓库资源不存在或暂不可用，请刷新后重试")

    # capability_id: console.kubeblocks.backup-repo.team-delete
    def test_delete_backup_repo_shows_clear_message_when_in_use(self):
        KubeBlocksBackupRepo.objects.create(
            tenant_id="tenant-1",
            team_name="team-a",
            region_name="region-a",
            namespace="team-a-ns",
            display_name="生产仓库",
            repo_name="team-a-ns-prod",
            secret_name="team-a-ns-prod-secret",
            secret_namespace="rbd-plugins",
            storage_provider="s3-compatible",
            bucket="rainbond-backup",
            endpoint="http://minio-service.rbd-system.svc.cluster.local:9000",
        )
        region_api = mock.Mock()
        region_api.delete_kubeblocks_backup_repo.return_value = ({
            "status": 409
        }, {
            "msg_show": 'block-mechanica service returned error: {"code":409,"msg":"delete backup repo: backup repo team-a-ns-prod is in use by cluster team-a-ns/mysql-abc"}\n'
        })

        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            status, body = self.service.delete_backup_repo(self.tenant, "region-a", "team-a-ns-prod")

        self.assertEqual(status, 409)
        self.assertEqual(body["msg_show"], "备份仓库正在被数据库组件 team-a-ns/mysql-abc 使用，不支持删除。请先在该组件的备份策略中取消使用该仓库后再删除")
        region_api.delete_kubeblocks_backup_repo.assert_called_once_with("region-a", "team-a-ns-prod")

    # capability_id: console.kubeblocks.backup-repo.team-delete
    def test_delete_backup_repo_removes_console_record_on_success(self):
        record = KubeBlocksBackupRepo.objects.create(
            tenant_id="tenant-1",
            team_name="team-a",
            region_name="region-a",
            namespace="team-a-ns",
            display_name="生产仓库",
            repo_name="team-a-ns-prod",
            secret_name="team-a-ns-prod-secret",
            secret_namespace="rbd-plugins",
            storage_provider="s3-compatible",
            bucket="rainbond-backup",
            endpoint="http://minio-service.rbd-system.svc.cluster.local:9000",
        )
        region_api = mock.Mock()
        region_api.delete_kubeblocks_backup_repo.return_value = ({"status": 200}, {"bean": {}})

        with mock.patch.object(kubeblocks_module, "region_api", region_api):
            status, body = self.service.delete_backup_repo(self.tenant, "region-a", "team-a-ns-prod")

        self.assertEqual(status, 200)
        self.assertEqual(body["msg_show"], "删除备份仓库成功")
        self.assertFalse(KubeBlocksBackupRepo.objects.filter(ID=record.ID).exists())
        region_api.delete_kubeblocks_backup_repo.assert_called_once_with("region-a", "team-a-ns-prod")

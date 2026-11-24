"""Recover the same Console component without recreating or importing disks."""
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from console.tests import vm_manage_view_test  # noqa: F401
from console.models.main import ServiceRecycleBin
from console.services.component_recycle import ComponentRecycleService, RecycleError
from www.models.main import ServiceGroup, ServiceGroupRelation, TenantServiceInfo


# capability_id: console.component-recycle.original-vm-recovery
class ComponentRecycleRecoveryTests(TestCase):
    def setUp(self):
        self.tenant = SimpleNamespace(tenant_id="recycle-team", tenant_name="team", enterprise_id="enterprise")
        self.app = ServiceGroup.objects.create(tenant_id=self.tenant.tenant_id,
                                               region_name="region",
                                               group_name="VMs",
                                               k8s_app="original-app",
                                               create_time=timezone.now(),
                                               update_time=timezone.now())
        self.service = TenantServiceInfo.objects.create(tenant_id=self.tenant.tenant_id,
                                                        service_id="original-id",
                                                        service_alias="original-alias",
                                                        service_cname="Original VM",
                                                        service_region="region",
                                                        service_key="vm",
                                                        category="application",
                                                        image="original-image",
                                                        version="v1",
                                                        arch="arm64",
                                                        k8s_component_name="original-k8s-name",
                                                        extend_method="vm",
                                                        service_source="vm_run",
                                                        create_status="complete")
        ServiceGroupRelation.objects.create(tenant_id=self.tenant.tenant_id,
                                            region_name="region",
                                            group_id=self.app.ID,
                                            service_id=self.service.service_id)
        self.region = mock.Mock()
        self.region.get_vm_recycle_recovery.return_value = (SimpleNamespace(status=200), {
            "bean": {
                "service_id": "original-id",
                "vm_uid": "same-vm",
                "storage_ready": True,
                "k8s_component_name": "original-k8s-name",
                "vm_name": "original-app-original-k8s-name",
                "disks": [{
                    "disk_key": "disk",
                    "pvc_uid": "same-root-pvc"
                }]
            }
        })
        self.manager = ComponentRecycleService(region_api=self.region)

    def recycle(self):
        from console.services.app_actions.app_manage import AppManageService
        with mock.patch('console.services.app_actions.app_manage.region_api', self.region):
            AppManageService().move_service_into_recycle_bin(self.service, tenant=self.tenant)
        return ServiceRecycleBin.objects.get(service_id="original-id")

    def test_restore_keeps_original_identity_architecture_config_and_does_no_region_create(self):
        trash = self.recycle()
        result = self.manager.restore(self.tenant, "region", trash.service_id)
        restored = TenantServiceInfo.objects.get(service_id="original-id")
        self.assertEqual(restored.arch, "arm64")
        self.assertEqual(restored.k8s_component_name, "original-k8s-name")
        self.assertEqual(restored.service_alias, "original-alias")
        self.assertEqual(result["service_id"], "original-id")
        self.assertFalse(ServiceRecycleBin.objects.filter(service_id=trash.service_id).exists())
        self.region.create_service.assert_not_called()
        self.region.add_service_volumes.assert_not_called()

    def test_wrong_team_region_missing_disk_and_alias_conflict_leave_recycle_record(self):
        trash = self.recycle()
        for tenant, region in [(SimpleNamespace(tenant_id="other"), "region"), (self.tenant, "other")]:
            with self.assertRaises(RecycleError):
                self.manager.restore(tenant, region, trash.service_id)
        self.region.get_vm_recycle_recovery.return_value = (SimpleNamespace(status=200), {
            "bean": {
                "service_id": "original-id",
                "storage_ready": False,
                "disks": []
            }
        })
        with self.assertRaises(RecycleError):
            self.manager.restore(self.tenant, "region", trash.service_id)
        self.assertTrue(ServiceRecycleBin.objects.filter(service_id=trash.service_id).exists())
        self.assertFalse(TenantServiceInfo.objects.filter(service_id=trash.service_id).exists())

    def test_recovery_is_idempotent_and_list_never_exposes_saved_internal_fields(self):
        self.service.secret = "test-placeholder"
        self.service.save()
        trash = self.recycle()
        row = self.manager.public(trash)
        self.assertNotIn("secret", row)
        self.assertNotIn("recovery_metadata", row)
        self.manager.restore(self.tenant, "region", trash.service_id)
        again = self.manager.restore(self.tenant, "region", trash.service_id)
        self.assertEqual(again["service_id"], trash.service_id)
        self.assertEqual(TenantServiceInfo.objects.filter(service_id=trash.service_id).count(), 1)

    def test_replaced_vm_or_original_disk_never_recovers_as_the_original(self):
        trash = self.recycle()
        for change in ({'vm_uid': 'replacement-vm'}, {'disks': [{'disk_key': 'disk', 'pvc_uid': 'replacement-pvc'}]}):
            proof = {
                'service_id': 'original-id',
                'vm_uid': 'same-vm',
                'storage_ready': True,
                'disks': [{
                    'disk_key': 'disk',
                    'pvc_uid': 'same-root-pvc'
                }],
                **change
            }
            self.region.get_vm_recycle_recovery.return_value = (SimpleNamespace(status=200), {'bean': proof})
            with self.assertRaises(RecycleError):
                self.manager.restore(self.tenant, 'region', trash.service_id)
            self.assertTrue(ServiceRecycleBin.objects.filter(service_id=trash.service_id).exists())

    def test_alias_conflict_does_not_touch_cluster_or_remove_recycle_record(self):
        trash = self.recycle()
        TenantServiceInfo.objects.create(tenant_id=self.tenant.tenant_id,
                                         service_id='another-id',
                                         service_alias='original-alias',
                                         service_region='region')
        self.region.get_vm_recycle_recovery.reset_mock()
        with self.assertRaises(RecycleError):
            self.manager.restore(self.tenant, 'region', trash.service_id)
        self.region.get_vm_recycle_recovery.assert_not_called()
        self.assertTrue(ServiceRecycleBin.objects.filter(service_id=trash.service_id).exists())

    def test_renamed_app_and_malformed_cluster_proof_preserve_recycle_record(self):
        trash = self.recycle()
        self.app.k8s_app = 'renamed-app'
        self.app.save()
        with self.assertRaises(RecycleError):
            self.manager.restore(self.tenant, 'region', trash.service_id)
        self.app.k8s_app = 'original-app'
        self.app.save()
        for bean in ([], {
                'service_id': 'original-id',
                'storage_ready': True,
                'vm_uid': 'same-vm',
                'disks': [{
                    'disk_key': 'disk',
                    'pvc_uid': 'same-root-pvc'
                }] * 2
        }):
            self.region.get_vm_recycle_recovery.return_value = (SimpleNamespace(status=200), {'bean': bean})
            with self.assertRaises(RecycleError):
                self.manager.restore(self.tenant, 'region', trash.service_id)
        self.assertTrue(ServiceRecycleBin.objects.filter(service_id=trash.service_id).exists())
        self.assertFalse(TenantServiceInfo.objects.filter(service_id=trash.service_id).exists())

    def test_failed_purge_rolls_back_temporary_active_row_and_retains_recycle_record(self):
        trash = self.recycle()
        self.region.get_service_info.return_value = {'bean': {'serviceId': trash.service_id}}
        self.region.check_service_status.return_value = {'bean': {'cur_status': 'closed'}}
        with mock.patch('console.services.app_actions.app_manage.AppManageService.delete',
                        return_value=(409, 'still referenced')):
            with self.assertRaises(RecycleError):
                self.manager.purge(self.tenant, 'region', trash.service_id, SimpleNamespace(nick_name='tester'))
        self.assertTrue(ServiceRecycleBin.objects.filter(service_id=trash.service_id).exists())
        self.assertFalse(TenantServiceInfo.objects.filter(service_id=trash.service_id).exists())

    def test_purge_reuses_normal_cluster_deletion_and_removes_the_recycle_record(self):
        trash = self.recycle()
        self.region.get_service_info.return_value = {'bean': {'serviceId': trash.service_id}}
        self.region.check_service_status.return_value = {'bean': {'cur_status': 'closed'}}
        with mock.patch('console.services.app_actions.app_manage.region_api', self.region):
            result = self.manager.purge(self.tenant, 'region', trash.service_id, SimpleNamespace(nick_name='tester'))
        self.assertTrue(result['deleted'])
        self.assertFalse(ServiceRecycleBin.objects.filter(service_id=trash.service_id).exists())
        self.assertFalse(TenantServiceInfo.objects.filter(service_id=trash.service_id).exists())
        self.region.delete_service.assert_called_once()
        self.assertEqual(self.region.delete_service.call_args.args[:3], ('region', 'team', 'original-alias'))

    def test_authenticated_read_does_not_grant_restore_or_delete_and_other_scopes_are_hidden(self):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from console.views.component_recycle import (ComponentRecycleListView, ComponentRecycleRestoreView,
                                                     ComponentRecyclePurgeView)
        from www.models.main import Tenants, TenantRegionInfo

        trash = self.recycle()
        Tenants.objects.create(tenant_id=self.tenant.tenant_id,
                               tenant_name='team',
                               namespace='test-ns',
                               enterprise_id='enterprise')
        TenantRegionInfo.objects.create(tenant_id=self.tenant.tenant_id, region_name='region')
        factory = APIRequestFactory()
        user = SimpleNamespace(user_id=17, enterprise_id='enterprise', nick_name='reader', is_authenticated=True)
        with mock.patch('console.repositories.perm_repo.optimized_role_perm_repo.get_user_team_all_perms',
                        return_value={'global_perms': [300002], 'app_perms': {}}), \
                mock.patch.object(ComponentRecycleService, 'restore') as restore, \
                mock.patch.object(ComponentRecycleService, 'purge') as purge:

            def request(view, method, team='team', region='region', authenticated=True):
                req = getattr(factory, method)('/recycle-bin?region_name=' + region)
                if authenticated:
                    force_authenticate(req, user=user)
                kwargs = {'team_name': team}
                if method != 'get':
                    kwargs['service_id'] = trash.service_id
                return view.as_view()(req, **kwargs)

            response = request(ComponentRecycleListView, 'get')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['data']['total'], 1)
            self.assertFalse(response.data['data']['list'][0]['can_restore'])
            self.assertFalse(response.data['data']['list'][0]['can_purge'])
            self.assertEqual(request(ComponentRecycleRestoreView, 'post').status_code, 403)
            self.assertEqual(request(ComponentRecyclePurgeView, 'delete').status_code, 403)
            self.assertEqual(request(ComponentRecycleListView, 'get', region='other').status_code, 404)
            self.assertEqual(request(ComponentRecycleListView, 'get', team='other').status_code, 404)
            self.assertIn(request(ComponentRecycleListView, 'get', authenticated=False).status_code, (401, 403))
            restore.assert_not_called()
            purge.assert_not_called()

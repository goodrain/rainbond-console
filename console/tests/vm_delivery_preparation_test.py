import os
import subprocess
import sys
import unittest
from unittest import mock
from types import SimpleNamespace
from pathlib import Path


class VMDeliveryPreparationRegressionTest(unittest.TestCase):
    # capability_id: rainbond-console.delivery.vm-current-disk-preparation
    def test_vm_delivery_lifecycle(self):
        root = Path(__file__).resolve().parents[2]
        environment = dict(os.environ, PYTHONPATH=str(root))
        result = subprocess.run([sys.executable, '-m', 'console.tests.isolated_vm_delivery', '-q'],
                                cwd=root,
                                env=environment,
                                capture_output=True,
                                text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    # capability_id: rainbond-console.delivery.vm-current-disk-preparation
    def test_preparation_view_requires_application_write_scope_and_returns_a_task(self):
        from console.views.delivery_templates import DeliveryVMPreparationView
        view = DeliveryVMPreparationView()
        view.user = SimpleNamespace(user_id=1)
        view.is_enterprise_admin = False
        preparation = mock.Mock()
        preparation.data.return_value = {'id': 'capture', 'status': 'queued', 'version_id': ''}
        scope = {'team_name': 'team', 'region_name': 'region', 'app_id': '1'}
        request = SimpleNamespace(data={'version': '1.0.0', 'request_id': 'request', 'region_name': 'region'})
        with mock.patch.object(view, 'scope', return_value=scope) as access, mock.patch.object(view,
                                                                                               'preparation',
                                                                                               return_value=preparation):
            response = view.post(request, 'team', '1')
            self.assertEqual(response.status_code, 202)
            access.assert_called_once_with(request, 'team', '1', write=True)
            preparation.submit.assert_called_once_with(view.user, scope, {'version': '1.0.0'}, 'request')
            access.reset_mock()
            view.post(request, 'team', '1', 'capture')
            access.assert_called_once_with(request, 'team', '1', write=True)
            preparation.retry.assert_called_once_with(scope, 'capture')
            access.reset_mock()
            view.delete(request, 'team', '1', 'capture')
            access.assert_called_once_with(request, 'team', '1', write=True)
            preparation.cancel.assert_called_once_with(scope, 'capture')

    # capability_id: rainbond-console.delivery.vm-current-disk-preparation
    def test_region_capture_client_matches_scoped_methods_and_bounded_timeouts(self):
        from www.apiclient.regionapi import RegionInvokeApi
        api = RegionInvokeApi()
        with mock.patch.object(api, '_RegionInvokeApi__get_region_access_info', return_value=('http://region.test', '')), \
                mock.patch.object(api, '_RegionInvokeApi__get_tenant_region_info',
                                  return_value=SimpleNamespace(region_tenant_name='region-team')), \
                mock.patch.object(api, '_set_headers'), \
                mock.patch.object(api, '_put', return_value=(None, {})) as put, \
                mock.patch.object(api, '_get', return_value=(None, {})) as get, \
                mock.patch.object(api, '_post', return_value=(None, {})) as post, \
                mock.patch.object(api, '_delete', return_value=(None, {})) as delete:
            for action in ('prepare', 'status', 'image', 'release'):
                api.vm_delivery_capture('region', 'team', 'vm', 'capture', action)
            for method in (put, get, post, delete):
                self.assertEqual(method.call_args.args[0],
                                 'http://region.test/v2/tenants/region-team/services/vm/vm-delivery-captures/capture')
                self.assertEqual(method.call_args.kwargs['timeout'], 8)
                self.assertEqual(method.call_args.kwargs['retries'], 0)

    # capability_id: rainbond-console.delivery.vm-current-disk-preparation
    def test_gateway_supports_default_region_and_configured_delivery_registries(self):
        import uuid
        from console.services.delivery_gateway import DeliveryGateway
        from console.appstore.appstore import app_store
        template = SimpleNamespace(id=uuid.UUID(int=1), enterprise_id='enterprise', team_name='team', region_name='region')
        task = SimpleNamespace(template=template, payload={'lease': 'owned-lease'}, items=mock.Mock())
        task.items.filter.return_value.update.return_value = 1
        gateway = DeliveryGateway()
        api = mock.Mock()
        api.vm_delivery_capture.return_value = (None, {'bean': {'phase': 'building'}})
        for hub, namespace, expected in ((None, None, 'region.test/vm:capture'), ('delivery.test', 'library',
                                                                                  'delivery.test/library/vm:capture')):
            with self.subTest(hub=hub):
                item = SimpleNamespace(pk=uuid.UUID(int=2),
                                       key='vm',
                                       component={
                                           'service_alias': 'vm',
                                           'arch': 'amd64'
                                       },
                                       result={
                                           'capture_id': 'capture',
                                           'image_name': 'region.test/vm:capture'
                                       })
                with mock.patch.object(app_store, 'get_app_hub_info', return_value={'hub_url': hub, 'namespace': namespace}), \
                        mock.patch.object(gateway, 'region_api', return_value=api):
                    self.assertEqual(gateway.vm_capture(task, item, 'image')['phase'], 'building')
                self.assertEqual(item.result['image_name'], expected)

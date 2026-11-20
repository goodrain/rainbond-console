# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
openapi_client_module = ModuleType("openapi_client")
openapi_client_module.ApiClient = lambda configuration=None: SimpleNamespace(configuration=configuration)
openapi_client_module.MarketOpenapiApi = lambda client=None: SimpleNamespace(client=client)

openapi_client_configuration = ModuleType("openapi_client.configuration")


class _OpenAPIConfiguration(object):
    def __init__(self):
        self.client_side_validation = False
        self.host = ""
        self.api_key = {}


openapi_client_configuration.Configuration = _OpenAPIConfiguration

openapi_client_rest = ModuleType("openapi_client.rest")


class _ApiException(Exception):
    def __init__(self, status=400, body=""):
        super().__init__(body)
        self.status = status
        self.body = body


openapi_client_rest.ApiException = _ApiException

sys.modules.setdefault("openapi_client", openapi_client_module)
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

# capability_id: console.vm-vnc.scoped-proxy
from django.http import Http404  # noqa: E402
from rest_framework.exceptions import PermissionDenied  # noqa: E402
from console.utils import vm_vnc_proxy as helper  # noqa: E402
from console.views.vm_vnc import ComponentVNCView  # noqa: E402


class VMVNCProxyTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.tenant = SimpleNamespace(tenant_name='team', namespace='team-ns', enterprise_id='ent')
        self.service = SimpleNamespace(extend_method='vm',
                                       service_alias='grvm',
                                       service_region='rg',
                                       k8s_component_name='windows')
        self.app = SimpleNamespace(k8s_app='demo')
        self.upstreams = mock.patch.dict(os.environ,
                                         {'RAINBOND_VM_VNC_PROXY_UPSTREAMS': '{"rg":"http://virtvnc.rbd-plugins.svc:8001"}'})
        self.upstreams.start()
        self.addCleanup(self.upstreams.stop)

    def request(self, url, **headers):
        view = ComponentVNCView()
        raw = self.factory.get(url, **headers)
        view.request = view.initialize_request(raw)
        view.tenant = self.tenant
        view.service = self.service
        view.app = self.app
        view.upstream = helper.get_vm_vnc_upstream('rg')
        view.backend_vnc_path = helper.component_vnc_backend_path(self.tenant, self.service, self.app)
        return view, view.request

    def test_url_is_same_origin_and_component_scoped_without_credentials(self):
        request = self.factory.get('/detail', HTTP_HOST='console.example:7071')
        url = helper.build_component_vnc_url(request, self.tenant, self.service)
        self.assertTrue(
            url.startswith('http://console.example:7071/console/regions/rg/teams/team/apps/grvm/vnc/vnc_lite.html?'))
        self.assertIn('websockify', url)
        self.assertNotIn('token=', url)
        self.assertNotIn('virtvnc.rbd', url)

    def test_only_selected_regions_use_configured_upstream(self):
        self.service.service_region = 'other'
        self.assertEqual('', helper.build_component_vnc_url(self.factory.get('/'), self.tenant, self.service))

    def test_asset_traversal_and_kubernetes_api_paths_are_rejected(self):
        for path in [
                '../secret', 'core/../secret.js', '%2e%2e/secret', 'core/%252e%252e/x.js', 'http://example/x.js', '/etc/passwd',
                'k8s/apis/v1/namespaces', 'core/x\\y.js'
        ]:
            with self.subTest(path=path), self.assertRaises(Http404):
                helper.validate_static_path(path)

    def test_normal_novnc_esmodule_and_styles_are_allowed(self):
        for path in [
                'vnc_lite.html', 'core/rfb.js', 'core/util/browser.js', 'app/styles/base.css',
                'vendor/pako/lib/zlib/inflate.js', 'app/images/icons/novnc-16x16.png'
        ]:
            self.assertEqual(path, helper.validate_static_path(path))

    def test_backend_target_is_derived_from_component(self):
        self.assertEqual(
            '/k8s/apis/subresources.kubevirt.io/v1alpha3/namespaces/team-ns/'
            'virtualmachineinstances/demo-windows/vnc', helper.component_vnc_backend_path(self.tenant, self.service, self.app))

    def test_unauthenticated_request_never_fetches_upstream(self):
        with mock.patch('console.views.vm_vnc.requests.get') as fetch:
            response = ComponentVNCView.as_view()(self.factory.get('/vnc/vnc_lite.html'),
                                                  tenantName='team',
                                                  region_name='rg',
                                                  serviceAlias='grvm',
                                                  vnc_path='vnc_lite.html')
        self.assertGreaterEqual(response.status_code, 400)
        fetch.assert_not_called()

    def test_websocket_requires_same_origin_and_no_target_query(self):
        for origin, query in [('http://other.example', ''), ('null', ''), ('', ''), ('http://testserver', '?target=other')]:
            with self.subTest(origin=origin, query=query):
                view, request = self.request('/websockify' + query, HTTP_ORIGIN=origin)
                with mock.patch('console.utils.vm_vnc_proxy_relay.relay_component_vnc') as relay, \
                        self.assertRaises(PermissionDenied):
                    view._websocket(request)
                relay.assert_not_called()

    def test_websocket_uses_only_authorized_vmi_and_binary_relay(self):
        view, request = self.request('/websockify', HTTP_ORIGIN='http://testserver')
        client = mock.Mock()
        request.META['wsgi.websocket'] = client
        with mock.patch('console.utils.vm_vnc_proxy_relay.relay_component_vnc', return_value='relay') as relay:
            self.assertEqual('relay', view._websocket(request))
        relay.assert_called_once_with(client, 'http://virtvnc.rbd-plugins.svc:8001', view.backend_vnc_path)

    def test_static_request_does_not_forward_authorization_or_cookie_or_redirect(self):
        view, request = self.request('/vnc_lite.html', HTTP_AUTHORIZATION='placeholder', HTTP_COOKIE='placeholder')
        upstream = mock.Mock(status_code=200, headers={'Content-Type': 'text/html'})
        upstream.iter_content.return_value = [b'HTML']
        with mock.patch('console.views.vm_vnc.requests.get', return_value=upstream) as fetch:
            response = view.get(request, vnc_path='vnc_lite.html')
            self.assertEqual(b'HTML', b''.join(response.streaming_content))
        fetch.assert_called_once_with('http://virtvnc.rbd-plugins.svc:8001/vnc_lite.html',
                                      stream=True,
                                      timeout=(10, 30),
                                      allow_redirects=False)
        upstream.close.assert_called_once()
        self.assertEqual('no-store', response['Cache-Control'])

    def test_cross_scope_initial_is_rejected_after_authentication(self):
        for field, value in [('service_region', 'another'), ('extend_method', 'container')]:
            with self.subTest(field=field):
                view, request = self.request('/vnc_lite.html')
                view.region_name = 'rg'
                view.user = SimpleNamespace(enterprise_id='ent')
                old = getattr(self.service, field)
                setattr(self.service, field, value)
                with mock.patch.object(view, 'perform_authentication') as auth, \
                        mock.patch.object(view, 'check_permissions'), \
                        mock.patch('console.views.vm_vnc.AppBaseView.initial'), self.assertRaises(PermissionDenied):
                    view.initial(request)
                auth.assert_called_once_with(request)
                setattr(self.service, field, old)

    def test_member_requires_web_terminal_permission(self):
        view = ComponentVNCView()
        view.is_team_owner = False
        view.is_enterprise_admin = False
        view.user_perms = []
        with self.assertRaises(Exception):
            view.check_perms(SimpleNamespace())

    def test_cross_enterprise_initial_never_resolves_upstream(self):
        view, request = self.request('/vnc_lite.html')
        view.region_name = 'rg'
        view.user = SimpleNamespace(enterprise_id='other-enterprise')
        with mock.patch.object(view, 'perform_authentication'), mock.patch.object(view, 'check_permissions'), \
                mock.patch('console.views.vm_vnc.AppBaseView.initial'), \
                mock.patch('console.views.vm_vnc.get_vm_vnc_upstream') as upstream, \
                self.assertRaises(PermissionDenied):
            view.initial(request)
        upstream.assert_not_called()

    def test_owner_bypasses_role_but_member_uses_terminal_permission(self):
        view = ComponentVNCView()
        view.is_team_owner, view.is_enterprise_admin = True, False
        with mock.patch('console.views.vm_vnc.AppBaseView.check_perms'), mock.patch.object(view, 'has_perms') as permission:
            view.check_perms(SimpleNamespace())
            permission.assert_not_called()
            view.is_team_owner = False
            view.check_perms(SimpleNamespace())
            permission.assert_called_once_with([300010])

    def test_static_rejects_cross_component_socket_selection(self):
        view, request = self.request('/vnc_lite.html?path=k8s/apis/another-vmi/vnc')
        with mock.patch('console.views.vm_vnc.requests.get') as fetch, self.assertRaises(PermissionDenied):
            view.get(request, vnc_path='vnc_lite.html')
        fetch.assert_not_called()

    def test_proxy_does_not_follow_redirects_or_forward_location(self):
        view, request = self.request('/vnc_lite.html')
        upstream = mock.Mock(status_code=302)
        with mock.patch('console.views.vm_vnc.requests.get', return_value=upstream):
            response = view.get(request, vnc_path='vnc_lite.html')
        self.assertEqual(502, response.status_code)
        self.assertNotIn('Location', response)
        upstream.close.assert_called_once()

    def test_binary_relay_cleans_up_both_peers_without_auth_headers(self):
        from console.utils.vm_vnc_proxy_relay import relay_component_vnc
        import websocket
        client = mock.Mock()
        client.receive.side_effect = [b'keyboard-data', None]
        backend = mock.Mock()
        backend.recv_data.side_effect = [(websocket.ABNF.OPCODE_BINARY, b'RFB 003.008\n'), (websocket.ABNF.OPCODE_CLOSE, b'')]
        jobs = []

        def spawn(fn):
            job = mock.Mock()
            job.fn = fn
            jobs.append(job)
            return job

        def joinall(jobs, count):
            for job in jobs:
                job.fn()

        with mock.patch('websocket.create_connection', return_value=backend) as connect, \
                mock.patch('gevent.spawn', side_effect=spawn), mock.patch('gevent.joinall', side_effect=joinall):
            response = relay_component_vnc(
                client, 'http://virtvnc.rbd-plugins.svc:8001', '/k8s/apis/subresources.kubevirt.io/v1alpha3/namespaces/team-ns/'
                'virtualmachineinstances/demo-windows/vnc')
        self.assertEqual(204, response.status_code)
        self.assertEqual({'timeout': 10}, connect.call_args.kwargs)
        client.send.assert_called_once_with(b'RFB 003.008\n', binary=True)
        backend.send_binary.assert_called_once_with(b'keyboard-data')
        backend.close.assert_called_once()
        client.close.assert_called_once()
        for job in jobs:
            job.kill.assert_called_once()

    def test_component_resolution_is_scoped_to_the_authorized_team(self):
        from console.exception.main import BusinessException
        view, request = self.request('/vnc_lite.html')
        view.tenant.tenant_id = 'authorized-team-id'
        with mock.patch.object(view, 'perform_authentication'), mock.patch.object(view, 'check_permissions'), \
                mock.patch('console.views.app_config.base.RegionTenantHeaderView.initial'), \
                mock.patch('console.views.app_config.base.TenantServiceInfo.objects.filter', return_value=[]) as lookup, \
                mock.patch('console.views.vm_vnc.requests.get') as fetch, \
                self.assertRaises(BusinessException):
            view.initial(request, region_name='rg', tenantName='team', serviceAlias='foreign-component')
        lookup.assert_called_once_with(service_alias='foreign-component', tenant_id='authorized-team-id')
        fetch.assert_not_called()

    def test_admin_upstream_rejects_credentials_paths_and_malformed_maps(self):
        from django.core.exceptions import ImproperlyConfigured
        for value in [
                'not-json', '[]', '{"rg":42}', '{"rg":"http://user:placeholder@host"}', '{"rg":"http://host/arbitrary-path"}'
        ]:
            with self.subTest(config=value), mock.patch.dict(os.environ, {'RAINBOND_VM_VNC_PROXY_UPSTREAMS': value}), \
                    self.assertRaises(ImproperlyConfigured):
                helper.get_vm_vnc_upstream('rg')

    def test_authorized_initial_sets_only_configured_region_target(self):
        view, request = self.request('/vnc_lite.html')
        view.region_name = 'rg'
        view.user = SimpleNamespace(enterprise_id='ent')
        with mock.patch.object(view, 'perform_authentication'), mock.patch.object(view, 'check_permissions'), \
                mock.patch('console.views.vm_vnc.AppBaseView.initial'):
            view.initial(request)
        self.assertEqual('http://virtvnc.rbd-plugins.svc:8001', view.upstream)
        self.assertTrue(view.backend_vnc_path.endswith('/demo-windows/vnc'))

    def test_cross_site_cookie_request_is_rejected(self):
        view, request = self.request('/vnc_lite.html', HTTP_SEC_FETCH_SITE='cross-site')
        view.region_name = 'rg'
        view.user = SimpleNamespace(enterprise_id='ent')
        with mock.patch.object(view, 'perform_authentication'), mock.patch.object(view, 'check_permissions'), \
                mock.patch('console.views.vm_vnc.AppBaseView.initial'), self.assertRaises(PermissionDenied):
            view.initial(request)

    def test_static_upstream_failure_returns_bounded_error(self):
        import requests
        view, request = self.request('/vnc_lite.html')
        with mock.patch('console.views.vm_vnc.requests.get', side_effect=requests.ConnectionError('unreachable')):
            self.assertEqual(502, view.get(request, vnc_path='vnc_lite.html').status_code)

    def test_head_validates_assets_and_does_not_upgrade_socket(self):
        view, request = self.request('/vnc_lite.html')
        self.assertEqual(200, view.head(request, vnc_path='core/rfb.js').status_code)
        self.assertEqual(405, view.head(request, vnc_path='websockify').status_code)
        with self.assertRaises(Http404):
            view.head(request, vnc_path='../secret')

    def test_backend_socket_failure_closes_client(self):
        from console.utils.vm_vnc_proxy_relay import relay_component_vnc
        client = mock.Mock()
        with mock.patch('websocket.create_connection', side_effect=OSError('unavailable')):
            response = relay_component_vnc(client, 'http://virtvnc.rbd-plugins.svc:8001', '/fixed-vnc')
        self.assertEqual(502, response.status_code)
        client.close.assert_called_once()

    def test_novnc_host_override_and_duplicate_path_are_rejected(self):
        expected = helper.component_vnc_prefix(self.tenant, self.service).lstrip('/') + 'websockify'
        for query in ['host=untrusted.example', 'path=' + expected + '&host=untrusted.example', 'path=other&path=' + expected]:
            with self.subTest(query=query):
                view, request = self.request('/vnc_lite.html?' + query)
                with mock.patch('console.views.vm_vnc.requests.get') as fetch, self.assertRaises(PermissionDenied):
                    view.get(request, vnc_path='vnc_lite.html')
                fetch.assert_not_called()

    def test_standard_binary_websocket_without_negotiated_subprotocol_relays_rfb(self):
        # A binary frame is a WebSocket opcode; the peer need not negotiate an
        # application subprotocol named "binary". Exercise the actual library
        # handshake against a local RFC6455 server, not a create_connection mock.
        import base64
        import hashlib
        import socketserver
        import threading
        import websocket
        from console.utils.vm_vnc_proxy_relay import relay_component_vnc

        class RFBHandler(socketserver.BaseRequestHandler):
            def handle(self):
                request = b''
                self.request.settimeout(3)
                while b'\r\n\r\n' not in request:
                    request += self.request.recv(4096)
                headers = dict(line.split(':', 1) for line in request.decode().split('\r\n')[1:] if ':' in line)
                key = headers['Sec-WebSocket-Key'].strip()
                accept = base64.b64encode(hashlib.sha1(
                    (key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
                response = ('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                            'Sec-WebSocket-Accept: ' + accept + '\r\n\r\n').encode()
                payload = b'RFB 003.008\n'
                self.request.sendall(response + bytes([0x82, len(payload)]) + payload + b'\x88\x00')

        server = socketserver.TCPServer(('127.0.0.1', 0), RFBHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        client = mock.Mock()
        client.receive.return_value = None
        original_connect = websocket.create_connection
        jobs = []

        def connect(url, **kwargs):
            return original_connect(url, http_no_proxy=['127.0.0.1'], **kwargs)

        def spawn(fn):
            job = mock.Mock()
            job.fn = fn
            jobs.append(job)
            return job

        def joinall(jobs, count):
            for job in reversed(jobs):
                job.fn()

        try:
            with mock.patch('websocket.create_connection', side_effect=connect), \
                    mock.patch('gevent.spawn', side_effect=spawn), mock.patch('gevent.joinall', side_effect=joinall):
                result = relay_component_vnc(client, 'http://127.0.0.1:' + str(server.server_address[1]), '/rfb')
            self.assertEqual(204, result.status_code)
            client.send.assert_called_once_with(b'RFB 003.008\n', binary=True)
            client.close.assert_called_once()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)

    def test_real_gevent_binary_bytearray_roundtrip_through_django_proxy(self):
        import json
        import subprocess
        from pathlib import Path
        fixture = Path(__file__).with_name('vnc_wsgi_roundtrip_fixture.py')
        process = subprocess.run([sys.executable, str(fixture)], capture_output=True, text=True, timeout=15)
        self.assertEqual(0, process.returncode, process.stderr[-1200:])
        result = json.loads(process.stdout.strip().splitlines()[-1])
        self.assertTrue(any(fact.get('client_binary_receive_type') == 'bytearray' for fact in result['facts']))
        self.assertTrue(result['results'][0]['rfb'])
        self.assertTrue(result['results'][0]['roundtrip'], result)
        self.assertTrue(result['upstream_received'][0]['protocol_reply_matches'])

# -*- coding: utf-8 -*-
# Local real-transport fixture; patch networking before importing Django/socket clients.
from gevent import monkey  # noqa: E402

monkey.patch_all()
import os  # noqa: E402
import sys  # noqa: E402
import json  # noqa: E402
import gevent  # noqa: E402
from gevent.pywsgi import WSGIServer  # noqa: E402
from geventwebsocket.handler import WebSocketHandler  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest import mock  # noqa: E402
from pathlib import Path  # noqa: E402

repo = str(Path(__file__).resolve().parents[2])
sys.path[:0] = [repo, repo + '/console/tests']
os.environ['DJANGO_SETTINGS_MODULE'] = 'goodrain_web.test_settings'
import vm_detail_view_test  # noqa: E402,F401 (shared Django/OpenAPI setup fixture)
from rest_framework.authentication import BaseAuthentication  # noqa: E402
from rest_framework.exceptions import NotAuthenticated  # noqa: E402
from console.login.jwt_authentication import JSONWebTokenAuthentication  # noqa: E402
from console.views.vm_vnc import ComponentVNCView  # noqa: E402
from console.views.app_config.base import AppBaseView  # noqa: E402
from geventwebsocket import WebSocketApplication, Resource  # noqa: E402
import websocket  # noqa: E402

facts = []
user = SimpleNamespace(is_authenticated=True, enterprise_id='fixture-enterprise')


class FixtureCookieAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if JSONWebTokenAuthentication().get_jwt_value(request) != 'transport-fixture':
            raise NotAuthenticated()
        return (user, None)


upstream_received = []


class Upstream(WebSocketApplication):
    def on_open(self):
        self.ws.send(b'RFB 003.008\n', binary=True)

    def on_message(self, message):
        if message is None:
            return
        upstream_received.append({'type': type(message).__name__, 'protocol_reply_matches': bytes(message) == b'RFB 003.008\n'})
        self.ws.send(b'local-roundtrip-ok', binary=True)
        self.ws.close()


upstream = WSGIServer(('127.0.0.1', 0),
                      Resource([('^/k8s/.*', Upstream)]),
                      handler_class=WebSocketHandler,
                      log=None,
                      error_log=None)
upstream.start()
os.environ['RAINBOND_VM_VNC_PROXY_UPSTREAMS'] = json.dumps({'fixture-region': 'http://127.0.0.1:' + str(upstream.server_port)})


def initial(view, request, *a, **kw):
    view.user = request.user
    view.tenant = SimpleNamespace(tenant_name='fixture-team', namespace='fixture-ns', enterprise_id='fixture-enterprise')
    view.service = SimpleNamespace(service_region='fixture-region',
                                   extend_method='vm',
                                   service_alias='grfixture',
                                   k8s_component_name='windows')
    view.app = SimpleNamespace(k8s_app='fixture-app')
    view.region_name = 'fixture-region'
    view.is_team_owner = True
    view.is_enterprise_admin = False


from types import ModuleType  # noqa: E402
from django.urls import re_path  # noqa: E402
from django.test.utils import override_settings  # noqa: E402
from django.core.wsgi import get_wsgi_application  # noqa: E402

fixture_urls = ModuleType('fixture_vnc_transport_urls')
fixture_urls.urlpatterns = [
    re_path('^websockify$', ComponentVNCView.as_view(authentication_classes=(FixtureCookieAuthentication, )), {
        'region_name': 'fixture-region',
        'tenantName': 'fixture-team',
        'serviceAlias': 'grfixture',
        'vnc_path': 'websockify'
    })
]
sys.modules[fixture_urls.__name__] = fixture_urls
url_override = override_settings(ROOT_URLCONF=fixture_urls.__name__)
url_override.enable()
full_wsgi = get_wsgi_application()


def app(environ, start_response):
    facts.append({
        'scheme':
        environ.get('wsgi.url_scheme'),
        'host':
        environ.get('HTTP_HOST'),
        'origin':
        environ.get('HTTP_ORIGIN'),
        'query_keys':
        list(__import__('urllib.parse', fromlist=['parse_qs']).parse_qs(environ.get('QUERY_STRING', '')).keys()),
        'wsgi_websocket_present':
        environ.get('wsgi.websocket') is not None
    })
    delegate = environ['wsgi.websocket']

    class ObserveClient:
        def __getattr__(self, name):
            return getattr(delegate, name)

        def receive(self):
            message = delegate.receive()
            facts.append({'client_binary_receive_type': type(message).__name__})
            return message

    environ['wsgi.websocket'] = ObserveClient()
    return full_wsgi(environ, start_response)


server = WSGIServer(('127.0.0.1', 0), app, handler_class=WebSocketHandler, log=None, error_log=None)
server.start()
results = []


def client():
    ws = None
    try:
        origin = 'http://127.0.0.1:' + str(server.server_port)
        ws = websocket.create_connection('ws://127.0.0.1:' + str(server.server_port) + '/websockify',
                                         origin=origin,
                                         cookie='token=transport-fixture',
                                         timeout=4,
                                         http_no_proxy=['127.0.0.1'])
        opcode, data = ws.recv_data()
        result = {'status': ws.status, 'opcode': opcode, 'rfb': data == b'RFB 003.008\n'}
        ws.send_binary(b'RFB 003.008\n')
        reply_opcode, reply_data = ws.recv_data()
        result.update(roundtrip=reply_opcode == 2 and reply_data == b'local-roundtrip-ok', reply_opcode=reply_opcode)
        results.append(result)
    except Exception as e:
        results.append({
            'error_type': type(e).__name__,
            'invalid_websocket_header': 'invalid websocket header' in str(e).lower()
        })
    finally:
        if ws:
            ws.close()


with mock.patch.object(AppBaseView, 'initial', initial):
    job = gevent.spawn(client)
    job.join(timeout=7)
server.stop()
upstream.stop()
print(
    json.dumps(
        {
            'facts':
            facts,
            'results':
            results,
            'upstream_received':
            upstream_received,
            'scope':
            ('local fixture Cookie authentication with full Django WSGI middleware + real GeventWebSocketHandler '
             '+ proxy + real upstream; no production credentials')
        },
        ensure_ascii=False))

import base64
import gzip
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


MANAGE_FIXTURE = '''
from django.conf import settings
from django.core.management import execute_from_command_line

settings.configure(
    DEBUG=False,
    INSTALLED_APPS=['django.contrib.staticfiles', 'www'],
    STATIC_URL='/static/',
    STATIC_ROOT='static/',
)
execute_from_command_line()
'''

REQUEST_FIXTURE = '''
import base64
import json
import sys

import django
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from django.middleware.gzip import GZipMiddleware
from django.test import RequestFactory
from whitenoise.middleware import WhiteNoiseMiddleware

options = json.loads(sys.argv[1])
settings.configure(
    DEBUG=options['debug'],
    INSTALLED_APPS=['django.contrib.staticfiles', 'www'],
    STATIC_URL='/static/',
    STATIC_ROOT='static/',
    WHITENOISE_USE_FINDERS=options['finders'],
)
django.setup()

def dynamic_view(request):
    if request.path == '/console/fixture':
        return HttpResponse(b'{"data":"' + b'unchanged-api-' * 100 + b'"}', content_type='application/json')
    if request.path == '/console/fixture-stream':
        response = StreamingHttpResponse(iter([b'data: unchanged-stream\\n\\n']), content_type='text/event-stream')
        response['Content-Encoding'] = 'identity'
        return response
    return HttpResponse(status=404)

application = WhiteNoiseMiddleware(GZipMiddleware(dynamic_view))
request = RequestFactory().generic(options['method'], options['path'], **options['headers'])
response = application(request)
body = b''.join(response.streaming_content) if response.streaming else response.content
response.close()
print(json.dumps({'status': response.status_code, 'headers': dict(response.items()),
                  'body': base64.b64encode(body).decode('ascii')}))
'''


# capability_id: console.runtime.static-precompression
class StaticPrecompressionTests(unittest.TestCase):
    """Execute the Docker static commands, then exercise real WhiteNoise serving."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='rainbond-static-precompression-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.source = cls.root / 'www' / 'static'
        cls.collected = cls.root / 'static'
        cls.assets = {
            'dists/umi.fixture.js': b'window.staticFixture = "same UI code";\n' * 1000,
            'dists/umi.fixture.css': b'.fixture { color: #123456; }\n' * 1000,
            'www/weavescope-topolog/app-polling-fixture.js': b'window.topologyFixture = "same topology code";\n' * 1000,
            'www/weavescope-topolog/vendors.js': b'window.vendorFixture = "same vendor code";\n' * 1000,
            'www/weavescope-topolog/index.html': (
                b'<script src="vendors.js?fixture"></script><script src="app-polling-fixture.js"></script>\n' * 30),
            'www/img/fixture.png': b'compressible-but-image-skipped' * 100,
            'tiny.txt': b'x',
            'incompressible.txt': b''.join(hashlib.sha256(str(index).encode('ascii')).digest() for index in range(128)),
        }
        (cls.root / 'www').mkdir()
        (cls.root / 'www' / '__init__.py').write_text('', encoding='utf-8')
        for relative, body in cls.assets.items():
            target = cls.source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        (cls.root / 'manage.py').write_text(MANAGE_FIXTURE, encoding='utf-8')
        (cls.root / 'request_fixture.py').write_text(REQUEST_FIXTURE, encoding='utf-8')
        dockerfile = (Path(__file__).resolve().parents[2] / 'Dockerfile').read_text(encoding='utf-8')
        commands = [shlex.split(part.strip()) for part in dockerfile.replace('\\\n', '').split('&&')]
        start = next(index for index, command in enumerate(commands) if command[:3] == ['python', 'manage.py', 'collectstatic'])
        cls.commands = []
        for command in commands[start:]:
            if command[0] != 'python':
                break
            cls.commands.append(command)
        cls.run_static_commands()

    @classmethod
    def run_static_commands(cls):
        for command in cls.commands:
            subprocess.run(
                [sys.executable] + command[1:], cwd=str(cls.root), check=True, capture_output=True, text=True, timeout=30)

    def request(self, path, encoding='gzip', debug=False, finders=False, method='GET', headers=None):
        options = {
            'path': path,
            'debug': debug,
            'finders': finders,
            'method': method,
            'headers': dict({'HTTP_ACCEPT_ENCODING': encoding}, **(headers or {})),
        }
        completed = subprocess.run(
            [sys.executable, 'request_fixture.py', json.dumps(options)],
            cwd=str(self.root), check=True, capture_output=True, text=True, timeout=10)
        result = json.loads(completed.stdout)
        result['body'] = base64.b64decode(result['body'])
        return result

    def assert_compressed(self, relative, debug=False, finders=False):
        response = self.request('/static/' + relative, debug=debug, finders=finders)
        self.assertEqual(200, response['status'])
        self.assertEqual('gzip', response['headers'].get('Content-Encoding'))
        self.assertEqual('Accept-Encoding', response['headers'].get('Vary'))
        self.assertEqual(self.assets[relative], gzip.decompress(response['body']))
        self.assertLess(len(response['body']), len(self.assets[relative]))
        identity = self.request('/static/' + relative, encoding='identity', debug=debug, finders=finders)
        self.assertEqual(200, identity['status'])
        self.assertNotIn('Content-Encoding', identity['headers'])
        self.assertEqual('Accept-Encoding', identity['headers'].get('Vary'))
        self.assertEqual(self.assets[relative], identity['body'])
        return response

    def test_collected_assets_negotiate_gzip_without_changing_originals(self):
        for relative in list(self.assets)[:5]:
            with self.subTest(asset=relative):
                self.assert_compressed(relative)
                self.assertEqual(self.assets[relative], (self.source / relative).read_bytes())
                self.assertEqual(self.assets[relative], (self.collected / relative).read_bytes())

    def test_source_finder_paths_also_negotiate_gzip(self):
        for debug in (False, True):
            with self.subTest(debug=debug):
                self.assert_compressed('dists/umi.fixture.js', debug=debug, finders=True)
                self.assert_compressed('www/weavescope-topolog/app-polling-fixture.js', debug=debug, finders=True)

    def test_gzip_etag_revalidation_and_head_preserve_response_contract(self):
        for debug, finders in ((False, False), (False, True), (True, True)):
            with self.subTest(debug=debug, finders=finders):
                response = self.assert_compressed('dists/umi.fixture.js', debug=debug, finders=finders)
                path = '/static/dists/umi.fixture.js'
                conditional = self.request(path, debug=debug, finders=finders,
                                           headers={'HTTP_IF_NONE_MATCH': response['headers']['ETag']})
                self.assertEqual(304, conditional['status'])
                self.assertEqual(b'', conditional['body'])
                self.assertEqual('Accept-Encoding', conditional['headers'].get('Vary'))
                head = self.request(path, debug=debug, finders=finders, method='HEAD')
                self.assertEqual(200, head['status'])
                self.assertEqual(b'', head['body'])
                self.assertEqual('gzip', head['headers'].get('Content-Encoding'))
                self.assertEqual(str(len(response['body'])), head['headers'].get('Content-Length'))

    def test_repeated_build_commands_keep_gzip_stable_without_recursive_variants(self):
        compressed_before = {
            str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*.gz')
        }
        self.assertTrue(compressed_before)
        self.run_static_commands()
        compressed_after = {
            str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*.gz')
        }
        self.assertEqual(compressed_before, compressed_after)
        self.assertFalse(list(self.root.rglob('*.gz.gz')))
        self.assertFalse(list(self.root.rglob('*.br')))
        self.assertFalse(list(self.root.rglob('staticfiles.json')))
        for relative, original in self.assets.items():
            self.assertEqual(original, (self.source / relative).read_bytes())
            self.assertEqual(original, (self.collected / relative).read_bytes())

    def test_images_and_ineffective_compression_keep_only_original(self):
        for relative in list(self.assets)[5:]:
            with self.subTest(asset=relative):
                for root in (self.source, self.collected):
                    self.assertFalse((root / (relative + '.gz')).exists())
                response = self.request('/static/' + relative)
                self.assertEqual(200, response['status'])
                self.assertNotIn('Content-Encoding', response['headers'])
                self.assertEqual(self.assets[relative], response['body'])

    def test_dynamic_api_and_identity_sse_keep_existing_behavior(self):
        api = self.request('/console/fixture')
        self.assertEqual(200, api['status'])
        self.assertEqual('gzip', api['headers'].get('Content-Encoding'))
        self.assertEqual('application/json', api['headers'].get('Content-Type'))
        self.assertEqual({'data': 'unchanged-api-' * 100}, json.loads(gzip.decompress(api['body'])))
        stream = self.request('/console/fixture-stream')
        self.assertEqual(200, stream['status'])
        self.assertEqual('identity', stream['headers'].get('Content-Encoding'))
        self.assertEqual(b'data: unchanged-stream\n\n', stream['body'])
        self.assertNotIn('Content-Length', stream['headers'])


if __name__ == '__main__':
    unittest.main()

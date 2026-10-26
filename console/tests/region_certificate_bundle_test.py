# -*- coding: utf-8 -*-
# capability_id: console.region-api.immutable-certificate-bundle
import multiprocessing
import errno
import os
import shutil
import stat
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from www.apiclient.certificate_bundle import materialize_certificate_bundle


def _materials(revision):
    return tuple('material revision {} item {}'.format(revision, item) for item in range(3))


def _concurrent_bundle_reader(root, revision, ready, results):
    """Spawned workers have no Django, network or active gevent dependency."""
    try:
        expected = _materials(revision)
        ready.wait(timeout=20)
        paths = materialize_certificate_bundle(root, *expected)
        for _ in range(40):
            if tuple(Path(path).read_text() for path in paths) != expected:
                results.put(('incomplete', revision))
                return
            if materialize_certificate_bundle(root, *expected) != paths:
                results.put(('unstable', revision))
                return
        results.put(('ok', revision))
    except Exception as error:
        results.put(('error', type(error).__name__))


class RegionCertificateBundleTestCase(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = os.path.join(self.directory.name, 'bundles')

    def test_materializes_complete_bundle_with_private_directory_and_file_modes(self):
        previous_umask = os.umask(0)
        try:
            paths = materialize_certificate_bundle(self.root, *_materials('A'))
        finally:
            os.umask(previous_umask)

        self.assertEqual(tuple(Path(path).read_text() for path in paths), _materials('A'))
        self.assertEqual(len({os.path.dirname(path) for path in paths}), 1)
        self.assertEqual(stat.S_IMODE(os.stat(self.root).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(paths[0])).st_mode), 0o700)
        for path in paths:
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_identical_material_reuses_files_without_write_fsync_or_metadata_changes(self):
        paths = materialize_certificate_bundle(self.root, *_materials('A'))
        before = [(os.stat(path).st_ino, os.stat(path).st_mtime_ns) for path in paths]

        with mock.patch('www.apiclient.certificate_bundle.os.open') as opened, \
                mock.patch('www.apiclient.certificate_bundle.os.fsync') as synced:
            repeated = materialize_certificate_bundle(self.root, *_materials('A'))

        self.assertEqual(repeated, paths)
        self.assertEqual(before, [(os.stat(path).st_ino, os.stat(path).st_mtime_ns) for path in paths])
        opened.assert_not_called()
        synced.assert_not_called()

    def test_any_material_change_publishes_new_complete_revision_without_changing_old_files(self):
        old_materials = _materials('A')
        old_paths = materialize_certificate_bundle(self.root, *old_materials)
        old_metadata = [os.stat(path).st_ino for path in old_paths]
        for index in range(3):
            with self.subTest(index=index):
                revised = list(old_materials)
                revised[index] = 'updated ordinary material {}'.format(index)
                new_paths = materialize_certificate_bundle(self.root, *revised)
                self.assertTrue(all(new != old for new, old in zip(new_paths, old_paths)))
                self.assertEqual(len({os.path.dirname(path) for path in new_paths}), 1)
                self.assertEqual(tuple(Path(path).read_text() for path in new_paths), tuple(revised))
                self.assertEqual(tuple(Path(path).read_text() for path in old_paths), old_materials)
                self.assertEqual([os.stat(path).st_ino for path in old_paths], old_metadata)

    def test_absolute_and_empty_values_are_untouched_and_do_not_create_storage(self):
        cases = ((None, '', None), ('/not-read/ca', '/not-read/cert', '/not-read/key'))
        for materials in cases:
            with self.subTest(materials=materials):
                self.assertEqual(materialize_certificate_bundle(self.root, *materials), materials)
                self.assertFalse(os.path.exists(self.root))

    def test_mixed_inputs_preserve_external_path_content_and_permissions(self):
        external = Path(self.directory.name) / 'external'
        external.write_text('external ordinary material')
        external.chmod(0o640)
        inputs = (str(external), 'inline ordinary material', None)
        paths = materialize_certificate_bundle(self.root, *inputs)
        self.assertEqual(paths[0], str(external))
        self.assertIsNone(paths[2])
        self.assertEqual(Path(paths[1]).read_text(), inputs[1])
        self.assertEqual(external.read_text(), 'external ordinary material')
        self.assertEqual(stat.S_IMODE(external.stat().st_mode), 0o640)
        self.assertEqual(os.listdir(os.path.dirname(paths[1])), ['client.pem'])
        changed_path = materialize_certificate_bundle(self.root, '/other/external', inputs[1], None)
        self.assertNotEqual(paths[1], changed_path[1])

    def test_write_or_publish_failure_cleans_only_own_pending_files(self):
        for operation in ('os.fsync', 'os.rename'):
            with self.subTest(operation=operation):
                with mock.patch('www.apiclient.certificate_bundle.' + operation, side_effect=OSError('write failed')):
                    with self.assertRaises(OSError):
                        materialize_certificate_bundle(self.root, *_materials('A'))
                self.assertEqual(os.listdir(self.root), [])

    def test_insecure_or_symlink_storage_root_is_rejected_without_writing_material(self):
        os.mkdir(self.root, 0o755)
        with self.assertRaises(OSError):
            materialize_certificate_bundle(self.root, *_materials('A'))
        self.assertEqual(os.listdir(self.root), [])
        os.rmdir(self.root)
        os.symlink(self.directory.name, self.root)
        with self.assertRaises(OSError):
            materialize_certificate_bundle(self.root, *_materials('A'))
        self.assertEqual(os.listdir(self.directory.name), ['bundles'])

    def test_incomplete_or_unsafe_published_revision_is_rejected_not_repaired_in_place(self):
        paths = materialize_certificate_bundle(self.root, *_materials('A'))
        Path(paths[0]).write_text('truncated')
        with self.assertRaises(OSError):
            materialize_certificate_bundle(self.root, *_materials('A'))
        self.assertEqual(Path(paths[0]).read_text(), 'truncated')

    def test_missing_or_symlink_file_and_symlink_revision_fail_without_repair(self):
        for failure in ('missing-file', 'symlink-file', 'symlink-directory'):
            with self.subTest(failure=failure):
                root = os.path.join(self.directory.name, failure)
                paths = materialize_certificate_bundle(root, *_materials('A'))
                if failure == 'symlink-directory':
                    revision = os.path.dirname(paths[0])
                    os.rename(revision, revision + '-saved')
                    os.symlink(revision + '-saved', revision)
                else:
                    os.unlink(paths[0])
                    if failure == 'symlink-file':
                        os.symlink(paths[1], paths[0])
                with self.assertRaises(OSError):
                    materialize_certificate_bundle(root, *_materials('A'))
                self.assertFalse(any(name.startswith('.pending-') for name in os.listdir(root)))

    def test_roles_boundaries_and_none_empty_values_have_distinct_revisions(self):
        materials = (('ab', 'c', ''), ('a', 'bc', ''), ('ab', 'c', None), ('c', 'ab', ''))
        revisions = {os.path.dirname(materialize_certificate_bundle(self.root, *values)[0]) for values in materials}
        self.assertEqual(len(revisions), len(materials))

    def test_simultaneous_publisher_reuses_winner_and_removes_only_own_pending_directory(self):
        def publish_winner(pending, revision):
            shutil.copytree(pending, revision)
            raise OSError(errno.EEXIST, 'revision already published')

        with mock.patch('www.apiclient.certificate_bundle.os.rename', side_effect=publish_winner):
            paths = materialize_certificate_bundle(self.root, *_materials('A'))

        self.assertEqual(tuple(Path(path).read_text() for path in paths), _materials('A'))
        self.assertEqual(os.listdir(self.root), [os.path.basename(os.path.dirname(paths[0]))])

    def test_multiple_processes_publish_and_read_complete_revisions_without_truncation(self):
        context = multiprocessing.get_context('spawn')
        ready = context.Barrier(7)
        results = context.Queue()
        workers = [
            context.Process(target=_concurrent_bundle_reader, args=(self.root, revision, ready, results))
            for revision in ('A', 'A', 'A', 'B', 'B', 'B')
        ]
        try:
            for worker in workers:
                worker.start()
            ready.wait(timeout=20)
            messages = [results.get(timeout=20) for _ in workers]
            self.assertEqual(sorted(messages), [('ok', 'A')] * 3 + [('ok', 'B')] * 3)
            for worker in workers:
                worker.join(timeout=20)
                self.assertEqual(worker.exitcode, 0)
            self.assertEqual(len(os.listdir(self.root)), 2)
            self.assertFalse(any(name.startswith('.pending-') for name in os.listdir(self.root)))
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                worker.join(timeout=5)
            results.close()
            results.join_thread()

    def test_configuration_binds_one_revision_and_preserves_tls_options(self):
        from django.test import override_settings
        from www.apiclient.regionapibaseclient import Configuration

        region = SimpleNamespace(url='https://region.example.invalid',
                                 enterprise_id='test-enterprise',
                                 region_name='../not-a-path',
                                 ssl_ca_cert=_materials('A')[0],
                                 cert_file=_materials('A')[1],
                                 key_file=_materials('A')[2])
        with override_settings(BASE_DIR=self.directory.name), \
                mock.patch.dict(os.environ, {'REGION_SSL_VERIFY': 'true'}), \
                mock.patch('www.apiclient.regionapibaseclient.check_file_path') as legacy_write:
            old = Configuration(region, assert_hostname='cluster.internal')
            region.cert_file = 'next ordinary material'
            new = Configuration(region, assert_hostname='cluster.internal')

        legacy_write.assert_not_called()
        self.assertTrue(old.verify_ssl)
        self.assertEqual(old.assert_hostname, 'cluster.internal')
        self.assertEqual(old.host, region.url)
        self.assertIsNone(old.proxy)
        self.assertEqual(old.connection_pool_maxsize, multiprocessing.cpu_count() * 5)
        old_paths = (old.ssl_ca_cert, old.cert_file, old.key_file)
        new_paths = (new.ssl_ca_cert, new.cert_file, new.key_file)
        self.assertEqual(tuple(Path(path).read_text() for path in old_paths), _materials('A'))
        self.assertEqual(len({os.path.dirname(path) for path in old_paths}), 1)
        self.assertEqual(len({os.path.dirname(path) for path in new_paths}), 1)
        self.assertNotEqual(old.ssl_ca_cert, new.ssl_ca_cert)
        self.assertTrue(all(path.startswith(self.directory.name + os.sep + 'data' + os.sep) for path in old_paths))

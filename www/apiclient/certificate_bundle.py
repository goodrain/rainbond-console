# -*- coding: utf-8 -*-
"""Publish complete, private certificate revisions without rewriting active files."""
import errno
import hashlib
import json
import os
import shutil
import stat
import tempfile

_FILENAMES = ('ca.pem', 'client.pem', 'client.key.pem')


def _private_directory(path):
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise OSError('Unsafe region certificate directory')


def _bundle_ready(path, inline):
    try:
        _private_directory(path)
    except FileNotFoundError:
        return False
    for name, body in inline:
        info = os.lstat(os.path.join(path, name))
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size != len(body)):
            raise OSError('Unsafe or incomplete region certificate bundle')
    return True


def materialize_certificate_bundle(root, ssl_ca_cert, cert_file, key_file):
    """Return one immutable revision for inline values; external paths stay caller-managed.

    A private temporary directory is published only after every inline file is
    complete. Another process can reuse that revision but cannot see it half
    written. Existing revisions are deliberately not removed: an older pool may
    still need them when it opens a new TLS connection.

    This is trusted private cache reuse, not a disk-integrity scanner. External
    paths and administrator changes to published files remain caller-managed.
    """
    materials = (ssl_ca_cert, cert_file, key_file)
    inline = [(name, value.encode('utf-8')) for name, value in zip(_FILENAMES, materials)
              if value and not value.startswith('/')]
    if not inline:
        return materials

    # Canonical ordered JSON preserves role boundaries, None/empty and external
    # paths without exposing any of those values in filenames or messages.
    digest = hashlib.sha256(json.dumps(materials, ensure_ascii=False).encode('utf-8')).hexdigest()
    os.makedirs(root, mode=0o700, exist_ok=True)
    _private_directory(root)
    revision = os.path.join(root, digest)
    if not _bundle_ready(revision, inline):
        pending = tempfile.mkdtemp(prefix='.pending-', dir=root)
        try:
            os.chmod(pending, 0o700)
            for name, body in inline:
                descriptor = os.open(os.path.join(pending, name), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, 'wb') as output:
                    os.fchmod(output.fileno(), 0o600)
                    output.write(body)
                    output.flush()
                    os.fsync(output.fileno())
            try:
                os.rename(pending, revision)
            except OSError as error:
                if error.errno not in (errno.EEXIST, errno.ENOTEMPTY) or not _bundle_ready(revision, inline):
                    raise
        finally:
            if os.path.exists(pending):
                shutil.rmtree(pending)

    return tuple(
        os.path.join(revision, name) if value and not value.startswith('/') else value
        for name, value in zip(_FILENAMES, materials))

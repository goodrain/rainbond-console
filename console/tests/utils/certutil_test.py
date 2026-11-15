# coding: utf-8
from unittest import TestCase

import os
import sys
from types import ModuleType

from cryptography.hazmat.primitives import serialization

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")


def _load_test_dependencies():
    """Keep the existing post-Django-setup import order and module bindings."""
    import django

    django.setup()

    from OpenSSL import crypto

    from console.exception.main import ServiceHandleException
    from console.utils.certutil import analyze_cert
    from console.utils.certutil import cert_is_effective
    from console.utils.certutil import parse_subject_alt_names
    from console.utils.certutil import utc2local
    from console.utils.certutil import validate_ca_certificate  # noqa: E402
    return (
        django,
        crypto,
        ServiceHandleException,
        analyze_cert,
        cert_is_effective,
        parse_subject_alt_names,
        utc2local,
        validate_ca_certificate,
    )


(
    django,
    crypto,
    ServiceHandleException,
    analyze_cert,
    cert_is_effective,
    parse_subject_alt_names,
    utc2local,
    validate_ca_certificate,
) = _load_test_dependencies()


class CertUtilTests(TestCase):
    def _generate_cert_and_key(self):
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)

        cert = crypto.X509()
        cert.set_version(2)
        cert.set_serial_number(1)
        cert.get_subject().CN = "example.com"
        cert.get_issuer().CN = "example.com"
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)
        cert.set_pubkey(key)
        cert.add_extensions([
            crypto.X509Extension(b"subjectAltName", False, b"DNS:example.com, DNS:api.example.com, IP:10.0.0.1"),
        ])
        cert.sign(key, "sha256")

        cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
        return cert_pem, key_pem

    def _generate_ca_certificate(self, is_ca=True, expired=False):
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)

        cert = crypto.X509()
        cert.set_version(2)
        cert.set_serial_number(10 if is_ca else 11)
        cert.get_subject().CN = "client-ca" if is_ca else "client"
        cert.get_issuer().CN = cert.get_subject().CN
        cert.gmtime_adj_notBefore(-2 * 24 * 60 * 60 if expired else 0)
        cert.gmtime_adj_notAfter(-24 * 60 * 60 if expired else 365 * 24 * 60 * 60)
        cert.set_pubkey(key)
        cert.add_extensions([
            crypto.X509Extension(b"basicConstraints", True, b"CA:TRUE" if is_ca else b"CA:FALSE"),
            crypto.X509Extension(b"keyUsage", True, b"keyCertSign" if is_ca else b"digitalSignature"),
        ])
        cert.sign(key, "sha256")
        return crypto.dump_certificate(crypto.FILETYPE_PEM, cert)

    # capability_id: console.cert.summary
    def test_analyze_cert(self):
        cert_pem, _ = self._generate_cert_and_key()
        info = analyze_cert(cert_pem)
        self.assertIn("example.com", info["issued_to"])
        self.assertIn("api.example.com", info["issued_to"])
        self.assertIn("10.0.0.1", info["issued_to"])
        self.assertFalse(info["has_expired"])

    # capability_id: console.cert.san-parse
    def test_parse_subject_alt_names(self):
        content = "DNS:example.com, DNS:api.example.com, IP Address:10.0.0.1, DNS:127.0.0.1"
        sans = parse_subject_alt_names(content)
        self.assertEqual(sans, ["example.com", "api.example.com", "10.0.0.1"])

    # capability_id: console.cert.utc-to-local
    def test_utc2local(self):
        local_time = utc2local("20260329093000Z")
        self.assertIn("2026-03-29", local_time)

    # capability_id: console.cert.key-match
    def test_cert_is_effective(self):
        cert_pem, key_pem = self._generate_cert_and_key()
        self.assertTrue(cert_is_effective(cert_pem, key_pem))

        wrong_key = crypto.PKey()
        wrong_key.generate_key(crypto.TYPE_RSA, 2048)
        wrong_key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, wrong_key)
        with self.assertRaises(ServiceHandleException):
            cert_is_effective(cert_pem, wrong_key_pem)

    # capability_id: console.cert.key-format-compatibility
    def test_cert_is_effective_matches_equivalent_private_key_encodings(self):
        cert_pem, key_pem = self._generate_cert_and_key()
        key = serialization.load_pem_private_key(key_pem, password=None)
        for encoding in (serialization.PrivateFormat.PKCS8, serialization.PrivateFormat.TraditionalOpenSSL):
            encoded = key.private_bytes(serialization.Encoding.PEM, encoding, serialization.NoEncryption())
            self.assertTrue(cert_is_effective(cert_pem, encoded))
            self.assertTrue(cert_is_effective(cert_pem, encoded.decode("ascii")))

    # capability_id: console.cert.key-format-compatibility
    def test_cert_is_effective_rejects_a_public_key_without_private_material(self):
        cert_pem, key_pem = self._generate_cert_and_key()
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
        public_pem = crypto.dump_publickey(crypto.FILETYPE_PEM, key)
        with self.assertRaises(ServiceHandleException):
            cert_is_effective(cert_pem, public_pem)

    # capability_id: console.cert.expired-reject
    def test_cert_is_effective_rejects_expired_cert(self):
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)

        cert = crypto.X509()
        cert.set_version(2)
        cert.set_serial_number(2)
        cert.get_subject().CN = "expired.example.com"
        cert.get_issuer().CN = "expired.example.com"
        cert.gmtime_adj_notBefore(-10 * 24 * 60 * 60)
        cert.gmtime_adj_notAfter(-24 * 60 * 60)
        cert.set_pubkey(key)
        cert.sign(key, "sha256")

        cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
        with self.assertRaises(ServiceHandleException):
            cert_is_effective(cert_pem, key_pem)

    # capability_id: console.cert.invalid-private-key
    def test_cert_is_effective_rejects_invalid_private_key(self):
        cert_pem, _ = self._generate_cert_and_key()
        with self.assertRaises(ServiceHandleException):
            cert_is_effective(cert_pem, b"not-a-private-key")

    # capability_id: console.gateway.client-ca-management
    def test_validate_ca_certificate(self):
        self.assertTrue(validate_ca_certificate(self._generate_ca_certificate()))

        with self.assertRaises(ServiceHandleException):
            validate_ca_certificate(self._generate_ca_certificate(is_ca=False))
        with self.assertRaises(ServiceHandleException):
            validate_ca_certificate(self._generate_ca_certificate(expired=True))
        with self.assertRaises(ServiceHandleException):
            validate_ca_certificate(b"not-a-certificate")

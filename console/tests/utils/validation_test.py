# coding: utf-8
from unittest import TestCase

import os
import sys
from types import ModuleType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django

django.setup()

from console.exception.main import ServiceHandleException
from console.utils.validation import is_qualified_name
from console.utils.validation import normalize_name_for_k8s_namespace
from console.utils.validation import validate_name
from console.utils.validation import validate_endpoint_address
from console.utils.validation import validate_endpoints_info


class EndpointValidationTests(TestCase):
    # capability_id: console.endpoint-address.reject-special-ranges
    def test_validate_endpoint_address_rejects_special_ranges(self):
        errs, domain_ip = validate_endpoint_address("0.0.0.0")
        self.assertFalse(domain_ip)
        self.assertTrue(any("unspecified" in err for err in errs))

        errs, domain_ip = validate_endpoint_address("127.0.0.1")
        self.assertFalse(domain_ip)
        self.assertTrue(any("loopback" in err for err in errs))

        errs, domain_ip = validate_endpoint_address("example.com")
        self.assertTrue(domain_ip)
        self.assertEqual(errs, [])

    # capability_id: console.endpoint-address.reject-invalid-format
    def test_validate_endpoint_address_rejects_invalid_format(self):
        errs, domain_ip = validate_endpoint_address("not-an-address")
        self.assertFalse(domain_ip)
        self.assertTrue(any("valid IP address" in err for err in errs))

    # capability_id: console.endpoint-list.normalize-scheme-port
    def test_validate_endpoints_info_normalizes_scheme_and_port(self):
        validate_endpoints_info([
            "https://1.2.3.4:8443",
            "http://5.6.7.8:8080",
        ])

        with self.assertRaises(ServiceHandleException):
            validate_endpoints_info([
                "https://example.com:8443",
                "http://1.2.3.4:8080",
            ])

        with self.assertRaises(ServiceHandleException):
            validate_endpoints_info([
                "https://example.com:8443",
                "http://another.example.com:8080",
            ])

    # capability_id: console.endpoint-list.reject-duplicate
    def test_validate_endpoints_info_rejects_duplicate_addresses(self):
        with self.assertRaises(ServiceHandleException):
            validate_endpoints_info([
                "1.2.3.4:80",
                "1.2.3.4:80",
            ])


class NamespaceNormalizationTests(TestCase):
    # capability_id: console.k8s-namespace.normalize-user-prefix
    def test_normalize_name_for_k8s_namespace(self):
        self.assertEqual(normalize_name_for_k8s_namespace("Alice"), "alice")
        self.assertEqual(normalize_name_for_k8s_namespace("123Bad Name"), "user-123bad-name")
        self.assertEqual(normalize_name_for_k8s_namespace("bad---name"), "bad-name")

        long_name = "USER_" + ("A" * 80)
        normalized = normalize_name_for_k8s_namespace(long_name)
        self.assertTrue(normalized.startswith("user-"))
        self.assertLessEqual(len(normalized), 63)

    # capability_id: console.validation.display-name
    def test_validate_name(self):
        self.assertTrue(validate_name("demo-name"))
        self.assertTrue(validate_name("中文名称"))
        self.assertFalse(validate_name("-bad"))
        self.assertFalse(validate_name("bad."))

    # capability_id: console.validation.k8s-qualified-name
    def test_is_qualified_name(self):
        self.assertTrue(is_qualified_name("demo-app"))
        self.assertTrue(is_qualified_name("a1"))
        self.assertFalse(is_qualified_name("1demo"))
        self.assertFalse(is_qualified_name("demo-"))

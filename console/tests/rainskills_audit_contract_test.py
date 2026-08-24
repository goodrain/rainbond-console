# -*- coding: utf-8 -*-
import hashlib
import json
import uuid

from django.test import SimpleTestCase

from console.exception.main import ServiceHandleException
from console.services.rainskills_audit_contract import (
    RAINSKILLS_META_NAMESPACE,
    extract_operation_meta,
    validate_operation_meta,
)


class RainSkillsAuditContractTests(SimpleTestCase):

    def setUp(self):
        self.content = "# Example Skill\n\nUse the existing Rainbond API.\n"
        self.operation_id = str(uuid.uuid4())
        self.valid_meta = {
            "schema": "rainskills.operation-meta.v1",
            "operation_id": self.operation_id,
            "cli_version": "2.2.0",
            "confirmation_type": "rainskills_cli",
            "root_skill_id": "rainbond-app-assistant",
            "skill": {
                "id": "rainbond-fullstack-bootstrap",
                "profile": "cli",
                "package_version": "1.0.0",
                "source_revision": None,
                "content_sha256": hashlib.sha256(self.content.encode("utf-8")).hexdigest(),
                "bundle_sha256": "a" * 64,
                "content": self.content,
            },
        }

    def assert_contract_error(self, metadata, error_code="invalid_operation_metadata"):
        with self.assertRaises(ServiceHandleException) as raised:
            validate_operation_meta(metadata)
        self.assertEqual(raised.exception.error_code, error_code)

    def test_valid_metadata_is_normalized_without_adding_authoritative_fields(self):
        validated = validate_operation_meta(self.valid_meta)

        self.assertEqual(validated["operation_id"], self.operation_id)
        self.assertEqual(validated["skill"]["content"], self.content)
        self.assertNotIn("actor", validated)
        self.assertNotIn("enterprise_id", validated)
        self.assertNotIn("risk", validated)
        self.assertNotIn("scope", validated)

    def test_extracts_only_the_namespaced_metadata(self):
        request_meta = {
            "progressToken": "client-owned",
            RAINSKILLS_META_NAMESPACE: self.valid_meta,
        }

        self.assertEqual(extract_operation_meta(request_meta), self.valid_meta)
        self.assertIsNone(extract_operation_meta({"progressToken": "other"}))
        self.assertIsNone(extract_operation_meta(None))

    def test_rejects_invalid_uuid_schema_and_unknown_fields(self):
        for metadata in (
                dict(self.valid_meta, operation_id="not-a-uuid"),
                dict(self.valid_meta, schema="rainskills.operation-meta.v2"),
                dict(self.valid_meta, actor={"username": "forged"}),
                dict(self.valid_meta, enterprise_id="forged-enterprise"),
                dict(self.valid_meta, risk="low"),
                dict(self.valid_meta, scope="component")):
            with self.subTest(metadata=metadata):
                self.assert_contract_error(metadata)

    def test_rejects_invalid_skill_identifiers_and_confirmation(self):
        invalid_skill = dict(self.valid_meta["skill"], id="../outside")
        self.assert_contract_error(dict(self.valid_meta, skill=invalid_skill))
        self.assert_contract_error(dict(self.valid_meta, confirmation_type="agent_approval"))

    def test_rejects_skill_digest_mismatch(self):
        skill = dict(self.valid_meta["skill"], content_sha256="b" * 64)
        self.assert_contract_error(dict(self.valid_meta, skill=skill), "skill_digest_mismatch")

    def test_rejects_content_and_total_metadata_over_limits(self):
        oversized_content = "x" * (128 * 1024 + 1)
        skill = dict(
            self.valid_meta["skill"],
            content=oversized_content,
            content_sha256=hashlib.sha256(oversized_content.encode("utf-8")).hexdigest(),
        )
        self.assert_contract_error(dict(self.valid_meta, skill=skill))

        metadata = dict(self.valid_meta, cli_version="x" * (160 * 1024))
        self.assertGreater(len(json.dumps(metadata).encode("utf-8")), 160 * 1024)
        self.assert_contract_error(metadata)

    def test_rejects_non_object_namespaced_metadata(self):
        with self.assertRaises(ServiceHandleException) as raised:
            extract_operation_meta({RAINSKILLS_META_NAMESPACE: "forged"})
        self.assertEqual(raised.exception.error_code, "invalid_operation_metadata")

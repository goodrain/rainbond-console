# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.views.webhook import (  # noqa: E402
    UnsupportedImageWebhookEvent,
    parse_image_webhook_payload,
)


class ImageWebhookPayloadTestCase(TestCase):
    # capability_id: console.image-webhook.harbor-push-artifact
    def test_parse_harbor_push_artifact_payload(self):
        payload = {
            "type": "PUSH_ARTIFACT",
            "operator": "alice",
            "event_data": {
                "repository": {
                    "repo_full_name": "demo/web",
                    "name": "web",
                },
                "resources": [{
                    "tag": "v1.2.3",
                }],
            },
        }

        event = parse_image_webhook_payload(payload)

        self.assertEqual(event.repo_name, "demo/web")
        self.assertEqual(event.tag, "v1.2.3")
        self.assertEqual(event.pusher, "alice")

    # capability_id: console.image-webhook.harbor-push-artifact
    def test_parse_harbor_ignores_non_push_artifact_payload(self):
        payload = {
            "type": "DELETE_ARTIFACT",
            "operator": "alice",
            "event_data": {
                "repository": {
                    "repo_full_name": "demo/web",
                },
                "resources": [{
                    "tag": "v1.2.3",
                }],
            },
        }

        with self.assertRaises(UnsupportedImageWebhookEvent):
            parse_image_webhook_payload(payload)

    # capability_id: console.image-webhook.harbor-push-artifact
    def test_parse_registry_payload_keeps_existing_format(self):
        payload = {
            "push_data": {
                "pusher": "bob",
                "tag": "latest",
            },
            "repository": {
                "repo_name": "demo/api",
            },
        }

        event = parse_image_webhook_payload(payload)

        self.assertEqual(event.repo_name, "demo/api")
        self.assertEqual(event.tag, "latest")
        self.assertEqual(event.pusher, "bob")

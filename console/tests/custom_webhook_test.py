# coding: utf-8
import base64
import os
import pickle
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views import webhook as webhook_module  # noqa: E402


class CustomWebhookDeployTests(TestCase):
    # capability_id: console.webhook.custom-deploy-missing-component
    def test_post_returns_not_found_before_reading_key_for_deleted_component(self):
        view = webhook_module.CustomWebHooksDeploy()
        request = view.initialize_request(
            APIRequestFactory().post(
                "/console/custom/deploy/missing-service",
                {"secret_key": "secret"},
                format="json",
            )
        )
        manager = mock.Mock()
        manager.get.side_effect = webhook_module.TenantServiceInfo.DoesNotExist
        manager.filter.return_value.first.return_value = None
        encoded_key = repr(base64.b64encode(pickle.dumps({"secret_key": "secret"})))

        with mock.patch.object(webhook_module.TenantServiceInfo, "objects", manager), mock.patch.object(
                webhook_module.deploy_repo,
                "get_secret_key_by_service_id",
                return_value=encoded_key,
        ) as get_secret_key:
            response = view.post(request, "missing-service")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["msg_show"], "组件不存在")
        get_secret_key.assert_not_called()

    # capability_id: console.webhook.custom-deploy-missing-component
    def test_post_still_rejects_invalid_key_for_existing_component(self):
        view = webhook_module.CustomWebHooksDeploy()
        request = view.initialize_request(
            APIRequestFactory().post(
                "/console/custom/deploy/service-1",
                {"secret_key": "wrong"},
                format="json",
            )
        )
        manager = mock.Mock()
        manager.filter.return_value.first.return_value = SimpleNamespace(service_id="service-1")
        encoded_key = repr(base64.b64encode(pickle.dumps({"secret_key": "expected"})))

        with mock.patch.object(webhook_module.TenantServiceInfo, "objects", manager), mock.patch.object(
                webhook_module.deploy_repo,
                "get_secret_key_by_service_id",
                return_value=encoded_key,
        ), mock.patch.object(webhook_module.Tenants.objects, "get") as get_tenant:
            response = view.post(request, "service-1")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "密钥错误")
        get_tenant.assert_not_called()

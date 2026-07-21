# -*- coding: utf-8 -*-
import json
import os
import sys
from contextlib import ExitStack
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

django.setup()

from console.views.agent_kubernetes import AgentKubernetesBootstrapView


class AgentKubernetesBootstrapViewTests(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AgentKubernetesBootstrapView.as_view()

    @staticmethod
    def _user(enterprise_id="eid"):
        return SimpleNamespace(
            user_id=1,
            nick_name="admin",
            enterprise_id=enterprise_id,
            is_authenticated=True,
        )

    def _post(self, data, *, user=None, is_admin=True, enterprise_id="eid", region_name="rainbond"):
        request = self.factory.post(
            "/console/enterprise/{}/regions/{}/agent-kubernetes/bootstrap".format(enterprise_id, region_name),
            data=json.dumps(data),
            content_type="application/json",
        )
        force_authenticate(request, user=user or self._user())

        stack = ExitStack()
        enterprise_filter = stack.enter_context(mock.patch("console.views.base.TenantEnterprise.objects.filter"))
        enterprise_filter.return_value.first.return_value = SimpleNamespace(enterprise_id=enterprise_id)
        stack.enter_context(mock.patch("console.views.base.enterprise_user_perm_repo.is_admin", return_value=is_admin))
        stack.enter_context(mock.patch("console.views.base.user_services.list_roles", return_value=[]))
        stack.enter_context(mock.patch("console.views.base.perms.list_enterprise_perm_codes_by_roles", return_value=[]))
        bootstrap = stack.enter_context(mock.patch("console.views.agent_kubernetes.region_api.bootstrap_agent_kubeconfig"))
        proxy = stack.enter_context(mock.patch("console.views.agent_kubernetes.region_api.proxy"))
        proxy.return_value = Response({"ok": True}, status=200)
        return request, stack, bootstrap, proxy

    def test_post_defaults_to_ops_profile_and_forwards_resolved_fields(self):
        request, stack, bootstrap, proxy = self._post({})
        bootstrap.return_value = (None, {
            "bean": {
                "region_name": "rainbond",
                "credential_profile": "ops",
                "service_account": "rainbond-agent",
                "context_id": "rainbond",
                "kubeconfig": "secret-kubeconfig",
            }
        })

        with stack:
            response = self.view(request, enterprise_id="eid", region_name="rainbond")

        self.assertEqual(200, response.status_code)
        bootstrap.assert_called_once_with("eid", "rainbond", {
            "region_name": "rainbond",
            "context_id": "rainbond",
            "credential_profile": "ops",
            "service_account": "rainbond-agent",
        })
        agent_payload = json.loads(proxy.call_args.kwargs["requests_args"]["body"])
        self.assertEqual("ops", agent_payload["credential_profile"])
        self.assertEqual("rainbond-agent", agent_payload["service_account"])
        self.assertEqual("rainbond", agent_payload["context_id"])
        self.assertEqual("secret-kubeconfig", agent_payload["kubeconfig"])
        self.assertEqual(
            "/v2/platform/backend/plugins/rainbond-agent/api/v1/kubernetes/credentials/bootstrap",
            proxy.call_args.args[1],
        )
        self.assertEqual("rainbond", proxy.call_args.args[2])

    def test_post_readonly_uses_reader_identity_and_forwards_region_response(self):
        request, stack, bootstrap, proxy = self._post({"credential_profile": "readonly"})
        bootstrap.return_value = (None, {
            "bean": {
                "region_name": "rainbond",
                "credential_profile": "readonly",
                "service_account": "rainbond-agent-reader",
                "context_id": "region-context:readonly",
                "kubeconfig": "reader-kubeconfig",
            }
        })

        with stack:
            response = self.view(request, enterprise_id="eid", region_name="rainbond")

        self.assertEqual(200, response.status_code)
        bootstrap.assert_called_once_with("eid", "rainbond", {
            "credential_profile": "readonly",
            "region_name": "rainbond",
            "context_id": "rainbond:readonly",
            "service_account": "rainbond-agent-reader",
        })
        agent_payload = json.loads(proxy.call_args.kwargs["requests_args"]["body"])
        self.assertEqual("readonly", agent_payload["credential_profile"])
        self.assertEqual("rainbond-agent-reader", agent_payload["service_account"])
        self.assertEqual("region-context:readonly", agent_payload["context_id"])

    def test_post_rejects_readonly_with_non_reader_service_account(self):
        request, stack, bootstrap, proxy = self._post({
            "credential_profile": "readonly",
            "service_account": "rainbond-agent",
        })

        with stack:
            response = self.view(request, enterprise_id="eid", region_name="rainbond")

        self.assertEqual(400, response.status_code)
        bootstrap.assert_not_called()
        proxy.assert_not_called()

    def test_post_rejects_readonly_with_non_readonly_context(self):
        request, stack, bootstrap, proxy = self._post({
            "credential_profile": "readonly",
            "context_id": "rainbond",
        })

        with stack:
            response = self.view(request, enterprise_id="eid", region_name="rainbond")

        self.assertEqual(400, response.status_code)
        bootstrap.assert_not_called()
        proxy.assert_not_called()

    def test_post_accepts_explicit_readonly_context(self):
        request, stack, bootstrap, proxy = self._post({
            "credential_profile": "readonly",
            "context_id": "rainbond:readonly",
        })
        bootstrap.return_value = (None, {
            "bean": {
                "region_name": "rainbond",
                "credential_profile": "readonly",
                "service_account": "rainbond-agent-reader",
                "context_id": "rainbond:readonly",
                "kubeconfig": "reader-kubeconfig",
            }
        })

        with stack:
            response = self.view(request, enterprise_id="eid", region_name="rainbond")

        self.assertEqual(200, response.status_code)
        bootstrap.assert_called_once_with("eid", "rainbond", {
            "credential_profile": "readonly",
            "context_id": "rainbond:readonly",
            "region_name": "rainbond",
            "service_account": "rainbond-agent-reader",
        })
        proxy.assert_called_once()

    def test_post_rejects_unknown_credential_profile(self):
        request, stack, bootstrap, proxy = self._post({"credential_profile": "administrator"})

        with stack:
            response = self.view(request, enterprise_id="eid", region_name="rainbond")

        self.assertEqual(400, response.status_code)
        bootstrap.assert_not_called()
        proxy.assert_not_called()

    def test_post_rejects_non_string_credential_profile(self):
        request, stack, bootstrap, proxy = self._post({"credential_profile": []})

        with stack:
            response = self.view(request, enterprise_id="eid", region_name="rainbond")

        self.assertEqual(400, response.status_code)
        bootstrap.assert_not_called()
        proxy.assert_not_called()

    def test_post_keeps_non_admin_forbidden(self):
        request, stack, bootstrap, proxy = self._post({}, is_admin=False)

        with stack:
            response = self.view(request, enterprise_id="eid", region_name="rainbond")

        self.assertEqual(403, response.status_code)
        bootstrap.assert_not_called()
        proxy.assert_not_called()

    def test_post_keeps_enterprise_ownership_forbidden(self):
        request, stack, bootstrap, proxy = self._post({}, user=self._user("other-eid"))

        with stack:
            response = self.view(request, enterprise_id="eid", region_name="rainbond")

        self.assertEqual(403, response.status_code)
        bootstrap.assert_not_called()
        proxy.assert_not_called()

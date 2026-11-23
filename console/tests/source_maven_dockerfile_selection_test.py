# -*- coding: utf-8 -*-
import copy
import os
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.test import TestCase  # noqa: E402
from django.utils import timezone  # noqa: E402

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.mcp_query_service import mcp_query_service  # noqa: E402
from console.services import source_component_service as source_module  # noqa: E402
from console.services.source_component_service import source_component_service  # noqa: E402
from console.services.deployment_invocation import deployment_invocation_context  # noqa: E402
from scripts.export_mcp_tools import collect_tools  # noqa: E402
from www.models.main import ServiceGroup, ServiceGroupRelation, TenantServiceInfo  # noqa: E402


# capability_id: console.source-component.maven-root-dockerfile-selection
class MavenRootDockerfileSelectionTests(TestCase):
    def setUp(self):
        self.service = TenantServiceInfo.objects.create(
            service_id="maven-dockerfile-fixture", tenant_id="fixture-team", service_key="application",
            service_alias="api", service_cname="API", service_region="region", category="application",
            version="1", image="", k8s_component_name="api", language="Java-maven", build_strategy="cnb",
            service_source="source_code", server_type="git", create_status="checking", check_uuid="fixture-check",
            git_url="https://example.invalid/repo.git", code_version="main", arch="amd64",
        )
        self.team = SimpleNamespace(tenant_id=self.service.tenant_id, tenant_name="fixture-team",
                                    enterprise_id="fixture-enterprise")
        self.app = ServiceGroup.objects.create(tenant_id=self.service.tenant_id, region_name="region",
                                               group_name="fixture", create_time=timezone.now(), update_time=timezone.now())
        ServiceGroupRelation.objects.create(tenant_id=self.service.tenant_id, region_name="region",
                                            service_id=self.service.service_id, group_id=self.app.ID)
        self.user = SimpleNamespace(user_id=1, pk=1, nick_name="fixture-operator")
        common = {"language": "Java-maven,dockerfile", "dockerfiles": ["Dockerfile"], "envs": [], "ports": [], "volumes": []}
        self.result = {"check_status": "success", "error_infos": [], "service_info": [
            dict(common, id="module-one", name="module-one", cname="Module one", packaging="jar"),
            dict(common, id="module-two", name="module-two", cname="Module two", packaging="jar"),
        ]}

    def create(self, prefer=True):
        with mock.patch.object(source_module.console_app_service, "is_k8s_component_name_duplicate", return_value=False), \
                mock.patch.object(source_module.console_app_service, "create_source_code_app",
                                  return_value=(200, "success", self.service)), \
                mock.patch.object(source_module.group_service, "add_service_to_group", return_value=(200, "success")), \
                mock.patch.object(source_module.app_check_service, "check_service",
                                  return_value=(200, "success", {"check_uuid": "fixture-check"})), \
                mock.patch.object(source_component_service, "_wait_for_check_result", return_value=copy.deepcopy(self.result)), \
                mock.patch.object(source_module.console_app_service, "create_region_service",
                                  return_value=self.service) as create_region, \
                mock.patch.object(source_module.arch_service, "update_affinity_by_arch"):
            result = source_component_service.auto_create_component(
                self.team, self.app, self.user, "API", "gitlab_manual", self.service.git_url,
                is_deploy=False, prefer_dockerfile_when_detected=prefer,
            )
        return result, create_region

    def test_auto_create_selects_root_dockerfile_before_multi_module_rejection(self):
        result, create_region = self.create()
        self.assertTrue(result["dockerfile_preference_applied"])
        self.service.refresh_from_db()
        self.assertEqual(self.service.language, "dockerfile")
        self.assertEqual(self.service.dockerfile, "Dockerfile")
        self.assertEqual(self.service.create_status, "checked")
        self.assertEqual(self.service.build_strategy, "")
        create_region.assert_called_once()

    def test_followup_check_applies_preference_to_same_multi_module_result(self):
        arguments = {"team_name": "fixture-team", "region_name": "region", "app_id": 1,
                     "service_id": self.service.service_id, "prefer_dockerfile_when_detected": True}
        with mock.patch.object(mcp_query_service, "_get_team_app_service_context",
                               return_value=(self.team, self.app, self.service)), \
                mock.patch("console.services.mcp_query_service.app_check_service.get_service_check_info",
                           return_value=(200, "success", copy.deepcopy(self.result))):
            result = mcp_query_service.get_component_check_result(self.user, arguments)
        self.assertTrue(result["can_build"])
        self.assertTrue(result["dockerfile_preference_applied"])
        self.assertFalse(result["check_result"]["is_multi"])
        self.service.refresh_from_db()
        self.assertEqual((self.service.language, self.service.dockerfile, self.service.create_status),
                         ("dockerfile", "Dockerfile", "checked"))

    def test_multi_module_without_explicit_preference_is_still_rejected(self):
        with self.assertRaises(ServiceHandleException) as error:
            self.create(prefer=False)
        self.assertEqual(error.exception.msg, "multiple services detected")

    def test_non_maven_multiple_services_are_not_collapsed(self):
        self.result["service_info"][1]["language"] = "Python"
        with self.assertRaises(ServiceHandleException) as error:
            self.create()
        self.assertEqual(error.exception.msg, "multiple services detected")

    def test_only_nested_dockerfiles_do_not_override_multi_module_selection(self):
        for item in self.result["service_info"]:
            item["dockerfiles"] = ["backend/Dockerfile"]
        with self.assertRaises(ServiceHandleException) as error:
            self.create()
        self.assertEqual(error.exception.msg, "multiple services detected")

    def test_root_selection_does_not_mutate_detection_or_use_module_identity(self):
        before = copy.deepcopy(self.result["service_info"])
        selected = source_component_service.select_check_services(self.result["service_info"], True)
        self.assertEqual(self.result["service_info"], before)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["language"], "dockerfile")
        self.assertTrue(all(key not in selected[0] for key in ("id", "name", "cname", "packaging")))

    def test_nonuniform_module_dockerfiles_do_not_select_a_repository_root(self):
        self.result["service_info"][1]["dockerfiles"] = []
        with self.assertRaises(ServiceHandleException):
            self.create()

    def test_single_service_selection_keeps_existing_preference_behavior(self):
        self.result["service_info"] = self.result["service_info"][:1]
        result, _ = self.create()
        self.assertTrue(result["dockerfile_preference_applied"])
        self.service.refresh_from_db()
        self.assertEqual(self.service.language, "dockerfile")

    def test_followup_check_can_resume_a_persisted_multi_module_preference(self):
        arguments = {"team_name": "fixture-team", "region_name": "region", "app_id": self.app.ID,
                     "service_id": self.service.service_id}
        with mock.patch.object(mcp_query_service, "_get_team_app_service_context",
                               return_value=(self.team, self.app, self.service)), \
                mock.patch.object(source_component_service, "load_dockerfile_preference", return_value=True), \
                mock.patch("console.services.mcp_query_service.app_check_service.get_service_check_info",
                           return_value=(200, "success", copy.deepcopy(self.result))):
            result = mcp_query_service.get_component_check_result(self.user, arguments)
        self.assertTrue(result["can_build"])
        self.assertTrue(result["dockerfile_preference_applied"])

    def test_failed_detection_does_not_collapse_modules_or_mark_preference_applied(self):
        self.result["check_status"] = "failure"
        arguments = {"team_name": "fixture-team", "region_name": "region", "app_id": self.app.ID,
                     "service_id": self.service.service_id, "prefer_dockerfile_when_detected": True}
        with mock.patch.object(mcp_query_service, "_get_team_app_service_context",
                               return_value=(self.team, self.app, self.service)), \
                mock.patch("console.services.mcp_query_service.app_check_service.get_service_check_info",
                           return_value=(200, "success", copy.deepcopy(self.result))):
            result = mcp_query_service.get_component_check_result(self.user, arguments)
        self.assertFalse(result["can_build"])
        self.assertTrue(result["check_result"]["is_multi"])
        self.assertIsNone(result["dockerfile_preference_applied"])
        self.service.refresh_from_db()
        self.assertEqual(self.service.language, "Java-maven")

    def test_complete_component_query_preserves_existing_maven_selection(self):
        self.service.create_status = "complete"
        self.service.save()
        arguments = {"team_name": "fixture-team", "region_name": "region", "app_id": self.app.ID,
                     "service_id": self.service.service_id, "prefer_dockerfile_when_detected": True}
        with mock.patch.object(mcp_query_service, "_get_team_app_service_context",
                               return_value=(self.team, self.app, self.service)), \
                mock.patch("console.services.mcp_query_service.app_check_service.get_service_check_info",
                           return_value=(200, "success", copy.deepcopy(self.result))):
            result = mcp_query_service.get_component_check_result(self.user, arguments)
        self.assertTrue(result["check_result"]["is_multi"])
        self.service.refresh_from_db()
        self.assertEqual(self.service.language, "Java-maven")

    def test_followup_without_check_id_is_rejected_before_downstream(self):
        self.service.check_uuid = ""
        arguments = {"team_name": "fixture-team", "region_name": "region", "app_id": self.app.ID,
                     "service_id": self.service.service_id, "prefer_dockerfile_when_detected": True}
        with mock.patch.object(mcp_query_service, "_get_team_app_service_context",
                               return_value=(self.team, self.app, self.service)), \
                mock.patch("console.services.mcp_query_service.app_check_service.get_service_check_info") as get_result:
            with self.assertRaises(ServiceHandleException) as error:
                mcp_query_service.get_component_check_result(self.user, arguments)
        self.assertEqual(error.exception.status_code, 400)
        get_result.assert_not_called()

    # capability_id: console.mcp.runtime-tool-name-snapshot
    def test_contract_snapshot_matches_full_runtime_tools_and_expected_filtering(self):
        root = Path(__file__).resolve().parents[2]
        snapshot = {tool["name"] for tool in json.loads((root / "contracts/mcp-tools.json").read_text())["tools"]}
        admin = SimpleNamespace(is_enterprise_admin=True)
        full = {tool["name"] for tool in mcp_query_service.list_tools(admin)}
        self.assertEqual(snapshot, full)
        self.assertEqual(set(collect_tools()), full)
        with deployment_invocation_context("rainskills", "codex"):
            filtered = {tool["name"] for tool in mcp_query_service.list_tools(admin)}
        self.assertEqual(full - filtered, set(mcp_query_service.RAINSKILLS_HIDDEN_TOOL_NAMES))
        for name in ("rainbond_create_component_from_source", "rainbond_get_component_check_result"):
            tool = next(item for item in mcp_query_service.list_tools(admin) if item["name"] == name)
            self.assertEqual(tool["inputSchema"]["properties"]["prefer_dockerfile_when_detected"]["type"], "boolean")

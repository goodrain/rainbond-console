# -*- coding: utf-8 -*-
# capability_id: console.build-source.preserve-source-type
import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import TestCase
from unittest.mock import Mock


SOURCE_PATH = Path(__file__).resolve().parents[1] / "views" / "app_overview.py"
MISSING = object()


class BuildSourceUpdateTests(TestCase):
    """Execute the production update method without unrelated Django initialization."""

    def update_source(self, requested=MISSING, existing="", is_oauth=False, code_version="webfront",
                      service_source="source_code", git_oauth=True):
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        view_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BuildSourceinfo")
        method = next(node for node in view_class.body if isinstance(node, ast.FunctionDef) and node.name == "put")
        method.decorator_list = []

        class Response:
            def __init__(self, data, status):
                self.data = data
                self.status_code = status

        service = SimpleNamespace(
            tenant_id="team-1", service_id="component-1", service_alias="component-alias",
            service_cname="Frontend", service_region="region-1", server_type=existing,
            code_version="old-branch", code_from="oauth_gitlab", service_source="source_code",
            image="", cmd="", arch="arm64", language="NodeJSStatic",
        )
        saved = []
        service.save = Mock(side_effect=lambda: saved.append((service.server_type, service.code_version)))
        source_repo = Mock()
        source_repo.get_service_source.return_value = SimpleNamespace(save=Mock())
        oauth_instance = Mock()
        oauth_instance.is_git_oauth.return_value = git_oauth
        oauth_repo = Mock()
        oauth_repo.get_oauth_services_by_service_id.return_value = SimpleNamespace(oauth_type="gitlab")
        scope = {
            "Any": Any,
            "Request": object,
            "Response": Response,
            "service_source_repo": source_repo,
            "oauth_repo": oauth_repo,
            "oauth_user_repo": Mock(),
            "get_oauth_instance": Mock(return_value=oauth_instance),
            "operation_log_service": Mock(),
            "Operation": SimpleNamespace(CHANGE="change"),
            "arch_service": Mock(),
            "transaction": Mock(),
            "logger": Mock(),
            "general_message": lambda code, msg, msg_show: {"code": code, "msg": msg, "msg_show": msg_show},
            "error_message": lambda: {"code": 500},
        }
        module = ast.Module(body=[method], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(SOURCE_PATH), "exec"), scope)
        view = SimpleNamespace(
            service=service,
            tenant=SimpleNamespace(tenant_name="team-name"),
            user=SimpleNamespace(enterprise_id="enterprise-1"),
            app=SimpleNamespace(ID=1),
            region_name="region-1",
        )
        data = {
            "service_source": service_source,
            "git_url": "https://example.com/team/project.git?dir=frontend",
            "code_version": code_version,
            "is_oauth": is_oauth,
            "service_id": "oauth-1",
            "full_name": "team/project",
            "arch": "arm64",
            "image": "example.com/demo:1",
        }
        if requested is not MISSING:
            data["server_type"] = requested
        request = SimpleNamespace(data=data, user=SimpleNamespace(user_id=7))
        response = scope["put"](view, request)
        return SimpleNamespace(response=response, service=service, saved=saved, scope=scope, view=view,
                               oauth_instance=oauth_instance)

    def assert_saved_type(self, result, expected_type, expected_version="webfront"):
        self.assertEqual(result.response.status_code, 200)
        self.assertEqual(result.response.data["code"], 200)
        self.assertTrue(result.saved)
        self.assertEqual(result.saved, [(expected_type, expected_version)] * len(result.saved))
        result.scope["transaction"].set_rollback.assert_not_called()
        result.scope["logger"].exception.assert_not_called()

    def test_oauth_updates_always_persist_git(self):
        for requested in (MISSING, "", None, " \t\n ", "svn"):
            for existing in ("git", "", "svn", None, " \t "):
                with self.subTest(requested=requested, existing=existing):
                    result = self.update_source(requested=requested, existing=existing, is_oauth=True)
                    self.assert_saved_type(result, "git")
                    result.oauth_instance.is_git_oauth.assert_called_once_with()

    def test_ordinary_updates_retain_existing_svn_or_oss_when_type_is_blank(self):
        for requested in (MISSING, "", None, " \t\n "):
            for existing in ("svn", "oss", " svn ", "\toss\n"):
                with self.subTest(requested=requested, existing=existing):
                    result = self.update_source(requested=requested, existing=existing)
                    self.assert_saved_type(result, existing.strip())
                    result.scope["get_oauth_instance"].assert_not_called()

    def test_ordinary_updates_recover_legacy_blank_types_as_git(self):
        for existing in ("", None, " \t\n "):
            for requested in (MISSING, "", None, " \t "):
                with self.subTest(existing=existing, requested=requested):
                    self.assert_saved_type(self.update_source(requested=requested, existing=existing), "git")

    def test_explicit_ordinary_source_type_switches_are_preserved(self):
        for requested, existing, expected in (("git", "svn", "git"), ("svn", "git", "svn"),
                                              ("oss", "git", "oss"), (" \tsvn\n", "git", "svn")):
            with self.subTest(requested=requested, existing=existing):
                self.assert_saved_type(self.update_source(requested=requested, existing=existing), expected)

    def test_oss_without_code_version_keeps_the_empty_version_default(self):
        for requested, existing in ((MISSING, "oss"), (None, "oss"), ("", "oss"), (" \t ", "oss"),
                                    ("oss", "git")):
            with self.subTest(requested=requested, existing=existing):
                result = self.update_source(requested=requested, existing=existing, code_version=None)
                self.assert_saved_type(result, "oss", expected_version="")

    def test_oauth_without_code_version_uses_git_master_default(self):
        result = self.update_source(existing="oss", is_oauth=True, code_version=None)
        self.assert_saved_type(result, "git", expected_version="master")

    def test_non_git_oauth_is_still_rejected_before_component_save(self):
        result = self.update_source(existing="svn", is_oauth=True, git_oauth=False)
        self.assertEqual(result.response.data["status"], 400)
        result.oauth_instance.is_git_oauth.assert_called_once_with()
        result.service.save.assert_not_called()
        self.assertEqual(result.service.server_type, "svn")

    def test_image_source_updates_do_not_apply_git_type_resolution(self):
        result = self.update_source(requested=" \t ", existing="svn", is_oauth=True, service_source="docker_run")
        self.assertEqual(result.response.data["code"], 200)
        self.assertEqual(result.service.service_source, "docker_image")
        self.assertEqual(result.service.server_type, "svn")
        self.assertEqual(result.view.server_type, " \t ")
        result.scope["get_oauth_instance"].assert_not_called()

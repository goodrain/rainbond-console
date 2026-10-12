# coding: utf-8
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views import helm_app as helm_app_module  # noqa: E402


class HelmRepoViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = helm_app_module.HelmRepo()

    # capability_id: console.helm-repo.input-length
    def test_post_rejects_repo_url_longer_than_model_limit(self):
        request = self.view.initialize_request(
            self.factory.post(
                "/console/helm/repos",
                {"repo_name": "demo", "repo_url": "x" * 129},
                format="json",
            )
        )

        with mock.patch.object(helm_app_module.helm_repo, "get_helm_repo_by_name", return_value=None), mock.patch.object(
                helm_app_module.helm_app_service,
                "add_helm_repo",
        ) as add_repo:
            response = self.view.post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "仓库地址长度不能超过128个字符")
        add_repo.assert_not_called()

    # capability_id: console.helm-repo.input-length
    def test_put_rejects_repo_url_longer_than_model_limit(self):
        request = self.view.initialize_request(
            self.factory.put(
                "/console/helm/repos",
                {"repo_name": "demo", "repo_url": "x" * 129},
                format="json",
            )
        )

        with mock.patch.object(helm_app_module.helm_repo, "update_helm_repo") as update_repo:
            response = self.view.put(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["msg_show"], "仓库地址长度不能超过128个字符")
        update_repo.assert_not_called()

    # capability_id: console.helm-repo.input-length
    def test_post_accepts_repo_url_at_model_limit(self):
        repo_url = "x" * 128
        request = self.view.initialize_request(
            self.factory.post(
                "/console/helm/repos",
                {"repo_name": "demo", "repo_url": repo_url},
                format="json",
            )
        )

        with mock.patch.object(helm_app_module.helm_repo, "get_helm_repo_by_name", return_value=None), mock.patch.object(
                helm_app_module.helm_app_service,
                "add_helm_repo",
        ) as add_repo:
            response = self.view.post(request)

        self.assertEqual(response.status_code, 200)
        add_repo.assert_called_once_with("demo", repo_url, "", "")

    # capability_id: console.helm-repo.input-length
    def test_post_rejects_missing_or_overlong_repo_identity(self):
        invalid_payloads = [
            ({"repo_url": "https://charts.example.com"}, "仓库名称不能为空"),
            ({"repo_name": "x" * 65, "repo_url": "https://charts.example.com"}, "仓库名称长度不能超过64个字符"),
            ({"repo_name": "demo", "repo_url": ""}, "仓库地址不能为空"),
        ]

        for payload, message in invalid_payloads:
            with self.subTest(message=message):
                request = self.view.initialize_request(
                    self.factory.post("/console/helm/repos", payload, format="json")
                )
                with mock.patch.object(helm_app_module.helm_app_service, "add_helm_repo") as add_repo:
                    response = self.view.post(request)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["msg_show"], message)
                add_repo.assert_not_called()

# coding: utf-8
from unittest import TestCase, mock

from console.utils.oauth.gitlab_api import GitlabApiV4


class GitlabApiV4WebhookTests(TestCase):
    def setUp(self):
        self.client = GitlabApiV4()
        self.client._get_access_token = mock.Mock(return_value=("token", None))
        self.repo = mock.Mock()
        self.client.api = mock.Mock()
        self.client.api.projects.list.return_value = [self.repo]

    # capability_id: console.oauth.gitlab-webhook-url
    def test_create_hook_adds_https_scheme_to_bare_host(self):
        self.client.create_hook("console.example.com", "team/project", endpoint="console/webhooks/service-id")

        self.repo.hooks.create.assert_called_once_with({
            "url": "https://console.example.com/console/webhooks/service-id",
            "push_events": 1,
        })

    # capability_id: console.oauth.gitlab-webhook-url
    def test_create_hook_supports_protocol_relative_host(self):
        self.client.create_hook("//console.example.com", "team/project")

        self.repo.hooks.create.assert_called_once_with({
            "url": "https://console.example.com/console/webhooks",
            "push_events": 1,
        })

    # capability_id: console.oauth.gitlab-webhook-url
    def test_create_hook_preserves_scheme_and_normalizes_slashes(self):
        self.client.create_hook("http://console.example.com/", "team/project", endpoint="/console/webhooks/service-id")

        self.repo.hooks.create.assert_called_once_with({
            "url": "http://console.example.com/console/webhooks/service-id",
            "push_events": 1,
        })

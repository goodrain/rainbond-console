# -*- coding: utf-8 -*-
"""Exercise OAuth binding replacement with real ORM persistence."""
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402
from console.models.main import OAuthServices, UserOAuthServices  # noqa: E402
from console.repositories.oauth_repo import oauth_user_repo  # noqa: E402
from console.views.oauth import OAuthServerUserAuthorize  # noqa: E402


# capability_id: console.oauth.reauthorization
class OAuthReauthorizationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        existing_tables = connection.introspection.table_names()
        cls.created_models = []
        with connection.schema_editor() as schema:
            for model in (OAuthServices, UserOAuthServices):
                if model._meta.db_table not in existing_tables:
                    schema.create_model(model)
                    cls.created_models.append(model)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as schema:
            for model in reversed(cls.created_models):
                schema.delete_model(model)
        super().tearDownClass()

    def setUp(self):
        self.service = OAuthServices.objects.create(
            name="gitlab-test", client_id="", client_secret="", redirect_uri="",
            oauth_type="gitlab", eid="enterprise-a", system=True)
        self.user = SimpleNamespace(user_id=11, enterprise_id="enterprise-a")
        self.api = mock.Mock()
        self.api.is_git_oauth.return_value = True
        self.api.get_user_info.return_value = (
            SimpleNamespace(id="new-account", name="New User", email="new@example.invalid"),
            "$OAUTH_ACCESS_TOKEN", "$OAUTH_REFRESH_TOKEN")

    def tearDown(self):
        UserOAuthServices.objects.filter(service_id=self.service.pk).delete()
        self.service.delete()

    def binding(self, account="old-account", user_id=11, **kwargs):
        return UserOAuthServices.objects.create(
            service_id=self.service.pk, oauth_user_id=account, user_id=user_id,
            oauth_user_name="Old User", **kwargs)

    def authorize(self, **data):
        body = {"code": "$OAUTH_CODE", "service_id": str(self.service.pk)}
        body.update(data)
        request = SimpleNamespace(user=self.user, data=body)
        with mock.patch("console.views.oauth.get_oauth_instance", return_value=self.api):
            return OAuthServerUserAuthorize().post(request)

    def test_same_account_refreshes_existing_binding(self):
        binding = self.binding("new-account", is_authenticated=False, is_expired=True)
        response = self.authorize()
        binding.refresh_from_db()
        self.assertEqual(response.data["status"], 200)
        self.assertEqual(binding.oauth_user_name, "New User")
        self.assertEqual(binding.access_token, "$OAUTH_ACCESS_TOKEN")
        self.assertEqual(binding.refresh_token, "$OAUTH_REFRESH_TOKEN")
        self.assertEqual(binding.code, "$OAUTH_CODE")
        self.assertTrue(binding.is_authenticated)
        self.assertFalse(binding.is_expired)
        self.assertEqual(UserOAuthServices.objects.count(), 1)

    def test_switch_account_replaces_current_binding(self):
        binding = self.binding()
        response = self.authorize()
        binding.refresh_from_db()
        self.assertEqual(response.data["status"], 200)
        self.assertEqual(binding.oauth_user_id, "new-account")
        self.assertEqual(binding.user_id, self.user.user_id)
        self.assertEqual(UserOAuthServices.objects.count(), 1)

    def test_other_users_account_is_rejected_without_changes(self):
        original = self.binding()
        target = self.binding("new-account", user_id=22)
        response = self.authorize()
        original.refresh_from_db()
        target.refresh_from_db()
        self.assertEqual(response.data["status"], 400)
        self.assertEqual(original.oauth_user_id, "old-account")
        self.assertEqual(target.user_id, 22)

    def test_first_binding_cannot_claim_another_users_account(self):
        target = self.binding("new-account", user_id=22)
        response = self.authorize()
        target.refresh_from_db()
        self.assertEqual(response.data["status"], 400)
        self.assertEqual(target.user_id, 22)
        self.assertFalse(UserOAuthServices.objects.filter(user_id=self.user.user_id).exists())

    def test_unbound_target_merges_into_current_binding(self):
        original = self.binding()
        self.binding("new-account", user_id=None)
        response = self.authorize()
        original.refresh_from_db()
        self.assertEqual(response.data["status"], 200)
        self.assertEqual(original.oauth_user_id, "new-account")
        self.assertEqual(UserOAuthServices.objects.count(), 1)

    def test_first_authorization_claims_unbound_target(self):
        target = self.binding("new-account", user_id=None, is_expired=True)
        response = self.authorize()
        target.refresh_from_db()
        self.assertEqual(response.data["status"], 200)
        self.assertEqual(target.user_id, self.user.user_id)
        self.assertFalse(target.is_expired)

    def test_first_authorization_creates_binding(self):
        response = self.authorize()
        self.assertEqual(response.data["status"], 200)
        binding = UserOAuthServices.objects.get(user_id=11)
        self.assertEqual(binding.oauth_user_id, "new-account")

    def test_own_private_service_can_be_reauthorized(self):
        self.service.system = False
        self.service.user_id = self.user.user_id
        self.service.save()
        self.assertEqual(self.authorize().data["status"], 200)

    def test_provider_failure_preserves_original_binding(self):
        original = self.binding()
        self.api.get_user_info.side_effect = RuntimeError("provider unavailable")
        response = self.authorize()
        original.refresh_from_db()
        self.assertGreaterEqual(response.data["status"], 400)
        self.assertEqual(original.oauth_user_id, "old-account")
        self.assertEqual(UserOAuthServices.objects.count(), 1)

    def test_gitea_pkce_state_is_passed_to_provider(self):
        self.service.oauth_type = "gitea"
        self.service.save()
        response = self.authorize(state='{"code_verifier": "$OAUTH_CODE_VERIFIER"}')
        self.assertEqual(response.data["status"], 200)
        self.api.get_user_info.assert_called_once_with(code="$OAUTH_CODE", code_verifier="$OAUTH_CODE_VERIFIER")

    def test_non_git_account_switch_remains_rejected(self):
        original = self.binding()
        self.api.is_git_oauth.return_value = False
        response = self.authorize()
        original.refresh_from_db()
        self.assertEqual(response.data["status"], 400)
        self.assertEqual(original.oauth_user_id, "old-account")

    def test_private_service_of_another_user_is_rejected(self):
        self.service.system = False
        self.service.user_id = 22
        self.service.save()
        response = self.authorize()
        self.assertEqual(response.data["status"], 403)
        self.api.get_user_info.assert_not_called()
        self.assertEqual(UserOAuthServices.objects.count(), 0)

    def test_service_of_another_enterprise_is_rejected(self):
        self.service.eid = "enterprise-b"
        self.service.save()
        response = self.authorize()
        self.assertEqual(response.data["status"], 403)
        self.api.get_user_info.assert_not_called()

    def test_failed_save_rolls_back_removal_of_unbound_target(self):
        original = self.binding()
        target = self.binding("new-account", user_id=None)
        with mock.patch.object(UserOAuthServices, "save", side_effect=RuntimeError("save failed")):
            with self.assertRaises(RuntimeError):
                oauth_user_repo.reauthorize_git_user(
                    self.service.pk, self.user.user_id, "new-account", "New User", "new@example.invalid", "", "", "")
        original.refresh_from_db()
        self.assertEqual(original.oauth_user_id, "old-account")
        self.assertTrue(UserOAuthServices.objects.filter(pk=target.pk).exists())

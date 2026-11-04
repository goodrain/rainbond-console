# -*- coding: utf-8 -*-
"""GitLab first-login provisioning against real ORM persistence."""
import os
import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402
from console.exception.main import ServiceHandleException  # noqa: E402
from console.models.main import EnterpriseUserPerm, OAuthServices, UserOAuthServices  # noqa: E402
from console.repositories.oauth_repo import oauth_repo  # noqa: E402
from console.services.oauth_service import oauth_sev_user_service  # noqa: E402
from console.views.oauth import EnterpriseOauthService, OAuthServerAuthorize  # noqa: E402
from www.models.main import TenantEnterprise, Users  # noqa: E402


# capability_id: console.oauth.gitlab-auto-provisioning
class GitlabAutoProvisioningTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.models = (TenantEnterprise, Users, EnterpriseUserPerm, OAuthServices, UserOAuthServices)
        cls.created_models = []
        tables = connection.introspection.table_names()
        with connection.schema_editor() as schema:
            for model in cls.models:
                if model._meta.db_table not in tables:
                    schema.create_model(model)
                    cls.created_models.append(model)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as schema:
            for model in reversed(cls.created_models):
                schema.delete_model(model)
        super().tearDownClass()

    def setUp(self):
        self.addCleanup(self.clean_rows)
        self.enterprise = TenantEnterprise.objects.create(enterprise_id="provision-test", enterprise_name="Provision test")
        self.admin = Users.objects.create(
            nick_name="provision-admin", email="admin@example.invalid", enterprise_id=self.enterprise.enterprise_id,
            is_active=True, sys_admin=True, password="!unusable")
        self.service = OAuthServices.objects.create(
            name="provision-gitlab", client_id="", client_secret="", redirect_uri="https://console.example.invalid/callback",
            home_url="https://gitlab.example.invalid", oauth_type="gitlab", eid=self.enterprise.enterprise_id,
            system=True, is_console=True, user_id=self.admin.user_id, auto_create_user=True)
        self.identity = SimpleNamespace(id="123", name="Domain User", email="domain@example.invalid")
        self.api = mock.Mock()
        self.api.is_communication_oauth.return_value = False
        self.jwt_manager = mock.patch("console.services.oauth_service.JwtManager").start()
        self.addCleanup(mock.patch.stopall)

    def clean_rows(self):
        services = OAuthServices.objects.filter(name__startswith="provision-").values_list("pk", flat=True)
        UserOAuthServices.objects.filter(service_id__in=list(services)).delete()
        OAuthServices.objects.filter(name__startswith="provision-").delete()
        EnterpriseUserPerm.objects.filter(enterprise_id__in=("provision-test", "provision-other")).delete()
        Users.objects.filter(enterprise_id__in=("provision-test", "provision-other")).delete()
        TenantEnterprise.objects.filter(enterprise_id__in=("provision-test", "provision-other")).delete()

    def authorize(self):
        return oauth_sev_user_service.set_oauth_user_relation(
            self.api, self.service, self.identity, "$OAUTH_ACCESS_TOKEN", "$OAUTH_REFRESH_TOKEN", "$OAUTH_CODE")

    def binding(self, user=None, **fields):
        return UserOAuthServices.objects.create(
            service_id=self.service.pk, oauth_user_id=self.identity.id, user_id=user.pk if user else None, **fields)

    def config(self, **overrides):
        values = {
            "service_id": self.service.pk, "name": self.service.name, "client_id": "", "client_secret": "",
            "eid": self.enterprise.enterprise_id, "redirect_uri": self.service.redirect_uri, "oauth_type": "gitlab",
            "home_url": self.service.home_url, "enable": True, "is_auto_login": False, "is_console": True,
            "system": True, "auto_create_user": True,
        }
        values.update(overrides)
        return values

    def save_config(self, values, actor=None):
        return oauth_repo.create_or_update_oauth_services(
            [values], self.enterprise.enterprise_id, (actor or self.admin).pk)

    def test_first_login_creates_plain_user_and_binding_and_returns_token(self):
        response = self.authorize()
        self.assertTrue(response.data["data"]["bean"]["token"])
        binding = UserOAuthServices.objects.get(service_id=self.service.pk)
        user = Users.objects.get(pk=binding.user_id)
        self.assertEqual(user.enterprise_id, self.enterprise.enterprise_id)
        self.assertEqual(user.real_name, self.identity.name)
        self.assertEqual(user.email, self.identity.email)
        self.assertTrue(user.is_active)
        self.assertFalse(user.sys_admin)
        self.assertTrue(user.password.startswith("!"))
        self.assertFalse(user.check_password(self.identity.name))
        self.assertFalse(EnterpriseUserPerm.objects.filter(user_id=user.pk).exists())
        self.jwt_manager.return_value.set.assert_called_once()

    def test_repeated_login_reuses_identity_even_when_display_name_and_email_change(self):
        self.authorize()
        original_id = UserOAuthServices.objects.get(service_id=self.service.pk).user_id
        self.identity.name = "Renamed user"
        self.identity.email = "renamed@example.invalid"
        self.authorize()
        self.assertEqual(Users.objects.filter(enterprise_id=self.enterprise.enterprise_id).count(), 2)
        binding = UserOAuthServices.objects.get(service_id=self.service.pk)
        self.assertEqual(binding.user_id, original_id)
        self.assertEqual(binding.oauth_user_name, "Renamed user")

    def test_login_response_leaves_cookie_to_existing_frontend_callback(self):
        response = self.authorize()
        # SecurityLayout reads the JS-managed token cookie. A server HttpOnly cookie shadows it.
        self.assertFalse("token" in response.cookies, "The frontend must own the login cookie")

    def test_historical_unbound_identity_is_completed_in_place(self):
        binding = self.binding(is_authenticated=True)
        self.authorize()
        binding.refresh_from_db()
        self.assertIsNotNone(binding.user_id)
        self.assertEqual(UserOAuthServices.objects.filter(service_id=self.service.pk).count(), 1)

    def test_existing_bound_account_is_reused(self):
        self.binding(self.admin)
        self.authorize()
        self.assertEqual(Users.objects.filter(enterprise_id=self.enterprise.enterprise_id).count(), 1)
        self.assertEqual(UserOAuthServices.objects.get(service_id=self.service.pk).user_id, self.admin.pk)

    def test_long_external_identity_creates_bounded_username_and_reuses_binding(self):
        self.identity.id = "12345678901234567890"
        self.authorize()
        binding = UserOAuthServices.objects.get(service_id=self.service.pk, oauth_user_id=self.identity.id)
        user = Users.objects.get(pk=binding.user_id)
        self.assertLessEqual(len(user.nick_name), 24)
        self.assertTrue(user.nick_name.startswith("gitlab-"))
        self.authorize()
        binding.refresh_from_db()
        self.assertEqual(binding.user_id, user.pk)

    def test_existing_bound_numeric_account_retains_its_identity(self):
        self.admin.nick_name = "00123"
        self.admin.save(update_fields=["nick_name"])
        self.binding(self.admin)
        self.authorize()
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.nick_name, "00123")
        self.assertEqual(UserOAuthServices.objects.get(service_id=self.service.pk).user_id, self.admin.pk)

    def test_missing_or_duplicate_identity_is_rejected_without_creating_users(self):
        self.identity.id = None
        with self.assertRaises(ServiceHandleException):
            self.authorize()
        self.identity.id = "123"
        self.binding(self.admin)
        self.binding()
        with self.assertRaises(ServiceHandleException):
            self.authorize()
        self.assertEqual(Users.objects.filter(enterprise_id=self.enterprise.enterprise_id).count(), 1)

    def test_matching_email_requires_explicit_binding_instead_of_taking_over_user(self):
        self.identity.email = self.admin.email.upper()
        with self.assertRaises(ServiceHandleException) as error:
            self.authorize()
        self.assertEqual(error.exception.status_code, 409)
        self.assertFalse(UserOAuthServices.objects.filter(service_id=self.service.pk).exists())

    def test_disabled_bound_user_is_denied_without_session(self):
        self.admin.is_active = False
        self.admin.save()
        self.binding(self.admin)
        with self.assertRaises(ServiceHandleException):
            self.authorize()
        self.jwt_manager.return_value.set.assert_not_called()

    def test_deleted_bound_user_is_not_recreated(self):
        binding = self.binding(self.admin)
        self.admin.delete()
        with self.assertRaises(ServiceHandleException):
            self.authorize()
        binding.refresh_from_db()
        self.assertIsNotNone(binding.user_id)
        self.assertFalse(Users.objects.filter(email=self.identity.email).exists())

    def test_binding_to_another_enterprise_is_denied(self):
        self.admin.enterprise_id = "provision-other"
        self.admin.save()
        self.binding(self.admin)
        with self.assertRaises(ServiceHandleException):
            self.authorize()
        self.jwt_manager.return_value.set.assert_not_called()

    def test_deleted_or_disabled_or_private_service_is_denied_even_with_stale_callback(self):
        for field, value in (("is_deleted", True), ("enable", False), ("system", False),
                             ("is_console", False), ("auto_create_user", False), ("oauth_type", "github")):
            with self.subTest(field=field):
                original = getattr(self.service, field)
                OAuthServices.objects.filter(pk=self.service.pk).update(**{field: value})
                with self.assertRaises(ServiceHandleException):
                    self.authorize()
                OAuthServices.objects.filter(pk=self.service.pk).update(**{field: original})
        self.assertFalse(Users.objects.filter(email=self.identity.email).exists())

    def test_missing_enterprise_or_empty_enterprise_cannot_bootstrap_admin(self):
        self.admin.delete()
        with self.assertRaises(ServiceHandleException):
            self.authorize()
        self.enterprise.delete()
        with self.assertRaises(ServiceHandleException):
            self.authorize()
        self.assertFalse(Users.objects.filter(email=self.identity.email).exists())

    def test_missing_or_invalid_email_cannot_create_user(self):
        for email in (None, "", "invalid", "x" * 130 + "@example.invalid"):
            with self.subTest(email=email):
                self.identity.email = email
                with self.assertRaises(ServiceHandleException):
                    self.authorize()
        self.assertFalse(UserOAuthServices.objects.filter(service_id=self.service.pk).exists())

    def test_binding_failure_rolls_back_created_user(self):
        with mock.patch.object(UserOAuthServices, "save", side_effect=RuntimeError("binding failed")):
            with self.assertRaises(RuntimeError):
                self.authorize()
        self.assertFalse(Users.objects.filter(email=self.identity.email).exists())

    def test_closed_public_registration_does_not_block_trusted_oauth(self):
        from rest_framework.test import APIRequestFactory
        from console.views.user_operation import TenantServiceView

        with mock.patch("console.views.user_operation.platform_config_service.get_config_by_key",
                        return_value=SimpleNamespace(enable=False)) as register_config:
            response = self.authorize()
            register_config.assert_not_called()
            view = TenantServiceView()
            request = view.initialize_request(APIRequestFactory().post("/console/users/register", {}, format="json"))
            self.assertEqual(view.post(request).status_code, 403)
        self.assertTrue(response.data["data"]["bean"]["token"])

    def test_opt_out_preserves_existing_manual_binding_flow(self):
        self.service.auto_create_user = False
        self.service.save()
        response = self.authorize()
        self.assertFalse("token" in response.data["data"]["bean"])
        self.assertIsNone(UserOAuthServices.objects.get(service_id=self.service.pk).user_id)
        self.assertFalse(Users.objects.filter(email=self.identity.email).exists())

    def test_config_round_trip_and_omitted_field_preserve_enabled_value(self):
        values = self.config()
        self.save_config(values)
        values.pop("auto_create_user")
        self.save_config(values)
        self.service.refresh_from_db()
        self.assertTrue(self.service.auto_create_user)
        view = EnterpriseOauthService()
        view.user = self.admin
        response = view.get(SimpleNamespace(GET={"system": "true"}), self.enterprise.enterprise_id)
        self.assertTrue(response.data["data"]["list"][0]["auto_create_user"])

    def test_invalid_batch_configuration_rolls_back_earlier_updates(self):
        with self.assertRaises(ServiceHandleException):
            oauth_repo.create_or_update_oauth_services(
                [self.config(auto_create_user=False),
                 self.config(service_id=None, name="provision-invalid-batch", auto_create_user="invalid")],
                self.enterprise.enterprise_id, self.admin.pk)
        self.service.refresh_from_db()
        self.assertTrue(self.service.auto_create_user)

    def test_new_configuration_defaults_to_disabled(self):
        values = self.config(service_id=None, name="provision-default")
        values.pop("auto_create_user")
        self.save_config(values)
        self.assertFalse(OAuthServices.objects.get(name="provision-default").auto_create_user)

    def test_only_boolean_flag_and_platform_gitlab_service_are_accepted(self):
        for changes in ({"auto_create_user": "true"}, {"oauth_type": "github"}, {"system": False},
                        {"is_console": False}, {"eid": "provision-other"}):
            with self.subTest(changes=changes):
                with self.assertRaises(ServiceHandleException):
                    self.save_config(self.config(service_id=None, name="provision-invalid", **changes))
        self.assertFalse(OAuthServices.objects.filter(name="provision-invalid").exists())

    def test_non_admin_cannot_enable_or_modify_enabled_configuration(self):
        actor = Users.objects.create(
            nick_name="plain-user", email="plain@example.invalid", enterprise_id=self.enterprise.enterprise_id,
            password="!unusable", is_active=True)
        for values in (self.config(), self.config(auto_create_user=False)):
            with self.assertRaises(ServiceHandleException) as error:
                self.save_config(values, actor)
            self.assertEqual(error.exception.status_code, 403)

    def test_non_admin_cannot_delete_enabled_configuration(self):
        with self.assertRaises(ServiceHandleException):
            oauth_repo.delete_oauth_service(self.service.pk)
        self.assertTrue(OAuthServices.objects.filter(pk=self.service.pk).exists())

    def test_configured_service_cannot_be_changed_through_another_enterprise(self):
        TenantEnterprise.objects.create(enterprise_id="provision-other", enterprise_name="Other")
        actor = Users.objects.create(
            nick_name="other-admin", email="other@example.invalid", enterprise_id="provision-other",
            is_active=True, sys_admin=True, password="!unusable")
        with self.assertRaises(ServiceHandleException):
            oauth_repo.create_or_update_oauth_services(
                [self.config(auto_create_user=False, eid="provision-other")], "provision-other", actor.pk)
        self.service.refresh_from_db()
        self.assertEqual(self.service.eid, self.enterprise.enterprise_id)
        self.assertTrue(self.service.auto_create_user)

    def test_enterprise_admin_can_disable_and_delete_service(self):
        self.admin.sys_admin = False
        self.admin.save()
        EnterpriseUserPerm.objects.create(
            enterprise_id=self.enterprise.enterprise_id, user_id=self.admin.pk, identity="admin")
        self.save_config(self.config(auto_create_user=False))
        self.service.refresh_from_db()
        self.assertFalse(self.service.auto_create_user)
        self.save_config(self.config(auto_create_user=True))
        oauth_repo.delete_oauth_service(self.service.pk, self.enterprise.enterprise_id, self.admin.pk)
        self.assertFalse(OAuthServices.objects.filter(pk=self.service.pk).exists())

    def test_legacy_console_config_path_saves_and_preserves_flag(self):
        values = self.config()
        oauth_repo.create_or_update_console_oauth_services(
            [values], self.enterprise.enterprise_id, self.admin.pk, True)
        values.pop("auto_create_user")
        oauth_repo.create_or_update_console_oauth_services(
            [values], self.enterprise.enterprise_id, self.admin.pk, True)
        self.service.refresh_from_db()
        self.assertTrue(self.service.auto_create_user)

    def test_same_display_name_does_not_merge_different_gitlab_identities(self):
        self.authorize()
        self.identity.id = "124"
        self.identity.email = "different@example.invalid"
        self.authorize()
        bindings = UserOAuthServices.objects.filter(service_id=self.service.pk)
        self.assertEqual(bindings.count(), 2)
        self.assertEqual(len(set(bindings.values_list("user_id", flat=True))), 2)

    def test_reserved_username_conflict_is_not_linked(self):
        self.admin.nick_name = "gitlab-{}-{}".format(self.service.pk, self.identity.id)
        self.admin.save()
        with self.assertRaises(ServiceHandleException):
            self.authorize()
        self.assertFalse(UserOAuthServices.objects.filter(service_id=self.service.pk).exists())

    def test_concurrent_first_logins_do_not_duplicate_users_and_can_be_retried(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import OperationalError, connections
        from console.services.oauth_user_provisioning import provision_gitlab_user

        barrier = Barrier(3)

        def login():
            try:
                barrier.wait(timeout=5)
                return provision_gitlab_user(
                    self.service.pk, self.identity, "$OAUTH_ACCESS_TOKEN", "$OAUTH_REFRESH_TOKEN", "$OAUTH_CODE").pk
            except OperationalError as error:
                # SQLite has no row locks; a conflicting transaction must roll back and retry.
                if connection.vendor != "sqlite" or "locked" not in str(error):
                    raise
                return None
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=3) as pool:
            ids = list(pool.map(lambda _: login(), range(3)))
        for index, user_id in enumerate(ids):
            if user_id is None:
                ids[index] = provision_gitlab_user(
                    self.service.pk, self.identity, "$OAUTH_ACCESS_TOKEN", "$OAUTH_REFRESH_TOKEN", "$OAUTH_CODE").pk
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual(Users.objects.filter(email=self.identity.email).count(), 1)
        self.assertEqual(UserOAuthServices.objects.filter(service_id=self.service.pk).count(), 1)

    def test_callback_authenticates_with_gitlab_before_creating_account(self):
        self.api.get_user_info.return_value = (self.identity, "$OAUTH_ACCESS_TOKEN", "$OAUTH_REFRESH_TOKEN")
        request = SimpleNamespace(GET={"code": "$OAUTH_CODE", "service_id": str(self.service.pk)})
        with mock.patch("console.views.oauth.get_oauth_instance", return_value=self.api):
            response = OAuthServerAuthorize().get(request)
        self.assertTrue(response.data["data"]["bean"]["token"])
        self.api.get_user_info.assert_called_once_with(code="$OAUTH_CODE")

    def test_failed_gitlab_authentication_does_not_create_account(self):
        self.api.get_user_info.side_effect = RuntimeError("GitLab authentication failed")
        request = SimpleNamespace(GET={"code": "$OAUTH_CODE", "service_id": str(self.service.pk)})
        with mock.patch("console.views.oauth.get_oauth_instance", return_value=self.api):
            response = OAuthServerAuthorize().get(request)
        self.assertFalse(bool((response.data["data"].get("bean") or {}).get("token")))
        self.assertFalse(UserOAuthServices.objects.filter(service_id=self.service.pk).exists())


# capability_id: console.oauth.gitlab-auto-provisioning
class GitlabAutoProvisioningMigrationTests(TestCase):
    @contextmanager
    def startup_database(self, with_column=False):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.db import connections
        from django.db.migrations.state import ModelState, ProjectState

        after = ProjectState()
        after.add_model(ModelState.from_model(OAuthServices))
        before = after.clone()
        before.remove_field("console", "oauthservices", "auto_create_user")
        alias = "oauth_startup_migration"
        with TemporaryDirectory(prefix="oauth-startup-") as directory:
            connections.databases[alias] = dict(connection.settings_dict, NAME=str(Path(directory) / "migration.sqlite3"))
            database = connections[alias]
            try:
                model = (after if with_column else before).apps.get_model("console", "OAuthServices")
                with database.schema_editor() as schema:
                    schema.create_model(model)
                model.objects.using(alias).create(name="old-service", client_id="", client_secret="", redirect_uri="")
                yield database, before, after
            finally:
                database.close()
                del connections[alias]
                del connections.databases[alias]

    def pending_field_migration(self):
        from django.db import migrations

        migration = migrations.Migration("0003_oauthservices_auto_create_user", "console")
        migration.dependencies = [("console", "0002_previous")]
        migration.operations = [migrations.AddField(
            model_name="oauthservices", name="auto_create_user",
            field=OAuthServices._meta.get_field("auto_create_user").clone())]
        loader = SimpleNamespace(
            disk_migrations={("console", migration.name): migration},
            applied_migrations={("console", "0002_previous")})
        return migration, loader

    def test_startup_leaves_pending_add_field_to_migrate(self):
        from console.management.commands.repair_legacy_schema import repair_oauth_auto_create_user_column

        migration, loader = self.pending_field_migration()
        with self.startup_database() as (database, before, after):
            with mock.patch("console.management.commands.repair_legacy_schema.MigrationLoader", return_value=loader):
                self.assertFalse(repair_oauth_auto_create_user_column(database))
            with database.schema_editor() as schema:
                migration.operations[0].database_forwards("console", schema, before, after)
            self.assertFalse(OAuthServices.objects.using(database.alias).get(name="old-service").auto_create_user)

    def test_startup_records_only_completed_single_field_migration(self):
        from django.db.migrations.recorder import MigrationRecorder
        from console.management.commands.repair_legacy_schema import repair_oauth_auto_create_user_column

        migration, loader = self.pending_field_migration()
        with self.startup_database(with_column=True) as (database, _, _):
            with mock.patch("console.management.commands.repair_legacy_schema.MigrationLoader", return_value=loader):
                self.assertTrue(repair_oauth_auto_create_user_column(database))
            self.assertIn(("console", migration.name), MigrationRecorder(database).applied_migrations())
            self.assertFalse(OAuthServices.objects.using(database.alias).get(name="old-service").auto_create_user)

    def test_startup_plan_does_not_record_completed_field_migration(self):
        from django.db.migrations.recorder import MigrationRecorder
        from console.management.commands.repair_legacy_schema import repair_oauth_auto_create_user_column

        migration, loader = self.pending_field_migration()
        with self.startup_database(with_column=True) as (database, _, _):
            with mock.patch("console.management.commands.repair_legacy_schema.MigrationLoader", return_value=loader):
                self.assertTrue(repair_oauth_auto_create_user_column(database, dry_run=True))
            self.assertNotIn(("console", migration.name), MigrationRecorder(database).applied_migrations())

    def test_startup_does_not_skip_other_pending_operations(self):
        from django.core.management.base import CommandError
        from django.db import migrations
        from django.db.migrations.recorder import MigrationRecorder
        from console.management.commands.repair_legacy_schema import repair_oauth_auto_create_user_column

        migration, loader = self.pending_field_migration()
        migration.operations.append(migrations.RunSQL("SELECT 1"))
        with self.startup_database(with_column=True) as (database, _, _):
            with mock.patch("console.management.commands.repair_legacy_schema.MigrationLoader", return_value=loader):
                with self.assertRaises(CommandError):
                    repair_oauth_auto_create_user_column(database)
            self.assertNotIn(("console", migration.name), MigrationRecorder(database).applied_migrations())

    def test_startup_does_not_record_migration_before_its_dependencies(self):
        from django.core.management.base import CommandError
        from django.db.migrations.recorder import MigrationRecorder
        from console.management.commands.repair_legacy_schema import repair_oauth_auto_create_user_column

        migration, loader = self.pending_field_migration()
        loader.applied_migrations = set()
        with self.startup_database(with_column=True) as (database, _, _):
            with mock.patch("console.management.commands.repair_legacy_schema.MigrationLoader", return_value=loader):
                with self.assertRaises(CommandError):
                    repair_oauth_auto_create_user_column(database)
            self.assertNotIn(("console", migration.name), MigrationRecorder(database).applied_migrations())

    def test_startup_does_not_record_migration_with_different_field_definition(self):
        from django.core.management.base import CommandError
        from django.db.migrations.recorder import MigrationRecorder
        from console.management.commands.repair_legacy_schema import repair_oauth_auto_create_user_column

        migration, loader = self.pending_field_migration()
        migration.operations[0].field.default = True
        with self.startup_database(with_column=True) as (database, _, _):
            with mock.patch("console.management.commands.repair_legacy_schema.MigrationLoader", return_value=loader):
                with self.assertRaises(CommandError):
                    repair_oauth_auto_create_user_column(database)
            self.assertNotIn(("console", migration.name), MigrationRecorder(database).applied_migrations())

    def test_upgrade_defaults_existing_services_to_disabled_and_is_idempotent(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.db import connections
        from django.db.migrations.state import ModelState, ProjectState
        from console.management.commands.repair_legacy_schema import repair_oauth_auto_create_user_column

        state = ProjectState()
        state.add_model(ModelState.from_model(OAuthServices))
        before = state.clone()
        before.remove_field("console", "oauthservices", "auto_create_user")
        old_model = before.apps.get_model("console", "OAuthServices")
        alias = "oauth_provisioning_migration"
        with TemporaryDirectory(prefix="oauth-migration-") as directory:
            connections.databases[alias] = dict(connection.settings_dict, NAME=str(Path(directory) / "migration.sqlite3"))
            database = connections[alias]
            try:
                self.assertFalse(repair_oauth_auto_create_user_column(database))
                with database.schema_editor() as schema:
                    schema.create_model(old_model)
                old_model.objects.using(alias).create(name="old-service", client_id="", client_secret="", redirect_uri="")
                self.assertTrue(repair_oauth_auto_create_user_column(database, dry_run=True))
                with database.cursor() as cursor:
                    names = [field.name for field in database.introspection.get_table_description(cursor, "oauth_service")]
                self.assertNotIn("auto_create_user", names)
                self.assertTrue(repair_oauth_auto_create_user_column(database))
                self.assertFalse(OAuthServices.objects.using(alias).get(name="old-service").auto_create_user)
                self.assertFalse(repair_oauth_auto_create_user_column(database))
            finally:
                database.close()
                del connections[alias]
                del connections.databases[alias]

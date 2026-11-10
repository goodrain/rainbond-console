# -*- coding: utf-8 -*-
"""OAuth configuration names are unique within their ownership scope."""
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from io import StringIO
from urllib.parse import parse_qs, urlsplit
from types import SimpleNamespace
from unittest import TestCase, mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.db import IntegrityError, connection, connections, transaction  # noqa: E402
from django.db.migrations.state import ModelState, ProjectState  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.core.management.base import CommandError  # noqa: E402
from console.exception.bcode import ErrOauthServiceExists  # noqa: E402
from console.models.main import OAuthServices  # noqa: E402
from console.repositories.oauth_repo import OAuthRepo  # noqa: E402
from console.views.oauth import EnterpriseOauthService, OauthService  # noqa: E402


# capability_id: console.oauth.name-scope
class OAuthNameScopeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.created = OAuthServices._meta.db_table not in connection.introspection.table_names()
        if cls.created:
            with connection.schema_editor() as schema:
                schema.create_model(OAuthServices)

    @classmethod
    def tearDownClass(cls):
        if cls.created:
            with connection.schema_editor() as schema:
                schema.delete_model(OAuthServices)
        super().tearDownClass()

    def setUp(self):
        self.repo = OAuthRepo()
        self.addCleanup(OAuthServices.objects.filter(eid__startswith="scope-test").delete)

    def values(self, **overrides):
        data = dict(name="gitlab", client_id="", client_secret="", eid="scope-test-one", system=False,
                    redirect_uri="https://console.example.invalid/callback", oauth_type="gitlab",
                    home_url="https://gitlab.example.invalid", is_auto_login=False, is_console=True, enable=True)
        data.update(overrides)
        return data

    def create(self, user_id=1, **overrides):
        value = self.values(**overrides)
        self.repo.create_or_update_oauth_services([value], value["eid"], user_id)
        return OAuthServices.objects.filter(eid=value["eid"], user_id=user_id, name=value["name"]).latest("ID")

    def test_personal_then_enterprise_can_use_same_name(self):
        personal = self.create()
        public = self.create(system=True)
        self.assertNotEqual(personal.pk, public.pk)
        self.assertFalse(personal.system)
        self.assertTrue(public.system)

    def test_enterprise_then_personal_can_use_same_name(self):
        self.create(system=True)
        self.create()
        self.assertEqual(OAuthServices.objects.filter(eid="scope-test-one").count(), 2)

    def test_different_users_can_use_same_personal_name(self):
        self.create(user_id=1)
        self.create(user_id=2)
        self.assertEqual(OAuthServices.objects.filter(eid="scope-test-one").count(), 2)

    def test_different_enterprises_can_use_same_public_name(self):
        self.create(system=True)
        self.create(system=True, eid="scope-test-two")

    def test_same_user_in_different_enterprises_can_use_same_personal_name(self):
        self.create()
        self.create(eid="scope-test-two")

    def test_same_personal_scope_rejects_duplicate(self):
        self.create()
        with self.assertRaises(ErrOauthServiceExists):
            self.create()

    def test_public_scope_rejects_duplicate_from_another_admin(self):
        self.create(system=True)
        with self.assertRaises(ErrOauthServiceExists):
            self.create(user_id=2, system=True)

    def test_deleted_configuration_releases_name(self):
        self.create(is_deleted=True)
        self.create()

    def test_disabled_configuration_still_reserves_name(self):
        service = self.create()
        service.enable = False
        service.save(update_fields=["enable"])
        with self.assertRaises(ErrOauthServiceExists):
            self.create()

    def test_rename_to_personal_name_does_not_conflict_with_public_scope(self):
        self.create()
        public = self.create(name="company-gitlab", system=True)
        self.repo.create_or_update_oauth_services(
            [self.values(name="gitlab", service_id=public.pk, system=True)], "scope-test-one", 1)
        public.refresh_from_db()
        self.assertEqual(public.name, "gitlab")
        self.assertTrue(public.system)

    def test_rename_rejects_duplicate_and_keeps_original_name(self):
        self.create()
        other = self.create(name="other")
        with self.assertRaises(ErrOauthServiceExists):
            self.repo.create_or_update_oauth_services(
                [self.values(service_id=other.pk)], "scope-test-one", 1)
        other.refresh_from_db()
        self.assertEqual(other.name, "other")

    def test_edit_without_rename_excludes_current_record(self):
        service = self.create()
        self.repo.create_or_update_oauth_services(
            [self.values(service_id=service.pk)], "scope-test-one", 1)
        self.assertEqual(OAuthServices.objects.filter(eid="scope-test-one").count(), 1)

    def test_public_edit_uses_original_scope_even_if_request_claims_private(self):
        self.create(system=True)
        other = self.create(name="other", system=True, user_id=2)
        with self.assertRaises(ErrOauthServiceExists):
            self.repo.create_or_update_oauth_services(
                [self.values(service_id=other.pk, system=False)], "scope-test-one", 2)

    def test_duplicate_batch_is_atomic_and_returns_business_error(self):
        with self.assertRaises(ErrOauthServiceExists):
            self.repo.create_or_update_oauth_services([self.values(), self.values()], "scope-test-one", 1)
        self.assertFalse(OAuthServices.objects.filter(eid="scope-test-one").exists())

    def test_database_enforces_scope_when_business_precheck_is_bypassed(self):
        self.create(system=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OAuthServices.objects.create(**self.values(system=True), user_id=2)

    def test_bulk_database_conflict_is_translated_after_rollback(self):
        self.create()
        with mock.patch.object(self.repo, "get_by_name", side_effect=OAuthServices.DoesNotExist):
            with self.assertRaises(ErrOauthServiceExists):
                self.create()
        self.assertEqual(OAuthServices.objects.filter(eid="scope-test-one").count(), 1)

    def test_unrelated_integrity_failure_is_not_reported_as_name_conflict(self):
        with mock.patch.object(OAuthServices.objects, "bulk_create", side_effect=IntegrityError("other constraint")):
            with self.assertRaises(IntegrityError):
                self.create()

    def test_model_save_releases_scope_on_soft_delete(self):
        service = self.create()
        service.is_deleted = True
        service.save(update_fields=["is_deleted"])
        self.create()

    def test_legacy_enterprise_center_names_remain_globally_unique(self):
        OAuthServices.objects.create(**self.values(oauth_type="enterprisecenter"), user_id=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OAuthServices.objects.create(
                **self.values(oauth_type="enterprisecenter", eid="scope-test-two", system=True), user_id=2)

    def test_deleted_enterprise_center_keeps_name_for_legacy_global_lookups(self):
        OAuthServices.objects.create(**self.values(oauth_type="enterprisecenter", is_deleted=True), user_id=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OAuthServices.objects.create(**self.values(oauth_type="enterprisecenter", system=True), user_id=2)

    def test_partial_save_does_not_apply_unsaved_ownership_to_name_scope(self):
        service = self.create()
        scope = service.name_scope
        service.user_id = 2
        service.enable = False
        service.save(update_fields=["enable"])
        service.refresh_from_db()
        self.assertEqual(service.user_id, 1)
        self.assertEqual(service.name_scope, scope)

    def test_legacy_console_entrypoint_uses_independent_public_scope(self):
        self.create()
        self.repo.create_or_update_console_oauth_services([self.values()], "scope-test-one", 1, True)
        self.assertEqual(OAuthServices.objects.filter(eid="scope-test-one").count(), 2)

    def test_legacy_console_entrypoint_rejects_another_admins_public_name(self):
        self.create(system=True)
        with self.assertRaises(ErrOauthServiceExists):
            self.repo.create_or_update_console_oauth_services([self.values()], "scope-test-one", 2, True)

    def test_legacy_console_rename_rejects_duplicate_and_keeps_original_name(self):
        self.create(system=True)
        other = self.create(name="other", system=True, user_id=2)
        with self.assertRaises(ErrOauthServiceExists):
            self.repo.create_or_update_console_oauth_services(
                [self.values(service_id=other.pk)], "scope-test-one", 2, True)
        other.refresh_from_db()
        self.assertEqual(other.name, "other")

    def test_public_list_only_returns_public_record_for_shared_name(self):
        self.create()
        public = self.create(system=True)
        view = EnterpriseOauthService()
        view.user = SimpleNamespace(user_id=1)
        response = view.get(SimpleNamespace(GET={"system": "true"}), "scope-test-one")
        rows = response.data["data"]["list"]
        self.assertEqual([row["service_id"] for row in rows], [public.pk])

    def assert_authorization_targets_match_records(self, records):
        self.assertEqual(len(records), 2)
        for row in records:
            parameters = parse_qs(urlsplit(row["authorize_url"]).query)
            self.assertEqual(parameters["redirect_uri"][0], row["redirect_uri"] + "?service_id=" + str(row["service_id"]))

    def test_legacy_list_authorizes_each_same_named_configuration_by_its_own_id(self):
        self.create()
        self.create(system=True)
        view = OauthService()
        view.user = SimpleNamespace(user_id=1, enterprise_id="scope-test-one")
        with mock.patch("console.views.oauth.oauth_user_repo.get_by_oauths_user_id", return_value=[]):
            response = view.get(SimpleNamespace(user=view.user))
        self.assert_authorization_targets_match_records(response.data["data"]["list"])

    def test_legacy_create_response_authorizes_each_configuration_by_its_own_id(self):
        self.create()
        view = OauthService()
        view.user = SimpleNamespace(user_id=1, enterprise_id="scope-test-one")
        request = SimpleNamespace(user=view.user, data={"system": True, "oauth_services": [self.values(system=True)]})
        with mock.patch("console.views.oauth.operation_log_service"):
            response = view.post(request)
        self.assert_authorization_targets_match_records(response.data["data"]["bean"]["oauth_services"])


# capability_id: console.oauth.name-scope
class OAuthNameScopeUpgradeTests(TestCase):
    @contextmanager
    def legacy_database(self, with_scope=False):
        state = ProjectState()
        model_state = ModelState.from_model(OAuthServices)
        if not with_scope:
            model_state.fields.pop("name_scope", None)
            model_state.fields["name"]._unique = True
            model_state.options["constraints"] = []
        state.add_model(model_state)
        alias = "oauth_name_upgrade"
        with TemporaryDirectory(prefix="oauth-name-upgrade-") as directory:
            connections.databases[alias] = dict(connection.settings_dict, NAME=str(Path(directory) / "db.sqlite3"))
            database = connections[alias]
            try:
                legacy = state.apps.get_model("console", "OAuthServices")
                with database.schema_editor() as schema:
                    schema.create_model(legacy)
                row = legacy.objects.using(alias).create(
                    name="gitlab", client_id="", client_secret="", redirect_uri="", eid="scope-test-one",
                    user_id=1, is_console=True, system=False)
                yield database, row
            finally:
                database.close()
                del connections[alias]
                del connections.databases[alias]

    def test_upgrade_preserves_data_removes_global_unique_and_is_idempotent(self):
        from console.management.commands.migrate_oauth_name_scope import migrate_oauth_name_scope

        with self.legacy_database() as (database, legacy):
            self.assertTrue(migrate_oauth_name_scope(database))
            row = OAuthServices.objects.using(database.alias).get(pk=legacy.pk)
            self.assertEqual(row.name, "gitlab")
            self.assertFalse(row.system)
            self.assertEqual(row.user_id, 1)
            self.assertEqual(row.eid, "scope-test-one")
            self.assertFalse(migrate_oauth_name_scope(database))
            OAuthServices.objects.using(database.alias).create(
                name="gitlab", client_id="", client_secret="", redirect_uri="", eid=row.eid, user_id=1, system=True)
            with self.assertRaises(IntegrityError):
                OAuthServices.objects.using(database.alias).create(
                    name="gitlab", client_id="", client_secret="", redirect_uri="", eid=row.eid, user_id=2, system=True)

    def test_plan_does_not_change_legacy_columns_or_rows(self):
        from console.management.commands.migrate_oauth_name_scope import migrate_oauth_name_scope

        with self.legacy_database() as (database, legacy):
            self.assertTrue(migrate_oauth_name_scope(database, dry_run=True))
            with database.cursor() as cursor:
                columns = database.introspection.get_table_description(cursor, "oauth_service")
            self.assertNotIn("name_scope", [column.name for column in columns])
            legacy.refresh_from_db(using=database.alias)
            self.assertFalse(legacy.system)

    def test_pending_backfill_after_generated_migration_is_planned_and_repaired(self):
        from console.management.commands.migrate_oauth_name_scope import migrate_oauth_name_scope

        with self.legacy_database(with_scope=True) as (database, legacy):
            self.assertTrue(migrate_oauth_name_scope(database, dry_run=True))
            legacy.refresh_from_db(using=database.alias)
            self.assertIsNone(legacy.name_scope)
            output = StringIO()
            call_command("migrate_oauth_name_scope", database=database.alias, stdout=output)
            self.assertIn("upgraded", output.getvalue())
            legacy.refresh_from_db(using=database.alias)
            self.assertIsNotNone(legacy.name_scope)
            output = StringIO()
            call_command("migrate_oauth_name_scope", database=database.alias, stdout=output)
            self.assertIn("up to date", output.getvalue())

    def test_missing_table_fails_instead_of_reporting_success(self):
        from console.management.commands.migrate_oauth_name_scope import migrate_oauth_name_scope

        database = mock.Mock()
        database.introspection.table_names.return_value = []
        with self.assertRaises(CommandError):
            migrate_oauth_name_scope(database)

    def test_unknown_database_fails(self):
        with self.assertRaises(CommandError):
            call_command("migrate_oauth_name_scope", database="missing_oauth_scope_database", stdout=StringIO())

    def test_startup_upgrades_names_after_regular_migrations_before_verification(self):
        source = (Path(__file__).resolve().parents[2] / "entrypoint.sh").read_text()
        migrate = "if ! python manage.py migrate --fake-initial --noinput; then"
        scope = "if ! python manage.py migrate_oauth_name_scope; then"
        verify = "if ! python manage.py verify_required_schema; then"
        self.assertIn(scope, source)
        self.assertLess(source.index(migrate), source.index(scope))
        self.assertLess(source.index(scope), source.index(verify))

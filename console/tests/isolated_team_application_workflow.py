"""Isolated SQLite lifecycle tests; provisioning calls use a fake, never a real cluster."""
import importlib.util
import unittest
import sys
from unittest import mock
from pathlib import Path
from types import SimpleNamespace
from django.conf import settings

if not settings.configured:
    settings.configure(INSTALLED_APPS=[], DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
                       SECRET_KEY="test-placeholder", USE_TZ=True, REST_FRAMEWORK={"UNAUTHENTICATED_USER": None})
import django

django.setup()
from django.db import connection  # noqa: E402
from rest_framework.exceptions import ValidationError  # noqa: E402
from console.repositories.team_application_repo import TeamApplicationRepository  # noqa: E402
from console.services.team_applications import TeamApplicationService, ApplicationError  # noqa: E402

path = Path(__file__).parents[1] / "models" / "team_application.py"
spec = importlib.util.spec_from_file_location("isolated_team_application", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TeamApplication = module.TeamApplication
USER = SimpleNamespace(user_id=2, enterprise_id="enterprise", nick_name="Applicant",
                       user_name="applicant", is_authenticated=True)
ADMIN = SimpleNamespace(user_id=1, enterprise_id="enterprise", nick_name="Admin", user_name="admin", is_authenticated=True)


class FakeProvisioner:
    def __init__(self):
        self.created = 0
        self.calls = []
        self.granted = 0
        self.fail = False

    def regions(self, enterprise, names):
        return names if enterprise == "enterprise" and set(names) <= {"one", "two"} else None

    def namespace_exists(self, namespace):
        return namespace == "occupied"

    def alias_exists(self, enterprise, alias):
        return False

    def applicant(self, row):
        return USER

    def create(self, row, reviewer):
        self.created += 1
        assert reviewer.user_id == ADMIN.user_id
        return SimpleNamespace(tenant_id="team-id", tenant_name="team-name")

    def apply_region(self, row, region):
        self.calls.append(region)
        assert row.quota["cpu_millicores"] == 1500
        if self.fail and region == "two":
            raise RuntimeError("upstream failure")

    def grant(self, row, applicant, reviewer):
        assert row.regions_done == row.regions
        self.granted += 1


class TeamApplicationWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with connection.schema_editor() as editor:
            editor.create_model(TeamApplication)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            editor.delete_model(TeamApplication)

    def setUp(self):
        TeamApplication.objects.all().delete()
        self.provisioner = FakeProvisioner()
        self.service = TeamApplicationService(TeamApplicationRepository(TeamApplication), self.provisioner)
        self.data = {
            "team_name": "Development", "namespace": "development", "useable_regions": ["one", "two"],
            "application_reason": "Development workspace",
            "quota": {"cpu_millicores": 1500, "memory_mib": 2048, "storage_gib": 20}
        }

    def submit(self, **changes):
        return self.service.submit(USER, "enterprise", {**self.data, **changes})

    def review(self, row, decision="approved", comment="Ready"):
        return self.service.review(ADMIN, "enterprise", row.id, {"decision": decision, "comment": comment}, admin=True)

    def test_submission_persists_server_identity_and_does_not_create_team(self):
        row = self.submit(applicant_id=1, status="approved", region_labels=["forged"])
        row.refresh_from_db()
        self.assertEqual(row.status, "pending")
        self.assertEqual(row.applicant_id, 2)
        self.assertEqual(row.region_labels, ["one", "two"])
        self.assertEqual(row.quota["cpu_millicores"], 1500)
        self.assertEqual(self.provisioner.created, 0)
        self.assertEqual(row.public()["id"], str(row.id))

    def test_nullable_nickname_uses_existing_user_model_fields(self):
        applicant = SimpleNamespace(user_id=2, enterprise_id="enterprise", nick_name=None)
        reviewer = SimpleNamespace(user_id=1, enterprise_id="enterprise", nick_name=None)
        row = self.service.submit(applicant, "enterprise", self.data)
        self.assertEqual(row.applicant_name, "2")
        row = self.service.review(reviewer, "enterprise", row.id, {"decision": "rejected", "comment": "Revise"}, admin=True)
        self.assertEqual(row.reviewer_name, "1")

    def test_ordinary_users_only_see_own_applications_and_cannot_review(self):
        row = self.submit()
        other = SimpleNamespace(user_id=3, enterprise_id="enterprise")
        self.assertEqual(self.service.list(other, "enterprise").count(), 0)
        with self.assertRaises(ApplicationError):
            self.service.list(USER, "enterprise", "all")
        with self.assertRaises(ApplicationError):
            self.service.review(USER, "enterprise", row.id, {"decision": "approved"})
        with self.assertRaises(ApplicationError):
            self.service.list(USER, "other")

    def test_duplicate_pending_and_invalid_resources_are_rejected(self):
        self.submit()
        with self.assertRaises(ApplicationError):
            self.submit()
        for quota in [{}, {"cpu_millicores": 0, "memory_mib": 1, "storage_gib": 1},
                      {"cpu_millicores": 1.5, "memory_mib": 1, "storage_gib": 1}]:
            with self.assertRaises(ValidationError):
                self.submit(namespace="new", quota=quota)
        with self.assertRaises(ApplicationError):
            self.submit(namespace="occupied")
        with self.assertRaises(ApplicationError):
            self.submit(useable_regions=["other-enterprise-region"])

    def test_rejection_requires_comment_and_resubmission_keeps_original(self):
        row = self.submit()
        with self.assertRaises(ValidationError):
            self.review(row, "rejected", " ")
        self.review(row, "rejected", "Explain usage")
        followup = self.submit(previous_id=str(row.id))
        row.refresh_from_db()
        self.assertEqual(row.status, "rejected")
        self.assertEqual(row.comment, "Explain usage")
        self.assertEqual(followup.status, "pending")
        self.assertEqual(TeamApplication.objects.count(), 2)

    def test_approval_creates_once_and_grants_only_after_all_regions(self):
        row = self.review(self.submit())
        self.assertEqual(row.status, "approved")
        self.assertEqual(row.team_id, "team-id")
        self.assertEqual(self.provisioner.calls, ["one", "two"])
        self.assertEqual(self.provisioner.granted, 1)
        with self.assertRaises(ApplicationError):
            self.review(row)
        self.assertEqual(self.provisioner.created, 1)

    def test_partial_failure_is_pending_and_retry_reuses_team_and_completed_regions(self):
        self.provisioner.fail = True
        row = self.review(self.submit())
        row.refresh_from_db()
        self.assertEqual(row.status, "pending")
        self.assertEqual(row.regions_done, ["one"])
        self.assertEqual(self.provisioner.granted, 0)
        self.assertTrue(row.provisioning_error)
        with self.assertRaises(ApplicationError):
            self.review(row, "rejected", "Stop")
        self.provisioner.fail = False
        row = self.review(row)
        self.assertEqual(row.status, "approved")
        self.assertEqual(self.provisioner.created, 1)
        self.assertEqual(self.provisioner.calls, ["one", "two", "two"])
        self.assertEqual(self.provisioner.granted, 1)

    def views(self):
        from rest_framework.views import APIView
        from rest_framework.permissions import IsAuthenticated

        class AuthenticatedBase(APIView):
            authentication_classes = []
            permission_classes = [IsAuthenticated]

            def initial(self, request, *args, **kwargs):
                self.user = request.user
                self.is_enterprise_admin = request.user.user_id == ADMIN.user_id

        source = (Path(__file__).parents[1] / "views" / "team_applications.py").read_text()
        source = source.replace("from console.views.base import JWTAuthApiView", "")
        namespace = {"JWTAuthApiView": AuthenticatedBase}
        exec(compile(source, "team_applications.py", "exec"), namespace)
        namespace["team_application_service"] = self.service
        return namespace

    def request(self, view, method, data=None, actor=USER, **kwargs):
        from rest_framework.test import APIRequestFactory, force_authenticate
        request = getattr(APIRequestFactory(), method)(
            "/console/enterprises/enterprise/team-applications", data or {}, format="json")
        if actor:
            force_authenticate(request, actor)
        return view.as_view()(request, enterprise_id="enterprise", **kwargs)

    def test_http_application_review_and_result_contract(self):
        views = self.views()
        response = self.request(views["TeamApplicationsView"], "post", self.data)
        self.assertEqual(response.status_code, 201)
        bean = response.data["data"]["bean"]
        self.assertEqual(bean["status"], "pending")
        from uuid import UUID
        reviewed = self.request(views["TeamApplicationReviewView"], "post", {"decision": "approved"},
                                actor=ADMIN, request_id=UUID(bean["id"]))
        self.assertEqual(reviewed.data["data"]["bean"]["status"], "approved")
        listed = self.request(views["TeamApplicationsView"], "get")
        self.assertEqual(listed.data["data"]["bean"]["total"], 1)
        self.assertEqual(listed.data["data"]["bean"]["list"][0]["team_id"], "team-id")

    def test_http_rejects_anonymous_and_forged_administrator(self):
        views = self.views()
        self.assertIn(self.request(views["TeamApplicationsView"], "get", actor=None).status_code, [401, 403])
        self.assertEqual(self.request(views["TeamApplicationsView"], "get", {"scope": "all"}).status_code, 403)
        row = self.submit()
        response = self.request(views["TeamApplicationReviewView"], "post",
                                {"decision": "approved", "is_enterprise_admin": True},
                                request_id=row.id)
        self.assertEqual(response.status_code, 403)
        row.refresh_from_db()
        self.assertEqual(row.status, "pending")

    def test_region_adapter_passes_requested_resource_units_to_existing_api(self):
        from console.services.team_application_provisioner import TeamApplicationProvisioner
        region_service = mock.Mock()
        region_api = mock.Mock()
        region_api.set_tenant_resource_limit.return_value = ({"status": 200}, {})
        row = SimpleNamespace(enterprise_id="enterprise", team_name="created-team", namespace="development",
                              quota={"cpu_millicores": 1500, "memory_mib": 1536, "storage_gib": 20})
        with mock.patch.dict(sys.modules, {
            "console.services.region_services": SimpleNamespace(region_services=region_service),
            "www.apiclient.regionapi": SimpleNamespace(RegionInvokeApi=lambda: region_api)
        }):
            TeamApplicationProvisioner().apply_region(row, "one")
        region_service.create_tenant_on_region.assert_called_once_with("enterprise", "created-team", "one", "development", False)
        region_api.set_tenant_resource_limit.assert_called_once_with("enterprise", "created-team", "one", {
            "limit_cpu": 1500, "limit_memory": 1536, "limit_storage": 20})

    def test_grant_transfers_owner_and_removes_only_the_temporary_creator(self):
        from console.services.team_application_provisioner import TeamApplicationProvisioner
        team = SimpleNamespace(pk=10, tenant_id="team-id", creater=1, save=mock.Mock())
        teams, memberships, users = mock.Mock(), mock.Mock(), mock.Mock()
        teams.objects.get.return_value = team
        users.objects.filter.return_value.first.return_value = ADMIN
        service, roles, user_roles = mock.Mock(), mock.Mock(), mock.Mock()
        roles.get_role_by_name.return_value = SimpleNamespace(ID=7)
        applicant = USER
        retry_reviewer = SimpleNamespace(user_id=9)
        row = SimpleNamespace(team_id="team-id", enterprise_id="enterprise", quota={"memory_mib": 1536})
        with mock.patch.dict(sys.modules, {
            "console.services.team_services": SimpleNamespace(team_services=service),
            "console.services.perm_services": SimpleNamespace(role_kind_services=roles, user_kind_role_service=user_roles),
            "www.models.main": SimpleNamespace(Tenants=teams, PermRelTenant=memberships, Users=users)
        }):
            TeamApplicationProvisioner().grant(row, applicant, retry_reviewer)
        service.add_user_role_to_team.assert_called_once_with(team, [2], [7])
        memberships.objects.filter.assert_any_call(tenant_id=10, user_id=2)
        memberships.objects.filter.return_value.update.assert_called_once_with(identity="owner")
        user_roles.delete_user_roles.assert_called_once_with(kind="team", kind_id="team-id", user=ADMIN)
        memberships.objects.filter.assert_any_call(tenant_id=10, user_id=1)
        self.assertEqual(team.creater, 2)
        self.assertEqual(team.limit_memory, 1536)
        team.save.assert_called_once_with(update_fields=["creater", "limit_memory"])

    def test_new_table_migration_matches_the_application_model(self):
        path = Path(__file__).parents[1] / "migrations" / "0010_team_creation_application.py"
        spec = importlib.util.spec_from_file_location("team_application_schema", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        operation = migration.Migration.operations[0]
        self.assertEqual(operation.options["db_table"], TeamApplication._meta.db_table)
        self.assertEqual({name for name, _ in operation.fields}, {field.name for field in TeamApplication._meta.local_fields})
        actual = dict(operation.fields)
        for field in TeamApplication._meta.local_fields:
            self.assertEqual(actual[field.name].deconstruct()[1:], field.deconstruct()[1:])


if __name__ == "__main__":
    unittest.main()

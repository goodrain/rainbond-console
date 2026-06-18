# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import perm_services as perm_services_module  # noqa: E402


class FakeRoles(object):
    def __bool__(self):
        return True

    def values_list(self, field, flat=False):
        return [1]


class FakeRolePerms(object):
    def __bool__(self):
        return True

    def values(self, *fields):
        return [{
            "role_id": 1,
            "perm_code": 300002,
            "app_id": -1,
        }]


class FakeAppQuerySet(object):
    def __init__(self, app_ids):
        self.app_ids = app_ids

    def values_list(self, field, flat=False):
        return self.app_ids


def get_sub_model(model, name):
    for sub_model in model["sub_models"]:
        if name in sub_model:
            return sub_model[name]
    raise AssertionError("sub model {} not found".format(name))


def get_perm(model, perm_name):
    for perm in model["perms"]:
        if perm_name in perm:
            return perm[perm_name]
    raise AssertionError("permission {} not found".format(perm_name))


# capability_id: console.app-creator.full-permissions
class AppCreatorPermissionTreeTestCase(TestCase):
    def test_created_app_gets_full_permissions_for_normal_team_member(self):
        service = perm_services_module.UserKindPermService()
        user = SimpleNamespace(user_id=2, nick_name="alice")

        def filter_apps(**kwargs):
            if kwargs == {"tenant_id": "team-1"}:
                return FakeAppQuerySet([101, 102])
            if kwargs == {"tenant_id": "team-1", "username": "alice"}:
                return FakeAppQuerySet([101])
            return FakeAppQuerySet([])

        with mock.patch.object(perm_services_module.role_perm_relation_repo,
                               "get_roles_perm_relation",
                               return_value=FakeRolePerms()), \
                mock.patch.object(perm_services_module.user_kind_role_repo,
                                  "get_user_roles_model",
                                  return_value=FakeRoles()), \
                mock.patch.object(perm_services_module.ServiceGroup.objects, "filter", side_effect=filter_apps):
            result = service.get_user_perms(kind="team", kind_id="team-1", user=user)

        team_model = result["permissions"]["team"]
        team_app_manage = get_sub_model(team_model, "team_app_manage")
        created_app = get_sub_model(team_app_manage, "app_101")
        other_app = get_sub_model(team_app_manage, "app_102")

        created_app_overview = get_sub_model(created_app, "app_overview")
        created_app_release = get_sub_model(created_app, "app_release")
        self.assertTrue(get_perm(created_app_overview, "describe"))
        self.assertTrue(get_perm(created_app_overview, "edit"))
        self.assertTrue(get_perm(created_app_overview, "delete"))
        self.assertTrue(get_perm(created_app_release, "share"))

        other_app_overview = get_sub_model(other_app, "app_overview")
        other_app_release = get_sub_model(other_app, "app_release")
        self.assertTrue(get_perm(other_app_overview, "describe"))
        self.assertFalse(get_perm(other_app_overview, "edit"))
        self.assertFalse(get_perm(other_app_overview, "delete"))
        self.assertFalse(get_perm(other_app_release, "share"))

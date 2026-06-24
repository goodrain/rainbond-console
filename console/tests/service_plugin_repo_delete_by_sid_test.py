# -*- coding: utf-8 -*-
import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.repositories.plugin import service_plugin_repo as repo_module  # noqa: E402


# capability_id: console.plugin.delete-by-sid
class DeleteBySidTest(TestCase):
    def test_delete_by_sid_deletes_matching_relations(self):
        repo = repo_module.AppPluginRelationRepo()
        with mock.patch.object(repo_module, "TenantServicePluginRelation") as mocked:
            repo.delete_by_sid("svc-1")

            mocked.objects.filter.assert_called_once_with(service_id="svc-1")
            mocked.objects.filter.return_value.delete.assert_called_once()

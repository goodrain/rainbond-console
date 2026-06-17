# -*- coding: utf-8 -*-
import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from console.repositories.deploy_repo import DeployRepo  # noqa: E402
from openapi.views.apps import apps as apps_module  # noqa: E402


# capability_id: openapi.app.create-third-component-deploy-key
class ThirdComponentDeployRepoTest(TestCase):
    def test_deploy_repo_is_the_singleton_not_the_module(self):
        # `from console.repositories import deploy_repo` imported the module, whose
        # get_deploy_relation_by_service_id lives on the DeployRepo singleton -> AttributeError.
        self.assertIsInstance(apps_module.deploy_repo, DeployRepo)
        self.assertTrue(hasattr(apps_module.deploy_repo, "get_deploy_relation_by_service_id"))

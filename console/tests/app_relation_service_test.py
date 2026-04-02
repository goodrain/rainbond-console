# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.test import SimpleTestCase

django.setup()

from console.exception.main import ServiceHandleException
from console.services.app_config.app_relation_service import AppServiceRelationService


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class AppRelationServiceTests(SimpleTestCase):

    # capability_id: console.dependency.invalid-container-port
    @patch("console.services.app_config.app_relation_service.dep_relation_repo.get_depency_by_serivce_id_and_dep_service_id")
    @patch("console.services.app_config.app_relation_service.service_repo.get_service_by_tenant_and_id")
    @patch("console.services.app_config.app_relation_service.port_service.get_service_port_by_port")
    def test_add_service_dependency_rejects_unknown_dep_service_port(
            self,
            mock_get_service_port_by_port,
            mock_get_dep_service,
            mock_get_dependency,
    ):
        relation_service = AppServiceRelationService()
        tenant = Obj(tenant_id="team-1", tenant_name="demo-team", enterprise_id="eid-1", namespace="default")
        service = Obj(service_id="svc-1", create_status="complete")
        dep_service = Obj(service_id="svc-2", tenant_id="team-1", service_region="rainbond", service_alias="dep-svc", service_type="web")

        mock_get_dependency.return_value = None
        mock_get_dep_service.return_value = dep_service
        mock_get_service_port_by_port.return_value = None

        with self.assertRaises(ServiceHandleException) as context:
            relation_service.add_service_dependency(
                tenant,
                service,
                "svc-2",
                open_inner=True,
                container_port=8080,
                user_name="admin",
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.details["field"], "container_port")
        self.assertEqual(context.exception.details["reason"], "not_found_on_dependency_service")
        self.assertEqual(context.exception.details["provided_value"], 8080)
        self.assertEqual(context.exception.details["dep_service_id"], "svc-2")

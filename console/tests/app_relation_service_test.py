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

APP_RELATION_PATH = "console.services.app_config.app_relation_service"


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakePorts(list):
    def filter(self, **kwargs):
        if kwargs.get("is_inner_service") is True:
            return FakePorts([port for port in self if getattr(port, "is_inner_service", False)])
        return self


class FakeDependency(object):
    def __init__(self):
        self.deleted = False

    def delete(self):
        self.deleted = True


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
        dep_service = Obj(
            service_id="svc-2",
            tenant_id="team-1",
            service_region="rainbond",
            service_alias="dep-svc",
            service_type="web",
        )

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

    @patch(APP_RELATION_PATH + ".network_policy_dependency_sync_service.sync_after_dependency_change")
    @patch(APP_RELATION_PATH + ".region_api.add_service_dependency")
    @patch(APP_RELATION_PATH + ".k8s_attribute_repo.get_by_component_id_name", return_value=[])
    @patch(APP_RELATION_PATH + ".dep_relation_repo.add_service_dependency")
    @patch(APP_RELATION_PATH + ".AppServiceRelationService._AppServiceRelationService__is_env_duplicate",
           return_value=False)
    @patch(APP_RELATION_PATH + ".port_repo.get_service_ports")
    @patch(APP_RELATION_PATH + ".service_repo.get_service_by_tenant_and_id")
    @patch(APP_RELATION_PATH + ".dep_relation_repo.get_depency_by_serivce_id_and_dep_service_id")
    def test_add_service_dependency_triggers_network_policy_dependency_sync(
            self,
            mock_get_dependency,
            mock_get_dep_service,
            mock_get_service_ports,
            _mock_is_env_duplicate,
            mock_add_dependency,
            _mock_get_sa,
            _mock_region_add,
            mock_sync,
    ):
        relation_service = AppServiceRelationService()
        tenant = Obj(
            tenant_id="team-1",
            tenant_name="demo-team",
            enterprise_id="eid-1",
            namespace="default",
        )
        service = Obj(
            tenant_id="team-1",
            service_id="svc-1",
            service_region="rainbond",
            service_alias="api",
            create_status="complete",
        )
        dep_service = Obj(service_id="svc-2", tenant_id="team-1", service_type="web")
        dep_relation = Obj(service_id="svc-1", dep_service_id="svc-2")

        mock_get_dependency.return_value = None
        mock_get_dep_service.return_value = dep_service
        mock_get_service_ports.return_value = FakePorts([Obj(container_port=3306, is_inner_service=True)])
        mock_add_dependency.return_value = dep_relation

        plugin_module = ModuleType("console.services.plugin")
        plugin_module.app_plugin_service = Obj(
            update_config_if_have_export_plugin=lambda *args, **kwargs: None,
        )
        with patch.dict(sys.modules, {"console.services.plugin": plugin_module}):
            code, msg, relation = relation_service.add_service_dependency(
                tenant,
                service,
                "svc-2",
                user_name="admin",
            )

        self.assertEqual(code, 200)
        self.assertEqual(msg, "success")
        self.assertEqual(relation, dep_relation)
        mock_sync.assert_called_once_with(tenant, service, "svc-2")

    @patch(APP_RELATION_PATH + ".network_policy_dependency_sync_service.sync_after_dependency_change")
    @patch(APP_RELATION_PATH + ".region_api.delete_service_dependency")
    @patch(APP_RELATION_PATH + ".k8s_attribute_repo.get_by_component_id_name", return_value=[])
    @patch(APP_RELATION_PATH + ".dep_relation_repo.get_depency_by_serivce_id_and_dep_service_id")
    def test_delete_service_dependency_triggers_network_policy_dependency_sync(
            self,
            mock_get_dependency,
            _mock_get_sa,
            _mock_region_delete,
            mock_sync,
    ):
        relation_service = AppServiceRelationService()
        tenant = Obj(
            tenant_id="team-1",
            tenant_name="demo-team",
            enterprise_id="eid-1",
            namespace="default",
        )
        service = Obj(
            tenant_id="team-1",
            service_id="svc-1",
            service_region="rainbond",
            service_alias="api",
            create_status="complete",
        )
        dependency = FakeDependency()
        mock_get_dependency.return_value = dependency

        plugin_module = ModuleType("console.services.plugin")
        plugin_module.app_plugin_service = Obj(
            update_config_if_have_export_plugin=lambda *args, **kwargs: None,
        )
        with patch.dict(sys.modules, {"console.services.plugin": plugin_module}):
            code, msg, relation = relation_service.delete_service_dependency(
                tenant,
                service,
                "svc-2",
                user_name="admin",
            )

        self.assertEqual(code, 200)
        self.assertEqual(msg, "success")
        self.assertEqual(relation, dependency)
        self.assertTrue(dependency.deleted)
        mock_sync.assert_called_once_with(tenant, service, "svc-2")

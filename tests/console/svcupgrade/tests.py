# -*- coding: utf-8 -*-
import json

import pytest
from django.conf import settings

from console.exception.main import RbdAppNotFound
from console.exception.main import RecordNotFound
from console.models.main import RainbondCenterApp
from console.models.main import ServiceSourceInfo
from www.models.main import TenantServiceInfo, Tenants


@pytest.mark.django_db
def test_record_not_found(mocker):
    with pytest.raises(RecordNotFound):
        from console.services.app_actions.properties_changes import PropertiesChanges
        service_source = ServiceSourceInfo()
        service_source.group_key = "dummy group_key"
        mocker.patch("console.repositories.app.service_source_repo.get_service_source", return_value=service_source)
        properties_changes = PropertiesChanges(TenantServiceInfo(), Tenants())
        properties_changes.get_property_changes("eid", "version")


@pytest.mark.django_db
def test_rbd_app_not_found(mocker):
    from console.services.app_actions.properties_changes import PropertiesChanges

    with open("{}/tests/console/svcupgrade/app_template.json".format(settings.BASE_DIR)) as json_file:
        app_template = json.load(json_file)
        rain_app = RainbondCenterApp()
        rain_app.app_template = json.dumps(app_template)
    mocker.patch(
        "console.repositories.market_app_repo.rainbond_app_repo.get_enterpirse_app_by_key_and_version", return_value=rain_app)

    service_source = ServiceSourceInfo()
    service_source.group_key = "dummy group_key"
    mocker.patch("console.repositories.app.service_source_repo.get_service_source", return_value=service_source)

    with pytest.raises(RbdAppNotFound):
        properties_changes = PropertiesChanges(TenantServiceInfo(), Tenants())
        properties_changes.get_property_changes("eid", "version")


@pytest.mark.django_db
def test_envs_changes():
    from console.services.app_actions.properties_changes import PropertiesChanges
    from console.repositories.app_config import env_var_repo

    tenant_id = "c1a29fe4d7b0413993dc859430cf743d"
    service_id = "03289ae373e65e4a1a22046d7f76ca5e"

    tenantServiceEnvVar = {}
    tenantServiceEnvVar["tenant_id"] = tenant_id
    tenantServiceEnvVar["service_id"] = service_id
    tenantServiceEnvVar['container_port'] = 0
    tenantServiceEnvVar["name"] = "NGINX_VERSION"
    tenantServiceEnvVar["attr_name"] = "NGINX_VERSION"
    tenantServiceEnvVar["attr_value"] = "1.15.12-1~stretch"
    tenantServiceEnvVar["is_change"] = False
    tenantServiceEnvVar["scope"] = "inner"
    env_var_repo.add_service_env(**tenantServiceEnvVar)

    envs = [
        {
            "is_change": True,
            "name": "\\u65e5\\u5fd7\\u8f93\\u51fa\\u65b9\\u5f0f",
            "attr_value": "file",
            "attr_name": "DESTINATION"
        },
        {
            "is_change": True,
            "name": "\\u8be6\\u7ec6\\u9519\\u8bef\\u65e5\\u5fd7",
            "attr_value": "true",
            "attr_name": "TRACEALLEXCEPTIONS"
        },
        {
            "is_change": True,
            "name": "NGINX_VERSION",
            "attr_value": "1.15.12-1~stretch",
            "attr_name": "NGINX_VERSION"
        },
    ]
    service = TenantServiceInfo()
    service.tenant_id = tenant_id
    service.service_id = service_id
    properties_changes = PropertiesChanges(service, Tenants())
    env_changes = properties_changes.env_changes(envs)
    print(env_changes)
    assert 2 == len(env_changes["add"])
    assert next(iter([x for x in env_changes["add"] if x["attr_name"] == "DESTINATION"]), None)
    assert next(iter([x for x in env_changes["add"] if x["attr_name"] == "TRACEALLEXCEPTIONS"]), None)

import logging

import pytest

from console.repositories.app_config import env_var_repo
from console.repositories.app_config import port_repo
from www.models.main import Tenants
from www.models.main import TenantServiceInfo

logger = logging.getLogger("default")


@pytest.mark.django_db
def test_restore_env():
    from console.services.app_actions.app_restore import AppRestore
    tn = Tenants()
    tn.tenant_id = "c1a29fe4d7b0413993dc859430cf743d"
    svc = TenantServiceInfo()
    svc.service_id = "36966cedcad44358a12f1707dece18da"
    backup_data = {
        "service_env_vars": [{
            "name": "PHPIZE_DEPS",
            "tenant_id": "c1a29fe4d7b0413993dc859430cf743d",
            "attr_name": "PHPIZE_DEPS",
            "container_port": 0,
            "create_time": "2019-05-14 18:04:26",
            "attr_value": "autoconf",
            "is_change": True,
            "scope": "inner",
            "service_id": "36966cedcad44358a12f1707dece18da",
            "ID": 1080
        }, {
            "name": "PHP_EXTRA_CONFIGURE_ARGS",
            "tenant_id": "c1a29fe4d7b0413993dc859430cf743d",
            "attr_name": "PHP_EXTRA_CONFIGURE_ARGS",
            "container_port": 0,
            "create_time": "2019-05-14 18:04:26",
            "attr_value": "--with-apxs2 --disable-cgi",
            "is_change": True,
            "scope": "inner",
            "service_id": "36966cedcad44358a12f1707dece18da",
            "ID": 1081
        }]
    }
    service_env_vars = backup_data["service_env_vars"]
    raw_envs = [env["name"] for env in service_env_vars]
    app_restore = AppRestore(tn, svc)
    app_restore.envs(service_env_vars)
    envs = env_var_repo.get_service_env(tn.tenant_id, svc.service_id)

    for env in envs:
        assert env.name in raw_envs


@pytest.mark.django_db
def test_restore_ports():
    from console.services.app_actions.app_restore import AppRestore
    tn = Tenants()
    tn.tenant_id = "c1a29fe4d7b0413993dc859430cf743d"
    svc = TenantServiceInfo()
    svc.service_id = "5a9209f3a3e94695b23fbd8b16a07d2b"
    backup_data = {
        "service_ports": [{
            "lb_mapping_port": 0,
            "protocol": "http",
            "mapping_port": 80,
            "tenant_id": "c1a29fe4d7b0413993dc859430cf743d",
            "port_alias": "GR063B3980",
            "container_port": 80,
            "is_outer_service": False,
            "is_inner_service": False,
            "service_id": "5a9209f3a3e94695b23fbd8b16a07d2b",
            "ID": 513
        }],
    }
    service_ports = backup_data["service_ports"]
    raw_ports = [port["port_alias"] for port in service_ports]
    app_restore = AppRestore(tn, svc)
    app_restore.ports(service_ports)
    ports = port_repo.get_service_ports(tn.tenant_id, svc.service_id)

    for port in ports:
        assert port.port_alias in raw_ports

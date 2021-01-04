import logging

import pytest

from console.models.main import ServiceSourceInfo
from console.models.main import TenantServiceBackup

logger = logging.getLogger("default")


@pytest.mark.django_db
def test_update_changed(mocker):
    from console.services.app_actions.app_deploy import MarketService
    service = ServiceSourceInfo()
    service.service_id = "dummy service_id"
    market_service = MarketService(None, service, "dummy version")
    market_service._update_changed()
    for k, v in list(market_service.changed.items()):
        continue


@pytest.mark.django_db
def test_restore_all_backup(mocker):
    from console.services.app_actions.app_deploy import MarketService
    service = ServiceSourceInfo()
    service.service_id = "dummy service_id"
    market_service = MarketService(None, service, "dummy version")
    backup = TenantServiceBackup()
    market_service.restore_func = {
        "deploy_version": market_service.dummy_func,
        "app_version": market_service.dummy_func,
        "image": market_service.dummy_func,
        "slug_path": market_service.dummy_func,
        "envs": market_service.dummy_func,
        "connect_infos": market_service.dummy_func,
        "ports": market_service.dummy_func,
        "volumes": market_service.dummy_func,
        "probe": market_service.dummy_func,
        "dep_services": market_service.dummy_func,
        "dep_volumes": market_service.dummy_func,
        "plugins": market_service.dummy_func,
    }
    logger.debug("market_service.async_action: {}".format(market_service.async_action))
    market_service.restore_backup(backup)
    assert 0 == market_service.async_action
    assert 0 == market_service.get_async_action()

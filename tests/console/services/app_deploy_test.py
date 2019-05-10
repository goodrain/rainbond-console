import pytest

from console.models.main import ServiceSourceInfo


@pytest.mark.django_db
def test_update_changed(mocker):
    from console.services.app_actions.app_deploy import MarketService
    service = ServiceSourceInfo()
    service.service_id = "dummy service_id"
    market_service = MarketService(None, service, "dummy version")
    market_service._update_changed()
    for k, v in market_service.changed.items():
        continue

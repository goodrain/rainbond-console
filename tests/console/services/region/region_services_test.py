# -*- coding: utf-8 -*-
import pytest

region_config_data = {
    "region_id": "3dddf798efc34be4acbd1442a81daff2",
    "region_name": "test-add-region",
    "region_alias": "测试添加数据中心2",
    "url": "https://region.goodrain.me:8443",
    "token": None,
    "wsurl": "ws://39.104.21.33:6060",
    "httpdomain": "389097.grapps.cn",
    "tcpdomain": "39.104.21.33",
    "scope": "private",
    "ssl_ca_cert": "dummy",
    "cert_file": "dummy",
    "key_file": "dummy",
    "status": "0",
    "desc": "当前数据中心是默认安装添加的数据中心",
}


@pytest.mark.django_db
def test_del_by_region_id_not_found():
    from console.services.region_services import region_services
    from console.models.main import RegionConfig
    with pytest.raises(RegionConfig.DoesNotExist):
        region_services.del_by_region_id("foobar")


@pytest.mark.django_db
def test_del_by_region_id_tx(mocker):
    from console.services.region_services import region_services
    from console.models.main import RegionConfig

    RegionConfig.objects.create(**region_config_data)
    mocker.patch("console.services.region_services.region_services.update_region_config", side_effect=Exception('Boom!'))
    with pytest.raises(Exception):
        region_services.del_by_region_id("3dddf798efc34be4acbd1442a81daff2")
    region = RegionConfig.objects.get(region_id="3dddf798efc34be4acbd1442a81daff2")
    assert region.region_id == "3dddf798efc34be4acbd1442a81daff2"


@pytest.mark.django_db
def test_del_by_region_ok():
    from console.services.region_services import region_services
    from console.models.main import RegionConfig

    region_config_data["status"] = 1
    RegionConfig.objects.create(**region_config_data)
    region_services.update_region_config()
    region_services.check_region_in_config("test-region")
    region_services.del_by_region_id("3dddf798efc34be4acbd1442a81daff2")

    with pytest.raises(RegionConfig.DoesNotExist):
        RegionConfig.objects.get(region_id="3dddf798efc34be4acbd1442a81daff2")

    assert region_services.check_region_in_config("test-region")

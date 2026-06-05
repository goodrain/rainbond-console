# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import group_service as group_service_module  # noqa: E402
from console.services.group_service import group_service  # noqa: E402
from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402


# capability_id: console.file-manage.selected-container-forwarding
def test_get_file_and_dir_forwards_selected_container_name():
    with mock.patch.object(group_service_module.region_api, "get_files", return_value={"list": []}) as get_files_mock:
        result = group_service.get_file_and_dir(
            "region-a",
            "team-a",
            "service-a",
            "/nas/book/45256补充",
            "pod-a",
            "grf987ca",
            "ns-a",
        )

    assert result == []
    get_files_mock.assert_called_once_with(
        "region-a",
        "team-a",
        "service-a",
        "/nas/book/45256%E8%A1%A5%E5%85%85",
        "pod-a",
        "grf987ca",
        "ns-a",
    )


# capability_id: console.file-manage.region-request-timeout
def test_region_api_get_files_uses_container_name_and_longer_timeout():
    client = RegionInvokeApi()

    with mock.patch.object(
            client, "_RegionInvokeApi__get_region_access_info", return_value=("http://region.example", "token")), \
            mock.patch.object(client, "_RegionInvokeApi__get_tenant_region_info",
                              return_value=type("TenantRegion", (), {"region_tenant_name": "tenant-region"})()), \
            mock.patch.object(client, "_set_headers") as set_headers_mock, \
            mock.patch.object(client, "_get", return_value=(200, {"list": []})) as get_mock:
        body = client.get_files(
            "region-a",
            "team-a",
            "service-a",
            "/nas/book/45256%E8%A1%A5%E5%85%85",
            "pod-a",
            "grf987ca",
            "ns-a",
        )

    assert body == {"list": []}
    set_headers_mock.assert_called_once_with("token")
    get_mock.assert_called_once()
    called_url = get_mock.call_args[0][0]
    assert "container_name=grf987ca" in called_url
    assert "path=/nas/book/45256%E8%A1%A5%E5%85%85" in called_url
    assert get_mock.call_args[1]["timeout"] == 30

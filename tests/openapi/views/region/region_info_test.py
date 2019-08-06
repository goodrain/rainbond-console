# -*- coding: utf-8 -*-
import pytest
from django.shortcuts import reverse

from tests.fixture.fixture import auth_setup
from tests.helper import get_client

_ = auth_setup


@pytest.mark.django_db
def test_region_info_delete_not_found(auth_setup):
    cli = get_client()
    res = cli.delete(reverse("region_info", kwargs={'region_id': 'foobar'}))
    assert res.status_code == 404
    assert res.data["msg"] == "修改的数据中心不存在"

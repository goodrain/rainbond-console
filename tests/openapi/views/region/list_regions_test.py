# -*- coding: utf-8 -*-
import pytest
from django.shortcuts import reverse
from django.test import Client


@pytest.fixture()
def custom_db_setup(db):
    from www.models.main import Users
    from console.models.main import EnterpriseUserPerm
    Users.objects.create(
        email="admin@goodrain.com",
        nick_name="gradmin",
        password="goodrain",
        phone="13800000000",
        enterprise_id="bb2f17abc58b328374351e9c92abd400")
    EnterpriseUserPerm.objects.create(
        user_id=1, enterprise_id="bb2f17abc58b328374351e9c92abd400", identity="admin", token="6923642f067b3cc8e4b7f2194cb25917")


@pytest.mark.django_db
def test_list_regions_get(custom_db_setup):
    cli = Client(HTTP_AUTHORIZATION='6923642f067b3cc8e4b7f2194cb25917')
    res = cli.get(reverse("list_regions"))
    assert res.status_code == 200
    assert len(res.data) == 2

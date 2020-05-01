import pytest
from django.test import Client
from django.urls import reverse

from console.models.main import EnterpriseUserPerm
from www.models.main import Users


@pytest.fixture(scope='function')
def setup_db(db):
    EnterpriseUserPerm.objects.create(
        user_id=1, enterprise_id="bb2f17abc58b328374351e9c92abd400", identity="admin", token="6923642f067b3cc8e4b7f2194cb25917")
    Users.objects.create(
        user_id=1,
        email="huangrh@goodrain.com",
        nick_name="gradmin",
        password="fcd5ffcabfb9bbc1",
        is_active=1,
        client_ip="192.168.195.4",
        status=0,
        enterprise_id="bb2f17abc58b328374351e9c92abd400")


@pytest.mark.django_db
def test_list_ent_info_GET(setup_db):
    from console.services.enterprise_services import enterprise_services
    enterprise_services.create_tenant_enterprise

    cli = Client(HTTP_AUTHORIZATION='6923642f067b3cc8e4b7f2194cb25917')
    res = cli.get(reverse("list_ent_info"))

    assert res.status_code == 200
    assert len(res.json()) == 0


@pytest.mark.django_db
def test_list_ent_info_GET_no_data(setup_db):

    cli = Client(HTTP_AUTHORIZATION='6923642f067b3cc8e4b7f2194cb25917')

    res = cli.get(reverse("list_ent_info"))

    assert res.status_code == 200
    assert len(res.json()) == 0

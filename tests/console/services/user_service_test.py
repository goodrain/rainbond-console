# -*- coding: utf8 -*-
import pytest

from console.exception.exceptions import EmailExistError
from console.exception.exceptions import PhoneExistError
from console.exception.exceptions import UserExistError
from www.models.main import Tenants
from www.models.main import Users


@pytest.mark.django_db
def test_create_tenant_not_exist():
    from console.services.user_services import user_services
    with pytest.raises(Tenants.DoesNotExist):
        user_services.create({})


@pytest.mark.django_db
def test_create_user_exits():
    from console.services.user_services import user_services
    Tenants.objects.create(tenant_id="dummy_tenant_id", tenant_name="dummy_tenant_name")
    Users.objects.create(
        nick_name="foobar",
        password="goodrain",
        email="huangrh@goodrain.com",
        phone="13800138000",
    )

    with pytest.raises(UserExistError):
        user_services.create({
            "tenant_id": "dummy_tenant_id",
            "nick_name": "foobar",
            "password": "goodrain",
        })
    with pytest.raises(EmailExistError):
        user_services.create({
            "tenant_id": "dummy_tenant_id",
            "nick_name": "email",
            "password": "goodrain",
            "email": "huangrh@goodrain.com",
        })
    with pytest.raises(PhoneExistError):
        user_services.create({
            "tenant_id": "dummy_tenant_id",
            "nick_name": "phone",
            "password": "goodrain",
            "phone": "13800138000",
        })

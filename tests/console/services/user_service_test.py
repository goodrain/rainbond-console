# -*- coding: utf8 -*-
import pytest


@pytest.mark.django_db
def test_create_tenant_not_exist():
    from console.services.user_services import user_services
    from www.models.main import Tenants

    with pytest.raises(Tenants.DoesNotExist):
        user_services.create({})

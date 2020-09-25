# -*- coding: utf-8 -*-
import pytest


@pytest.fixture()
def auth_setup(db):
    """
    Set the data required for authentication
    """
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

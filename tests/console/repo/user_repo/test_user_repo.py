# -*- coding: utf-8 -*-
import pytest


@pytest.mark.django_db
def test_list_users_by_tenant_id():
    from console.services.user_services import user_services
    from console.repositories.team_repo import team_repo
    from console.repositories.perm_repo import perms_repo
    from console.repositories.user_repo import user_repo

    eid = "bb2f17abc58b328374351e9c92abd400"
    tenant_id = "374351e9c92abd400bb2f17abc58b328"

    params = {
        "tenant_id": tenant_id,
        "tenant_name": "xxxxxxxx",
        "creater": 1,
        "tenant_alias": "foobar team",
        "enterprise_id": eid,
    }
    team = team_repo.create_tenant(**params)

    userinfo = [{
        "nick_name": "foo",
        "email": "foo@goodrain.com",
        "password": "goodrain",
        "eid": eid
    }, {
        "nick_name": "bar",
        "email": "bar@goodrain.com",
        "password": "goodrain",
        "eid": eid
    }, {
        "nick_name": "dummy",
        "email": "dummy@goodrain.com",
        "password": "goodrain",
        "eid": eid
    }]
    for item in userinfo:
        user = user_services.create(item)
        perminfo = {"user_id": user.user_id, "tenant_id": team.ID, "identity": "owner", "enterprise_id": 1}
        perms_repo.add_user_tenant_perm(perminfo)

    testcases = [
        {
            "tenant_id": tenant_id,
            "query": "",
            "page": None,
            "size": None,
            "count": 3,
            "user_id": 1
        },
        {
            "tenant_id": tenant_id,
            "query": "bar",
            "page": None,
            "size": None,
            "count": 1,
            "user_id": 2
        },
        {
            "tenant_id": tenant_id,
            "query": "foo@goodrain.com",
            "page": None,
            "size": None,
            "count": 1,
            "user_id": 1
        },
        {
            "tenant_id": tenant_id,
            "query": "",
            "page": 2,
            "size": 2,
            "count": 1,
            "user_id": 3
        },
        {
            "tenant_id": tenant_id,
            "query": "nothing",
            "page": None,
            "size": None,
            "count": 0,
            "user_id": 0
        },
        {
            "tenant_id": tenant_id,
            "query": "",
            "page": -1,
            "size": None,
            "count": 3,
            "user_id": 1
        },
    ]

    for tc in testcases:
        result = user_repo.list_users_by_tenant_id(tc["tenant_id"], tc["query"], tc["page"], tc["size"])
        print(result)
        assert len(result) == tc["count"]
        if len(result) > 0:
            assert result[0].get("user_id") == tc["user_id"]

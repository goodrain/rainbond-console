# -*- coding: utf-8 -*-
import pytest

from console.models.main import ServiceSourceInfo
from www.models import ServiceGroupRelation
from www.models import TenantServiceInfo


@pytest.mark.django_db
def test_list_by_svc_share_uuids():
    tenant_id = "6d1c06e1d9e84d57aeb42ea80d49018a"
    service_id = "560ca84003254737a426d0bd5f513afd"
    service_cname = "WordPress"
    group_id = 20
    service = TenantServiceInfo()
    service.tenant_id = tenant_id
    service.service_id = service_id
    service.service_cname = service_cname
    service.save()

    service_source = ServiceSourceInfo()
    service_source.team_id = tenant_id
    service_source.service_id = service_id
    service_source.service_share_uuid = "2669c2cec6bc7bf5aab29a0ea2703d66"
    service_source.save()

    group_relation = ServiceGroupRelation()
    group_relation.service_id = service_id
    group_relation.group_id = group_id
    group_relation.save()

    from console.repositories.service_repo import service_repo
    uuids = "'{}'".format("','".join(str(uuid) for uuid in ["2669c2cec6bc7bf5aab29a0ea2703d66"]))
    result = service_repo.list_by_svc_share_uuids(
        group_id, uuids)
    service = result[0]
    assert service.get("service_id") == service_id
    assert service.get("service_cname") == service_cname

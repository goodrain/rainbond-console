# -*- coding: utf8 -*-

from www.db import svc_grop_repo as svc_group_repo


class ServiceGroupService:
    def __init__(self):
        pass

    def has_created_app(self, tenants):
        for tenant in tenants:
            if svc_group_repo.count_non_default_group_by_tenant(tenant) > 0:
                return True
        return False


service_group_service = ServiceGroupService()

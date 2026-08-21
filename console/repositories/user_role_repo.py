# -*- coding: utf-8 -*-
from typing import Any, Optional

from console.repositories.exceptions import UserRoleNotFoundException
from console.models.main import TenantUserRole
from www.models.main import PermRelTenant, Tenants


class UserRoleRepo(object):
    def get_role_names(self, user_id: str, tenant_id: str) -> Any:
        tenant = Tenants.objects.filter(tenant_id=tenant_id).only("ID").first()
        if tenant is None:
            raise UserRoleNotFoundException("tenant_id: {tenant_id}; user_id: {user_id}; user role not found".format(
                tenant_id=tenant_id, user_id=user_id))

        role_ids = PermRelTenant.objects.filter(
            user_id=user_id, tenant_id=tenant.ID, role_id__isnull=False).values_list("role_id", flat=True)
        role_names = list(TenantUserRole.objects.filter(ID__in=role_ids).order_by("ID").values_list("role_name", flat=True))
        if not role_names:
            raise UserRoleNotFoundException("tenant_id: {tenant_id}; user_id: {user_id}; user role not found".format(
                tenant_id=tenant_id, user_id=user_id))
        return ",".join(role_names)

    def get_viewer_role(self) -> Optional[TenantUserRole]:
        re = TenantUserRole.objects.filter(role_name="viewer")
        if re:
            return re[0]
        return None


user_role_repo = UserRoleRepo()

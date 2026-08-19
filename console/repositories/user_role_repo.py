# -*- coding: utf-8 -*-
from typing import Any, Optional

from console.repositories.base import BaseConnection
from console.repositories.exceptions import UserRoleNotFoundException
from console.models.main import TenantUserRole
from console.utils.database import database_type, list_aggregate


class UserRoleRepo(object):
    def get_role_names(self, user_id: str, tenant_id: str) -> Any:
        role_names = list_aggregate("b.role_name", database_type(), order_by="b.role_name")
        sql = """
        SELECT
            {role_names} AS role_names
        FROM
            tenant_perms a,
            tenant_user_role b,
            tenant_info c
        WHERE
            a.role_id = b.ID
            AND a.tenant_id = c.ID
            AND a.user_id = %s
            AND c.tenant_id = %s""".format(role_names=role_names)
        conn = BaseConnection()
        result = conn.query(sql, [user_id, tenant_id])
        if len(result) == 0 or result[0].get("role_names") is None:
            raise UserRoleNotFoundException("tenant_id: {tenant_id}; user_id: {user_id}; user role not found".format(
                tenant_id=tenant_id, user_id=user_id))
        return result[0].get("role_names")

    def get_viewer_role(self) -> Optional[TenantUserRole]:
        re = TenantUserRole.objects.filter(role_name="viewer")
        if re:
            return re[0]
        return None


user_role_repo = UserRoleRepo()

# -*- coding: utf-8 -*-
from console.repositories.base import BaseConnection
from console.repositories.exceptions import UserRoleNotFoundException
from console.models.main import TenantUserRole


class UserRoleRepo(object):
    def get_role_names(self, user_id, tenant_id):
        sql = """
        SELECT
            group_concat( b.role_name ) AS role_names
        FROM
            tenant_perms a,
            tenant_user_role b,
            tenant_info c
        WHERE
            a.role_id = b.ID
            AND a.tenant_id = c.ID
            AND a.user_id = {user_id}
            AND c.tenant_id = '{tenant_id}'""".format(user_id=user_id, tenant_id=tenant_id)
        conn = BaseConnection()
        result = conn.query(sql)
        if len(result) == 0 or result[0].get("role_names") is None:
            raise UserRoleNotFoundException(
                "tenant_id: {tenant_id}; user_id: {user_id}; user role not found".format(
                    tenant_id=tenant_id, user_id=user_id))
        return result[0].get("role_names")

    def get_viewer_role(self):
        re = TenantUserRole.objects.filter(role_name="viewer")
        if re:
            return re[0]
        return None


user_role_repo = UserRoleRepo()

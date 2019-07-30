# -*- coding: utf-8 -*-
from console.repositories.base import BaseConnection


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
        if len(result) == 0:
            return None
        return result[0].get("role_names")


user_role_repo = UserRoleRepo()

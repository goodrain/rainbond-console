# -*- coding: utf-8 -*-
from console.repositories.user_repo import user_repo
from console.repositories.perm_repo import service_perm_repo, perms_repo, role_perm_repo, role_repo
from console.repositories.enterprise_repo import enterprise_repo
import logging

logger = logging.getLogger("default")


class PermService(object):
    def add_user_tenant_perm(self, perm_info):
        return perms_repo.add_user_tenant_perm(perm_info=perm_info)

    def get_user_tenant_perm(self, tenant_pk, user_id):
        return perms_repo.get_user_tenant_perm(tenant_pk, user_id)


class ServicePermService(object):
    def add_service_perm(self, current_user, user_id, tenant, service, identity):
        if current_user.user_id == user_id:
            return 409, u"不能给自己添加应用权限", None
        user = user_repo.get_user_by_user_id(user_id)
        if not user:
            return 404, "用户{0}不存在".format(user_id), None
        service_perm = service_perm_repo.get_service_perm_by_user_pk(service.ID, user_id)
        if service_perm:
            return 409, "用户{0}已有权限，无需添加".format(user.nick_name), None
        service_perm = service_perm_repo.add_service_perm(user_id, service.ID, identity)
        perm_tenant = perms_repo.get_user_tenant_perm(tenant.ID, user_id)
        enterprise = None
        try:
            enterprise = enterprise_repo.get_enterprise_by_enterprise_id(tenant.enterprise_id)
        except Exception as e:
            pass
        if not perm_tenant:
            perm_info = {
                "user_id": user.user_id,
                "tenant_id": tenant.ID,
                "identity": "access",
                "enterprise_id": enterprise.ID if enterprise else 0
            }
            perm_tenant = perms_repo.add_user_tenant_perm(perm_info)
        logger.debug("service_perm {0} , perm_tenant {1}".format(service_perm, perm_tenant))
        return 200, "已向用户{0}授权".format(user.nick_name), service_perm

    def get_service_perm(self, service):
        service_perms = service_perm_repo.get_service_perms(service.ID)
        perm_list = []
        for service_perm in service_perms:
            perm = {}
            u = user_repo.get_by_user_id(service_perm.user_id)
            perm["user_id"] = service_perm.user_id
            perm["identity"] = service_perm.identity
            perm["nick_name"] = u.nick_name
            perm["email"] = u.email
            perm_list.append(perm)
        return perm_list

    def update_service_perm(self, current_user, user_id, service, identity):
        if current_user.user_id == user_id:
            return 409, u"您不能修改自己的权限", None
        service_perm = service_perm_repo.get_service_perm_by_user_pk(service.ID, user_id)
        if not service_perm:
            return 404, u"需要修改的权限不存在", None
        service_perm.identity = identity
        service_perm.save()
        return 200, u"success", service_perm

    def delete_service_perm(self, current_user, user_id, service):
        if current_user.user_id == user_id:
            return 409, u"您不能删除自己的权限"
        service_perm = service_perm_repo.get_service_perm_by_user_pk(service.ID, user_id)
        if not service_perm:
            return 404, u"需要删除的权限不存在"
        service_perm.delete()
        return 200, u"success"

    def get_user_service_perm(self, user_id, service_pk):
        service_perm_repo.get_service_perm_by_user_pk(service_pk, user_id)

    def add_user_service_perm(self, current_user, user_list, tenant, service, perm_list):
        """添加用户在一个应用中的权限"""
        if current_user.user_id in user_list:
            return 409, u"不能给自己添加应用权限", None
        for user_id in user_list:
            user = user_repo.get_user_by_user_id(user_id)
            if not user:
                return 404, "用户{0}不存在".format(user_id), None

            service_perm = service_perm_repo.get_service_perm_by_user_pk_service_pk(service_pk=service.ID,
                                                                                    user_pk=user_id)
            if service_perm:
                return 409, "用户{0}已有权限，无需添加".format(user.nick_name), None

        service_perm_repo.add_user_service_perm(user_ids=user_list, service_pk=service.ID,
                                                perm_ids=perm_list)

        enterprise = None
        try:
            enterprise = enterprise_repo.get_enterprise_by_enterprise_id(tenant.enterprise_id)
        except Exception as e:
            pass

        for user_id in user_list:
            perm_tenant = perms_repo.get_user_tenant_perm(tenant.ID, user_id)

            if not perm_tenant:
                perm_info = {
                    "user_id": user_id,
                    "tenant_id": tenant.ID,
                    "role_id": role_repo.get_role_id_by_role_name("viewer"),
                    "enterprise_id": enterprise.ID if enterprise else 0
                }
                perm_tenant = perms_repo.add_user_tenant_perm(perm_info)

        return 200, "添加用户应用权限成功", None

    def delete_user_service_perm(self, current_user, user_id, service):
        if current_user.user_id == user_id:
            return 409, u"您不能删除自己的权限"
        service_perm = service_perm_repo.get_service_perm_by_service_pk_user_pk(service.ID, user_id)
        if not service_perm:
            return 404, u"需要删除的权限不存在"
        service_perm.delete()
        return 200, u"success"

    def update_user_service_perm(self, current_user, user_id, service, perm_list):
        if current_user.user_id == user_id:
            return 409, u"您不能修改自己的权限", None
        service_perm = service_perm_repo.get_service_perm_by_service_pk_user_pk(service.ID, user_id)
        if not service_perm:
            return 404, u"需要修改的权限不存在", None
        service_perm_repo.update_service_perm_by_service_id_user_id_perm_list(user_id=user_id, service_id=service.ID,
                                                                              perm_list=perm_list)
        return 200, u"success", service_perm

    def get_user_service_perm_info(self, service):
        """获取应用下的成员及对应的权限"""
        user_id_list = service_perm_repo.get_user_id_in_service(service.ID)
        user_id_list = list(set(user_id_list))
        perm_list = []

        for user_id in user_id_list:
            user_obj = user_repo.get_by_user_id(user_id)
            if not user_obj:
                continue
            user_info = {}
            user_perm_list = []

            perm_id_list = service_perm_repo.get_perms_by_user_id_service_id(user_id=user_id, service_id=service.ID)

            for perm_id in perm_id_list:
                perm_obj = role_perm_repo.get_perm_obj_by_perm_id(perm_id=perm_id)
                if not perm_obj:
                    continue
                perm_info = {}
                perm_info["id"] = perm_obj.ID
                perm_info["codename"] = perm_obj.codename
                perm_info["perm_info"] = perm_obj.per_info

                user_perm_list.append(perm_info)

            user_info["user_id"] = user_obj.user_id
            user_info["nick_name"] = user_obj.nick_name
            user_info["email"] = user_obj.email
            user_info["service_perms"] = user_perm_list
            perm_list.append(user_info)
        return perm_list


perm_services = PermService()
app_perm_service = ServicePermService()

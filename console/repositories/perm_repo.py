# -*- coding: utf-8 -*-
from www.models import PermRelTenant, PermRelService
from django.db import transaction
from django.db.models import Q
from console.models.main import TenantUserRole, TenantUserPermission, TenantUserRolePermission, PermGroup, \
    ServiceRelPerms
from console.repositories.team_repo import team_repo
from www.models import Tenants


class PermsRepo(object):
    def add_user_tenant_perm(self, perm_info):
        perm_re_tenant = PermRelTenant(**perm_info)
        perm_re_tenant.save()
        return perm_re_tenant

    def get_user_tenant_perm(self, tenant_pk, user_pk):
        """
        获取用户在某个团队下的权限
        """
        prts = PermRelTenant.objects.filter(tenant_id=tenant_pk, user_id=user_pk)
        if prts:
            return prts[0]
        return None


class ServicePermRepo(object):
    def get_service_perm_by_user_pk(self, service_pk, user_pk):
        try:
            return PermRelService.objects.get(user_id=user_pk, service_id=service_pk)
        except PermRelService.DoesNotExist:
            return None

    def get_service_perms(self, service_pk):
        return PermRelService.objects.filter(service_id=service_pk)

    def add_service_perm(self, user_id, service_pk, identity):
        return PermRelService.objects.create(user_id=user_id, service_id=service_pk, identity=identity)

    def get_user_id_in_service(self, service_pk):
        return ServiceRelPerms.objects.filter(service_id=service_pk).values_list("user_id", flat=True)

    def get_service_perm_by_user_pk_service_pk(self, service_pk, user_pk):
        """判断一个用户在一个应用中有没有权限"""

        query = ServiceRelPerms.objects.filter(user_id=user_pk, service_id=service_pk)
        if not query:
            return None
        return query

    def add_user_service_perm(self, user_ids, service_pk, perm_ids):
        """添加用户应用权限"""
        with transaction.atomic():
            for user_id in user_ids:
                for perm_id in perm_ids:
                    ServiceRelPerms.objects.create(user_id=user_id, service_id=service_pk, perm_id=perm_id)

    def get_service_perm_by_service_pk_user_pk(self, service_pk, user_pk):
        """判断一个用户在一个应用中是否存在权限"""

        service_perm = ServiceRelPerms.objects.filter(user_id=user_pk, service_id=service_pk)
        if not service_perm:
            return None
        return service_perm

    def update_service_perm_by_service_id_user_id_perm_list(self, user_id, service_id, perm_list):
        """更新用户在一个应用中的权限"""
        with transaction.atomic():
            ServiceRelPerms.objects.filter(user_id=user_id, service_id=service_id).delete()
            for perm_id in perm_list:
                ServiceRelPerms.objects.create(user_id=user_id, service_id=service_id, perm_id=perm_id)

    def get_perms_by_user_id_service_id(self, user_id, service_id):
        """获取一个用户在一个团队中的权限id列表"""
        return ServiceRelPerms.objects.filter(user_id=user_id, service_id=service_id).values_list("perm_id", flat=True)


class RoleRepo(object):
    def get_default_role_by_role_name(self, role_name, is_default=True):
        return TenantUserRole.objects.get(role_name=role_name, is_default=is_default)

    def get_tenant_role_by_tenant_id(self, tenant_id):
        """获取一个团队中的所有角色和角色对应的权限信息"""
        default_role_list = []
        team_role_list = []

        default_role_queryset = TenantUserRole.objects.filter(Q(is_default=True) & ~Q(role_name="owner"))
        for role_obj in default_role_queryset:
            role_dict = {}
            default_role_perm_list = []

            per_id_list = TenantUserRolePermission.objects.filter(role_id=role_obj.pk).values_list("per_id", flat=True)
            for perm_obj in TenantUserPermission.objects.filter(ID__in=per_id_list):
                perm_dict = {}
                perm_dict["perm_id"] = perm_obj.pk
                perm_dict["codename"] = perm_obj.codename
                perm_dict["perm_info"] = perm_obj.per_info
                perm_dict["is_select"] = perm_obj.is_select
                perm_dict["group_id"] = perm_obj.group
                if perm_obj.group:
                    perm_dict["group_name"] = PermGroup.objects.get(ID=perm_obj.group).group_name
                else:
                    perm_dict["group_name"] = None
                default_role_perm_list.append(perm_dict)
            role_dict["role_id"] = role_obj.pk
            role_dict["role_name"] = role_obj.role_name
            role_dict["is_default"] = role_obj.is_default
            role_dict["role_perm"] = default_role_perm_list
            default_role_list.append(role_dict)

        team_role_queryset = TenantUserRole.objects.filter(tenant_id=tenant_id, is_default=False)
        for role_obj in team_role_queryset:
            role_dict = {}
            team_role_perm_list = []
            per_id_list = TenantUserRolePermission.objects.filter(role_id=role_obj.pk).values_list("per_id", flat=True)
            for perm_obj in TenantUserPermission.objects.filter(ID__in=per_id_list):
                perm_dict = {}
                perm_dict["perm_id"] = perm_obj.pk
                perm_dict["codename"] = perm_obj.codename
                perm_dict["perm_info"] = perm_obj.per_info
                perm_dict["is_select"] = perm_obj.is_select
                perm_dict["group_id"] = perm_obj.group
                if perm_obj.group:
                    perm_dict["group_name"] = PermGroup.objects.get(ID=perm_obj.group).group_name
                else:
                    perm_dict["group_name"] = None
                team_role_perm_list.append(perm_dict)
            role_dict["role_id"] = role_obj.pk
            role_dict["role_name"] = role_obj.role_name
            role_dict["is_default"] = role_obj.is_default
            role_dict["role_perm"] = team_role_perm_list
            team_role_list.append(role_dict)

        return default_role_list + team_role_list

    def get_default_role(self):
        """获取默认的角色"""
        return TenantUserRole.objects.filter(is_default=True).values_list("role_name", flat=True)

    def get_default_role_id(self):
        """获取默认的角色ID"""
        return TenantUserRole.objects.filter(is_default=True).values_list("pk", flat=True)

    def team_role_is_exist_by_role_name_team_id(self, tenant_name, role_id):
        """判断一个角色在一个团队中是否存在"""

        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        if not tenant:
            raise Tenants.DoesNotExist

        role_obj = TenantUserRole.objects.filter(tenant_id=tenant.pk, ID=role_id)

        return role_obj

    def team_role_is_exist_by_role_name_team_id_2(self, tenant_name, role_name):
        """判断一个角色在一个团队中是否存在"""

        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        if not tenant:
            raise Tenants.DoesNotExist

        role_obj = TenantUserRole.objects.filter(tenant_id=tenant.pk, role_name=role_name)

        return role_obj

    def team_user_is_exist_by_role_id_tenant_name(self, role_id, tenant_name):
        """判断团队中一个角色是否有绑定的人"""
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        if not tenant:
            raise Tenants.DoesNotExist
        return PermRelTenant.objects.filter(tenant_id=tenant.ID, role_id=role_id)

    def get_role_name_by_role_id(self, role_id):
        """获取角色名称"""
        return TenantUserRole.objects.get(pk=role_id).role_name

    def get_role_id_by_role_name(self, role_name):
        """获取角色ID"""
        role_query = TenantUserRole.objects.filter(role_name=role_name)
        if role_query:
            return role_query[0].pk
        else:
            return None

    def add_role_by_tenant_pk_perm_list(self, role_name, tenant_pk, perm_id_list):
        """创建一个角色"""
        with transaction.atomic():
            role_obj = TenantUserRole.objects.create(role_name=role_name, tenant_id=tenant_pk, is_default=False)
            for perm_id in perm_id_list:
                TenantUserRolePermission.objects.create(role_id=role_obj.pk, per_id=perm_id)
        return role_obj

    def del_role_by_team_pk_role_name_role_id(self, tenant_pk, role_id):
        """删除一个角色"""
        with transaction.atomic():
            TenantUserRole.objects.get(tenant_id=tenant_pk, ID=role_id, is_default=False).delete()
            TenantUserRolePermission.objects.filter(role_id=role_id).delete()

    def update_role_by_team_name_role_name_perm_list(self, tenant_pk,
                                                     role_id,
                                                     new_role_name,
                                                     perm_id_list):
        """更新一个自定义角色的权限"""
        with transaction.atomic():
            role_obj = TenantUserRole.objects.filter(ID=role_id, tenant_id=tenant_pk,
                                                     is_default=False).update(role_name=new_role_name)
            TenantUserRolePermission.objects.filter(role_id=role_id).delete()
            for perm_id in perm_id_list:
                TenantUserRolePermission.objects.create(role_id=role_id, per_id=perm_id)
        if role_obj:

            return TenantUserRole.objects.get(ID=role_id, role_name=new_role_name, tenant_id=tenant_pk,
                                              is_default=False)
        else:
            return None

    def update_user_role_in_tenant_by_user_id_tenant_id_role_id(self, user_id, tenant_id, role_id_list, enterprise_id):
        """修改一个用户在一个团队中的角色"""
        with transaction.atomic():
            PermRelTenant.objects.filter(user_id=user_id, tenant_id=tenant_id, enterprise_id=enterprise_id).delete()
            for role_id in role_id_list:
                PermRelTenant.objects.create(user_id=user_id, tenant_id=tenant_id, enterprise_id=enterprise_id,
                                             role_id=role_id)


class RolePermRepo(object):
    def get_perm_by_role_id(self, role_id):
        perm_id_list = TenantUserRolePermission.objects.filter(role_id=role_id).values_list("per_id", flat=True)
        perm_codename_list = TenantUserPermission.objects.filter(ID__in=perm_id_list).values_list("codename", flat=True)
        return tuple(perm_codename_list)

    def get_permission_options(self):
        """获取可选项"""
        options_list = list()
        outher_options_dict = dict()

        perm_group_obj = PermGroup.objects.all()
        for group in perm_group_obj:
            perm_list = []
            options_dict = dict()
            perm_options_query = TenantUserPermission.objects.filter(is_select=True, group=group.pk)
            for obj in perm_options_query:
                perm_list.append(
                    {"id": obj.pk, "codename": obj.codename, "info": obj.per_info}
                )
            options_dict["group_name"] = group.group_name
            options_dict["perms_info"] = perm_list
            options_list.append(options_dict)
        outher_perm_options_query = TenantUserPermission.objects.filter(is_select=True, group__isnull=True)

        outher_perm_list = []

        for obj in outher_perm_options_query:
            outher_perm_list.append(
                {"id": obj.pk, "codename": obj.codename, "info": obj.per_info}
            )
        outher_options_dict["group_name"] = "其他"
        outher_options_dict["perms_info"] = outher_perm_list
        options_list.append(outher_options_dict)

        return options_list

    def get_select_perm_list(self):
        """获取可以选择的权限列表"""
        select_perm_list = TenantUserPermission.objects.filter(is_select=True).values_list("pk", flat=True)
        return list(select_perm_list)

    def get_perm_list_by_perm_id_list(self, perm_id_list):
        perm_query = TenantUserPermission.objects.filter(ID__in=perm_id_list)
        return [perm_obj.codename for perm_obj in perm_query]

    def get_perm_obj_by_perm_id(self, perm_id):

        if TenantUserPermission.objects.filter(ID=perm_id):
            return TenantUserPermission.objects.filter(ID=perm_id)[0]
        else:
            return None

    @transaction.atomic
    def initialize_permission_settings(self):
        """判断有没有初始化权限数据，没有则初始化"""
        try:
            role_dict = dict()
            group_dict = dict()
            perms_dict = dict()

            owner_exists = TenantUserRole.objects.filter(is_default=True, role_name="owner", tenant_id=None).exists()
            admin_exists = TenantUserRole.objects.filter(is_default=True, role_name="admin", tenant_id=None).exists()
            developer_exists = TenantUserRole.objects.filter(is_default=True, role_name="developer",
                                                             tenant_id=None).exists()
            if owner_exists or admin_exists or developer_exists:
                return "已经初始化过了"
            # 初始化角色数据
            if not TenantUserRole.objects.filter(is_default=True, role_name="owner", tenant_id=None).exists():
                owner_obj = TenantUserRole.objects.create(role_name="owner", is_default=True)
                role_dict["owner"] = owner_obj.pk
            else:
                owner_obj = TenantUserRole.objects.get(is_default=True, role_name="owner", tenant_id=None)
                role_dict["owner"] = owner_obj.pk

            if not TenantUserRole.objects.filter(is_default=True, role_name="admin", tenant_id=None).exists():
                admin_obj = TenantUserRole.objects.create(role_name="admin", is_default=True)
                role_dict["admin"] = admin_obj.pk
            else:
                admin_obj = TenantUserRole.objects.get(is_default=True, role_name="admin", tenant_id=None)
                role_dict["admin"] = admin_obj.pk
            if not TenantUserRole.objects.filter(is_default=True, role_name="developer", tenant_id=None).exists():

                developer_obj = TenantUserRole.objects.create(role_name="developer", is_default=True)
                role_dict["developer"] = developer_obj.pk
            else:
                developer_obj = TenantUserRole.objects.get(is_default=True, role_name="developer", tenant_id=None)
                role_dict["developer"] = developer_obj.pk
            if not TenantUserRole.objects.filter(is_default=True, role_name="viewer", tenant_id=None).exists():
                viewer_obj = TenantUserRole.objects.create(role_name="viewer", is_default=True)
                role_dict["viewer"] = viewer_obj.pk
            else:
                viewer_obj = TenantUserRole.objects.get(is_default=True, role_name="viewer", tenant_id=None)
                role_dict["viewer"] = viewer_obj.pk
            # 初始化权限组数据
            if not PermGroup.objects.filter(group_name="团队相关").exists():
                group_obj = PermGroup.objects.create(group_name="团队相关")
                group_dict["团队相关"] = group_obj.pk
            else:
                group_obj = PermGroup.objects.get(group_name="团队相关")
                group_dict["团队相关"] = group_obj.pk
            if not PermGroup.objects.filter(group_name="应用相关").exists():
                service_group_obj = PermGroup.objects.create(group_name="应用相关")
                group_dict["应用相关"] = service_group_obj.pk
            else:
                service_group_obj = PermGroup.objects.get(group_name="应用相关")
                group_dict["应用相关"] = service_group_obj.pk
            # 初始化权限数据
            team_group = group_dict.get("团队相关")
            service_group = group_dict.get("应用相关")

            obj = TenantUserPermission.objects.create(codename="tenant_access", per_info="登入团队", is_select=True,
                                                      group=team_group)
            perms_dict["tenant_access"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="manage_team_member_permissions", per_info="团队权限设置",
                                                      is_select=True,
                                                      group=team_group)
            perms_dict["manage_team_member_permissions"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="tenant_open_region", per_info="开通数据中心", is_select=True,
                                                      group=team_group)
            perms_dict["tenant_open_region"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="manage_group", per_info="应用组管理", is_select=True,
                                                      group=service_group)
            perms_dict["manage_group"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="view_service", per_info="查看应用信息", is_select=True,
                                                      group=service_group)
            perms_dict["view_service"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="deploy_service", per_info="部署应用", is_select=True,
                                                      group=service_group)
            perms_dict["deploy_service"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="create_service", per_info="创建应用", is_select=True,
                                                      group=service_group)
            perms_dict["create_service"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="delete_service", per_info="删除应用", is_select=True,
                                                      group=service_group)
            perms_dict["delete_service"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="share_service", per_info="应用组分享", is_select=True,
                                                      group=service_group)
            perms_dict["share_service"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="stop_service", per_info="关闭应用", is_select=True,
                                                      group=service_group)
            perms_dict["stop_service"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="start_service", per_info="启动应用", is_select=True,
                                                      group=service_group)
            perms_dict["start_service"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="restart_service", per_info="重启应用", is_select=True,
                                                      group=service_group)
            perms_dict["restart_service"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="rollback_service", per_info="回滚应用", is_select=True,
                                                      group=service_group)
            perms_dict["rollback_service"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="manage_service_container", per_info="应用容器管理",
                                                      is_select=True,
                                                      group=service_group)
            perms_dict["manage_service_container"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="manage_service_extend", per_info="应用伸缩管理",
                                                      is_select=True,
                                                      group=service_group)
            perms_dict["manage_service_extend"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="manage_service_config", per_info="应用配置管理",
                                                      is_select=True,
                                                      group=service_group)
            perms_dict["manage_service_config"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="manage_service_plugin", per_info="应用扩展管理",
                                                      is_select=True,
                                                      group=service_group)
            perms_dict["manage_service_plugin"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="manage_service_member_perms", per_info="应用权限设置",
                                                      is_select=True,
                                                      group=service_group)
            perms_dict["manage_service_member_perms"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="view_plugin", per_info="查看插件信息",
                                                      is_select=True,
                                                      group=team_group)
            perms_dict["view_plugin"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="manage_plugin", per_info="插件管理",
                                                      is_select=True,
                                                      group=team_group)
            perms_dict["manage_plugin"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="drop_tenant", per_info="删除团队",
                                                      is_select=False,
                                                      group=team_group)
            perms_dict["drop_tenant"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="transfer_ownership", per_info="移交所有权",
                                                      is_select=False,
                                                      group=team_group)
            perms_dict["transfer_ownership"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="modify_team_name", per_info="修改团队名称",
                                                      is_select=False,
                                                      group=team_group)
            perms_dict["modify_team_name"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="tenant_manage_role", per_info="自定义角色",
                                                      is_select=False,
                                                      group=team_group)
            perms_dict["tenant_manage_role"] = obj.pk

            obj = TenantUserPermission.objects.create(codename="import_and_export_service", per_info="应用导入导出",
                                                      is_select=True,
                                                      group=team_group)
            perms_dict["import_and_export_service"] = obj.pk
            # 初始化角色与权限对应关系
            owner_id = role_dict.get("owner")
            admin_id = role_dict.get("admin")
            developer_id = role_dict.get("developer")
            viewer_id = role_dict.get("viewer")
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("tenant_access"))
            TenantUserRolePermission.objects.create(role_id=owner_id,
                                                    per_id=perms_dict.get("manage_team_member_permissions"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("tenant_open_region"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("manage_group"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("view_service"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("deploy_service"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("create_service"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("delete_service"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("share_service"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("stop_service"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("start_service"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("restart_service"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("rollback_service"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("manage_service_container"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("manage_service_extend"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("manage_service_config"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("manage_service_plugin"))
            TenantUserRolePermission.objects.create(role_id=owner_id,
                                                    per_id=perms_dict.get("manage_service_member_perms"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("view_plugin"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("manage_plugin"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("drop_tenant"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("transfer_ownership"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("modify_team_name"))
            TenantUserRolePermission.objects.create(role_id=owner_id, per_id=perms_dict.get("tenant_manage_role"))
            TenantUserRolePermission.objects.create(role_id=owner_id,
                                                    per_id=perms_dict.get("import_and_export_service"))

            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("tenant_access"))
            TenantUserRolePermission.objects.create(role_id=admin_id,
                                                    per_id=perms_dict.get("manage_team_member_permissions"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("tenant_open_region"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("manage_group"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("view_service"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("deploy_service"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("create_service"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("delete_service"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("share_service"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("stop_service"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("start_service"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("restart_service"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("rollback_service"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("manage_service_container"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("manage_service_extend"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("manage_service_config"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("manage_service_plugin"))
            TenantUserRolePermission.objects.create(role_id=admin_id,
                                                    per_id=perms_dict.get("manage_service_member_perms"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("view_plugin"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("manage_plugin"))
            TenantUserRolePermission.objects.create(role_id=admin_id, per_id=perms_dict.get("tenant_manage_role"))
            TenantUserRolePermission.objects.create(role_id=admin_id,
                                                    per_id=perms_dict.get("import_and_export_service"))

            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("tenant_access"))
            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("manage_group"))
            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("view_service"))
            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("deploy_service"))
            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("create_service"))
            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("stop_service"))
            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("start_service"))
            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("restart_service"))
            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("rollback_service"))
            TenantUserRolePermission.objects.create(role_id=developer_id,
                                                    per_id=perms_dict.get("manage_service_container"))
            TenantUserRolePermission.objects.create(role_id=developer_id,
                                                    per_id=perms_dict.get("manage_service_extend"))
            TenantUserRolePermission.objects.create(role_id=developer_id,
                                                    per_id=perms_dict.get("manage_service_config"))
            TenantUserRolePermission.objects.create(role_id=developer_id,
                                                    per_id=perms_dict.get("manage_service_plugin"))
            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("view_plugin"))
            TenantUserRolePermission.objects.create(role_id=developer_id, per_id=perms_dict.get("manage_plugin"))
            TenantUserRolePermission.objects.create(role_id=developer_id,
                                                    per_id=perms_dict.get("import_and_export_service"))

            TenantUserRolePermission.objects.create(role_id=viewer_id, per_id=perms_dict.get("tenant_access"))
            TenantUserRolePermission.objects.create(role_id=viewer_id, per_id=perms_dict.get("view_service"))
            TenantUserRolePermission.objects.create(role_id=viewer_id, per_id=perms_dict.get("view_plugin"))
            return "初始化成功"
        except Exception as e:
            raise Exception("初始化权限数据错误:{}".format(e.message))


perms_repo = PermsRepo()
service_perm_repo = ServicePermRepo()
role_repo = RoleRepo()
role_perm_repo = RolePermRepo()

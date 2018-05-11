# -*- coding: utf-8 -*-
import logging

from django.db.models import Q
from fuzzyfinder.main import fuzzyfinder

from backends.services.exceptions import AccountNotExistError
from backends.services.exceptions import UserExistError, TenantNotExistError, UserNotExistError
from backends.services.tenantservice import tenant_service as tenantService, EmailExistError, PhoneExistError, \
    PasswordTooShortError
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from www.gitlab_http import GitlabApi
from www.models import Tenants, Users, PermRelTenant
from www.tenantservice.baseservice import CodeRepositoriesService
from console.repositories.enterprise_repo import enterprise_user_perm_repo

logger = logging.getLogger("default")
codeRepositoriesService = CodeRepositoriesService()
gitClient = GitlabApi()


class UserService(object):
    def get_user_by_user_name(self, user_name):
        user = user_repo.get_user_by_username(user_name=user_name)
        if not user:
            return None
        else:
            return user

    def check_user_password(self, user_id, password):
        u = user_repo.get_user_by_user_id(user_id=user_id)
        if u:
            return u.check_password(password)
        else:
            raise AccountNotExistError("账户不存在")

    def update_password(self, user_id, new_password):
        u = user_repo.get_user_by_user_id(user_id=user_id)
        if not u:
            raise AccountNotExistError("账户不存在")
        else:
            if len(new_password) < 8:
                raise PasswordTooShortError("密码不能小于8位")
            u.set_password(new_password)
            u.save()
            return True, "password update success"

    def add_user(self, request, tenant_name):
        phone = request.data.get("phone", None)
        user_name = request.data.get("user_name", None)
        email = request.data.get("email", None)
        password = request.data.get("password", None)
        tenant = tenantService.get_tenant(tenant_name)
        if Users.objects.filter(nick_name=user_name).exists():
            raise UserExistError("用户名已存在")
        if Users.objects.filter(email=email).exists():
            raise EmailExistError("邮箱已存在")
        if Users.objects.filter(phone=phone).exists():
            raise PhoneExistError("手机号已存在")

        user = Users(email=email, nick_name=user_name, phone=phone, client_ip=self.get_client_ip(request),
                     rf="backend")
        user.set_password(password)
        user.save()

        PermRelTenant.objects.create(
            user_id=user.pk, tenant_id=tenant.pk, identity='admin')

        codeRepositoriesService.createUser(user, email, password,
                                           user_name, user_name)

    def delete_user(self, user_id):
        user = Users.objects.get(user_id=user_id)
        git_user_id = user.git_user_id

        PermRelTenant.objects.filter(user_id=user.pk).delete()
        gitClient.deleteUser(git_user_id)
        user.delete()

    def update_user_password(self, user_id, new_password):
        user = Users.objects.get(user_id=user_id)
        if len(new_password) < 8:
            raise PasswordTooShortError("密码不能小于8位")
        user.set_password(new_password)
        user.save()
        # 同时修改git的密码
        codeRepositoriesService.modifyUser(user, new_password)

    def get_user_tenants(self, user_id):
        tenant_id_list = PermRelTenant.objects.filter(user_id=user_id).values_list("tenant_id", flat=True)
        tenant_list = Tenants.objects.filter(pk__in=tenant_id_list).values_list("tenant_name", flat=True)
        return tenant_list

    def get_users_count(self):
        user_count = Users.objects.all().count()
        return user_count

    def get_user_by_filter(self, args=None, kwargs=None):
        return user_repo.get_user_by_filter(args=args, kwargs=kwargs)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_fuzzy_users(self, user_name, tenant_name):
        # 如果租户名存在
        if tenant_name:
            tenants = Tenants.objects.filter(tenant_name=tenant_name)
            if not tenants:
                raise TenantNotExistError("租户{}不存在".format(tenant_name))
            tenant = tenants[0]
            user_id_list = PermRelTenant.objects.filter(tenant_id=tenant.ID).values_list("user_id", flat=True)
            user_list = Users.objects.filter(user_id__in=user_id_list)
            user_name_list = map(lambda x: x.nick_name.lower(), user_list)

        else:
            user_name_map = list(Users.objects.values("nick_name"))
            user_name_list = map(lambda x: x.get("nick_name").lower(), user_name_map)

        find_user_name = list(fuzzyfinder(user_name.lower(), user_name_list))
        user_query = Q(nick_name__in=find_user_name)
        user_list = Users.objects.filter(user_query)
        return user_list

    def batch_delete_users(self, tenant_name, user_id_list):
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        PermRelTenant.objects.filter(user_id__in=user_id_list, tenant_id=tenant.ID).delete()

    def get_user_by_username(self, user_name):
        users = Users.objects.filter(nick_name=user_name)
        if not users:
            raise UserNotExistError("用户名{}不存在".format(user_name))

        return users[0]

    def is_user_exist(self, user_name):
        try:
            self.get_user_by_username(user_name)
            return True
        except UserNotExistError:
            return False

    def create_user(self, nick_name, password, email, enterprise_id, rf):
        user = Users.objects.create(nick_name=nick_name,
                                    password=password,
                                    email=email,
                                    sso_user_id="",
                                    enterprise_id=enterprise_id,
                                    is_active=False,
                                    rf=rf)
        return user

    def get_user_detail(self, tenant_name, nick_name):
        u = user_repo.get_user_by_username(user_name=nick_name)
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        perms = team_repo.get_tenant_perms(tenant_id=tenant.ID, user_id=u.user_id)
        return u, perms

    def get_user_by_sso_user_id(self, sso_user_id):
        return user_repo.get_by_sso_user_id(sso_user_id)

    def make_user_as_admin_for_enterprise(self, user_id, enterprise_id):
        user_perm = enterprise_user_perm_repo.get_user_enterprise_perm(user_id, enterprise_id)
        if not user_perm:
            return enterprise_user_perm_repo.create_enterprise_user_perm(user_id, enterprise_id, "admin")
        return user_perm

    def is_user_admin_in_current_enterprise(self, current_user, enterprise_id):
        """判断用户在该企业下是否为管理员"""
        if current_user.enterprise_id != enterprise_id:
            return False
        user_perms = enterprise_user_perm_repo.get_user_enterprise_perm(current_user.user_id, enterprise_id)
        if not user_perms:
            users = user_repo.get_enterprise_users(enterprise_id).order_by("-user_id")
            if users:
                admin_user = users[0]
                # 如果有，判断用户最开始注册的用户和当前用户是否为同一人，如果是，添加数据返回true
                if admin_user.user_id == current_user.user_id:
                    enterprise_user_perm_repo.create_enterprise_user_perm(current_user.user_id, enterprise_id, "admin")
                    return True
                else:
                    return False
        else:
            return True

    def get_user_by_email(self, email):
        return user_repo.get_user_by_email(email)

    def get_enterprise_first_user(self, enterprise_id):
        users = user_repo.get_enterprise_users(enterprise_id).order_by("user_id")
        if users:
            return users[0]
        return None

    def get_user_by_phone(self, phone):
        return user_repo.get_user_by_phone(phone)

    def get_user_by_user_id(self, user_id):
        return user_repo.get_user_by_user_id(user_id=user_id)

user_services = UserService()

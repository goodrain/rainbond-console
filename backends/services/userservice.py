# -*- coding: utf8 -*-
import logging

from django.db.models import Q

from backends.services.tenantservice import tenant_service as tenantService
from exceptions import *
from www.gitlab_http import GitlabApi
from www.models import Tenants, Users, PermRelTenant
from www.tenantservice.baseservice import CodeRepositoriesService
from fuzzyfinder.main import fuzzyfinder

logger = logging.getLogger("default")
codeRepositoriesService = CodeRepositoriesService()
gitClient = GitlabApi()


class UserService(object):
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

        user = Users(email=email, nick_name=user_name, phone=phone, client_ip=self.get_client_ip(request), rf="backend")
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

    def get_all_users(self):
        user_list = Users.objects.all()
        return user_list

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_fuzzy_users(self, tenant_name, user_name):
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

    def create_user(self, nick_name, password, email, phone, enterprise_id, rf):
        user = Users.objects.create(nick_name=nick_name,
                                    password=password,
                                    email=email,
                                    phone=phone,
                                    sso_user_id="",
                                    enterprise_id=enterprise_id,
                                    is_active=False,
                                    rf=rf)
        return user


user_service = UserService()

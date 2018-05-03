# -*- coding: utf8 -*-
import logging

from django.db.models import Q

from backends.services.exceptions import UserExistError, TenantNotExistError, UserNotExistError
from backends.services.tenantservice import tenant_service as tenantService, EmailExistError, PhoneExistError, \
    PasswordTooShortError
from www.gitlab_http import GitlabApi
from www.models import Tenants, Users, PermRelTenant
from www.tenantservice.baseservice import CodeRepositoriesService
from fuzzyfinder.main import fuzzyfinder
from console.services.user_services import user_services as console_user_service

logger = logging.getLogger("default")
codeRepositoriesService = CodeRepositoriesService()
gitClient = GitlabApi()


class UserService(object):

    def check_params(self, user_name, phone, email, password, re_password):
        if not user_name:
            return False, "用户名不能为空"
        if not phone:
            return False, "手机号不能为空"
        if not email:
            return False, "邮箱不能为空"
        if console_user_service.is_user_exist(user_name):
            return False, "用户{0}已存在".format(user_name)
        if console_user_service.get_user_by_phone(phone):
            return False, "手机号{0}已存在".format(phone)
        if console_user_service.get_user_by_phone(email):
            return False, "邮箱{0}已存在".format(email)
        if password != re_password:
            return False, "两次输入的密码不一致"
        return True, "success"

    def create_user(self, user_name, phone, email, raw_password, rf, enterprise, client_ip):
        user = Users.objects.create(
            nick_name=user_name,
            email=email,
            phone=phone,
            sso_user_id="",
            enterprise_id=enterprise.enterprise_id,
            is_active=False,
            rf=rf,
            client_ip=client_ip
        )
        user.set_password(raw_password)
        return user

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

    def get_by_username_or_phone_or_email(self, query_condition):
        query = Q()
        if query_condition:
            query = query | Q(nick_name=query_condition) | Q(phone=query_condition) | Q(email=query_condition)

        users = Users.objects.filter(query).order_by("-user_id")
        return users


user_service = UserService()

# -*- coding: utf-8 -*-
import binascii
import logging
import os
import re
from datetime import datetime

from django.core.paginator import Paginator
from django.db.models import Q
from fuzzyfinder.main import fuzzyfinder
from rest_framework.response import Response

from console.exception.exceptions import AccountNotExistError
from console.exception.exceptions import EmailExistError
from console.exception.exceptions import PasswordTooShortError
from console.exception.exceptions import PhoneExistError
from console.exception.exceptions import TenantNotExistError
from console.exception.exceptions import UserExistError
from console.exception.exceptions import UserNotExistError
from console.models.main import EnterpriseUserPerm
from console.repositories.enterprise_repo import enterprise_user_perm_repo
from console.repositories.perm_repo import role_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.repositories.oauth_repo import oauth_user_repo
from console.services.user_accesstoken_services import user_access_services
from console.services.app_actions import app_manage_service
from console.services.exception import ErrAdminUserDoesNotExist
from console.services.exception import ErrCannotDelLastAdminUser
from console.services.team_services import team_services
from www.gitlab_http import GitlabApi
from www.models.main import PermRelTenant
from www.models.main import Tenants
from www.models.main import Users
from www.tenantservice.baseservice import CodeRepositoriesService
from www.utils.crypt import encrypt_passwd
from www.utils.return_message import general_message

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
        tenant = team_services.get_tenant(tenant_name)
        if Users.objects.filter(nick_name=user_name).exists():
            raise UserExistError("用户名已存在")
        if Users.objects.filter(email=email).exists():
            raise EmailExistError("邮箱已存在")
        if Users.objects.filter(phone=phone).exists():
            raise PhoneExistError("手机号已存在")

        user = Users(email=email, nick_name=user_name, phone=phone, client_ip=self.get_client_ip(request), rf="backend")
        user.set_password(password)
        user.save()

        PermRelTenant.objects.create(user_id=user.pk, tenant_id=tenant.pk, identity='admin')

        codeRepositoriesService.createUser(user, email, password, user_name, user_name)

    # delete user and delete user of tenant perm
    def delete_user(self, user_id):
        user = Users.objects.get(user_id=user_id)
        try:
            PermRelTenant.objects.filter(user_id=user.pk).delete()
        except PermRelTenant.DoesNotExist:
            pass
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
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = Tenants.objects.get(tenant_id=tenant_name)
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

    def create(self, data):
        # check nick name
        try:
            user_repo.get_by_username(data["nick_name"])
            raise UserExistError("{} already exists.".format(data["nick_name"]))
        except Users.DoesNotExist:
            pass
        if data.get("email", ""):
            user = user_repo.get_user_by_email(data["email"])
            if user is not None:
                raise EmailExistError("{} already exists.".format(data["email"]))
        if data.get("phone", ""):
            user = user_repo.get_user_by_phone(data["phone"])
            if user is not None:
                raise PhoneExistError("{} already exists.".format(data["phone"]))

        user = {
            "nick_name": data["nick_name"],
            "password": encrypt_passwd(data["email"]+data["password"]),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "enterprise_id": data["eid"],
            "is_active": data.get("is_active", True),
            "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        return Users.objects.create(**user)

    def update(self, user_id, data):
        d = {}
        if data.get("email", None) is not None:
            d["email"] = data["email"]
        if data.get("phone", None) is not None:
            d["phone"] = data["phone"]
        if data.get("is_active", None) is not None:
            d["is_active"] = data["is_active"]

        Users.objects.filter(user_id=user_id).update(**d)
        if data.get("password", None) is not None:
            user = Users.objects.get(user_id=user_id)
            user.set_password(data["password"])
            user.save()

    def delete(self, user_id):
        Users.objects.filter(user_id=user_id).delete()

    def create_user(self, nick_name, password, email, enterprise_id, rf):
        user = Users.objects.create(
            nick_name=nick_name,
            password=password,
            email=email,
            sso_user_id="",
            enterprise_id=enterprise_id,
            is_active=False,
            rf=rf)
        return user

    def create_user_set_password(self, user_name, email, raw_password, rf, enterprise, client_ip):
        user = Users.objects.create(
            nick_name=user_name,
            email=email,
            sso_user_id="",
            enterprise_id=enterprise.enterprise_id,
            is_active=True,
            rf=rf,
            client_ip=client_ip)
        user.set_password(raw_password)
        user.save()
        return user

    def update_user_set_password(self, enterprise_id, user_id, user_name, email, raw_password):
        user = Users.objects.get(user_id=user_id, enterprise_id=enterprise_id)
        user.nick_name = user_name
        user.email = email
        user.set_password(raw_password)
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
            token = self.generate_key()
            return enterprise_user_perm_repo.create_enterprise_user_perm(user_id, enterprise_id, "admin", token)
        return user_perm

    def is_user_admin_in_current_enterprise(self, current_user, enterprise_id):
        """判断用户在该企业下是否为管理员"""
        if current_user.enterprise_id != enterprise_id:
            return False
        user_perms = enterprise_user_perm_repo.get_user_enterprise_perm(current_user.user_id, enterprise_id)
        if not user_perms:
            users = user_repo.get_enterprise_users(enterprise_id).order_by("user_id")
            if users:
                admin_user = users[0]
                # 如果有，判断用户最开始注册的用户和当前用户是否为同一人，如果是，添加数据返回true
                if admin_user.user_id == current_user.user_id:
                    token = self.generate_key()
                    enterprise_user_perm_repo.create_enterprise_user_perm(
                        current_user.user_id, enterprise_id, "admin", token)
                    return True
                else:
                    return False
        else:
            return True

    def get_user_in_enterprise_perm(self, user, enterprise_id):
        return enterprise_user_perm_repo.get_user_enterprise_perm(user.user_id, enterprise_id)

    def get_administrator_user_by_token(self, token):
        perm = user_access_services.check_user_access_key(token)
        if not perm:
            perm = enterprise_user_perm_repo.get_by_token(token)
        if not perm:
            return None
        user = self.get_user_by_user_id(perm.user_id)
        permList = enterprise_user_perm_repo.get_user_enterprise_perm(user.user_id, user.enterprise_id)
        if not permList:
            return None
        return user

    def get_administrator_user_token(self, user):
        permList = enterprise_user_perm_repo.get_user_enterprise_perm(user.user_id, user.enterprise_id)
        if not permList:
            return None
        perm = permList[0]
        if not perm.token:
            perm.token = self.generate_key()
            perm.save()
        return perm.token

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

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

    def get_user_by_eid(self, eid, name, page, page_size):
        users = user_repo.get_enterprise_users(eid)
        if name:
            users = users.filter(nick_name__contains=name)
        total = users.count()
        return users[(page-1)*page_size: page*page_size], total

    def deploy_service(self, tenant_obj, service_obj, user, committer_name=None):
        """重新构建"""
        group_version = None
        code, msg, event_id = app_manage_service.deploy(tenant_obj, service_obj, user, group_version, committer_name)
        bean = {}
        if code != 200:
            return Response(general_message(code, "deploy app error", msg, bean=bean), status=code)
        result = general_message(code, "success", "重新构建成功", bean=bean)
        return Response(result, status=200)

    def list_users(self, page, size, item=""):
        uall = user_repo.list_users(item)
        paginator = Paginator(uall, size)
        try:
            upp = paginator.page(page)
        except Exception as e:
            logger.debug(e)
            return [], 0
        users = []
        for user in upp:
            users.append({
                "user_id": user.user_id,
                "email": user.email,
                "nick_name": user.nick_name,
                "phone": user.phone,
                "is_active": user.is_active,
                "origion": user.origion,
                "create_time": user.create_time,
                "client_ip": user.client_ip,
                "enterprise_id": user.enterprise_id,
            })
        return users, uall.count()

    def list_users_by_tenant_id(self, tenant_id, page=None, size=None, query=""):
        result = user_repo.list_users_by_tenant_id(tenant_id, query=query, page=page, size=size)
        users = []
        for item in result:
            # 获取一个用户在一个团队中的身份列表
            perms_identitys = team_services.get_user_perm_identitys_in_permtenant(
                user_id=item.get("user_id"), tenant_name=tenant_id)
            # 获取一个用户在一个团队中的角色ID列表
            perms_role_list = team_services.get_user_perm_role_id_in_permtenant(
                user_id=item.get("user_id"), tenant_name=tenant_id)

            role_infos = []

            for identity in perms_identitys:
                if identity == "access":
                    role_infos.append({"role_name": identity, "role_id": None})
                else:
                    role_id = role_repo.get_role_id_by_role_name(identity)
                    role_infos.append({"role_name": identity, "role_id": role_id})
            for role in perms_role_list:
                role_name = role_repo.get_role_name_by_role_id(role)
                role_infos.append({"role_name": role_name, "role_id": role})

            users.append({
                "user_id": item.get("user_id"),
                "nick_name": item.get("nick_name"),
                "email": item.get("email"),
                "phone": item.get("phone"),
                "is_active": item.get("is_active"),
                "enterprise_id": item.get("enterprise_id"),
                "role_infos": role_infos,
            })

        total = user_repo.count_users_by_tenant_id(tenant_id, query=query)
        return users, total

    def list_admin_users(self, page, size, eid=None):
        if eid is None:
            perms = EnterpriseUserPerm.objects.filter().all()
        else:
            perms = EnterpriseUserPerm.objects.filter(enterprise_id=eid).all()
        total = perms.count()
        paginator = Paginator(perms, size)
        try:
            permsp = paginator.page(page)
        except Exception as e:
            logger.debug(e)
            return [], total
        users = []
        for item in permsp:
            try:
                user = user_services.get_user_by_user_id(item.user_id)
                users.append({
                    "user_id": user.user_id,
                    "email": user.email,
                    "nick_name": user.nick_name,
                    "phone": user.phone,
                    "is_active": user.is_active,
                    "origion": user.origion,
                    "create_time": user.create_time,
                    "client_ip": user.client_ip,
                    "enterprise_id": user.enterprise_id,
                })
            except UserNotExistError:
                logger.warning("user_id: {}; user not found".format(item.user_id))

        return users, total

    def get_admin_users(self, eid):
        perms = EnterpriseUserPerm.objects.filter(enterprise_id=eid)
        users = []
        for item in perms:
            try:
                user = user_services.get_user_by_user_id(item.user_id)
                users.append({
                    "user_id": user.user_id,
                    "email": user.email,
                    "nick_name": user.nick_name,
                    "phone": user.phone,
                    "is_active": user.is_active,
                    "origion": user.origion,
                    "create_time": user.create_time,
                    "client_ip": user.client_ip,
                    "enterprise_id": user.enterprise_id,
                })
            except UserNotExistError:
                logger.warning("user_id: {}; user not found".format(item.user_id))
                continue
        return users

    def create_admin_user(self, user, ent):
        # 判断用户是否为企业管理员
        if user_services.is_user_admin_in_current_enterprise(user, ent.enterprise_id):
            return
        # 添加企业管理员
        token = self.generate_key()
        return enterprise_user_perm_repo.create_enterprise_user_perm(user.user_id, ent.enterprise_id, "admin", token)

    def delete_admin_user(self, user_id):
        perm = enterprise_user_perm_repo.get_backend_enterprise_admin_by_user_id(user_id)
        if perm is None:
            raise ErrAdminUserDoesNotExist("用户'{}'不是企业管理员".format(user_id))
        count = enterprise_user_perm_repo.count_by_eid(perm.enterprise_id)
        if count == 1:
            raise ErrCannotDelLastAdminUser("当前用户为最后一个企业管理员，无法删除")
        enterprise_user_perm_repo.delete_backend_enterprise_admin_by_user_id(user_id)

    def get_user_by_tenant_id(self, tenant_id, user_id):
        return user_repo.get_by_tenant_id(tenant_id, user_id)

    def check_params(self, user_name, email, password, re_password):
        is_pass, msg = self.__check_user_name(user_name)
        if not is_pass:
            return is_pass, msg
        is_pass, msg = self.__check_email(email)
        if not is_pass:
            return is_pass, msg

        if password != re_password:
            return False, "两次输入的密码不一致"
        return True, "success"

    def __check_user_name(self, user_name):
        if not user_name:
            return False, "用户名不能为空"
        if self.is_user_exist(user_name):
            return False, "用户{0}已存在".format(user_name)
        r = re.compile(u'^[a-zA-Z0-9_\\-\u4e00-\u9fa5]+$')
        if not r.match(user_name.decode("utf-8")):
            return False, "用户名称只支持中英文下划线和中划线"
        return True, "success"

    def __check_email(self, email):
        if not email:
            return False, "邮箱不能为空"
        if self.get_user_by_phone(email):
            return False, "邮箱{0}已存在".format(email)
        r = re.compile(r'^[\w\-\.]+@[\w\-]+(\.[\w\-]+)+$')
        if not r.match(email):
            return False, "邮箱地址不合法"
        return True, "success"

    def init_webhook_user(self, service, hook_type, committer_name=None):
        nick_name = hook_type
        if service.oauth_service_id:
            oauth_user = oauth_user_repo.get_user_oauth_by_oauth_user_name(service.oauth_service_id, committer_name)
            if not oauth_user:
                nick_name = committer_name
            else:
                try:
                    user = Users.objects.get(user_id=oauth_user.user_id)
                    nick_name = user.get_name()
                except Users.DoesNotExist:
                    nick_name = None
            if not nick_name:
                nick_name = hook_type
        user_obj = Users(
            user_id=service.creater,
            nick_name=nick_name
        )
        return user_obj


user_services = UserService()

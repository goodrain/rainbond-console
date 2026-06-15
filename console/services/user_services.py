# -*- coding: utf-8 -*-
import binascii
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from console.utils import perms
from console.exception.exceptions import (AccountNotExistError, EmailExistError, PasswordTooShortError, PhoneExistError,
                                          TenantNotExistError, UserExistError, UserNotExistError)
from console.exception.main import AbortRequest
from console.models.main import EnterpriseUserPerm, UserRole, PermsInfo, RoleInfo, RolePerms
from console.repositories.enterprise_repo import enterprise_user_perm_repo
from console.repositories.oauth_repo import oauth_user_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.services.app_actions import app_manage_service
from console.services.exception import (ErrAdminUserDoesNotExist, ErrCannotDelLastAdminUser)
from console.services.perm_services import (role_kind_services, user_kind_role_service)
from console.services.team_services import team_services
from console.services.user_accesstoken_services import user_access_services
from console.utils.oauth.oauth_types import get_oauth_instance
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, QuerySet
from fuzzyfinder.main import fuzzyfinder
from rest_framework.response import Response
from www.gitlab_http import GitlabApi
from www.models.main import PermRelTenant, Tenants, Users
from www.tenantservice.baseservice import CodeRepositoriesService
from www.utils.crypt import encrypt_passwd
from www.utils.return_message import general_message

logger = logging.getLogger("default")
codeRepositoriesService = CodeRepositoriesService()
gitClient = GitlabApi()


class UserService(object):
    def get_user_by_user_name(self, eid: str, user_name: str) -> Optional[Users]:
        user = user_repo.get_enterprise_user_by_username(eid, username=user_name)
        if not user:
            return None
        else:
            return user

    def check_user_password(self, user_id: str, password: str) -> bool:
        u = user_repo.get_user_by_user_id(user_id=user_id)
        if u:
            default_pass = u.check_password("goodrain")
            if not default_pass:
                return u.check_password(password)
            return default_pass
        else:
            raise AccountNotExistError("账户不存在")

    def update_password(self, user_id: str, new_password: str) -> Tuple[bool, str]:
        u = user_repo.get_user_by_user_id(user_id=user_id)
        if not u:
            raise AccountNotExistError("账户不存在")
        else:
            if len(new_password) < 8:
                raise PasswordTooShortError("密码不能小于8位")
            u.set_password(new_password)
            u.save()
            return True, "password update success"

    # delete user and delete user of tenant perm
    def delete_user(self, user_id: str) -> None:
        user = Users.objects.get(user_id=user_id)
        try:
            PermRelTenant.objects.filter(user_id=user.pk).delete()
        except PermRelTenant.DoesNotExist:
            pass
        try:
            UserRole.objects.filter(user_id=user.user_id).delete()
        except UserRole.DoesNotExist:
            pass
        user.delete()

    def get_users_by_user_ids(self, user_ids: List[str]) -> QuerySet[Users]:
        return user_repo.get_by_user_ids(user_ids)

    def get_user_tenants(self, user_id: str) -> QuerySet:
        tenant_id_list = PermRelTenant.objects.filter(user_id=user_id).values_list("tenant_id", flat=True)
        tenant_list = Tenants.objects.filter(pk__in=tenant_id_list).values_list("tenant_name", flat=True)
        return tenant_list

    def get_user_by_filter(self, args: Any = None, kwargs: Any = None) -> QuerySet[Users]:
        return user_repo.get_user_by_filter(args=args, kwargs=kwargs)

    def get_client_ip(self, request: Any) -> Optional[str]:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def batch_delete_users(self, tenant_name: str, user_id_list: List[str]) -> None:
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            tenant = Tenants.objects.get(tenant_id=tenant_name)
        PermRelTenant.objects.filter(user_id__in=user_id_list, tenant_id=tenant.ID).delete()
        roles = role_kind_services.get_roles(kind="team", kind_id=tenant.tenant_id)
        if roles:
            role_ids = roles.values_list("ID", flat=True)
            UserRole.objects.filter(user_id__in=user_id_list, role_id__in=role_ids).delete()

    def get_user_by_username(self, user_name: str) -> Users:
        return user_repo.get_user_by_username(user_name)

    def get_enterprise_user_by_username(self, user_name: str, eid: str) -> Users:
        return user_repo.get_enterprise_user_by_username(eid, user_name)

    def is_user_exist(self, user_name: str, eid: Any = None) -> bool:
        try:
            self.get_enterprise_user_by_username(user_name, eid)
            return True
        except Users.DoesNotExist:
            return False

    def create(self, data: dict) -> Users:
        # no re-password
        self.check_params(data["nick_name"], data["email"], data["password"], data["password"])
        # check nick name
        try:
            data["eid"] = data["enterprise_id"]
            user_repo.get_enterprise_user_by_username(data["eid"], data["nick_name"])
            raise UserExistError("{} already exists.".format(data["nick_name"]))
        except Users.DoesNotExist:
            pass
        if data.get("email", ""):
            user_by_email = user_repo.get_user_by_email(data["email"])
            if user_by_email is not None:
                raise EmailExistError("{} already exists.".format(data["email"]))
        if data.get("phone", ""):
            user_by_phone = user_repo.get_user_by_phone(data["phone"])
            if user_by_phone is not None:
                raise PhoneExistError("{} already exists.".format(data["phone"]))

        user_dict: Dict[str, Any] = {
            "nick_name": data["nick_name"],
            "password": encrypt_passwd(data["email"] + data["password"]),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "enterprise_id": data["eid"],
            "is_active": data.get("is_active", True),
            "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        return Users.objects.create(**user_dict)

    def update(self, user_id: str, data: dict) -> None:
        d: Dict[str, Any] = {}
        if data.get("email", None) is not None:
            d["email"] = data["email"]
        if data.get("phone", None) is not None:
            d["phone"] = data["phone"]
        if data.get("is_active", None) is not None:
            d["is_active"] = data["is_active"]
        if data.get("real_name", None) is not None:
            d["real_name"] = data["real_name"]

        Users.objects.filter(user_id=user_id).update(**d)
        if data.get("password", None) is not None:
            user = Users.objects.get(user_id=user_id)
            user.set_password(data["password"])
            user.save()

    def delete(self, user_id: str) -> None:
        Users.objects.filter(user_id=user_id).delete()

    def create_user(self, nick_name: str, password: str, email: str, enterprise_id: str, rf: str) -> Users:
        user = Users.objects.create(
            nick_name=nick_name,
            password=password,
            email=email,
            enterprise_id=enterprise_id,
            is_active=False,
            rf=rf)  # type: ignore[misc]  # NOTE: Users model may not declare `rf`; runtime field accepted by Django
        return user

    def create_user_set_password(self, user_name: str, email: str, raw_password: str, rf: str, enterprise: Any,
                                 client_ip: str, phone: Optional[str] = None, real_name: Optional[str] = None) -> Users:
        user = Users.objects.create(
            nick_name=user_name,
            email=email,
            enterprise_id=enterprise.enterprise_id,
            is_active=True,
            phone=phone,
            real_name=real_name,
        )
        user.set_password(raw_password)
        user.save()
        return user

    def check_user_is_enterprise_center_user(self, user_id: str) -> Tuple[Any, Any]:
        oauth_user, oauth_service = oauth_user_repo.get_enterprise_center_user_by_user_id(user_id)
        if oauth_user and oauth_service:
            return get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user), oauth_user
        return None, None

    @transaction.atomic()
    def create_enterprise_center_user_set_password(self, user_name: str, email: str, raw_password: str, rf: str,
                                                   enterprise: Any, client_ip: str, phone: Optional[str],
                                                   real_name: Optional[str], instance: Any) -> Users:
        data: Dict[str, Any] = {
            "username": user_name,
            "real_name": real_name,
            "password": raw_password,
            "email": email,
            "phone": phone,
        }
        enterprise_center_user = instance.create_user(enterprise.enterprise_id, data)
        user = self.create_user_set_password(
            enterprise_center_user.username, email, raw_password, rf, enterprise, client_ip, phone=phone, real_name=real_name)
        user.enterprise_center_user_id = enterprise_center_user.user_id  # type: ignore[attr-defined]  # NOTE: enterprise_center_user_id is set dynamically at runtime; not declared in Users model stub
        user.save()
        return user

    def update_user_set_password(self, enterprise_id: str, user_id: str, raw_password: str, real_name: str,
                                 phone: str) -> Users:
        user = Users.objects.get(user_id=user_id, enterprise_id=enterprise_id)
        user.real_name = real_name
        if phone:
            u = user_repo.get_user_by_phone(phone)
            if u and int(u.user_id) != int(user.user_id):
                raise AbortRequest(msg="phone exists", msg_show="手机号已存在")
            user.phone = phone
        if raw_password:
            user.set_password(raw_password)
        return user

    def get_user_detail(self, tenant_name: str, nick_name: str) -> Tuple[Users, Any]:
        u = user_repo.get_user_by_username(user_name=nick_name)
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=tenant_name)
        perms_qs = team_repo.get_tenant_perms(
            tenant_id=tenant.ID,  # type: ignore[union-attr, arg-type]  # NOTE: tenant can be None if not found; tenant.ID is int but get_tenant_perms expects str; runtime assumes tenant exists
            user_id=u.user_id)  # type: ignore[arg-type]  # NOTE: get_tenant_perms expects str; u.user_id is int at runtime
        return u, perms_qs

    def make_user_as_admin_for_enterprise(self, user_id: str, enterprise_id: str) -> EnterpriseUserPerm:
        user_perm = enterprise_user_perm_repo.get_user_enterprise_perm(user_id, enterprise_id)
        if not user_perm:
            token = self.generate_key()
            return enterprise_user_perm_repo.create_enterprise_user_perm(user_id, enterprise_id, "admin", token)
        return user_perm  # type: ignore[return-value]  # NOTE: get_user_enterprise_perm returns QuerySet; caller treats as single perm

    def is_user_admin_in_current_enterprise(self, current_user: Any, enterprise_id: str) -> bool:
        """判断用户在该企业下是否为管理员"""
        if current_user.enterprise_id != enterprise_id:
            return False
        is_admin = enterprise_user_perm_repo.is_admin(enterprise_id, current_user.user_id)
        if is_admin:
            return True
        users = user_repo.get_enterprise_users(enterprise_id).order_by("user_id")
        if users:
            admin_user = users[0]
            # 如果有，判断用户最开始注册的用户和当前用户是否为同一人，如果是，添加数据返回true
            if admin_user.user_id == current_user.user_id:
                token = self.generate_key()
                enterprise_user_perm_repo.create_enterprise_user_perm(current_user.user_id, enterprise_id, "admin", token)
                return True
        return False

    def get_user_in_enterprise_perm(self, user: Any, enterprise_id: str) -> QuerySet[EnterpriseUserPerm]:
        return enterprise_user_perm_repo.get_user_enterprise_perm(user.user_id, enterprise_id)

    def get_user_by_openapi_token(self, token: str) -> Optional[Users]:
        perm = user_access_services.check_user_access_key(token)
        if not perm:
            return None
        user = self.get_user_by_user_id(perm.user_id)  # type: ignore[arg-type]  # NOTE: int user_id vs str (systemic)
        return user

    def get_administrator_user_token(self, user: Any) -> Optional[str]:
        perm_list = enterprise_user_perm_repo.get_user_enterprise_perm(user.user_id, user.enterprise_id)
        if not perm_list:
            return None
        perm = perm_list[0]
        if not perm.token:
            perm.token = self.generate_key()
            perm.save()
        return perm.token

    def generate_key(self) -> str:
        return binascii.hexlify(os.urandom(20)).decode()

    def get_user_by_email(self, email: str) -> Optional[Users]:
        return user_repo.get_user_by_email(email)

    def get_enterprise_first_user(self, enterprise_id: str) -> Optional[Users]:
        users = user_repo.get_enterprise_users(enterprise_id).order_by("user_id")
        if users:
            return users[0]
        return None

    def get_user_by_phone(self, phone: str, eid: str) -> Optional[Users]:
        return user_repo.get_enterprise_user_by_phone(phone, eid)

    def get_user_by_user_id(self, user_id: str) -> Users:
        return user_repo.get_user_by_user_id(user_id=user_id)

    def get_user_by_eid(self, eid: str, name: str, page: int, page_size: int) -> Tuple[QuerySet[Users], int]:
        users = user_repo.get_enterprise_users(eid)
        if name:
            users = users.filter(
                Q(nick_name__contains=name)
                | Q(real_name__contains=name)
                | Q(phone__contains=name)
                | Q(email__contains=name))
        total = users.count()
        return users[(page - 1) * page_size:page * page_size], total

    def deploy_service(self, tenant_obj: Tenants, service_obj: Any, user: Any, committer_name: Optional[str] = None,
                       oauth_instance: Any = None) -> Response:
        """重新构建"""
        code, msg, event_id = app_manage_service.deploy(tenant_obj, service_obj, user, oauth_instance=oauth_instance)
        bean: Dict[str, Any] = {}
        if code != 200:
            return Response(general_message(code, "deploy app error", msg, bean=bean), status=code)
        result = general_message(code, "success", "重新构建成功", bean=bean)
        return Response(result, status=200)

    def list_users(self, page: int, size: int, item: str = "") -> Tuple[List[Dict[str, Any]], int]:
        uall = user_repo.list_users(item)
        paginator = Paginator(uall, size)
        try:
            upp = paginator.page(page)
        except Exception as e:
            logger.debug(e)
            return [], 0
        users: List[Dict[str, Any]] = []
        for user in upp:
            users.append({
                "user_id": user.user_id,
                "email": user.email,
                "nick_name": user.nick_name,
                "phone": user.phone,
                "is_active": user.is_active,
                "create_time": user.create_time,
                "enterprise_id": user.enterprise_id,
            })
        return users, uall.count()

    def list_users_by_tenant_id(self, tenant_id: str, page: Optional[int] = None, size: Optional[int] = None,
                                query: str = "") -> Tuple[List[Dict[str, Any]], Any]:
        result = user_repo.list_users_by_tenant_id(tenant_id, query=query, page=page, size=size)
        users: List[Dict[str, Any]] = []
        for item in result:
            user = user_repo.get_by_user_id(item.get("user_id"))
            role_infos = user_kind_role_service.get_user_roles(kind="team", kind_id=tenant_id, user=user)
            users.append({
                "user_id": item.get("user_id"),
                "nick_name": item.get("nick_name"),
                "email": item.get("email"),
                "phone": item.get("phone"),
                "is_active": item.get("is_active"),
                "enterprise_id": item.get("enterprise_id"),
                "role_infos": role_infos["roles"],
            })

        total = user_repo.count_users_by_tenant_id(tenant_id, query=query)
        return users, total

    def list_admin_users(self, page: int, size: int, eid: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        if eid is None:
            perms_qs = EnterpriseUserPerm.objects.filter().all()
        else:
            perms_qs = EnterpriseUserPerm.objects.filter(enterprise_id=eid).all()
        total = perms_qs.count()
        paginator = Paginator(perms_qs, size)
        try:
            permsp = paginator.page(page)
        except Exception as e:
            logger.debug(e)
            return [], total
        users: List[Dict[str, Any]] = []
        for item in permsp:
            try:
                user = user_services.get_user_by_user_id(item.user_id)  # type: ignore[arg-type]  # NOTE: item.user_id is int; get_user_by_user_id expects str; runtime passes int to Django ORM which accepts it
                users.append({
                    "user_id": user.user_id,
                    "email": user.email,
                    "nick_name": user.nick_name,
                    "phone": user.phone,
                    "is_active": user.is_active,
                    "create_time": user.create_time,
                    "enterprise_id": user.enterprise_id,
                })
            except UserNotExistError:
                logger.warning("user_id: {}; user not found".format(item.user_id))

        return users, total

    def get_admin_users(self, eid: str) -> List[Dict[str, Any]]:
        perms_qs = EnterpriseUserPerm.objects.filter(enterprise_id=eid)
        users: List[Dict[str, Any]] = []
        for item in perms_qs:
            try:
                user = user_services.get_user_by_user_id(item.user_id)  # type: ignore[arg-type]  # NOTE: same as list_admin_users; item.user_id is int at runtime
                users.append({
                    "user_id": user.user_id,
                    "email": user.email,
                    "nick_name": user.nick_name,
                    "real_name": user.real_name,
                    "phone": user.phone,
                    "is_active": user.is_active,
                    "create_time": user.create_time,
                    "enterprise_id": user.enterprise_id,
                    "roles": item.identity.split(","),
                })
            except UserNotExistError:
                logger.warning("user_id: {}; user not found".format(item.user_id))
                continue
        return users

    def create_admin_user(self, user: Any, ent: Any, roles: List[str]) -> EnterpriseUserPerm:
        try:
            enterprise_user_perm_repo.get(ent.enterprise_id, user.user_id)
            return enterprise_user_perm_repo.update_roles(ent.enterprise_id, user.user_id, ",".join(roles))  # type: ignore[return-value, func-returns-value]  # NOTE: update_roles is declared to return None; callers treat the result as a perm; this is a latent bug
        except EnterpriseUserPerm.DoesNotExist:
            token = self.generate_key()
            return enterprise_user_perm_repo.create_enterprise_user_perm(user.user_id, ent.enterprise_id, ",".join(roles),
                                                                         token)

    def delete_admin_user(self, user_id: str) -> None:
        perm = enterprise_user_perm_repo.get_backend_enterprise_admin_by_user_id(user_id)
        if perm is None:
            raise ErrAdminUserDoesNotExist("用户'{}'不是企业管理员".format(user_id))
        count = enterprise_user_perm_repo.count_by_eid(perm.enterprise_id)
        if count == 1:
            raise ErrCannotDelLastAdminUser("当前用户为最后一个企业管理员，无法删除")
        enterprise_user_perm_repo.delete_backend_enterprise_admin_by_user_id(user_id)

    def update_roles(self, enterprise_id: str, user_id: str, roles: List[str]) -> None:
        enterprise_user_perm_repo.update_roles(enterprise_id, user_id, ",".join(roles))

    def list_roles(self, enterprise_id: str, user_id: str) -> List[str]:
        try:
            perm = enterprise_user_perm_repo.get(enterprise_id, user_id)
            return perm.identity.split(",")
        except EnterpriseUserPerm.DoesNotExist:
            return []

    def get_user_by_tenant_id(self, tenant_id: str, user_id: str) -> dict:
        return user_repo.get_by_tenant_id(tenant_id, user_id)

    def check_params(self, user_name: str, email: str, password: str, re_password: str, eid: Any = None,
                     phone: Optional[str] = None) -> None:
        self.__check_user_name(user_name, eid)
        self.__check_email(email)
        self.__check_phone(phone)
        if password != re_password:
            raise AbortRequest("The two passwords do not match", "两次输入的密码不一致")

    def __check_user_name(self, user_name: str, eid: Any = None) -> None:
        if not user_name:
            raise AbortRequest("empty username", "用户名不能为空")
        if self.is_user_exist(user_name, eid):
            raise AbortRequest("username already exists", "用户{0}已存在".format(user_name), status_code=409, error_code=409)
        r = re.compile('^[a-zA-Z0-9_\\-\\u4e00-\\u9fa5]+$')
        if not r.match(user_name):
            raise AbortRequest("invalid username", "用户名称只支持中英文下划线和中划线")

    def __check_email(self, email: str) -> None:
        if not email:
            raise AbortRequest("empty email", "邮箱不能为空")
        if self.get_user_by_email(email):
            raise AbortRequest("email already exists", "邮箱{0}已存在".format(email))
        r = re.compile(r'^[\w\-\.]+@[\w\-]+(\.[\w\-]+)+$')
        if not r.match(email):
            raise AbortRequest("invalid email", "邮箱地址不合法")
        if self.get_user_by_email(email):
            raise AbortRequest("username already exists", "邮箱已存在", status_code=409, error_code=409)

    def __check_phone(self, phone: Optional[str]) -> None:
        if not phone:
            return
        user = user_repo.get_user_by_phone(phone)
        if user is not None:
            raise AbortRequest("user phone already exists", "用户手机号已存在", status_code=409)

    def init_webhook_user(self, service: Any, hook_type: str, committer_name: Optional[str] = None) -> Users:
        nick_name: Optional[str] = hook_type
        if service.oauth_service_id:
            oauth_user = oauth_user_repo.get_user_oauth_by_oauth_user_name(service.oauth_service_id, committer_name)  # type: ignore[arg-type]  # NOTE: committer_name may be None; repo signature expects str; runtime tolerates None for optional webhook committer
            if not oauth_user:
                nick_name = committer_name
            else:
                try:
                    user = Users.objects.get(user_id=oauth_user.user_id)  # type: ignore[misc]  # NOTE: oauth_user.user_id may be int; Django ORM accepts int for lookup
                    nick_name = user.get_name()
                except Users.DoesNotExist:
                    nick_name = None
            if not nick_name:
                nick_name = hook_type
        user_obj = Users(user_id=service.creater, nick_name=nick_name)
        return user_obj

    @staticmethod
    def list_user_team_perms(user: Any, tenant: Any) -> List[int]:
        admin_roles = user_services.list_roles(user.enterprise_id, user.user_id)
        user_perms = list(perms.list_enterprise_perm_codes_by_roles(admin_roles))
        if tenant.creater == user.user_id:
            team_perms = list(PermsInfo.objects.filter(kind="team").values_list("code", flat=True))
            user_perms.extend(team_perms)
            user_perms.append(100001)
        else:
            team_roles = RoleInfo.objects.filter(kind="team", kind_id=tenant.tenant_id)
            if team_roles:
                role_ids = team_roles.values_list("ID", flat=True)
                team_user_roles = UserRole.objects.filter(user_id=user.user_id, role_id__in=role_ids)
                if team_user_roles:
                    team_user_role_ids = team_user_roles.values_list("role_id", flat=True)
                    team_role_perms = RolePerms.objects.filter(role_id__in=team_user_role_ids)
                    if team_role_perms:
                        user_perms.extend(list(team_role_perms.values_list("perm_code", flat=True)))
        return list(set(user_perms))


user_services = UserService()

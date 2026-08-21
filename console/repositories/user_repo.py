# -*- coding: utf-8 -*-
from typing import Any, List, Optional

from addict import Dict
from django.db.models import Q, QuerySet

from console.exception.exceptions import UserFavoriteNotExistError, UserNotExistError
from console.exception.bcode import ErrUserNotFound
from console.models.main import UserFavorite
from www.models.main import PermRelTenant, Tenants, Users


class UserRepo(object):
    def get_user_by_user_id(self, user_id: str) -> Users:
        u = Users.objects.filter(user_id=user_id)
        if not u:
            raise UserNotExistError("用户{}不存在".format(user_id))
        return u[0]

    def get_enterprise_user_by_id(self, enterprise_id: str, user_id: str) -> Optional[Users]:
        return Users.objects.filter(user_id=user_id, enterprise_id=enterprise_id).first()

    def get_enterprise_user_by_username(self, eid: str, username: str) -> Users:
        return Users.objects.get(nick_name=username, enterprise_id=eid)

    @staticmethod
    def get_user_by_username(user_name: str) -> Users:
        users = Users.objects.filter(nick_name=user_name)
        if not users:
            raise ErrUserNotFound
        return users[0]

    def get_user_by_user_name(self, user_name: str) -> Optional[Users]:
        user = Users.objects.filter(nick_name=user_name).first()
        return user

    def get_user_by_filter(self, args: Any = None, kwargs: Any = None) -> QuerySet:
        args = tuple(args) if isinstance(args, (tuple, list, set)) else tuple()
        kwargs = kwargs if isinstance(kwargs, dict) else dict()
        users = Users.objects.filter(*args, **kwargs)
        return users

    def get_by_user_id(self, user_id: str) -> Optional[Users]:
        u = Users.objects.filter(user_id=user_id)
        if u:
            return u[0]
        return None

    def get_by_user_ids(self, user_ids: List[str]) -> QuerySet:
        u = Users.objects.filter(user_id__in=user_ids)
        return u

    def get_enterprise_users(self, enterprise_id: str) -> QuerySet:
        return Users.objects.filter(enterprise_id=enterprise_id)

    def get_user_by_email(self, email: str) -> Optional[Users]:
        u = Users.objects.filter(email=email)
        if u:
            return u[0]
        return None

    def get_user_by_phone(self, phone: str) -> Optional[Users]:
        u = Users.objects.filter(phone=phone)
        if u:
            return u[0]
        return None

    def get_enterprise_user_by_phone(self, phone: str, eid: str) -> Optional[Users]:
        u = Users.objects.filter(phone=phone, enterprise_id=eid)
        if u:
            return u[0]
        return None

    def get_all_users(self) -> QuerySet:
        return Users.objects.all()

    def get_user_nickname_by_id(self, user_id: str) -> Optional[str]:
        u = Users.objects.filter(user_id=user_id)
        if u:
            return u[0].nick_name
        else:
            return None

    def list_users(self, item: str = "") -> QuerySet:
        """
        Support search by username, email, phone number
        """
        return Users.objects.filter(Q(nick_name__icontains=item)
                                    | Q(email__icontains=item)
                                    | Q(phone__icontains=item)).all().order_by("-create_time")

    def get_by_tenant_id(self, tenant_id: str, user_id: str) -> dict:
        rows = self._tenant_user_rows(tenant_id, user_id=user_id)
        if not rows:
            raise UserNotExistError("用户{0}不存在于团队{1}中".format(user_id, tenant_id))
        return rows[0]

    def list_users_by_tenant_id(self, tenant_id: str, query: str = "", page: Optional[int] = None,
                                size: Optional[int] = None) -> Any:
        """
        Support search by username, email, phone number
        """
        rows = self._tenant_user_rows(tenant_id, query=query)
        if page is not None and size is not None:
            start = max(int(page) - 1, 0) * int(size)
            rows = rows[start:start + int(size)]
        return rows

    def count_users_by_tenant_id(self, tenant_id: str, query: str = "") -> Any:
        """
        Support search by username, email, phone number
        """
        return len({row.user_id for row in self._tenant_user_rows(tenant_id, query=query)})

    @staticmethod
    def _tenant_user_rows(tenant_id: str, query: str = "", user_id: Optional[str] = None) -> List[Dict]:
        tenant = Tenants.objects.filter(tenant_id=tenant_id).only("ID").first()
        if tenant is None:
            return []
        permissions = PermRelTenant.objects.filter(tenant_id=tenant.ID)
        if user_id is not None:
            permissions = permissions.filter(user_id=user_id)
        permission_rows = list(permissions.values_list("user_id", "identity"))
        user_ids = [permission_user_id for permission_user_id, _ in permission_rows]
        users = Users.objects.filter(user_id__in=user_ids)
        if query:
            users = users.filter(Q(nick_name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query))
        user_map = {user.user_id: user for user in users}
        rows = []
        seen = set()
        for permission_user_id, identity in permission_rows:
            user = user_map.get(permission_user_id)
            key = (permission_user_id, identity)
            if user is None or key in seen:
                continue
            seen.add(key)
            rows.append(Dict({
                "user_id": user.user_id,
                "email": user.email,
                "nick_name": user.nick_name,
                "phone": user.phone,
                "is_active": user.is_active,
                "enterprise_id": user.enterprise_id,
                "identity": identity,
            }))
        return rows

    def get_user_favorite(self, user_id: Any) -> QuerySet:
        # user_id arrives as str from some callers and as the int model field from others
        return UserFavorite.objects.filter(user_id=user_id).order_by("custom_sort")

    def get_user_favorite_by_name(self, user_id: str, name: str) -> QuerySet:
        return UserFavorite.objects.filter(user_id=user_id, name=name)

    def get_user_favorite_by_ID(self, user_id: str, favorite_id: str) -> UserFavorite:
        try:
            return UserFavorite.objects.get(user_id=user_id, ID=favorite_id)
        except Exception:
            # pre-existing: exception class declares required args but is raised bare
            raise UserFavoriteNotExistError  # type: ignore[call-arg]

    def get_user_default_favorite(self, user_id: str) -> Optional[UserFavorite]:
        return UserFavorite.objects.filter(user_id=user_id, is_default=True).first()

    def create_user_favorite(self, user_id: str, name: str, url: str, is_default: bool) -> None:
        user_favorites = self.get_user_favorite(user_id)
        if user_favorites:
            custom_sort = user_favorites.last().custom_sort + 1  # type: ignore[union-attr]
        else:
            custom_sort = 0
        UserFavorite.objects.create(user_id=user_id, name=name, url=url, custom_sort=custom_sort, is_default=is_default)

    def update_user_favorite(self, user_favorite: UserFavorite, name: str, url: str, custom_sort: int,
                             is_default: bool) -> bool:
        rst = True
        try:
            user_favorite.name = name
            user_favorite.url = url
            user_favorite.is_default = is_default
            if custom_sort != user_favorite.custom_sort:
                user_favorites = self.get_user_favorite(user_favorite.user_id)
                if custom_sort < user_favorite.custom_sort:
                    operate_user_favorites = user_favorites[custom_sort:user_favorite.custom_sort]
                    for operate_user_favorite in operate_user_favorites:
                        print((operate_user_favorite.ID))
                        operate_user_favorite.custom_sort += 1
                        operate_user_favorite.save()
                elif custom_sort > user_favorite.custom_sort:
                    operate_user_favorites = user_favorites[user_favorite.custom_sort + 1:custom_sort + 1]
                    for operate_user_favorite in operate_user_favorites:
                        operate_user_favorite.custom_sort -= 1
                        operate_user_favorite.save()
            user_favorite.custom_sort = custom_sort
            user_favorite.save()
        except Exception:
            rst = False
        return rst

    def delete_user_favorite_by_id(self, user_id: str, favorite_id: str) -> None:
        user_favorites = self.get_user_favorite(user_id)
        tar_user_favorite = self.get_user_favorite_by_ID(user_id, favorite_id)
        operate_user_favorites = user_favorites[tar_user_favorite.custom_sort:]
        for operate_user_favorite in operate_user_favorites:
            operate_user_favorite.custom_sort -= 1
            operate_user_favorite.save()
        tar_user_favorite.delete()


user_repo = UserRepo()

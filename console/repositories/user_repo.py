# -*- coding: utf-8 -*-
from typing import Any, List, Optional

from django.db.models import Q, QuerySet

from console.exception.exceptions import UserFavoriteNotExistError, UserNotExistError
from console.exception.bcode import ErrUserNotFound
from console.models.main import UserFavorite
from console.repositories.base import BaseConnection
from www.models.main import Users


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

    def get_user_by_filter(self, args: Any = None, kwargs: Any = None) -> QuerySet[Users]:
        args = tuple(args) if isinstance(args, (tuple, list, set)) else tuple()
        kwargs = kwargs if isinstance(kwargs, dict) else dict()
        users = Users.objects.filter(*args, **kwargs)
        return users

    def get_by_user_id(self, user_id: str) -> Optional[Users]:
        u = Users.objects.filter(user_id=user_id)
        if u:
            return u[0]
        return None

    def get_by_user_ids(self, user_ids: List[str]) -> QuerySet[Users]:
        u = Users.objects.filter(user_id__in=user_ids)
        return u

    def get_enterprise_users(self, enterprise_id: str) -> QuerySet[Users]:
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

    def get_all_users(self) -> QuerySet[Users]:
        return Users.objects.all()

    def get_user_nickname_by_id(self, user_id: str) -> Optional[str]:
        u = Users.objects.filter(user_id=user_id)
        if u:
            return u[0].nick_name
        else:
            return None

    def list_users(self, item: str = "") -> QuerySet[Users]:
        """
        Support search by username, email, phone number
        """
        return Users.objects.filter(Q(nick_name__contains=item)
                                    | Q(email__contains=item)
                                    | Q(phone__contains=item)).all().order_by("-create_time")

    def get_by_tenant_id(self, tenant_id: str, user_id: str) -> dict:
        conn = BaseConnection()

        sql = """
            SELECT DISTINCT
                a.user_id,
                a.email,
                a.nick_name,
                a.phone,
                a.is_active,
                a.enterprise_id,
                b.identity
            FROM
                user_info a,
                tenant_perms b,
                tenant_info c
            WHERE a.user_id = b.user_id
            AND b.tenant_id = c.ID
            AND a.user_id = {user_id}
            AND c.tenant_id = '{tenant_id}'""".format(
            tenant_id=tenant_id, user_id=user_id)
        result = conn.query(sql)
        if len(result) == 0:
            raise UserNotExistError("用户{0}不存在于团队{1}中".format(user_id, tenant_id))
        return result[0]

    def list_users_by_tenant_id(self, tenant_id: str, query: str = "", page: Optional[int] = None,
                                size: Optional[int] = None) -> Any:
        """
        Support search by username, email, phone number
        """
        conn = BaseConnection()

        limit = ""
        if page is not None and size is not None:
            page = page if page > 0 else 1
            page = (page - 1) * size
            limit = "Limit {page}, {size}".format(page=page, size=size)
        where = """WHERE a.user_id = b.user_id
            AND b.tenant_id = c.ID
            AND c.tenant_id = '{tenant_id}'""".format(tenant_id=tenant_id)
        if query:
            where += """ AND ( a.nick_name LIKE "%{query}%"
            OR a.phone LIKE "%{query}%"
            OR a.email LIKE "%{query}%" )""".format(query=query)
        sql = """
            SELECT DISTINCT
                a.user_id,
                a.email,
                a.nick_name,
                a.phone,
                a.is_active,
                a.enterprise_id,
                b.identity
            FROM
                user_info a,
                tenant_perms b,
                tenant_info c
            {where}
            {limit}""".format(
            where=where, limit=limit)
        result = conn.query(sql)
        return result

    def count_users_by_tenant_id(self, tenant_id: str, query: str = "") -> Any:
        """
        Support search by username, email, phone number
        """
        where = """WHERE a.user_id = b.user_id
            AND b.tenant_id = c.ID
            AND c.tenant_id = '{tenant_id}'""".format(tenant_id=tenant_id)
        if query:
            where += """ AND ( a.nick_name LIKE "%{query}%"
            OR a.phone LIKE "%{query}%"
            OR a.email LIKE "%{query}%" )""".format(query=query)

        sql = """
            SELECT
                count(*) as total
            FROM
                (
                SELECT DISTINCT
                    a.user_id AS user_id
                FROM
                    user_info a,
                    tenant_perms b,
                    tenant_info c
                {where}
                ) as userid""".format(where=where)

        conn = BaseConnection()
        result = conn.query(sql)
        return result[0].get("total")

    def get_user_favorite(self, user_id: Any) -> QuerySet[UserFavorite]:
        # user_id arrives as str from some callers and as the int model field from others
        return UserFavorite.objects.filter(user_id=user_id).order_by("custom_sort")

    def get_user_favorite_by_name(self, user_id: str, name: str) -> QuerySet[UserFavorite]:
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

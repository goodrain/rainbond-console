# -*- coding: utf-8 -*-

from rest_framework.response import Response

from console.repositories.user_repo import user_repo


def auth(func):
    # 验证COOKIE中用户信息是否完善的装饰器
    def inner(request, *args, **kwargs):
        user_id = request.COOKIES.get('uid')
        user = user_repo.get_by_user_id(user_id)
        if not user:
            return Response("用户不存在", status=400)
        if not user.enterprise_id:
            return Response("用户信息不完善", status=400)
        return func(request, *args, **kwargs)
    return inner


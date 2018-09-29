# -*- coding: utf-8 -*-

from django.shortcuts import redirect


def auth(func):
    # 验证用户信息是否完善的装饰器
    def inner(request, *args, **kwargs):
        user = request.COOKIES.get("company")
        if not user:
            return redirect("/a/login")
        return func(request, *args, **kwargs)
    return inner


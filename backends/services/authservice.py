# -*- coding: utf8 -*-
"""
  Created on 2018/4/12.
"""
from django.contrib.auth.models import User as TokenAuthUser
from rest_framework.authtoken.models import Token


class AuthService(object):
    def create_token_auth_user(self, username, password):
        """生成token验证"""
        app_user = TokenAuthUser.objects.filter(username=username)
        if app_user:
            token = Token.objects.filter(user=app_user)
            return token
        else:
            app_user = TokenAuthUser.objects.create(username=username)
            app_user.set_password(password)
            app_user.is_staff = True
            app_user.is_superuser = True
            app_user.save()
            token = Token.objects.create(user=app_user)
            return token

    def get_token_by_user_id(self, user_id):
        token = Token.objects.filter(user_id=user_id).first()
        return token


auth_service = AuthService()
# -*- coding: utf8 -*-
from www.models import Users, WeChatUser
from django.db.models import Q


class ModelBackend(object):

    def authenticate(self, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            user = Users.objects.get(Q(phone=username) | Q(email=username) | Q(nick_name=username))
            if user.check_password(password):
                return user
        except Users.DoesNotExist:
            pass

    def get_user(self, user_id):
        try:
            return Users.objects.get(pk=user_id)
        except Users.DoesNotExist:
            return None


class PartnerModelBackend(ModelBackend):

    def authenticate(self, username=None, source=None, **kwargs):
        if username is None or source is None:
            return None

        try:
            if username.find("@") > 0:
                user = Users.objects.get(email=username)
            else:
                user = Users.objects.get(phone=username)
            if user.password == 'nopass':
                return user
        except Users.DoesNotExist:
            pass


class WeChatModelBackend(ModelBackend):
    """微信用户登录拦截"""
    def authenticate(self, union_id=None, **kwargs):
        # user登录失败,微信登录
        if union_id is None or union_id == "":
            return None
        try:
            return Users.objects.get(union_id=union_id)
        except Users.DoesNotExist:
            pass


class GoodRainSSOModelBackend(ModelBackend):
    """SSO用户登陆认证"""
    def authenticate(self, user_id=None, sso_user_id=None, **kwargs):
        if not sso_user_id or not user_id:
            return None
        try:
            return Users.objects.get(user_id=user_id, sso_user_id=sso_user_id)
        except Users.DoesNotExist:
            pass

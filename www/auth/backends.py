# -*- coding: utf8 -*-
from www.models import Users, WeChatUser


class ModelBackend(object):

    def authenticate(self, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            if username.find("@") > 0:
                user = Users.objects.get(email=username)
            elif username.isdigit():
                user = Users.objects.get(phone=username)
            else:
                user = Users.objects.get(nick_name=username)
            if user.check_password(password):
                return user
        except Users.DoesNotExist:
            pass

    def get_user(self, user_id):
        try:
            user = Users.objects.get(pk=user_id)
            # 查询是否存在微信信息
            if user.union_id is not None and user.union_id != "":
                union_id = user.union_id
                wechat_list = WeChatUser.objects.filter(union_id=union_id)
                if len(wechat_list) > 0:
                    wechat_user = list(wechat_list)[0]
                    user.nick_name = wechat_user.nick_name
            return user
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



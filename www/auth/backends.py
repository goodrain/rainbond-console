# -*- coding: utf8 -*-
from www.models import Users


class ModelBackend(object):
    def authenticate(self, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('email')

        try:
            if username.find("@") > 0:
                user = Users.objects.get(email=username)
            else:
                user = Users.objects.get(phone=username)            
            if user.check_password(password):
                return user
        except Users.DoesNotExist:
            pass

    def get_user(self, user_id):
        try:
            return Users.objects.get(pk=user_id)
        except Users.DoesNotExist:
            return None

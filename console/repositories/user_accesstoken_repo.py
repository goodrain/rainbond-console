# -*- coding: utf-8 -*-
import logging
from time import time

from django.db.models import Q

from console.models.main import UserAccessKey

logger = logging.getLogger("default")


class UserAccessTokenRepo(object):
    def create_user_access_key(self, **kwargs):
        return UserAccessKey.objects.create(**kwargs)

    def get_user_perm_by_access_key(self, access_key):
        _now = int(time())
        return UserAccessKey.objects.filter(
            Q(access_key=access_key, expire_time__gt=_now) |
            Q(access_key=access_key, expire_time=None)
        ).first()

    def get_user_access_key(self, user_id):
        return UserAccessKey.objects.filter(user_id=user_id)

    def get_user_access_key_by_id(self, user_id, id):
        return UserAccessKey.objects.filter(ID=id, user_id=user_id)

    def get_user_access_key_by_note(self, user_id, note):
        return UserAccessKey.objects.filter(note, user_id=user_id)

    def delete_user_access_key_by_id(self, user_id, id):
        return self.get_user_access_key_by_id(user_id, id).delete()


user_access_repo = UserAccessTokenRepo()

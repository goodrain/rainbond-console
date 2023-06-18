# -*- coding: utf-8 -*-
import logging
import os
import hashlib
import time

from console.repositories.user_accesstoken_repo import user_access_repo

logger = logging.getLogger('default')


class UserAccessTokenServices(object):
    def generate_key(self):
        return hashlib.sha1(os.urandom(24)).hexdigest()

    def create_user_access_key(self, note, user_id, age):
        access_key = self.generate_key()
        if age:
            expire_time = time.time() + age
        else:
            expire_time = None
        return user_access_repo.create_user_access_key(note=note,
                                                       user_id=user_id,
                                                       expire_time=expire_time,
                                                       access_key=access_key)

    def check_user_access_key(self, access_key):
        return user_access_repo.get_user_perm_by_access_key(access_key)

    def get_user_access_key(self, user_id):
        return user_access_repo.get_user_access_key(user_id)

    def get_user_access_key_by_id(self, user_id, id):
        return user_access_repo.get_user_access_key_by_id(user_id, id)

    def get_user_access_key_by_note(self, user_id, note):
        return user_access_repo.get_user_access_key_by_note(user_id, note)

    def delete_user_access_key_by_id(self, user_id, note):
        return user_access_repo.delete_user_access_key_by_id(user_id, note)

    def update_user_access_key_by_id(self, user_id, id):
        new_access_key = self.generate_key()
        user_access_key = self.get_user_access_key_by_id(user_id, id).first()
        if user_access_key:
            user_access_key.access_key = new_access_key
            user_access_key.save()
        return user_access_key


user_access_services = UserAccessTokenServices()

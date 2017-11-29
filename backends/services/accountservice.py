# -*- coding: utf8 -*-
import hashlib
import logging

from backends.models.main import BackendAdminUser
from backends.services.exceptions import *

logger = logging.getLogger("default")


class AccountService(object):
    def is_checked(self, username, password):
        m = hashlib.md5()
        m.update(password)
        newpass = m.hexdigest()
        users = BackendAdminUser.objects.filter(username=username)

        if not users:
            raise AccountNotExistError("用户不存在")
        admin = users[0]
        if admin.password != newpass:
            raise PasswordWrongError("密码不正确")
        return True


account_service = AccountService()
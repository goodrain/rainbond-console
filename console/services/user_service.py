# -*- coding: utf8 -*-
import logging

from console.repositories.user_repo import user_repo
from console.repositories.sms_repo import sms_repo
from console.exception.main import ServiceHandleException
from www.models.main import Users

logger = logging.getLogger("default")

class UserService(object):
    def register_by_phone(self,enterprise_id, phone, code, nick_name):
        """手机号注册"""
        # 校验验证码
        valid_code = sms_repo.get_valid_code(phone, "register")
        if not valid_code:
            raise ServiceHandleException(
                msg="verification code expired",
                msg_show="验证码已过期",
                status_code=400
            )
        
        if valid_code.code != code:
            raise ServiceHandleException(
                msg="wrong verification code", 
                msg_show="验证码错误",
                status_code=400
            )

        # 检查手机号是否已注册
        if user_repo.get_user_by_phone(phone):
            raise ServiceHandleException(
                msg="phone already registered",
                msg_show="该手机号已注册",
                status_code=400
            )

        # 检查用户名是否已存在
        if user_repo.get_user_by_user_name(nick_name):
            raise ServiceHandleException(
                msg="username already exists",
                msg_show="用户名已存在",
                status_code=400
            )

        # 创建用户
        user = Users.objects.create(
            phone=phone,
            nick_name=nick_name,
            is_active=True,
            enterprise_id=enterprise_id,
        )

        # 如果是第一个用户,设置为系统管理员
        if Users.objects.count() == 1:
            user.sys_admin = True
            user.save()
        # 验证通过后删除验证码
        valid_code.delete()
        return user

    def login_by_phone(self, phone, code):
        """手机号登录"""
        # 校验验证码
        valid_code = sms_repo.get_valid_code(phone, "login")
        if not valid_code:
            raise ServiceHandleException(
                msg="verification code expired",
                msg_show="验证码已过期",
                status_code=400
            )
        
        if valid_code.code != code:
            raise ServiceHandleException(
                msg="wrong verification code", 
                msg_show="验证码错误",
                status_code=400
            )

        # 获取用户
        user = user_repo.get_user_by_phone(phone)
        if not user:
            raise ServiceHandleException(
                msg="user not found",
                msg_show="用户不存在",
                status_code=404
            )

        # 验证通过后删除验证码
        valid_code.delete()
        return user

user_service = UserService() 
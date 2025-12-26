# -*- coding: utf-8 -*-
from rest_framework import authentication
from rest_framework import exceptions
from django.conf import settings
from www.models.main import Users
import logging

logger = logging.getLogger('default')

class InternalTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        token = request.META.get('HTTP_X_INTERNAL_TOKEN')
        
        if not token:
            return None
        
        internal_token = getattr(settings, 'INTERNAL_API_TOKEN', None)
        
        if not internal_token or token != internal_token:
            return None

        # 如果 Token 匹配，返回一个超级管理员用户
        # 尝试获取系统的第一个超级管理员
        user = Users.objects.filter(sys_admin=True).first()
        
        if not user:
            # 如果没有超级管理员，抛出异常，因为我们需要一个用户上下文
            logger.error("InternalAuth: No superuser found!")
            raise exceptions.AuthenticationFailed('No superuser found for internal authentication')
            
        return (user, None)

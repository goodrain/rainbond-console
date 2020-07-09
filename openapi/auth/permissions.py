# -*- coding: utf-8 -*-
# creater by: barnett
import logging
from django.contrib.auth.models import AnonymousUser
from rest_framework.permissions import BasePermission
from openapi.services.api_user_service import apiUserService
logger = logging.getLogger("default")


class OpenAPIPermissions(BasePermission):
    def has_perms(self, user, perms):
        if isinstance(user, AnonymousUser):
            return False
        user_perms = apiUserService.get_permissions_by_user(user, user.enterprise_id)
        if "all" in user_perms:
            return True
        for perm in perms:
            if perm in user_perms:
                return True
        return False

    def has_permission(self, request, view):
        '''
        check permission
        '''
        if not request.user:
            return False
        view_perms = ["common"]
        if hasattr(view, "view_perms"):
            view_perms = view.view_perms
        return self.has_perms(request.user, view_perms)

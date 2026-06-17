# -*- coding: utf-8 -*-
# creater by: barnett
import logging
from typing import Any, List
from www.models.main import AnonymousUser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

logger = logging.getLogger("default")


class OpenAPIPermissions(BasePermission):
    def has_perms(self, user: Any, perms: List[str]) -> bool:
        if isinstance(user, AnonymousUser):
            return False
        return True

    def has_permission(self, request: Request, view: Any) -> bool:
        '''
        check permission
        '''
        if not request.user:
            return False
        view_perms = ["common"]
        if hasattr(view, "view_perms"):
            view_perms = view.view_perms
        return self.has_perms(request.user, view_perms)

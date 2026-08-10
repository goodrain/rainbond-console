# -*- coding: utf8 -*-
from typing import Any, Optional

from console.models.main import LoginEvent


class LoginEventRepo(object):
    @staticmethod
    def get_last_one(enterprise_id: str, username: str) -> Optional[LoginEvent]:
        return LoginEvent.objects.filter(enterprise_id=enterprise_id, username=username).order_by("-ID").first()

    @staticmethod
    def create(**data: Any) -> None:
        LoginEvent.objects.create(**data)


login_event_repo = LoginEventRepo()

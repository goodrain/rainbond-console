# -*- coding: utf8 -*-
from console.models.main import LoginEvent


class LoginEventRepo(object):
    @staticmethod
    def get_last_one(enterprise_id, username):
        events = LoginEvent.objects.filter(enterprise_id=enterprise_id, username=username).order_by("-ID")
        if not events:
            return None
        return events[0]

    @staticmethod
    def create(**data):
        LoginEvent.objects.create(**data)


login_event_repo = LoginEventRepo()

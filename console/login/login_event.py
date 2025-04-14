# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from console.models.main import LoginEvent as LoginEventModel
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


class LoginEvent(object):
    def __init__(self, user, repo, request=None):
        self.repo = repo
        self.username = user.username
        self.enterprise_id = user.enterprise_id
        self.client_ip = ""
        self.user_agent = ""
        if request:
            self.client_ip = self.__get_client_ip(request)
            self.user_agent = request.META['HTTP_USER_AGENT']
            logger.info("{0} {1}".format(self.client_ip, self.user_agent))
        # get the last login event
        self.login_event = repo.get_last_one(self.enterprise_id, self.username)

    @staticmethod
    def __get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def login(self):
        # create a new one
        self.login_event = LoginEventModel(
            event_id=make_uuid(),
            enterprise_id=self.enterprise_id,
            username=self.username,
            login_time=datetime.now(),
            last_active_time=datetime.now(),
            client_ip=self.client_ip,
            user_agent=self.user_agent,
        )
        self.repo.create(**self.login_event.to_dict())

    def logout(self):
        if not self.login_event:
            logger.warning("no login event. username: {}".format(self.username))
            return
        # finish the event
        self.login_event.logout_time = datetime.now()
        self.active()

    def active(self):
        if self.login_event:
            self.login_event.last_active_time = datetime.now()
            delta = self.login_event.last_active_time - self.login_event.login_time
            self.login_event.duration = delta.seconds
            self.login_event.save()

# -*- coding: utf-8 -*-
# creater by: barnett
from region_client.api.base import Base


class Event(Base):
    def __init__(self, api):
        super(Event, self).__init__(api)
        self.api = api

    def list_events(self, page=1, pageSize=10, only_return_body=False):
        list_teanants_path = "/v2/events?page={0}&pageSize={1}".format(page, pageSize)
        re, body = self.api.GET(list_teanants_path)
        if only_return_body:
            return body
        return re, body

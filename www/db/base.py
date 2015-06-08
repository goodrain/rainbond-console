# -*- coding: utf8 -*-
from addict import Dict
from django.db import connections


class BaseConnection(object):
    def __init__(self, db_alias='default', *args, **kwargs):
        self.db_alias = db_alias

    def _dict_fetch_all(self, cursor):
        desc = cursor.description
        return [
            Dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
        ]

    def query(self, sql):
        cursor = connections[self.db_alias].cursor()
        cursor.execute(sql)
        return self._dict_fetch_all(cursor)

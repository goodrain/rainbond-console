# -*- coding: utf8 -*-
from typing import Any, List, Optional

from addict import Dict
from django.db import connections

from console.utils.database import database_type, normalize_result_column


class BaseConnection(object):
    def __init__(self, db_alias: str = 'default', *args: Any, **kwargs: Any) -> None:
        self.db_alias = db_alias

    def _dict_fetch_all(self, cursor: Any) -> List[Any]:
        desc = cursor.description
        columns = [normalize_result_column(col[0], database_type()) for col in desc]
        return [Dict(list(zip(columns, row))) for row in cursor.fetchall()]

    def query(self, sql: str, args: Optional[Any] = None) -> List[Any]:
        cursor = connections[self.db_alias].cursor()
        cursor.execute(sql, args)
        return self._dict_fetch_all(cursor)

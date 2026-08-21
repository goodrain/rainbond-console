# -*- coding: utf8 -*-
from typing import Any, List, Optional

from addict import Dict
from django.db import connections


class BaseConnection(object):
    def __init__(self, db_alias: str = 'default', *args: Any, **kwargs: Any) -> None:
        self.db_alias = db_alias

    def _dict_fetch_all(self, cursor: Any) -> List[Any]:
        desc = cursor.description
        columns = ["ID" if str(col[0]) == "ID" else str(col[0]).lower() for col in desc]
        return [Dict(list(zip(columns, row))) for row in cursor.fetchall()]

    def query(self, sql: str, args: Optional[Any] = None) -> List[Any]:
        cursor = connections[self.db_alias].cursor()
        cursor.execute(sql, args)
        return self._dict_fetch_all(cursor)

    def paginate(self, sql: str, offset: int, limit: int) -> str:
        offset = max(int(offset), 0)
        limit = max(int(limit), 0)
        suffix = connections[self.db_alias].ops.limit_offset_sql(offset, offset + limit)
        return "{} {}".format(sql.rstrip().rstrip(";"), suffix)

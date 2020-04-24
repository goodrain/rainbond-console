# -*- coding: utf-8 -*-
# creater by: barnett
import re

urlregex = re.compile(
    r'^(?:http|ftp|ws)s?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$',
    re.IGNORECASE)
ipregex = re.compile(r'((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}', re.IGNORECASE)


def pagination(data, total, page=1, page_size=10):
    return {
        "list": data,
        "total": total,
        "page": page,
        "page_size": page_size
    }

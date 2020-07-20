# -*- coding: utf-8 -*-
# creater by: barnett
import re
import six
import datetime
from pytz import timezone
from django.conf import settings
from rest_framework.fields import CharField

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
    return {"list": data, "total": total, "page": page, "page_size": page_size}


cst_tz = timezone(settings.TIME_ZONE)
utc_tz = timezone('UTC')


class DateCharField(CharField):
    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, six.string_types + six.integer_types + (float, datetime.datetime)):
            self.fail('invalid')
        if isinstance(data, datetime.datetime):
            value = data.utcnow().replace(tzinfo=utc_tz).astimezone(cst_tz).isoformat()
            value = value[:19] + 'Z' + value[-5:]
        else:
            value = six.text_type(data)
        return value.strip() if self.trim_whitespace else value

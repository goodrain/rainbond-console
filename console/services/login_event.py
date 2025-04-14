# -*- coding: utf8 -*-
import logging

from django.db.models import Q
from django.core.paginator import Paginator

from console.models.main import LoginEvent

logger = logging.getLogger("default")


class LogEventService(object):
    @staticmethod
    def list_log_events(enterprise_id, username, event_type, start_time, end_time, page=1, page_size=10):
        q = Q(enterprise_id=enterprise_id)
        if username:
            q &= Q(username=username)
        if event_type:
            q &= Q(event_type=event_type)
        if start_time:
            q &= Q(login_time__gte=start_time)
        if end_time:
            q &= Q(last_active_time__lte=end_time)
        all_events = LoginEvent.objects.filter(q).order_by("-login_time")
        if not all_events:
            return [], 0

        paginator = Paginator(all_events, page_size)
        if page > paginator.num_pages:
            return [], paginator.count
        events = paginator.page(page)
        return [event.to_dict() for event in events], paginator.count


log_event_service = LogEventService()

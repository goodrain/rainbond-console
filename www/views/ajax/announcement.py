# -*- coding: utf8 -*-

import logging

from django.forms.models import model_to_dict
from django.http import JsonResponse

from backends.models.main import Announcement
from www.decorator import perm_required
from www.views import AuthedView

logger = logging.getLogger("default")


class AnnouncementInfoView(AuthedView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        announcements = Announcement.objects.filter(active=True).order_by("-create_time")
        context = {
            "announcements": [model_to_dict(a) for a in announcements]
        }
        return JsonResponse(data=context, status=200)

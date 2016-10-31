# -*- coding: utf8 -*-
import datetime
import json
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import JsonResponse
from www.views import AuthedView
from www.decorator import perm_required
from django.conf import settings

import logging
from django.template.defaultfilters import length
logger = logging.getLogger('default')


class AdminViews(AuthedView):

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            data["status"] = "success"
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
        return JsonResponse(data, status=500)


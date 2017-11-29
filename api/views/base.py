# -*- coding: utf8 -*-
import logging

from addict import Dict
from rest_framework.views import APIView

logger = logging.getLogger('default')


class BaseAPIView(APIView):
    def __init__(self, *args, **kwargs):
        APIView.__init__(self, *args, **kwargs)
        self.report = Dict({"ok": True})


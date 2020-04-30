# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from console.services.errlog_service import errlog_service
from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class ErrLogView(JWTAuthApiView):
    def post(self, req, *args, **kwargslf):
        msg = req.data.get("msg")
        if msg:
            logger.error("error from frontend: %s".format(msg))
            errlog_service.create(msg)
        return Response(general_message(200, "success", u"ok"), status=200)

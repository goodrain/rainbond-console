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
        username = req.data.get("username")
        enterprise_id = req.data.get("enterprise_id")
        address = req.data.get("address")
        if msg:
            logger.error("error from frontend: {}".format(msg))
            errlog_service.create(msg, username, enterprise_id, address)
        return Response(general_message(200, "success", "ok"), status=200)

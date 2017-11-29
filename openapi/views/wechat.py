# -*- coding: utf8 -*-
from rest_framework.response import Response
from openapi.views.base import BaseAPIView

import json
import logging
from www.wechat.openapi import MPWeChatAPI
logger = logging.getLogger("default")


class WechatTokenView(BaseAPIView):

    allowed_methods = ('GET',)

    def get(self, request, *args, **kwargs):
        """
        查询微信的access_token
        ---
        parameters:
            - name: wechat_config
              description: 服务ID
              required: false
              type: string
              paramType: form
        """
        config_name = request.data.get("config", "goodrain")
        logger.debug("openapi.cloudservice", "now query wecheat {} token:".format(config_name))
        #
        mp_api = MPWeChatAPI()
        access_token = mp_api.get_access_token()
        logger.debug("openapi.cloudservice", "access token is: {0}".format(access_token))
        return Response(status=200, data={"success": True, "data": {"access_token": access_token}})

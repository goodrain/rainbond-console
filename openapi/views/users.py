# -*- coding: utf8 -*-
from rest_framework.response import Response

from www.models import *
import logging
from www.monitorservice.monitorhook import MonitorHook
from openapi.views.base import BaseAPIView
from openapi.controllers.openservicemanager import OpenTenantServiceManager
manager = OpenTenantServiceManager()
monitorhook = MonitorHook()
logger = logging.getLogger("default")


class UserInfoView(BaseAPIView):

    allowed_methods = ('GET',)

    def get(self, request, *args, **kwargs):
        """
        根据用户uid查询用户open_id(公众平台的open_id)
        ---
        parameters:
            - name: user_id
              description: 用户id
              required: true
              type: string
              paramType: path
            - name: wechat_type
              description: 微信号标示，默认为goodrain
              required: false
              type: string
              paramType: form
        """
        logger.debug("openapi.user", request.data)
        user_id = request.data.get("user_id", None)
        if user_id is None:
            return Response(status=405, data={"success": False, "msg": u"用户user_id为空"})
        wechat_type = request.data.get("wechat_type", "goodrain")
        # 查询是否有当前用户
        try:
            user = Users.objects.get(pk=user_id)
        except Exception as e:
            return Response(status=406, data={"success": False, "msg": u"用户不存在!"})
        # 检查wechat_type是否有对应的微信信息
        union_id = user.union_id
        try:
            wechat_user = WeChatUser.objects.get(union_id=union_id, config=wechat_type)
        except Exception as e:
            return Response(status=408, data={"success": False, "msg": u"微信信息不存在!"})

        open_id = wechat_user.open_id
        logger.debug("openapi.user", "user:{0}'s open_id is {1}".format(user_id, open_id))
        json_data = {"open_id": open_id}
        return Response(status=200, data={"success": True, "user_info": json_data})



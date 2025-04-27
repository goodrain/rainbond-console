# -*- coding: utf8 -*-
import logging
from rest_framework import status
from rest_framework.response import Response

from console.exception.main import ServiceHandleException
from console.views.base import BaseApiView
from console.services.sms_service import sms_service
from www.utils.return_message import general_message

logger = logging.getLogger("default")

class SMSVerificationView(BaseApiView):
    def post(self, request, *args, **kwargs):
        """
        发送短信验证码
        ---
        parameters:
            - name: phone
              description: 手机号
              required: true
              type: string
              paramType: form
            - name: purpose
              description: 用途(register/login)
              required: true
              type: string
              paramType: form
        """
        try:
            phone = request.data.get("phone")
            purpose = request.data.get("purpose")

            if not phone:
                result = general_message(400, "参数错误", "手机号不能为空")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

            if not purpose or purpose not in ["register", "login"]:
                result = general_message(400, "参数错误", "无效的验证码用途")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

            sms_service.send_verification_code(phone, purpose)
            
            result = general_message(200, "success", "验证码发送成功")
            return Response(result, status=status.HTTP_200_OK)
        except ServiceHandleException as e:
            raise e
        except Exception as e:
            logger.exception(e)
            result = general_message(500, "发送验证码失败", str(e))
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
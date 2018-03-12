# coding:utf-8
import logging
from datetime import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import JSONWebTokenAPIView, jwt_response_payload_handler

from console.serializer import CustomJWTSerializer
from www.services import user_svc
from www.utils.return_message import general_message, error_message


class JWTTokenView(JSONWebTokenAPIView):
    serializer_class = CustomJWTSerializer

    def post(self, request, *args, **kwargs):
        """
        用户登录接口
        ---
        parameters:
            - name: nick_name
              description: 用户名
              required: true
              type: string
              paramType: form
            - name: password
              description: 密码
              required: true
              type: string
              paramType: form
        """
        nick_name = request.POST.get("nick_name", None)
        password = request.POST.get("password", None)
        try:
            if not nick_name:
                code = 400
                result = general_message(code, "username is missing", "请填写用户名")
                return Response(result, status=code)
            elif not password:
                code = 400
                result = general_message(code, "password is missing", "请填写密码")
                return Response(result, status=code)
            user, msg, code = user_svc.is_exist(nick_name, password)
            if not user:
                code = 400
                result = general_message(code, "authorization fail ", msg)
                return Response(result, status=code)
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                user = serializer.object.get('user') or request.user
                token = serializer.object.get('token')
                response_data = jwt_response_payload_handler(token, user, request)
                result = general_message(200, "login success", "登录成功", bean=response_data)
                response = Response(result)
                if api_settings.JWT_AUTH_COOKIE:
                    expiration = (datetime.utcnow() +
                                  api_settings.JWT_EXPIRATION_DELTA)
                    response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                        token,
                                        expires=expiration,
                                        httponly=True)
                return response
            result = general_message(400, "login failed", "{}".format(list(dict(serializer.errors).values())[0][0]))
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.exception(e)
            result = error_message()
            return Response(result, status=500)

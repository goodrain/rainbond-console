# coding:utf-8
import logging
import datetime

from console.login.login_event import LoginEvent
from console.repositories.login_event import login_event_repo
from console.services.operation_log import operation_log_service, Operation, OperationModule
from console.utils.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import JSONWebTokenAPIView, jwt_response_payload_handler

from console.serializer import CustomJWTSerializer
from console.login.jwt_manager import JwtManager
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
        captcha_code = request.POST.get("captcha_code", None)
        real_captcha_code = request.session.get("captcha_code")
        is_validate = request.POST.get("is_validate", False)
        times = cache.get(nick_name)
        pass_error_times = cache.get(nick_name + "pass_error_times")
        if pass_error_times and int(pass_error_times) >= 4:
            ten_min = cache.get(nick_name + "freeze")
            if not ten_min:
                ten_min = (datetime.datetime.now() + datetime.timedelta(minutes=10)).strftime('%H:%M:%S')
                cache.set(nick_name + "freeze", ten_min, 600)
                cache.set(nick_name + "pass_error_times", pass_error_times, 600)
                freeze_time = ten_min
            elif type(ten_min) == bytes:
                freeze_time = str(ten_min, encoding='utf-8')
            else:
                freeze_time = str(ten_min)
            return Response(
                general_message(400, "captcha code error", "连续登录失败次数过多,{0}后重试".format(freeze_time),
                                {"is_verification_code": True}),
                status=400)
        times = 1 if not times else int(times) + 1
        if is_validate == "false" and (real_captcha_code is None or captcha_code is None
                                       or real_captcha_code.lower() != captcha_code.lower()):
            return Response(general_message(400, "captcha code error", "验证码有误", {"is_verification_code": True}), status=400)
        if is_validate == "true" and times > 3 and (real_captcha_code is None or captcha_code is None
                                                    or real_captcha_code.lower() != captcha_code.lower()):
            cache.set(nick_name, times, 3600)
            return Response(general_message(400, "captcha code error", "验证码有误", {"is_verification_code": True}), status=400)
        cache.set(nick_name, times, 3600)
        # Invalidate the verification code after verification
        request.session["captcha_code"] = None
        request.session.save()
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
                    # 设置10年过期时间，相当于永久
                    expiration = (datetime.datetime.now() + datetime.timedelta(days=3650))
                    response.set_cookie(api_settings.JWT_AUTH_COOKIE, token, expires=expiration)
                jwt_manager = JwtManager()
                jwt_manager.set(response_data["token"], user.user_id)
                login_event = LoginEvent(user, login_event_repo, request=request)
                login_event.login()
                comment = operation_log_service.generate_generic_comment(
                    operation=Operation.FINISH, module=OperationModule.LOGIN, module_name="")
                operation_log_service.create_enterprise_log(user=user, comment=comment,
                                                            enterprise_id=user.enterprise_id)
                return response
            result = general_message(400, "login failed", "{}".format(list(dict(serializer.errors).values())[0][0]))
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.exception(e)
            result = error_message()
            return Response(result, status=500)

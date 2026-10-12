# coding:utf-8
import logging
import datetime
import secrets
from typing import Any

from console.login.login_event import LoginEvent
from console.repositories.login_event import login_event_repo
from console.services.operation_log import operation_log_service, Operation, OperationModule
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from console.serializer import CustomJWTSerializer
from console.login.jwt_manager import JwtManager
from console.services.login_security_service import (LOGIN_FAILURE_THRESHOLD, LOGIN_LOCK_SECONDS,
                                                     login_attempt_service, login_security_config_service)
from console.utils import jwt_issuer
from www.utils.return_message import general_message, error_message


def _consume_captcha(request: Request, provided_code: Any) -> bool:
    expected_code = request.session.pop("captcha_code", None)
    request.session.save()
    if expected_code is None or provided_code is None:
        return False
    return secrets.compare_digest(str(expected_code).casefold(), str(provided_code).strip().casefold())


def _locked_response(retry_after: int) -> Response:
    response = Response(
        general_message(
            429,
            "login temporarily locked",
            "登录失败次数过多，请 {0} 秒后重试".format(retry_after),
            bean={"retry_after": retry_after},
        ),
        status=429,
    )
    response["Retry-After"] = str(retry_after)
    return response


class JWTTokenView(APIView):
    permission_classes = (AllowAny, )
    authentication_classes = ()
    serializer_class = CustomJWTSerializer

    def get_serializer(self, *args: Any, **kwargs: Any) -> CustomJWTSerializer:
        return self.serializer_class(*args, **kwargs)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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
            config = login_security_config_service.get_config(login_identifier=nick_name)
            attempt_identity = None
            if config["login_limit_enabled"]:
                attempt_identity = login_attempt_service.identity(nick_name)
                retry_after = login_attempt_service.lock_remaining(attempt_identity)
                if retry_after > 0:
                    return _locked_response(retry_after)

            if config["login_captcha_enabled"]:
                captcha_code = request.POST.get("captcha_code", None)
                if not _consume_captcha(request, captcha_code):
                    return Response(general_message(400, "captcha code error", "验证码错误"), status=400)

            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data.get('user') or request.user
                token = serializer.validated_data.get('token')
                if attempt_identity is not None:
                    login_attempt_service.clear(attempt_identity)
                response_data = jwt_issuer.jwt_response_payload(token, user, request)
                result = general_message(200, "login success", "登录成功", bean=response_data)
                response = Response(result)
                if jwt_issuer.JWT_AUTH_COOKIE:
                    # 设置10年过期时间，相当于永久
                    expiration = (datetime.datetime.now() + datetime.timedelta(days=3650))
                    response.set_cookie(jwt_issuer.JWT_AUTH_COOKIE, token, expires=expiration)
                jwt_manager = JwtManager()
                # NOTE: user resolves to Any|User|AnonymousUser; user_id/enterprise_id are on
                # the concrete Users model (union-attr backlog).
                jwt_manager.set(response_data["token"], user.user_id)  # type: ignore[union-attr]
                login_event = LoginEvent(user, login_event_repo, request=request)
                login_event.login()
                comment = operation_log_service.generate_generic_comment(
                    operation=Operation.FINISH, module=OperationModule.LOGIN, module_name="")
                operation_log_service.create_enterprise_log(user=user, comment=comment,
                                                            enterprise_id=user.enterprise_id)  # type: ignore[union-attr]
                return response
            if config["login_limit_enabled"] and attempt_identity is not None:
                failure_count = login_attempt_service.record_failure(attempt_identity)
                if failure_count is not None and failure_count >= LOGIN_FAILURE_THRESHOLD:
                    return _locked_response(LOGIN_LOCK_SECONDS)
            result = general_message(400, "login failed", "用户名或密码错误")
            return Response(result, status=400)
        except Exception as e:
            logging.exception(e)
            result = error_message()
            return Response(result, status=500)

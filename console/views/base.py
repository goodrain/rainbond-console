# -*- coding: utf8 -*-
import json
import logging
import os

import jwt
from addict import Dict
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils import six
from django.utils.encoding import smart_text
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as trans
from rest_framework import exceptions, status
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView, set_rollback
from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication
from rest_framework_jwt.settings import api_settings

from console.exception.exceptions import AuthenticationInfoHasExpiredError
from console.exception.main import (BusinessException, ResourceNotEnoughException, ServiceHandleException)
from console.models.main import OAuthServices, UserOAuthServices
from console.repositories.enterprise_repo import enterprise_repo
from console.utils.oauth.oauth_types import get_oauth_instance
from entsrv_client.rest import ApiException as EnterPriseCenterApiException
from goodrain_web import errors
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.models.main import Tenants, Users

jwt_get_username_from_payload = api_settings.JWT_PAYLOAD_GET_USERNAME_HANDLER
jwt_decode_handler = api_settings.JWT_DECODE_HANDLER
logger = logging.getLogger("default")
jwt_response_payload_handler = api_settings.JWT_RESPONSE_PAYLOAD_HANDLER


class JSONWebTokenAuthentication(BaseJSONWebTokenAuthentication):
    """
    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string specified in the setting
    `JWT_AUTH_HEADER_PREFIX`. For example:

        Authorization: JWT eyJhbGciOiAiSFMyNTYiLCAidHlwIj
    """
    www_authenticate_realm = 'api'

    def get_jwt_value(self, request):
        auth = get_authorization_header(request).split()
        auth_header_prefix = api_settings.JWT_AUTH_HEADER_PREFIX.lower()

        if not auth:
            if api_settings.JWT_AUTH_COOKIE:
                return request.COOKIES.get(api_settings.JWT_AUTH_COOKIE)
            return None

        if smart_text(auth[0].lower()) != auth_header_prefix:
            return None

        if len(auth) == 1:
            msg = _('请求头不合法，未提供认证信息')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _("请求头不合法")
            raise exceptions.AuthenticationFailed(msg)
        return auth[1]

    def authenticate(self, request):
        """
        Returns a two-tuple of `User` and token if a valid signature has been
        supplied using JWT-based authentication.  Otherwise returns `None`.
        """
        # update request authentication info

        jwt_value = self.get_jwt_value(request)
        if jwt_value is None:
            msg = _('未提供验证信息')
            raise AuthenticationInfoHasExpiredError(msg)
        # if have SSO login modules
        if settings.MODULES.get('SSO_LOGIN', None):
            sso_user_id = request.COOKIES.get('uid')
            sso_user_token = jwt_value

            if not sso_user_id or not sso_user_token:
                msg = _("Cookie信息里面应该包含Token和用户uid")
                raise AuthenticationInfoHasExpiredError(msg)

            if sso_user_id == 'null' or sso_user_token == 'null':
                msg = _("Cookie信息里面应该包含Token和用户uid")
                raise AuthenticationInfoHasExpiredError(msg)
            try:
                user = Users.objects.get(sso_user_id=sso_user_id)
                return user, None
            except Users.DoesNotExist:
                msg = _('认证信息错误')
                raise AuthenticationInfoHasExpiredError(msg)
        else:
            try:
                payload = jwt_decode_handler(jwt_value)
            except jwt.ExpiredSignature:
                msg = _('认证信息已过期')
                raise AuthenticationInfoHasExpiredError(msg)
            except jwt.DecodeError:
                msg = _('认证信息错误')
                raise AuthenticationInfoHasExpiredError(msg)
            except jwt.InvalidTokenError:
                msg = _('认证信息错误,请求Token不合法')
                raise AuthenticationInfoHasExpiredError(msg)

            user = self.authenticate_credentials(payload)
            return user, jwt_value

    def authenticate_credentials(self, payload):
        """
        Returns an active user that matches the payload's user id and email.
        """
        username = jwt_get_username_from_payload(payload)
        if not username:
            msg = _('认证信息不合法.')
            # raise exceptions.AuthenticationFailed(msg)
            logger.debug('==========================>{}'.format(msg))
            raise AuthenticationInfoHasExpiredError(msg)

        try:
            user = Users.objects.get(nick_name=username)
        except Users.DoesNotExist:
            msg = _('签名不合法.')
            raise AuthenticationInfoHasExpiredError(msg)

        if not user.is_active:
            msg = _('用户身份未激活.')
            raise AuthenticationInfoHasExpiredError(msg)

        return user


class BaseApiView(APIView):
    permission_classes = (AllowAny, )

    def __init__(self, *args, **kwargs):
        super(BaseApiView, self).__init__(*args, **kwargs)
        self.report = Dict({"ok": True})


class AlowAnyApiView(APIView):
    """
    该API不需要通过任何认证
    """
    permission_classes = (AllowAny, )
    authentication_classes = ()

    def __init__(self, *args, **kwargs):
        super(AlowAnyApiView, self).__init__(*args, **kwargs)
        self.report = Dict({"ok": True})
        self.user = None

    def initial(self, request, *args, **kwargs):
        self.user = request.user


class JWTAuthApiView(APIView):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (JSONWebTokenAuthentication, )

    def __init__(self, *args, **kwargs):
        super(JWTAuthApiView, self).__init__(*args, **kwargs)
        self.report = Dict({"ok": True})
        self.user = None

    def initial(self, request, *args, **kwargs):
        self.user = request.user


class CloudEnterpriseCenterView(JWTAuthApiView):
    def __init__(self, *args, **kwargs):
        super(CloudEnterpriseCenterView, self).__init__(*args, **kwargs)
        self.oauth_instance = None
        self.oauth = None
        self.oauth_user = None

    def initial(self, request, *args, **kwargs):
        super(CloudEnterpriseCenterView, self).initial(request, *args, **kwargs)
        try:
            oauth_service = OAuthServices.objects.get(oauth_type="enterprisecenter", ID=1)
            pre_enterprise_center = os.getenv("PRE_ENTERPRISE_CENTER", None)
            if pre_enterprise_center:
                oauth_service = OAuthServices.objects.get(name=pre_enterprise_center, oauth_type="enterprisecenter")
            oauth_user = UserOAuthServices.objects.get(service_id=oauth_service.ID, user_id=self.user.user_id)
        except OAuthServices.DoesNotExist:
            raise NotFound("enterprise center oauth server not found")
        except UserOAuthServices.DoesNotExist:
            msg = _('用户身份未在企业中心认证')
            raise AuthenticationInfoHasExpiredError(msg)
        self.oauth_instance = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
        if not self.oauth_instance:
            msg = _('未找到企业中心OAuth服务类型')
            raise AuthenticationInfoHasExpiredError(msg)


class RegionTenantHeaderView(JWTAuthApiView):
    def __init__(self, *args, **kwargs):
        super(RegionTenantHeaderView, self).__init__(*args, **kwargs)
        self.response_region = None
        self.region_name = None
        self.tenant_name = None
        self.team_name = None
        self.tenant = None
        self.team = None
        self.report = Dict({"ok": True})
        self.user = None

    def initial(self, request, *args, **kwargs):

        super(RegionTenantHeaderView, self).initial(request, *args, **kwargs)
        self.response_region = kwargs.get("region_name", None)
        self.tenant_name = kwargs.get("tenantName", None)
        if kwargs.get("team_name", None):
            self.tenant_name = kwargs.get("team_name", None)
            self.team_name = self.tenant_name
        else:
            self.team_name = self.tenant_name
        self.user = request.user
        if not self.response_region:
            self.response_region = request.META.get('HTTP_X_REGION_NAME', None)
        if not self.tenant_name:
            self.tenant_name = request.META.get('HTTP_X_TEAM_NAME', None)

        if not self.response_region:
            self.response_region = self.request.COOKIES.get('region_name', None)
        if not self.tenant_name:
            self.tenant_name = self.request.COOKIES.get('team', None)

        if not self.response_region:
            raise ImportError("region_name not found !")
        self.region_name = self.response_region
        if not self.tenant_name:
            raise ImportError("team_name not found !")
        if self.tenant_name:
            try:
                self.tenant = Tenants.objects.get(tenant_name=self.tenant_name)
                self.team = self.tenant
            except Tenants.DoesNotExist:
                raise NotFound("tenant {0} not found".format(self.tenant_name))


class EnterpriseHeaderView(JWTAuthApiView):
    def __init__(self, *args, **kwargs):
        super(EnterpriseHeaderView, self).__init__(*args, **kwargs)
        self.enterprise = None

    def initial(self, request, *args, **kwargs):
        super(EnterpriseHeaderView, self).initial(request, *args, **kwargs)
        eid = kwargs.get("eid", None)
        if not eid:
            raise ImportError("enterprise_id not found !")
        self.enterprise = enterprise_repo.get_enterprise_by_enterprise_id(eid)
        if not self.enterprise:
            raise NotFound("enterprise id: {};enterprise not found".format(eid))


def custom_exception_handler(exc, context):
    """
        Returns the response that should be used for any given exception.

        By default we handle the REST framework `APIException`, and also
        Django's built-in `Http404` and `PermissionDenied` exceptions.

        Any unhandled exceptions may return `None`, which will cause a 500 error
        to be raised.
    """
    if isinstance(exc, RegionApiBaseHttpClient.InvalidLicenseError):
        data = {"code": 10400, "msg": "invalid license", "msg_show": "license不正确或已过期"}
        return Response(data, status=401)
    if isinstance(exc, ServiceHandleException):
        return exc.response
    elif isinstance(exc, ResourceNotEnoughException):
        data = {"code": 10406, "msg": "resource is not enough", "msg_show": exc.message}
        return Response(data, status=412)
    elif isinstance(exc, RegionApiBaseHttpClient.CallApiFrequentError):
        data = {"code": 409, "msg": "wait a moment please", "msg_show": "操作过于频繁，请稍后再试"}
        return Response(data, status=409)
    elif isinstance(exc, RegionApiBaseHttpClient.CallApiError):
        if exc.message.get("httpcode") == 404:
            data = {"code": 404, "msg": "region no found this resource", "msg_show": u"数据中心资源不存在"}
        else:
            data = {"code": 400, "msg": exc.message, "msg_show": u"数据中心操作失败"}
        return Response(data, status=404)
    elif isinstance(exc, ValidationError):
        return Response({"detail": "参数错误", "err": exc.detail, "code": 20400}, status=exc.status_code)
    elif isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        if isinstance(exc.detail, dict):
            data = exc.detail
        else:
            data = {'detail': exc.detail}

        set_rollback()
        # 处理数据为标准返回格式
        data.update({"code": exc.status_code, "msg": "{0}".format(exc.detail), "msg_show": "{0}".format(exc.detail)})
        return Response(data, status=exc.status_code, headers=headers)
    elif isinstance(exc, AuthenticationInfoHasExpiredError):
        data = {"code": 10405, "msg": "Signature has expired.", "msg_show": "身份认证信息失败，请登录"}
        return Response(data, status=403)
    elif isinstance(exc, Http404):
        msg = trans('Not found.')
        data = {'detail': six.text_type(msg)}
        # 处理数据为标准返回格式
        data.update({
            "code": status.HTTP_404_NOT_FOUND,
            "msg": "{0}".format(six.text_type(msg)),
            "msg_show": "{0}".format(six.text_type(msg))
        })
        set_rollback()
        return Response(data, status=status.HTTP_404_NOT_FOUND)
    elif isinstance(exc, PermissionDenied):
        msg = trans('Permission denied.')
        data = {'detail': six.text_type(msg)}
        # 处理数据为标准返回格式
        data.update({
            "code": status.HTTP_403_FORBIDDEN,
            "msg": "{0}".format(six.text_type(msg)),
            "msg_show": "{0}".format("不允许的操作")
        })
        set_rollback()
        return Response(data, status=status.HTTP_403_FORBIDDEN)
    elif isinstance(exc, errors.PermissionDenied):
        msg = trans('Permission denied.')
        data = {'detail': six.text_type(msg)}
        # 处理数据为标准返回格式
        data.update({
            "code": status.HTTP_403_FORBIDDEN,
            "msg": "{0}".format(six.text_type(msg)),
            "msg_show": "{0}".format("您无权限执行此操作")
        })
        set_rollback()
        return Response(data, status=status.HTTP_403_FORBIDDEN)
    elif isinstance(exc, BusinessException):
        return exc.get_response()
    elif isinstance(exc, ImportError):
        # 处理数据为标准返回格式
        data = {"code": status.HTTP_400_BAD_REQUEST, "msg": exc.message, "msg_show": "{0}".format("请求参数不全")}
        return Response(data, status=status.HTTP_400_BAD_REQUEST)
    elif isinstance(exc, EnterPriseCenterApiException):
        # 处理数据为标准返回格式
        try:
            body = json.loads(exc.body)
            code = body.get("code")
            msg = body.get("msg")
        except Exception:
            code = 400
            msg = exc.body
        data = {"code": code, "msg": msg, "msg_show": "{0}".format("企业中心接口错误")}
        return Response(data, status=status.HTTP_400_BAD_REQUEST)
    else:
        logger.exception(exc)
        return Response({"code": 10401, "msg": exc.message, "msg_show": "服务端异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

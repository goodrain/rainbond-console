# -*- coding: utf8 -*-
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.models import User as OAuthUser

import requests

from www.models import Users

from rest_framework.views import APIView
import logging

from oauth2_provider.views.base import OAuthLibMixin
from oauth2_provider.models import Application
from oauth2_provider.settings import oauth2_settings

logger = logging.getLogger("default")


class AccessTokenView(APIView, OAuthLibMixin):

    allowed_methods = ('POST',)
    server_class = oauth2_settings.OAUTH2_SERVER_CLASS
    validator_class = oauth2_settings.OAUTH2_VALIDATOR_CLASS
    oauthlib_backend_class = oauth2_settings.OAUTH2_BACKEND_CLASS

    def post(self, request, *args, **kwargs):
        """
        获取用户token
        ---
        parameters:
            - name: username
              description: 用户名
              required: true
              type: string
              paramType: form
            - name: password
              description: 密码
              required: true
              type: string
              paramType: form
            - name: client_id
              description: 应用id
              required: true
              type: string
              paramType: form
            - name: client_secret
              description: 应用的加密串
              required: true
              type: string
              paramType: form
            - name: grant_type
              description: oauth2授权类型,现在支持password
              required: true
              type: string
              paramType: form
        """
        # 数据中心
        username = request.data.get("username")
        password = request.data.get("password")
        client_id = request.data.get("client_id")
        client_secret = request.data.get("client_secret")
        grant_type = request.data.get("grant_type")
        if grant_type != "password":
            return Response(status=405, data={"success": False, "msg": u"授权类型不支持!"})
        config_client_id = settings.OAUTH2_APP.get("CLIENT_ID")
        config_client_secret = settings.OAUTH2_APP.get("CLIENT_SECRET")

        if username is None:
            return Response(status=406, data={"success": False, "msg": u"用户名不能为空"})
        if password is None:
            return Response(status=408, data={"success": False, "msg": u"密码不能为空"})
        if client_id != config_client_id or client_secret != config_client_secret:
            return Response(status=409, data={"success": False, "msg": u"无效客户端!"})
        # 根据用户名密码查询用户是否存在
        try:
            oauth_user = Users.objects.get(nick_name=username)
            # oauth_user = OAuthUser.objects.get(username=username)
            if not oauth_user.check_password(password):
                return Response(status=410, data={"success": False, "msg": u"密码不正确!"})
        except Exception as e:
            return Response(status=411, data={"success": False, "msg": u"用户不存在!"})

        num = Application.objects.filter(client_id=client_id).count()
        if num == 0:
            # 创建auth_user
            app_user = OAuthUser.objects.create(username=client_id)
            app_user.set_password(client_secret)
            app_user.is_staff = True
            app_user.is_superuser = True
            app_user.save()
            # 创建application
            Application.objects.create(client_id=client_id,
                                       user=app_user,
                                       client_type=Application.CLIENT_CONFIDENTIAL,
                                       authorization_grant_type=Application.GRANT_PASSWORD,
                                       client_secret=client_secret,
                                       name="console")
        # 使用httplib查询token
        tdata = {
            'username': username + "_token",
            'password': password,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': grant_type
        }
        scheme = request.scheme
        host = request.get_host()
        path = "/openapi/oauth2/token/"
        token_url = "{0}://{1}{2}".format(scheme, host, path)
        logger.debug(token_url)
        r = requests.post(token_url, data=tdata)
        return Response(data=r.json(), status=200)
        # # 跳转到api/oauth2/token/
        # url, headers, body, status = self.create_token_response(request)
        # response = HttpResponse(content=body, status=status)
        #
        # for k, v in headers.items():
        #     response[k] = v
        # return response



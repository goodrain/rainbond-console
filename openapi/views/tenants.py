# -*- coding: utf8 -*-
from rest_framework.response import Response

from django.contrib.auth.models import User as OAuthUser

from www.models import Tenants, Users, PermRelTenant
from www.forms.account import is_standard_word, is_sensitive

from rest_framework.views import APIView
from openapi.controllers.openservicemanager import OpenTenantServiceManager
import logging
from www.utils import sn

logger = logging.getLogger("default")
manager = OpenTenantServiceManager()


class TenantServiceView(APIView):

    allowed_methods = ('POST',)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def post(self, request, *args, **kwargs):
        """
        注册用户租户
        ---
        parameters:
            - name: username
              description: 用户名
              required: true
              type: int
              paramType: form
            - name: password
              description: 密码
              required: true
              type: string
              paramType: form
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: form
            - name: region
              description: 数据中心
              required: true
              type: string
              paramType: form
        """
        # 数据中心
        if sn.instance.is_private():
            return Response(status=501, data={"success": False, "msg": u"不允许创建用户!"})

        region = request.data.get("region")
        username = request.data.get("username")
        password = request.data.get("password")
        tenant_name = request.data.get("tenant_name")
        if region is None:
            return Response(status=405, data={"success": False, "msg": u"数据中心名称为空"})
        if username is None:
            return Response(status=406, data={"success": False, "msg": u"用户名不能为空"})
        if tenant_name is None:
            return Response(status=407, data={"success": False, "msg": u"租户名称不能为空!"})
        # 校验username
        try:
            is_standard_word(username)
            is_sensitive(username)
        except Exception as e:
            return Response(status=408, data={"success": False, "msg": u"用户名不合法!"})
        try:
            is_standard_word(tenant_name)
            is_sensitive(tenant_name)
        except Exception as e:
            return Response(status=408, data={"success": False, "msg": u"租户名称不合法!"})

        # 参数log
        logger.debug("openapi.services", "now create user tenant: tenant_name:{0}, region:{1}, username:{2}".format(tenant_name, region, username))

        # 创建用户
        user_exists = True
        try:
            curr_user = Users.objects.get(nick_name=username)
        except Users.DoesNotExist:
            user_exists = False
            rf = "openapi"
            # 用户不存在,检查password
            if password is None:
                return Response(status=410, data={"success": False, "msg": u"密码不能为空"})
            # 新增用户
            curr_user = Users(nick_name=username,
                              client_ip=self.get_client_ip(request),
                              rf=rf)
            if password.endswith("#"):
                return Response(status=411, data={"success": False, "msg": u"密码不能以#结尾"})
            # 设置密码
            curr_user.set_password(password)
            curr_user.save()
            logger.debug("openapi.services", "now create user success")

            # 添加auth_user
            tmpname = username + "_token"
            oauth_user = OAuthUser.objects.create(username=tmpname)
            oauth_user.set_password(password)
            oauth_user.is_staff = True
            oauth_user.save()

        # 处理租户逻辑
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            logger.debug("openapi.services", "Tenant {0} is not exists, now create...".format(tenant_name))
            # 创建tenant
            tenant = manager.create_tenant(tenant_name, region, curr_user.user_id, username)
        if tenant:
            # 添加user-tenant关系
            if not user_exists:
                try:
                    PermRelTenant.objects.create(user_id=curr_user.pk,
                                                 tenant_id=tenant.pk,
                                                 identity='admin')
                except Exception as e:
                    logger.exception("openapi.services", e)

            return Response(status=200, data={"success": True,
                                              "tenant": {
                                                  "tenant_id": tenant.tenant_id,
                                                  "tenant_name": tenant.tenant_name,
                                                  "region": tenant.region
                                              },
                                              "user": {
                                                  "user_id": curr_user.user_id,
                                                  "nick_name": curr_user.nick_name,
                                                  "email": curr_user.email
                                              }})
        else:
            return Response(status=500, data={"success": False,
                                              "msg": "操作失败!"})


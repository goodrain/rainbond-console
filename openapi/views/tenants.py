# -*- coding: utf8 -*-
from rest_framework.response import Response

from www.models import Tenants

from openapi.views.base import BaseAPIView
from openapi.controllers.openservicemanager import OpenTenantServiceManager
import logging

logger = logging.getLogger("default")
manager = OpenTenantServiceManager()


class TenantServiceView(BaseAPIView):

    allowed_methods = ('POST',)

    def post(self, request, tenant_name, *args, **kwargs):
        """
        租户创建接口
        ---
        parameters:
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: path
            - name: region
              description: 数据中心
              required: true
              type: string
              paramType: form
            - name: user_id
              description: 创建人id
              required: true
              type: int
              paramType: form
            - name: username
              description: 创建人姓名
              required: true
              type: string
              paramType: form
        """
        # 数据中心
        region = request.POST.get("region")
        if region is None:
            return Response(status=405, data={"success": False, "msg": u"数据中心名称为空"})
        # 创建人
        user_id = request.POST.get("user_id")
        if user_id is None:
            return Response(status=405, data={"success": False, "msg": u"创建人不能为空"})
        username = request.POST.get("username")
        if username is None:
            return Response(status=405, data={"success": False, "msg": u"创建人不能为空"})
        # 参数log
        logger.debug("openapi.services", "now create tenant: tenant_name:{0}, region:{1}, user_id:{2}, username:{3}".format(tenant_name, region, user_id, username))

        # 根据租户名称获取租户信息
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            if tenant:
                return Response(status=406, data={"success": False, "msg": u"租户名称已经存在"})
        except Tenants.DoesNotExist:
            logger.debug("openapi.services", "Tenant {0} is not exists, now create...".format(tenant_name))
        # 创建tenant
        tenant = manager.create_tenant(tenant_name, region, user_id, username)
        if tenant:
            return Response(status=200, data={"success": True, "tenant": tenant})
        return Response(status=200, data={"success": False, "msg": u"创建失败!"})




# -*- coding: utf8 -*-

from rest_framework.response import Response

from www.models import Tenants, TenantServiceInfo
from openapi.views.base import BaseAPIView
from openapi.controllers.openservicemanager import OpenTenantServiceManager

import re
import logging
logger = logging.getLogger("default")
manager = OpenTenantServiceManager()


class DomainController(BaseAPIView):
    """域名管理模块"""
    allowed_methods = ('POST', 'GET', 'DELETE')

    def get(self, request, service_name, *args, **kwargs):
        """
        获取当前服务的域名
        ---
        parameters:
            - name: service_name
              description: 服务名称
              required: true
              type: string
              paramType: path
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: query

        """
        tenant_name = request.data.get("tenant_name")
        if tenant_name is None:
            logger.error("openapi.services", "租户名称为空!")
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_name)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "Tenant {0} is not exists".format(tenant_name))
            return Response(status=406, data={"success": False, "msg": u"租户不存在,请检查租户名称"})
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "Tenant {0} ServiceAlias {1} is not exists".format(tenant_name, service_name))
            return Response(status=408, data={"success": False, "msg": u"服务名称不存在"})
        # 查询服务
        domain_array = manager.query_domain(service)
        return Response(status=200, data={"success": True, "data": domain_array})

    def post(self, request, service_name, *args, **kwargs):
        """
        当前服务添加域名
        ---
        parameters:
            - name: service_name
              description: 服务名称
              required: true
              type: string
              paramType: path
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: form
            - name: domain_name
              description: 域名
              required: true
              type: string
              paramType: form
            - name: username
              description: 操作人名称
              required: true
              type: string
              paramType: form
        """
        tenant_name = request.data.get("tenant_name")
        if tenant_name is None:
            logger.error("openapi.services", "租户名称为空!")
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})
        domain_name = request.data.get("domain_name")
        if domain_name is None:
            logger.error("openapi.services", "域名称为空!")
            return Response(status=406, data={"success": False, "msg": u"域名称为空"})
        # 名称
        username = request.data.get("username")
        # 汉字校验
        zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
        match = zhPattern.search(domain_name.decode('utf-8'))
        if match:
            logger.error("openapi.services", "绑定域名有汉字!")
            return Response(status=412, data={"success": False, "msg": u"绑定域名有汉字"})

        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_name)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "Tenant {0} is not exists".format(tenant_name))
            return Response(status=408, data={"success": False, "msg": u"租户不存在,请检查租户名称"})
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "Tenant {0} ServiceAlias {1} is not exists".format(tenant_name, service_name))
            return Response(status=409, data={"success": False, "msg": u"服务名称不存在"})
        # 添加domain_name
        status, success, msg = manager.domain_service(action="start",
                                                      service=service,
                                                      domain_name=domain_name,
                                                      tenant_name=tenant_name,
                                                      username=username)
        return Response(status=status, data={"success": success, "msg": msg})

    def delete(self, request, service_name, *args, **kwargs):
        """
        当前服务删除域名
        ---
        parameters:
            - name: service_name
              description: 服务名称
              required: true
              type: string
              paramType: path
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: form
            - name: domain_name
              description: 域名
              required: true
              type: string
              paramType: form
            - name: username
              description: 操作人名称
              required: true
              type: string
              paramType: form
        """
        tenant_name = request.data.get("tenant_name")
        if tenant_name is None:
            logger.error("openapi.services", "租户名称为空!")
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})
        domain_name = request.data.get("domain_name")
        if domain_name is None:
            logger.error("openapi.services", "域名称为空!")
            return Response(status=406, data={"success": False, "msg": u"域名称为空"})
        # 名称
        username = request.data.get("username")
        # 汉字校验
        zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
        match = zhPattern.search(domain_name.decode('utf-8'))
        if match:
            logger.error("openapi.services", "绑定域名有汉字!")
            return Response(status=412, data={"success": False, "msg": u"绑定域名有汉字"})
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_name)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "Tenant {0} is not exists".format(tenant_name))
            return Response(status=408, data={"success": False, "msg": u"租户不存在,请检查租户名称"})
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "Tenant {0} ServiceAlias {1} is not exists".format(tenant_name, service_name))
            return Response(status=409, data={"success": False, "msg": u"服务名称不存在"})
        # 删除domain_name
        status, success, msg = manager.domain_service(action="close",
                                                      service=service,
                                                      domain_name=domain_name,
                                                      tenant_name=tenant_name,
                                                      username=username)
        return Response(status=status, data={"success": success, "msg": msg})

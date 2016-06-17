# -*- coding: utf8 -*-

from rest_framework.response import Response

from openapi.views.base import BaseAPIView


class DomainController(BaseAPIView):
    """域名管理模块"""
    allowed_methods = ('POST', 'GET', 'DELETE')

    def get(self, request, service_name, *args, **kwargs):
        """
        获取当前服务的域名
        parameters:
            - name: service_name
              description: 服务名称
              required: true
              type: string
              paramType: form
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: form

        """
        tenant_name = request.GET.get("tenant_name")
        uid = request.GET.get("uid")
        return Response(status=200, data={"success": True})


    def post(self, request, service_name, *args, **kwargs):
        """
        当前服务添加域名
        parameters:
            - name: service_name
              description: 服务名称
              required: true
              type: string
              paramType: form
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: form
            - name: domain
              description: 域名
              required: true
              type: string
              paramType: form
        """
        tenant_name = request.POST.get("tenant_name")
        domain = request.POST.get("domain")
        uid = request.GET.get("uid")

        return Response(status=200, data={"success": True})

    def delete(self, request, service_name, *args, **kwargs):
        """
        当前服务删除域名
        parameters:
            - name: service_name
              description: 服务名称
              required: true
              type: string
              paramType: form
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: form
            - name: domain
              description: 域名
              required: true
              type: string
              paramType: form
        """
        tenant_name = request.POST.get("tenant_name")
        domain = request.POST.get("domain")

        return Response(status=200, data={"success": True})

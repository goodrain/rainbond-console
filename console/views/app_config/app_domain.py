# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.app_config import domain_service
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message

logger = logging.getLogger("default")


class TenantCertificateView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取团队下的证书
        ---
        parameters:
            - name: tenantName
              description: 团队名
              required: true
              type: string
              paramType: path

        """
        try:
            certificates = domain_service.get_certificate(self.tenant)
            result = general_message(200, "success", "查询成功", list=certificates)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('tenant.tenant_access')
    def post(self, request, *args, **kwargs):
        """
        为团队添加证书
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: alias
              description: 证书名称
              required: true
              type: string
              paramType: form
            - name: private_key
              description: key
              required: true
              type: string
              paramType: form
            - name: certificate
              description: 证书内容
              required: true
              type: string
              paramType: form

        """
        try:
            alias = request.data.get("alias", None)
            private_key = request.data.get("private_key", None)
            certificate = request.data.get("certificate", None)
            code, msg, new_c = domain_service.add_certificate(self.tenant, alias, certificate, private_key)
            if code != 200:
                return Response(general_message(code, "add certificate error", msg), status=code)
            bean = {"alias": alias, "id": new_c.ID}
            result = general_message(200, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class TenantCertificateManageView(RegionTenantHeaderView):
    @never_cache
    @perm_required('tenant.tenant_access')
    def delete(self, request, *args, **kwargs):
        """
        删除证书
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: certificate_id
              description: 证书ID
              required: true
              type: string
              paramType: path

        """
        try:
            certificate_id = kwargs.get("certificate_id", None)
            code, msg = domain_service.delete_certificate_by_pk(certificate_id)
            if code != 200:
                return Response(general_message(code, "delete error", msg), status=code)

            result = general_message(200, "success", "证书删除成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('tenant.tenant_access')
    def put(self, request, *args, **kwargs):
        """
        修改证书
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: certificate_id
              description: 证书ID
              required: true
              type: string
              paramType: path
            - name: alias
              description: 新的证书名称（非必须）
              required: false
              type: string
              paramType: form
            - name: private_key
              description: key （非必须）
              required: false
              type: string
              paramType: form
            - name: certificate
              description: 证书内容 （非必须）
              required: false
              type: string
              paramType: form

        """
        try:
            certificate_id = kwargs.get("certificate_id", None)
            if not certificate_id:
                return Response(400, "no param certificate_id", "缺少未指明具体证书")
            new_alias = request.data.get("alias", None)
            private_key = request.data.get("private_key", None)
            certificate = request.data.get("certificate", None)
            code, msg = domain_service.update_certificate(self.tenant, certificate_id, new_alias, certificate,
                                                          private_key)
            if code != 200:
                return Response(general_message(code, "update certificate error", msg), status=code)

            result = general_message(200, "success", "证书修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        """
        查询某个证书详情
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: certificate_id
              description: 证书ID
              required: true
              type: string
              paramType: path

        """
        try:
            certificate_id = kwargs.get("certificate_id", None)
            code, msg, certificate = domain_service.get_certificate_by_pk(certificate_id)
            if code != 200:
                return Response(general_message(code, "delete error", msg), status=code)

            result = general_message(200, "success", "查询成功", bean=certificate.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class ServiceDomainView(AppBaseView):
    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        """
        获取服务下某个端口绑定的域名
        ---
        parameters:
            - name: tenantName
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: container_port
              description: 服务端口
              required: true
              type: string
              paramType: query

        """
        try:
            container_port = request.GET.get("container_port", None)

            domains = domain_service.get_port_bind_domains(self.service, int(container_port))
            domain_list = [domain.to_dict() for domain in domains]
            result = general_message(200, "success", "查询成功", list=domain_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('tenant.tenant_access')
    def post(self, request, *args, **kwargs):
        """
        服务端口绑定域名
        ---
        parameters:
            - name: tenantName
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: domain_name
              description: 域名
              required: true
              type: string
              paramType: form
            - name: container_port
              description: 服务端口
              required: true
              type: string
              paramType: form
            - name: protocol
              description: 端口协议（http,https,httptohttps,httpandhttps）
              required: true
              type: string
              paramType: form
            - name: certificate_id
              description: 证书ID
              required: false
              type: string
              paramType: form

        """
        try:
            container_port = request.data.get("container_port", None)
            domain_name = request.data.get("domain_name", None)
            protocol = request.data.get("protocol", None)
            certificate_id = request.data.get("certificate_id", None)

            code, msg = domain_service.bind_domain(self.tenant, self.user, self.service, domain_name, container_port,
                                                   protocol, certificate_id)
            if code != 200:
                return Response(general_message(code, "bind domain error", msg), status=code)

            result = general_message(200, "success", "域名绑定成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('tenant.tenant_access')
    def delete(self, request, *args, **kwargs):
        """
        服务端口解绑域名
        ---
        parameters:
            - name: tenantName
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: domain_name
              description: 域名
              required: true
              type: string
              paramType: form
            - name: container_port
              description: 服务端口
              required: true
              type: string
              paramType: form

        """
        try:
            container_port = request.data.get("container_port", None)
            domain_name = request.data.get("domain_name", None)
            if not container_port or not domain_name:
                return Response(general_message(400, "params error", "参数错误"), status=400)
            code, msg = domain_service.unbind_domain(self.tenant, self.service, container_port, domain_name)
            if code != 200:
                return Response(general_message(code, "delete domain error", msg), status=code)
            result = general_message(200, "success", "域名解绑成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class DomainView(RegionTenantHeaderView):
    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        """
        查询某个域名是否存在
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: domain_name
              description: 域名
              required: true
              type: string
              paramType: query

        """
        try:
            domain_name = request.GET.get("domain_name", None)
            if not domain_name:
                return Response(general_message(400, "domain name cannot be null", "查询的域名不能为空"), status=400)
            is_exist = domain_service.is_domain_exist(domain_name)
            bean = {"is_domain_exist": is_exist}
            result = general_message(200, "success", "查询成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

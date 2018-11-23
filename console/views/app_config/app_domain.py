# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from django.db import transaction
from django.db import connection
from console.services.app_config import domain_service, port_service
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from console.constants import DomainType
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.region_services import region_services
from console.repositories.app import service_repo
from console.services.team_services import team_services
from www.utils.crypt import make_uuid
from console.services.app_actions import app_manage_service
from console.repositories.app_config import domain_repo


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
            certificate_id = make_uuid()
            code, msg, new_c = domain_service.add_certificate(self.tenant, alias, certificate_id,certificate, private_key)
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
    @perm_required('manage_service_config')
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
    @perm_required('manage_service_config')
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
    @perm_required('manage_service_config')
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
            service_id = request.data.get("service_id", None)
            group_name = request.data.get("group_name", None)
            domain_path = request.data.get("domain_path", None)
            domain_cookie = request.data.get("domain_cookie", None)
            domain_heander = request.data.get("domain_heander", None)
            rule_extensions = request.data.get("rule_extensions", None)
            whether_open = request.data.get("whether_open", False)
            the_weight = request.data.get("the_weight", 100)

            identitys = team_services.get_user_perm_identitys_in_permtenant(user_id=self.user.user_id,
                                                                            tenant_name=self.tenant.tenant_name)
            # 判断权限
            if "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                return Response(general_message(400, "Permission denied", "您无权此操作"), status=400)

            # 判断参数
            if not container_port or not domain_name or not service_id:
                return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)

            service = service_repo.get_service_by_service_id(service_id)
            if not service:
                return Response(general_message(400, "not service", "服务不存在"), status=400)
            # 判断策略是否存在
            service_domain = domain_repo.get_domain_by_name_and_port(service.service_id, container_port, domain_name)
            if service_domain:
                result = general_message(400, "faild", "策略已存在")
                return Response(result)

            if whether_open:
                # 开启对外端口并重启（开启事物）
                with transaction.atomic():
                    # 开启保存点
                    save_id = transaction.savepoint()
                    try:
                        tenant_service_ports = port_service.get_service_ports(service)
                        for tenant_service_port in tenant_service_ports:
                            code, msg, data = port_service.manage_port(self.tenant, service, int(tenant_service_port.container_port), "open_outer",
                                                                       tenant_service_port.protocol, tenant_service_port.port_alias)
                            if code != 200:

                                return Response(general_message(code, "change port fail", msg), status=code)
                        code, msg, event = app_manage_service.restart(self.tenant, service, self.user)
                        if code != 200:
                            return Response(general_message(code, "restart app error", msg), status=code)
                    except Exception:
                        # 回滚
                        transaction.savepoint_rollback(save_id)
                        raise
                    # 提交事物
                    transaction.savepoint_commit(save_id)
            tenant_service_ports = port_service.get_service_ports(service)
            for tenant_service_port in tenant_service_ports:
                if not tenant_service_port:
                    return Response(general_message(200, "not outer port", "没有开启对外窗口", bean={"is_outer_service": False}), status=200)

            # 绑定端口(添加策略)
            code, msg = domain_service.bind_domain(self.tenant, self.user, service, domain_name, container_port, protocol,
                                                   certificate_id, DomainType.WWW, group_name, domain_path,
                                                   domain_cookie, domain_heander, rule_extensions, the_weight)
            if code != 200:
                return Response(general_message(code, "bind domain error", msg), status=code)

            result = general_message(200, "success", "域名绑定成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def put(self, request, *args, **kwargs):
        """
        服务端口编辑域名
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
            certificate_id = request.data.get("certificate_id", None)
            service_id = request.data.get("service_id", None)
            group_name = request.data.get("group_name", None)
            domain_path = request.data.get("domain_path", None)
            domain_cookie = request.data.get("domain_cookie", None)
            domain_heander = request.data.get("domain_heander", None)
            rule_extensions = request.data.get("rule_extensions", None)
            protocol = request.data.get("protocol", None)
            http_rule_id = request.data.get("http_rule_id", None)
            the_weight = request.data.get("the_weight", 100)

            # 判断参数
            if not service_id or not group_name or not container_port or not domain_name or not http_rule_id:
                return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)

            service = service_repo.get_service_by_service_id(service_id)
            if not service:
                return Response(general_message(400, "not service", "服务不存在"), status=400)

            identitys = team_services.get_user_perm_identitys_in_permtenant(user_id=self.user.user_id,
                                                                            tenant_name=self.tenant.tenant_name)
            # 判断权限
            if "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                return Response(general_message(400, "Permission denied", "您无权此操作"), status=400)

            # 编辑域名
            code, msg = domain_service.update_domain(self.tenant, self.user, service, domain_name, container_port,
                                                   certificate_id, DomainType.WWW, group_name, domain_path,
                                                   domain_cookie, domain_heander, rule_extensions, http_rule_id, protocol, the_weight)

            if code != 200:
                return Response(general_message(code, "bind domain error", msg), status=code)

            result = general_message(200, "success", "域名编辑成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
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
            service_id = request.data.get("service_id", None)
            if not container_port or not domain_name or not service_id:
                return Response(general_message(400, "params error", "参数错误"), status=400)

            identitys = team_services.get_user_perm_identitys_in_permtenant(user_id=self.user.user_id,
                                                                            tenant_name=self.tenant.tenant_name)
            # 判断权限
            if "owner" not in identitys and "admin" not in identitys and "developer" not in identitys:
                return Response(general_message(400, "Permission denied", "您无权此操作"), status=400)

            service = service_repo.get_service_by_service_id(service_id)
            if not service:
                return Response(general_message(400, "not service", "服务不存在"), status=400)
            code, msg = domain_service.unbind_domain(self.tenant, service, container_port, domain_name)
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


class SecondLevelDomainView(AppBaseView):
    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        """
        获取二级域名后缀
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
        """
        try:
            http_domain = region_services.get_region_httpdomain(self.service.service_region)
            sld_suffix = "{0}.{1}".format(self.tenant.tenant_name, http_domain)
            result = general_message(200, "success", "查询成功", {"sld_suffix": sld_suffix})
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def put(self, request, *args, **kwargs):
        """
        服务端口自定义二级域名
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
            container_port = int(container_port)
            sld_domains = domain_service.get_sld_domains(self.service, container_port)
            if not sld_domains:

                code, msg = domain_service.bind_domain(self.tenant, self.user, self.service, domain_name, container_port,
                                                       "http", None, DomainType.SLD_DOMAIN)
                if code != 200:
                    return Response(general_message(code, "bind domain error", msg), status=code)
            else:
                # 先解绑 再绑定
                code, msg = domain_service.unbind_domain(self.tenant, self.service, container_port, sld_domains[0].domain_name)
                if code != 200:
                    return Response(general_message(code, "unbind domain error", msg), status=code)
                domain_service.bind_domain(self.tenant, self.user, self.service, domain_name, container_port,
                                           "http", None, DomainType.SLD_DOMAIN)

            result = general_message(200, "success", "二级域名修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


# 获取团队下的策略
class DomainQueryView(AppBaseView):
    def get(self, request, *args, **kwargs):
        try:
            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 10)
            search_conditions = request.GET.get("search_conditions", None)
            total = domain_repo.get_all_domain_count()
            start = (page - 1) * 10
            remaining_num = total - (page - 1) * 10
            end = 10
            if remaining_num < page_size:
                end = remaining_num
            try:
                if search_conditions:
                    cursor = connection.cursor()
                    cursor.execute(
                        "select domain_name, type, is_senior, certificate_id, group_name, service_alias, protocol from service_domain where domain_name like '%{0}%' or service_name like '%{1}%' or group_name like '%{2}%' order by type desc LIMIT {3},{4};".format(
                            search_conditions, search_conditions, search_conditions, start, end))
                    tenant_tuples = cursor.fetchall()
                else:
                    cursor = connection.cursor()
                    cursor.execute(
                        "select domain_name, type, is_senior, certificate_id, group_name, service_alias, protocol from service_domain order by type desc LIMIT {0},{1};".format(
                            start, end))
                    tenant_tuples = cursor.fetchall()
            except Exception as e:
                logger.exception(e)
                result = general_message(405, "faild", "查询数据库失败")
                return Response(result)

            # 拼接展示数据
            domain_list = list()
            for tenant_tuple in tenant_tuples:
                domain_dict = dict()
                certificate_info = domain_repo.get_certificate_by_pk(int(tenant_tuple[3]))
                domain_dict["certificate_alias"] = certificate_info.alias
                domain_dict["domain_name"] = tenant_tuple[6] + "://" + tenant_tuple[0]
                domain_dict["type"] = tenant_tuple[1]
                domain_dict["is_senior"] = tenant_tuple[2]
                domain_dict["group_name"] = tenant_tuple[4]
                domain_dict["service_cname"] = tenant_tuple[5]
                domain_list.append(domain_dict)
            bean = dict()
            bean["total"] = total
            result = general_message(200, "success", "查询成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)





# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging
import json

from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from console.repositories.group import group_repo
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
from console.repositories.app_config import domain_repo, tcp_domain, configuration_repo
from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.region_repo import region_repo
from console.repositories.group import group_service_relation_repo


logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class TenantCertificateView(RegionTenantHeaderView):
    @never_cache
    @perm_required('certificate_operation')
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
        page = int(request.GET.get("page_num", 1))
        page_size = int(request.GET.get("page_size", 10))
        try:
            certificates, nums = domain_service.get_certificate(self.tenant, page, page_size)
            bean = {"nums": nums}
            result = general_message(200, "success", "查询成功", list=certificates,bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('certificate_operation')
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
            certificate_type = request.data.get("certificate_type",None)
            certificate_id = make_uuid()
            code, msg, new_c = domain_service.add_certificate(self.tenant, alias, certificate_id,certificate, private_key,certificate_type)
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
    @perm_required('certificate_management')
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
    @perm_required('certificate_management')
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
            certificate_type = request.data.get("certificate_type", None)
            code, msg = domain_service.update_certificate(self.tenant, certificate_id, new_alias, certificate,
                                                          private_key,certificate_type)
            if code != 200:
                return Response(general_message(code, "update certificate error", msg), status=code)

            result = general_message(200, "success", "证书修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required("certificate_management")
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

            result = general_message(200, "success", "查询成功", bean=certificate)
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
            rule_extensions = request.data.get("rule_extensions", None)

            # 判断策略是否存在
            service_domain = domain_repo.get_domain_by_name_and_port_and_protocol(self.service.service_id, container_port,
                                                                                  domain_name, protocol)
            if service_domain:
                result = general_message(400, "faild", "策略已存在")
                return Response(result, status=400)

            code, msg = domain_service.bind_domain(self.tenant, self.user, self.service, domain_name, container_port,
                                                   protocol, certificate_id, DomainType.WWW, rule_extensions)
            if code != 200:
                return Response(general_message(code, "bind domain error", msg), status=code)
            # htt与https共存的协议需存储两条数据(创建完https数据再创建一条http数据)
            if protocol == "httpandhttps":
                certificate_id = 0
                code, msg = domain_service.bind_domain(self.tenant, self.user, self.service, domain_name,
                                                       container_port,
                                                       protocol, certificate_id, DomainType.WWW,
                                                       rule_extensions)
                if code != 200:
                    return Response(general_message(code, "bind domain error", msg), status=code)

            result = general_message(200, "success", "域名绑定成功")
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
            is_tcp = request.data.get("is_tcp", False)
            if not container_port or not domain_name:
                return Response(general_message(400, "params error", "参数错误"), status=400)
            code, msg = domain_service.unbind_domain(self.tenant, self.service, container_port, domain_name, is_tcp)
            if code != 200:
                return Response(general_message(code, "delete domain error", msg), status=code)
            result = general_message(200, "success", "域名解绑成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class HttpStrategyView(RegionTenantHeaderView):
    @never_cache
    @perm_required('access_control')
    def get(self, request, *args, **kwargs):
        """
        获取单个http策略

        """
        try:
            http_rule_id = request.GET.get("http_rule_id", None)
            # 判断参数
            if not http_rule_id:
                return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)

            domain = domain_repo.get_service_domain_by_http_rule_id(http_rule_id)
            if domain:
                bean = domain.to_dict()
                service = service_repo.get_service_by_service_id(domain.service_id)
                service_alias = service.service_cname if service else ''
                group_name = ''
                g_id = 0
                if service:
                    gsr = group_service_relation_repo.get_group_by_service_id(service.service_id)
                    if gsr:
                        group = group_repo.get_group_by_id(int(gsr.group_id))
                        group_name = group.group_name if group else ''
                        g_id = int(gsr.group_id)
                if domain.certificate_id:
                    certificate_info = domain_repo.get_certificate_by_pk(int(domain.certificate_id))

                    bean.update({"certificate_name": certificate_info.alias})
                bean.update({"service_alias": service_alias})
                bean.update({"group_name": group_name})
                bean.update({"g_id": g_id})
            else:
                bean = dict()
            result = general_message(200, "success", "查询成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('control_operation')
    def post(self, request, *args, **kwargs):
        """
        添加http策略

        """
        try:
            container_port = request.data.get("container_port", None)
            domain_name = request.data.get("domain_name", None)
            certificate_id = request.data.get("certificate_id", None)
            service_id = request.data.get("service_id", None)
            domain_path = request.data.get("domain_path", None)
            domain_cookie = request.data.get("domain_cookie", None)
            domain_heander = request.data.get("domain_heander", None)
            rule_extensions = request.data.get("rule_extensions", None)
            whether_open = request.data.get("whether_open", False)
            the_weight = request.data.get("the_weight", 100)

            # 判断参数
            if not container_port or not domain_name or not service_id:
                return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)

            service = service_repo.get_service_by_service_id(service_id)
            if not service:
                return Response(general_message(400, "not service", "服务不存在"), status=400)
            # 判断域名格式(如果用户添加的域名与默认域名后缀一致，那么他后缀必须是 "租户别名.默认后缀"
            #
            # 比如默认域名后缀是:37e53f.grapps.cn  这个值来自于region_info  http_domain
            # 那么如果它绑定 xxx.37e53f.grapps.cn是不允许的，只能绑定：
            # xxx.yaufe6r5.37e53f.grapps.cn
            #
            # 此限制是防止租户之间盗用域名。)
            region = region_repo.get_region_by_region_name(service.service_region)
            if domain_name.endswith(region.httpdomain):
                domain_name_spt = domain_name.split(region.httpdomain)
                if self.tenant.tenant_name != domain_name_spt[0].split('.')[len(domain_name_spt[0].split('.'))-2]:
                    return Response(general_message(400, "the domain name format is incorrect", "域名格式不正确"), status=400)
            protocol = "http"
            if certificate_id:
                protocol = "https"
            # 判断策略是否存在
            service_domain = domain_repo.get_domain_by_name_and_port_and_protocol(service.service_id, container_port, domain_name, protocol, domain_path)
            if service_domain:
                result = general_message(400, "faild", "策略已存在")
                return Response(result, status=400)

            if whether_open:
                try:
                    tenant_service_port = port_service.get_service_port_by_port(service, container_port)
                    # 仅开启对外端口
                    code, msg, data = port_service.manage_port(self.tenant, service, service.service_region, int(tenant_service_port.container_port), "only_open_outer",
                                                               tenant_service_port.protocol, tenant_service_port.port_alias)
                    if code != 200:
                        return Response(general_message(code, "change port fail", msg), status=code)
                except Exception:
                    raise

            tenant_service_port = port_service.get_service_port_by_port(service, container_port)
            if not tenant_service_port.is_outer_service:
                return Response(general_message(200, "not outer port", "没有开启对外端口", bean={"is_outer_service": False}),
                                status=200)

            # 绑定端口(添加策略)
            code, msg, data = domain_service.bind_httpdomain(self.tenant, self.user, service, domain_name, container_port, protocol,
                                                   certificate_id, DomainType.WWW, domain_path,
                                                   domain_cookie, domain_heander, the_weight, rule_extensions)
            if code != 200:
                return Response(general_message(code, "bind domain error", msg), status=code)

            result = general_message(200, "success", "策略添加成功", bean=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('control_operation')
    def put(self, request, *args, **kwargs):
        """
        编辑http策略
        """
        try:
            container_port = request.data.get("container_port", None)
            domain_name = request.data.get("domain_name", None)
            certificate_id = request.data.get("certificate_id", None)
            service_id = request.data.get("service_id", None)
            domain_path = request.data.get("domain_path", None)
            domain_cookie = request.data.get("domain_cookie", None)
            domain_heander = request.data.get("domain_heander", None)
            rule_extensions = request.data.get("rule_extensions", None)
            http_rule_id = request.data.get("http_rule_id", None)
            the_weight = request.data.get("the_weight", 100)

            # 判断参数
            if not service_id or not container_port or not domain_name or not http_rule_id:
                return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)

            service = service_repo.get_service_by_service_id(service_id)
            if not service:
                return Response(general_message(400, "not service", "服务不存在"), status=400)

            # 判断域名格式(如果用户添加的域名与默认域名后缀一致，那么他后缀必须是 "租户别名.默认后缀"
            #
            # 比如默认域名后缀是:37e53f.grapps.cn  这个值来自于region_info  http_domain
            # 那么如果它绑定 xxx.37e53f.grapps.cn是不允许的，只能绑定：
            # xxx.yaufe6r5.37e53f.grapps.cn
            #
            # 此限制是防止租户之间盗用域名。)
            region = region_repo.get_region_by_region_name(service.service_region)
            if domain_name.endswith(region.httpdomain):
                domain_name_spt = domain_name.split(region.httpdomain)
                if self.tenant.tenant_name != domain_name_spt[0].split('.')[len(domain_name_spt[0].split('.'))-2]:
                    return Response(general_message(400, "the domain name format is incorrect", "域名格式不正确"), status=400)

            # 编辑域名
            code, msg, data = domain_service.update_httpdomain(self.tenant, self.user, service, domain_name, container_port,
                                                   certificate_id, DomainType.WWW, domain_path,
                                                   domain_cookie, domain_heander, http_rule_id, the_weight, rule_extensions)

            if code != 200:
                return Response(general_message(code, "bind domain error", msg), status=code)

            result = general_message(200, "success", "策略编辑成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('control_operation')
    def delete(self, request, *args, **kwargs):
        """
       删除策略

        """
        try:
            service_id = request.data.get("service_id", None)
            http_rule_id = request.data.get("http_rule_id", None)

            if not http_rule_id or not service_id:
                return Response(general_message(400, "params error", "参数错误"), status=400)

            # 解绑域名
            code, msg = domain_service.unbind_httpdomain(self.tenant, self.response_region, http_rule_id)
            if code != 200:
                return Response(general_message(code, "delete domain error", msg), status=code)
            result = general_message(200, "success", "策略删除成功")
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
                code, msg = domain_service.unbind_domain(self.tenant, self.service, container_port, sld_domains[0].domain_name, is_tcp=False)
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
class DomainQueryView(RegionTenantHeaderView):
    def get(self, request, tenantName, *args, **kwargs):
        try:
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))
            search_conditions = request.GET.get("search_conditions", None)
            tenant = team_services.get_tenant_by_tenant_name(tenantName)
            region = region_repo.get_region_by_region_name(self.response_region)
            try:
                # 查询分页排序
                if search_conditions:
                    # 获取总数
                    cursor = connection.cursor()
                    cursor.execute(
                        "select count(*) from service_domain where tenant_id='{0}' and region_id='{1}' and domain_name like '%{2}%';".format(
                            tenant.tenant_id, region.region_id, search_conditions))
                    domain_count = cursor.fetchall()

                    total = domain_count[0][0]
                    start = (page - 1) * page_size
                    remaining_num = total - (page - 1) * page_size
                    end = page_size
                    if remaining_num < page_size:
                        end = remaining_num

                    cursor = connection.cursor()
                    cursor.execute(
                        "select domain_name, type, is_senior, certificate_id, service_alias, protocol, service_name, container_port, http_rule_id, service_id, domain_path, domain_cookie, domain_heander, the_weight, is_outer_service from service_domain where tenant_id='{0}' and region_id='{1}' and domain_name like '%{2}%' order by type desc LIMIT {3},{4};".format(
                            tenant.tenant_id, region.region_id, search_conditions, start, end))
                    tenant_tuples = cursor.fetchall()
                else:

                    # 获取总数
                    cursor = connection.cursor()
                    cursor.execute(
                        "select count(*) from service_domain where tenant_id='{0}' and region_id='{1}';".format(
                            tenant.tenant_id, region.region_id))
                    domain_count = cursor.fetchall()

                    total = domain_count[0][0]
                    start = (page - 1) * page_size
                    remaining_num = total - (page - 1) * page_size
                    end = page_size
                    if remaining_num < page_size:
                        end = remaining_num

                    cursor = connection.cursor()

                    cursor.execute(
                        "select domain_name, type, is_senior, certificate_id, service_alias, protocol, service_name, container_port, http_rule_id, service_id, domain_path, domain_cookie, domain_heander, the_weight, is_outer_service from service_domain where tenant_id='{0}' and region_id='{1}' order by type desc LIMIT {2},{3};".format(
                            tenant.tenant_id, region.region_id, start, end))
                    tenant_tuples = cursor.fetchall()

            except Exception as e:
                logger.exception(e)
                result = general_message(405, "faild", "查询数据库失败")
                return Response(result)

            # 拼接展示数据
            domain_list = list()
            for tenant_tuple in tenant_tuples:
                service = service_repo.get_service_by_service_id(tenant_tuple[9])
                service_alias = service.service_cname if service else ''
                group_name = ''
                group_id = 0
                if service:
                    gsr = group_service_relation_repo.get_group_by_service_id(service.service_id)
                    if gsr:
                        group = group_repo.get_group_by_id(int(gsr.group_id))
                        group_name = group.group_name if group else ''
                        group_id = int(gsr.group_id)
                domain_dict = dict()
                certificate_info = domain_repo.get_certificate_by_pk(int(tenant_tuple[3]))
                if not certificate_info:
                    domain_dict["certificate_alias"] = ''
                else:
                    domain_dict["certificate_alias"] = certificate_info.alias
                domain_dict["domain_name"] = tenant_tuple[5] + "://" + tenant_tuple[0]
                domain_dict["type"] = tenant_tuple[1]
                domain_dict["is_senior"] = tenant_tuple[2]
                domain_dict["group_name"] = group_name
                domain_dict["service_cname"] = service_alias
                domain_dict["service_alias"] = tenant_tuple[6]
                domain_dict["container_port"] = tenant_tuple[7]
                domain_dict["http_rule_id"] = tenant_tuple[8]
                domain_dict["service_id"] = tenant_tuple[9]
                domain_dict["domain_path"] = tenant_tuple[10]
                domain_dict["domain_cookie"] = tenant_tuple[11]
                domain_dict["domain_heander"] = tenant_tuple[12]
                domain_dict["the_weight"] = tenant_tuple[13]
                domain_dict["is_outer_service"] = tenant_tuple[14]
                domain_dict["group_id"] = group_id
                domain_list.append(domain_dict)
            bean = dict()
            bean["total"] = total
            result = general_message(200, "success", "查询成功", list=domain_list, bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)


class ServiceTcpDomainQueryView(RegionTenantHeaderView):
    # 查询团队下tcp/udp策略
    def get(self, request, tenantName, *args, **kwargs):
        try:
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))
            search_conditions = request.GET.get("search_conditions", None)
            tenant = team_services.get_tenant_by_tenant_name(tenantName)
            region = region_repo.get_region_by_region_name(self.response_region)
            try:
                # 查询分页排序
                if search_conditions:
                    # 获取总数
                    cursor = connection.cursor()
                    cursor.execute(
                        "select count(*) from service_tcp_domain where tenant_id='{0}' and region_id='{1}' and domain_name like '%{2}%' or service_alias like '%{3}%';".format(
                            tenant.tenant_id, region.region_id, search_conditions, search_conditions))
                    domain_count = cursor.fetchall()

                    total = domain_count[0][0]
                    start = (page - 1) * page_size
                    remaining_num = total - (page - 1) * page_size
                    end = page_size
                    if remaining_num < page_size:
                        end = remaining_num

                    cursor = connection.cursor()
                    cursor.execute(
                        "select end_point, type, protocol, service_name, service_alias, container_port, tcp_rule_id, service_id, is_outer_service from service_tcp_domain where tenant_id='{0}' and region_id='{1}' and end_point like '%{2}%' or service_alias like '%{3}%' or group_name like '%{4}%' order by type desc LIMIT {5},{6};".format(
                            tenant.tenant_id, region.region_id, search_conditions, search_conditions, search_conditions, start, end))
                    tenant_tuples = cursor.fetchall()
                else:
                    # 获取总数
                    cursor = connection.cursor()
                    cursor.execute(
                        "select count(*) from service_tcp_domain where tenant_id='{0}' and region_id='{1}';".format(
                            tenant.tenant_id, region.region_id))
                    domain_count = cursor.fetchall()

                    total = domain_count[0][0]
                    start = (page - 1) * page_size
                    remaining_num = total - (page - 1) * page_size
                    end = page_size
                    if remaining_num < page_size:
                        end = remaining_num

                    cursor = connection.cursor()
                    cursor.execute(
                        "select end_point, type, protocol, service_name, service_alias, container_port, tcp_rule_id, service_id, is_outer_service from service_tcp_domain where tenant_id='{0}' and region_id='{1}' order by type desc LIMIT {2},{3};".format(
                            tenant.tenant_id, region.region_id, start, end))
                    tenant_tuples = cursor.fetchall()
            except Exception as e:
                logger.exception(e)
                result = general_message(405, "faild", "查询数据库失败")
                return Response(result)

            # 拼接展示数据
            domain_list = list()
            for tenant_tuple in tenant_tuples:
                service = service_repo.get_service_by_service_id(tenant_tuple[7])
                service_alias = service.service_cname if service else ''
                group_name = ''
                group_id = 0
                if service:
                    gsr = group_service_relation_repo.get_group_by_service_id(service.service_id)
                    if gsr:
                        group = group_repo.get_group_by_id(int(gsr.group_id))
                        group_name = group.group_name if group else ''
                        group_id = int(gsr.group_id)
                domain_dict = dict()
                domain_dict["end_point"] = tenant_tuple[0]
                domain_dict["type"] = tenant_tuple[1]
                domain_dict["protocol"] = tenant_tuple[2]
                domain_dict["group_name"] = group_name
                domain_dict["service_alias"] = tenant_tuple[3]
                domain_dict["container_port"] = tenant_tuple[5]
                domain_dict["service_cname"] = service_alias
                domain_dict["tcp_rule_id"] = tenant_tuple[6]
                domain_dict["service_id"] = tenant_tuple[7]
                domain_dict["is_outer_service"] = tenant_tuple[8]
                domain_dict["group_id"] = group_id

                domain_list.append(domain_dict)
            bean = dict()
            bean["total"] = total
            result = general_message(200, "success", "查询成功", list=domain_list, bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)


# tcp/ucp策略操作
class ServiceTcpDomainView(RegionTenantHeaderView):

    @never_cache
    @perm_required('access_control')
    def get(self, request, *args, **kwargs):
        # 获取单个tcp/udp策略信息
        try:
            tcp_rule_id = request.GET.get("tcp_rule_id", None)
            # 判断参数
            if not tcp_rule_id:
                return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)

            tcpdomain = tcp_domain.get_service_tcpdomain_by_tcp_rule_id(tcp_rule_id)
            if tcpdomain:
                bean = tcpdomain.to_dict()
                service = service_repo.get_service_by_service_id(tcpdomain.service_id)
                service_alias = service.service_cname if service else ''
                group_name = ''
                g_id = 0
                if service:
                    gsr = group_service_relation_repo.get_group_by_service_id(service.service_id)
                    if gsr:
                        group = group_repo.get_group_by_id(int(gsr.group_id))
                        group_name = group.group_name if group else ''
                        g_id = int(gsr.group_id)
                bean.update({"service_alias": service_alias})
                bean.update({"group_name": group_name})
                bean.update({"g_id": g_id})
                result = general_message(200, "success", "查询成功", bean=bean)
            else:
                bean = dict()
                result = general_message(200, "success", "查询成功", bean=bean)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('control_operation')
    # 添加
    def post(self, request, *args, **kwargs):
        try:
            container_port = request.data.get("container_port", None)
            service_id = request.data.get("service_id", None)
            end_point = request.data.get("end_point", None)
            whether_open = request.data.get("whether_open", False)
            rule_extensions = request.data.get("rule_extensions", None)
            default_port = request.data.get("default_port", None)
            default_ip = request.data.get("default_ip", None)

            if not container_port or not service_id or not end_point:
                return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)

            service = service_repo.get_service_by_service_id(service_id)
            if not service:
                return Response(general_message(400, "not service", "服务不存在"), status=400)

            # 判断策略是否存在
            service_tcpdomain = tcp_domain.get_tcpdomain_by_name_and_port(service.service_id, container_port, end_point)
            if service_tcpdomain:
                result = general_message(400, "faild", "策略已存在")
                return Response(result)

            if whether_open:
                try:
                    tenant_service_port = port_service.get_service_port_by_port(service, container_port)
                    # 仅打开对外端口
                    code, msg, data = port_service.manage_port(self.tenant, service, service.service_region,
                                                               int(tenant_service_port.container_port), "only_open_outer",
                                                               tenant_service_port.protocol,
                                                               tenant_service_port.port_alias)
                    if code != 200:
                        return Response(general_message(code, "change port fail", msg), status=code)
                except Exception:
                    raise
            tenant_service_port = port_service.get_service_port_by_port(service, container_port)

            if not tenant_service_port.is_outer_service:
                return Response(general_message(200, "not outer port", "没有开启对外端口", bean={"is_outer_service": False}),
                                status=200)

            # 添加tcp策略
            code, msg, data = domain_service.bind_tcpdomain(self.tenant, self.user, service, end_point, container_port,
                                                            default_port, rule_extensions, default_ip)

            if code != 200:
                return Response(general_message(code, "bind domain error", msg), status=code)

            result = general_message(200, "success", "tcp策略添加成功", bean=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('control_operation')
    # 修改
    def put(self, request, *args, **kwargs):

        try:
            container_port = request.data.get("container_port", None)
            service_id = request.data.get("service_id", None)
            end_point = request.data.get("end_point", None)
            tcp_rule_id = request.data.get("tcp_rule_id", None)
            rule_extensions = request.data.get("rule_extensions", None)
            type = request.data.get("type", None)
            default_ip = request.data.get("default_ip", None)

            # 判断参数
            if not tcp_rule_id:
                return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)

            service = service_repo.get_service_by_service_id(service_id)
            if not service:
                return Response(general_message(400, "not service", "服务不存在"), status=400)

            # 查询端口协议
            tenant_service_port = port_service.get_service_port_by_port(service, container_port)
            if tenant_service_port:
                protocol = tenant_service_port.protocol
            else:
                protocol = ''

            # 修改策略
            code, msg = domain_service.update_tcpdomain(self.tenant, self.user, service, end_point, container_port,
                                                     tcp_rule_id, protocol, type, rule_extensions, default_ip)

            if code != 200:
                return Response(general_message(code, "bind domain error", msg), status=code)

            result = general_message(200, "success", "策略修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('control_operation')
    # 删除
    def delete(self, request, *args, **kwargs):

        try:
            tcp_rule_id = request.data.get("tcp_rule_id", None)

            if not tcp_rule_id:
                return Response(general_message(400, "params error", "参数错误"), status=400)

            # 删除策略
            code, msg = domain_service.unbind_tcpdomain(self.tenant, self.response_region, tcp_rule_id)
            if code != 200:
                return Response(general_message(code, "delete domain error", msg), status=code)
            result = general_message(200, "success", "策略删除成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


# 给数据中心发请求获取可用端口
class GetPortView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        try:
            res, data = region_api.get_port(self.response_region, self.tenant.tenant_name)

            if int(res.status) != 200:
                result = general_message(400, "call region error", "请求数据中心异常")
                return Response(result, status=400)
            region = region_repo.get_region_by_region_name(self.response_region)
            ip = region.tcpdomain
            ip_port_list = list()
            ip_dict = dict()
            ip_dict["ip"] = ip
            ip_dict["port"] = data["bean"]
            ip_port_list.append(ip_dict)
            result = general_message(200, "success", "可用端口查询成功", list=ip_port_list)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


# 查看高级路由信息
class GetSeniorUrlView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        try:
            http_rule_id = request.GET.get("http_rule_id", None)
            # 判断参数
            if not http_rule_id:
                return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)
            service_domain = domain_repo.get_service_domain_by_http_rule_id(http_rule_id)
            result = general_message(200, "success", "查询成功", bean=service_domain.to_dict())
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


# 网关自定义参数设置
class GatewayCustomConfigurationView(RegionTenantHeaderView):
    # 获取策略的网关自定义参数
    @never_cache
    @perm_required('access_control')
    def get(self, request, rule_id, *args, **kwargs):
        if not rule_id:
            return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)
        try:
            cf = configuration_repo.get_configuration_by_rule_id(rule_id)
            bean = dict()
            if cf:
                bean["rule_id"] = cf.rule_id
                bean["value"] = json.loads(cf.value)
            result = general_message(200, "success", "查询成功", bean=bean)
            return Response(result, status=200)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)

    # 修改网关的自定义参数
    @never_cache
    @perm_required('control_operation')
    def put(self, request, rule_id, *args, **kwargs):
        value = request.data.get("value", None)
        if not rule_id:
            return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)
        service_domain = domain_repo.get_service_domain_by_http_rule_id(rule_id)
        if not service_domain:
            return Response(general_message(400, "no domain", "策略不存在"), status=400)
        service_obj = service_repo.get_service_by_service_id(service_domain.service_id)
        try:
            if not value:
                cf = configuration_repo.get_configuration_by_rule_id(rule_id)
                if not cf:
                    return Response(general_message(400, "no_modification", "暂无修改"), status=400)
                gcc_dict = dict()
                gcc_dict["body"] = cf
                gcc_dict["rule_id"] = rule_id
                res, data = region_api.upgrade_configuration(self.response_region, self.tenant, service_obj.service_alias, gcc_dict)
                if res.status != 200:
                    return Response(general_message(500, "upgrade faild", "数据中心修改失败"), status=500)
                result = general_message(200, "success", "修改成功")
                return Response(result, status=200)
            else:
                cf = configuration_repo.get_configuration_by_rule_id(rule_id)
                gcc_dict = dict()
                gcc_dict["body"] = value
                gcc_dict["rule_id"] = rule_id
                res, data = region_api.upgrade_configuration(self.response_region, self.tenant, service_obj.service_alias, gcc_dict)
                if res.status == 200:
                    if cf:
                        cf.value = json.dumps(value)
                        cf.save()
                    else:
                        cf_dict = dict()
                        cf_dict["rule_id"] = rule_id
                        cf_dict["value"] = json.dumps(value)
                        configuration_repo.add_configuration(**cf_dict)
                result = general_message(200, "success", "修改成功")
                return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)












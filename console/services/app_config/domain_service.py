# -*- coding: utf8 -*-
"""
  Created on 18/1/23.
"""
import base64
import datetime
import json
import logging
import re

from console.constants import DomainType
from console.exception.main import ServiceHandleException
from console.repositories.app_config import (configuration_repo, domain_repo, port_repo, tcp_domain)
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.services.app_config.exceptoin import (err_cert_name_exists, err_cert_not_found, err_still_has_http_rules)
from console.services.group_service import group_service
from console.services.region_services import region_services
from console.utils.certutil import analyze_cert, cert_is_effective
from console.utils.shortcuts import get_object_or_404
from django.db import connection, transaction
from django.forms.models import model_to_dict
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceDomain, TenantServiceInfo
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

ErrNotFoundDomain = ServiceHandleException(status_code=404, error_code=1404, msg="domain not found", msg_show="域名不存在")
ErrNotFoundStreamDomain = ServiceHandleException(status_code=404, error_code=2404, msg="domain not found", msg_show="策略不存在")


class DomainService(object):
    HTTP = "http"

    def get_time_now(self):
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def get_certificate(self, tenant, page, page_size):
        end = page_size * page - 1  # 一页数据的开始索引
        start = end - page_size + 1  # 一页数据的结束索引
        certificate, nums = domain_repo.get_tenant_certificate_page(tenant.tenant_id, start, end)
        c_list = []
        for c in certificate:
            cert = base64.b64decode(c.certificate)
            data = dict()
            data["alias"] = c.alias
            data["certificate_type"] = c.certificate_type
            data["id"] = c.ID
            data.update(analyze_cert(cert))
            c_list.append(data)
        return c_list, nums

    def __check_certificate_alias(self, tenant, alias):
        if domain_repo.get_certificate_by_alias(tenant.tenant_id, alias):
            raise err_cert_name_exists

    def add_certificate(self, tenant, alias, certificate_id, certificate, private_key, certificate_type):
        self.__check_certificate_alias(tenant, alias)
        cert_is_effective(certificate, private_key)
        certificate = base64.b64encode(certificate)
        certificate = domain_repo.add_certificate(tenant.tenant_id, alias, certificate_id, certificate, private_key,
                                                  certificate_type)
        return certificate

    def delete_certificate_by_alias(self, tenant, alias):
        certificate = domain_repo.get_certificate_by_alias(tenant.tenant_id, alias)
        if certificate:
            certificate.delete()
            return 200, "success"
        else:
            return 404, "证书不存在"

    def get_certificate_by_pk(self, pk):
        certificate = domain_repo.get_certificate_by_pk(pk)
        if not certificate:
            return 404, "证书不存在", None
        data = dict()
        data["alias"] = certificate.alias
        data["certificate_type"] = certificate.certificate_type
        data["id"] = certificate.ID
        data["tenant_id"] = certificate.tenant_id
        data["certificate"] = base64.b64decode(certificate.certificate)
        data["private_key"] = certificate.private_key
        return 200, "success", data

    def delete_certificate_by_pk(self, pk):
        cert = domain_repo.get_certificate_by_pk(pk)
        if not cert:
            raise err_cert_not_found

        # can't delete the cerificate that till has http rules
        http_rules = domain_repo.list_service_domains_by_cert_id(pk)
        if http_rules:
            raise err_still_has_http_rules

        cert.delete()

    @transaction.atomic
    def update_certificate(self, tenant, certificate_id, alias, certificate, private_key, certificate_type):
        cert_is_effective(certificate, private_key)
        cert = domain_repo.get_certificate_by_pk(certificate_id)
        if cert is None:
            raise err_cert_not_found
        if cert.alias != alias:
            self.__check_certificate_alias(tenant, alias)
            cert.alias = alias
        if certificate:
            cert.certificate = base64.b64encode(certificate)
        if certificate_type:
            cert.certificate_type = certificate_type
        if private_key:
            cert.private_key = private_key
        cert.save()

        # update all ingress related to the certificate
        body = {
            "certificate_id": cert.certificate_id,
            "certificate_name": "foobar",
            "certificate": base64.b64decode(cert.certificate),
            "private_key": cert.private_key,
        }
        team_regions = region_services.get_team_usable_regions(tenant.tenant_name, tenant.enterprise_id)
        for team_region in team_regions:
            try:
                region_api.update_ingresses_by_certificate(team_region.region_name, tenant.tenant_name, body)
            except Exception as e:
                logger.debug(e)
                continue
        return cert

    def __check_domain_name(self, team_id, domain_name, certificate_id=None):
        if not domain_name:
            raise ServiceHandleException(status_code=400, error_code=400, msg="domain can not be empty", msg_show="域名不能为空")
        zh_pattern = re.compile('[\\u4e00-\\u9fa5]+')
        match = zh_pattern.search(domain_name.decode('utf-8'))
        if match:
            raise ServiceHandleException(
                status_code=400, error_code=400, msg="domain can not be include chinese", msg_show="域名不能包含中文")
        # a租户绑定了域名manage.com,b租户就不可以在绑定该域名，只有a租户下可以绑定
        s_domain = domain_repo.get_domain_by_domain_name(domain_name)
        if s_domain and s_domain.tenant_id != team_id:
            raise ServiceHandleException(
                status_code=400, error_code=400, msg="domain be used other team", msg_show="域名已经被其他团队使用")
        if len(domain_name) > 256:
            raise ServiceHandleException(
                status_code=400, error_code=400, msg="domain more than 256 bytes", msg_show="域名超过256个字符")
        if certificate_id:
            certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
            cert = base64.b64decode(certificate_info.certificate)
            data = analyze_cert(cert)
            sans = data["issued_to"]
            for certificat_domain_name in sans:
                if certificat_domain_name.startswith('*'):
                    domain_suffix = certificat_domain_name[2:]
                else:
                    domain_suffix = certificat_domain_name
                domain_str = domain_name.encode('utf-8')
                if domain_str.endswith(domain_suffix):
                    return
            raise ServiceHandleException(status_code=400, error_code=400, msg="domain", msg_show="域名与选择的证书不匹配")

    def get_port_bind_domains(self, service, container_port):
        return domain_repo.get_service_domain_by_container_port(service.service_id, container_port)

    def get_tcp_port_bind_domains(self, service, container_port):
        return tcp_domain.get_service_tcp_domains_by_service_id_and_port(service.service_id, container_port)

        # get all http rules in define app
    def get_tcp_rules_by_app_id(self, app_id):
        services = group_service.get_group_services(app_id)
        service_ids = [s.service_id for s in services]
        return tcp_domain.get_services_tcpdomains(service_ids)

    def get_sld_domains(self, service, container_port):
        return domain_repo.get_service_domain_by_container_port(service.service_id,
                                                                container_port).filter(domain_type=DomainType.SLD_DOMAIN)

    def is_domain_exist(self, domain_name):
        domain = domain_repo.get_domain_by_domain_name(domain_name)
        return True if domain else False

    def bind_domain(self, tenant, user, service, domain_name, container_port, protocol, certificate_id, domain_type,
                    rule_extensions):
        self.__check_domain_name(tenant.tenant_id, domain_name, certificate_id)
        certificate_info = None
        http_rule_id = make_uuid(domain_name)
        if certificate_id:
            certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
        data = dict()
        data["domain"] = domain_name
        data["service_id"] = service.service_id
        data["tenant_id"] = tenant.tenant_id
        data["container_port"] = int(container_port)
        data["protocol"] = protocol
        data["http_rule_id"] = http_rule_id
        # 证书信息
        data["certificate"] = ""
        data["private_key"] = ""
        data["certificate_name"] = ""
        if rule_extensions:
            data["rule_extensions"] = rule_extensions
        if certificate_info:
            data["certificate"] = base64.b64decode(certificate_info.certificate)
            data["private_key"] = certificate_info.private_key
            data["certificate_name"] = certificate_info.alias
            data["certificate_id"] = certificate_info.certificate_id
        region_api.bind_http_domain(service.service_region, tenant.tenant_name, data)
        domain_info = dict()
        region = region_repo.get_region_by_region_name(service.service_region)
        domain_info["service_id"] = service.service_id
        domain_info["service_name"] = service.service_alias
        domain_info["domain_name"] = domain_name
        domain_info["domain_type"] = domain_type
        domain_info["service_alias"] = service.service_cname
        domain_info["create_time"] = self.get_time_now()
        domain_info["container_port"] = int(container_port)
        domain_info["protocol"] = "http"
        if certificate_id:
            domain_info["protocol"] = "https"
        if rule_extensions:
            domain_info["rule_extensions"] = rule_extensions
        domain_info["certificate_id"] = certificate_info.ID if certificate_info else 0
        domain_info["http_rule_id"] = http_rule_id
        domain_info["type"] = 1
        domain_info["service_alias"] = service.service_cname
        domain_info["tenant_id"] = tenant.tenant_id
        domain_info["region_id"] = region.region_id
        return domain_repo.add_service_domain(**domain_info)

    def unbind_domain(self, tenant, service, container_port, domain_name, is_tcp=False):
        if not is_tcp:
            service_domains = domain_repo.get_domain_by_name_and_port(service.service_id, container_port, domain_name)
            if not service_domains:
                raise ErrNotFoundDomain
            for servicer_domain in service_domains:
                data = dict()
                data["service_id"] = servicer_domain.service_id
                data["domain"] = servicer_domain.domain_name
                data["container_port"] = int(container_port)
                data["http_rule_id"] = servicer_domain.http_rule_id
                try:
                    region_api.delete_http_domain(service.service_region, tenant.tenant_name, data)
                    servicer_domain.delete()
                except region_api.CallApiError as e:
                    if e.status != 404:
                        raise e
        else:
            servicer_tcp_domain = tcp_domain.get_service_tcp_domain_by_service_id_and_port(
                service.service_id, container_port, domain_name)
            if not servicer_tcp_domain:
                raise ErrNotFoundStreamDomain
            data = dict()
            data["tcp_rule_id"] = servicer_tcp_domain.tcp_rule_id
            try:
                region_api.unbindTcpDomain(service.service_region, tenant.tenant_name, data)
                servicer_tcp_domain.delete()
            except region_api.CallApiError as e:
                if e.status != 404:
                    raise e

    def unbind_domian_by_domain(self, tenant, service, domain_id):
        domain = domain_repo.get_domain_by_id(domain_id)
        if domain and domain.service_id == service.service_id and tenant.tenant_id == domain.tenant_id:
            data = dict()
            data["service_id"] = domain.service_id
            data["domain"] = domain.domain_name
            data["container_port"] = int(domain.container_port)
            data["http_rule_id"] = domain.http_rule_id
            try:
                region_api.delete_http_domain(service.service_region, tenant.tenant_name, data)
            except region_api.CallApiError as e:
                if e.status != 404:
                    raise e
            domain_repo.delete_service_domain_by_id(domain_id)
            return True, "success"
        else:
            return False, "do not delete this domain id {0} service_id {1}".format(domain_id, service.service_id)

    def bind_siample_http_domain(self, tenant, user, service, domain_name, container_port):
        self.bind_domain(tenant, user, service, domain_name, container_port, "http", None, DomainType.WWW, None)
        return domain_repo.get_domain_by_domain_name(domain_name)

    def bind_httpdomain(self, tenant, user, service, httpdomain, return_model=False):
        domain_name = httpdomain["domain_name"]
        certificate_id = httpdomain["certificate_id"]
        rule_extensions = httpdomain.get("rule_extensions", [])
        domain_path = httpdomain.get("domain_path", None)
        domain_cookie = httpdomain.get("domain_cookie", None)
        domain_heander = httpdomain.get("domain_heander", None)
        protocol = httpdomain.get("protocol", None)
        domain_type = httpdomain["domain_type"]
        auto_ssl = httpdomain["auto_ssl"]
        auto_ssl_config = httpdomain["auto_ssl_config"]

        # 校验域名格式
        self.__check_domain_name(tenant.tenant_id, domain_name, certificate_id)
        http_rule_id = make_uuid(domain_name)
        domain_info = dict()
        certificate_info = None
        if certificate_id:
            certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
        data = dict()
        data["uuid"] = make_uuid(domain_name)
        data["domain"] = domain_name
        data["service_id"] = service.service_id
        data["tenant_id"] = tenant.tenant_id
        data["tenant_name"] = tenant.tenant_name
        data["protocol"] = protocol
        data["container_port"] = int(httpdomain["container_port"])
        data["add_time"] = self.get_time_now()
        data["add_user"] = user.nick_name if user else ""
        data["enterprise_id"] = tenant.enterprise_id
        data["http_rule_id"] = http_rule_id
        data["path"] = domain_path
        data["cookie"] = domain_cookie
        data["header"] = domain_heander
        data["weight"] = int(httpdomain.get("the_weight", 100))
        if rule_extensions:
            data["rule_extensions"] = rule_extensions
        data["certificate"] = ""
        data["private_key"] = ""
        data["certificate_name"] = ""
        data["certificate_id"] = ""
        if certificate_info:
            data["certificate"] = base64.b64decode(certificate_info.certificate)
            data["private_key"] = certificate_info.private_key
            data["certificate_name"] = certificate_info.alias
            data["certificate_id"] = certificate_info.certificate_id
        try:
            region_api.bind_http_domain(service.service_region, tenant.tenant_name, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        region = region_repo.get_region_by_region_name(service.service_region)
        if domain_path and domain_path != "/" or domain_cookie or domain_heander:
            domain_info["is_senior"] = True
        if protocol:
            domain_info["protocol"] = protocol
        else:
            domain_info["protocol"] = "http"
            if certificate_id:
                domain_info["protocol"] = "https"
        domain_info["http_rule_id"] = http_rule_id
        domain_info["service_id"] = service.service_id
        domain_info["service_name"] = service.service_alias
        domain_info["domain_name"] = domain_name
        domain_info["domain_type"] = domain_type
        domain_info["service_alias"] = service.service_cname
        domain_info["create_time"] = self.get_time_now()
        domain_info["container_port"] = int(httpdomain["container_port"])
        domain_info["certificate_id"] = certificate_info.ID if certificate_info else 0
        domain_info["domain_path"] = domain_path if domain_path else '/'
        domain_info["domain_cookie"] = domain_cookie if domain_cookie else ""
        domain_info["domain_heander"] = domain_heander if domain_heander else ""
        domain_info["the_weight"] = int(httpdomain.get("the_weight", 100))
        domain_info["tenant_id"] = tenant.tenant_id
        domain_info["auto_ssl"] = auto_ssl
        domain_info["auto_ssl_config"] = auto_ssl_config

        rule_extensions_str = ""
        if rule_extensions:
            # 拼接字符串，存入数据库
            for rule in rule_extensions:
                last_index = len(rule_extensions) - 1
                if last_index == rule_extensions.index(rule):
                    rule_extensions_str += rule["key"] + ":" + rule["value"]
                    continue
                rule_extensions_str += rule["key"] + ":" + rule["value"] + ","

        domain_info["rule_extensions"] = rule_extensions_str
        domain_info["region_id"] = region.region_id
        region = region_repo.get_region_by_region_name(service.service_region)
        # 判断类型（默认or自定义）
        if domain_name != "{0}.{1}.{2}.{3}".format(httpdomain["container_port"], service.service_alias, tenant.tenant_name,
                                                   region.httpdomain):
            domain_info["type"] = 1
        # 高级路由
        model = domain_repo.add_service_domain(**domain_info)
        if return_model:
            return model
        domain_info.update({"rule_extensions": rule_extensions})
        if certificate_info:
            domain_info.update({"certificate_name": certificate_info.alias})
        return domain_info

    def update_httpdomain(self, tenant, service, http_rule_id, update_data, re_model=False):
        service_domain = domain_repo.get_service_domain_by_http_rule_id(http_rule_id)
        if not service_domain:
            raise ServiceHandleException(msg="no found", status_code=404)
        domain_info = service_domain.to_dict()
        domain_info.update(update_data)

        self.__check_domain_name(tenant.tenant_id, domain_info["domain_name"], certificate_id=domain_info["certificate_id"])

        certificate_info = None
        if domain_info["certificate_id"]:
            certificate_info = domain_repo.get_certificate_by_pk(int(domain_info["certificate_id"]))

        data = dict()
        data["domain"] = domain_info["domain_name"]
        data["service_id"] = service.service_id
        data["tenant_id"] = tenant.tenant_id
        data["tenant_name"] = tenant.tenant_name
        data["container_port"] = int(domain_info["container_port"])
        data["enterprise_id"] = tenant.enterprise_id
        data["http_rule_id"] = http_rule_id
        data["path"] = domain_info["domain_path"] if domain_info["domain_path"] else None
        data["cookie"] = domain_info["domain_cookie"] if domain_info["domain_cookie"] else None
        data["header"] = domain_info["domain_heander"] if domain_info["domain_heander"] else None
        data["weight"] = int(domain_info["the_weight"])
        if "rule_extensions" in list(update_data.keys()):
            if domain_info["rule_extensions"]:
                data["rule_extensions"] = domain_info["rule_extensions"]
        else:
            try:
                rule_extensions = eval(domain_info["rule_extensions"])
            except Exception:
                rule_extensions = []
            if rule_extensions:
                data["rule_extensions"] = rule_extensions

        # 证书信息
        data["certificate"] = ""
        data["private_key"] = ""
        data["certificate_name"] = ""
        data["certificate_id"] = ""
        if certificate_info:
            data["certificate"] = base64.b64decode(certificate_info.certificate)
            data["private_key"] = certificate_info.private_key
            data["certificate_name"] = certificate_info.alias
            data["certificate_id"] = certificate_info.certificate_id
        try:
            # 给数据中心传送数据更新域名
            region_api.update_http_domain(service.service_region, tenant.tenant_name, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        if "rule_extensions" in list(update_data.keys()):
            rule_extensions_str = ""
            # 拼接字符串，存入数据库
            for rule in update_data["rule_extensions"]:
                last_index = len(update_data["rule_extensions"]) - 1
                if last_index == update_data["rule_extensions"].index(rule):
                    rule_extensions_str += rule["key"] + ":" + rule["value"]
                    continue
                rule_extensions_str += rule["key"] + ":" + rule["value"] + ","
        else:
            rule_extensions_str = domain_info["rule_extensions"]
        domain_info["rule_extensions"] = rule_extensions_str
        if domain_info["domain_path"] and domain_info["domain_path"] != "/" or \
                domain_info["domain_cookie"] or domain_info["domain_heander"]:
            domain_info["is_senior"] = True
        domain_info["protocol"] = "http"
        if domain_info["certificate_id"]:
            domain_info["protocol"] = "https"
        domain_info["certificate_id"] = domain_info["certificate_id"] if domain_info["certificate_id"] else 0
        domain_info["domain_path"] = domain_info["domain_path"] if domain_info["domain_path"] else '/'
        domain_info["domain_cookie"] = domain_info["domain_cookie"] if domain_info["domain_cookie"] else ""
        domain_info["domain_heander"] = domain_info["domain_heander"] if domain_info["domain_heander"] else ""
        domain_info["container_port"] = int(domain_info["container_port"])
        domain_info["service_id"] = service.service_id
        domain_info["service_name"] = service.service_alias
        model_data = ServiceDomain(**domain_info)
        model_data.save()
        if re_model:
            return model_data
        return domain_info

    def unbind_httpdomain(self, tenant, region, http_rule_id):
        servicer_http_omain = domain_repo.get_service_domain_by_http_rule_id(http_rule_id)
        if not servicer_http_omain:
            raise self.ErrNotFoundDomain
        data = dict()
        data["service_id"] = servicer_http_omain.service_id
        data["domain"] = servicer_http_omain.domain_name
        data["http_rule_id"] = http_rule_id
        try:
            region_api.delete_http_domain(region, tenant.tenant_name, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        servicer_http_omain.delete()

    def bind_tcpdomain(self, tenant, user, service, end_point, container_port, default_port, rule_extensions, default_ip):
        tcp_rule_id = make_uuid(tenant.tenant_name)
        ip = str(end_point.split(":")[0])
        ip = ip.replace(' ', '')
        port = end_point.split(":")[1]
        data = dict()
        data["service_id"] = service.service_id
        data["container_port"] = int(container_port)
        data["ip"] = ip
        data["port"] = int(port)
        data["tcp_rule_id"] = tcp_rule_id
        if rule_extensions:
            data["rule_extensions"] = rule_extensions
        try:
            # 给数据中心传送数据添加策略
            region_api.bindTcpDomain(service.service_region, tenant.tenant_name, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        region = region_repo.get_region_by_region_name(service.service_region)
        domain_info = dict()
        domain_info["tcp_rule_id"] = tcp_rule_id
        domain_info["service_id"] = service.service_id
        domain_info["service_name"] = service.service_alias
        domain_info["service_alias"] = service.service_cname
        domain_info["create_time"] = self.get_time_now()
        domain_info["container_port"] = int(container_port)
        domain_info["tenant_id"] = tenant.tenant_id
        # 查询端口协议
        tenant_service_port = port_repo.get_service_port_by_port(service.tenant_id, service.service_id, container_port)
        if tenant_service_port:
            protocol = tenant_service_port.protocol
        else:
            protocol = ''
        if protocol:
            domain_info["protocol"] = protocol
        else:
            domain_info["protocol"] = 'tcp'
        domain_info["end_point"] = end_point
        domain_info["region_id"] = region.region_id
        rule_extensions_str = ""
        if rule_extensions:
            # 拼接字符串，存入数据库
            for rule in rule_extensions:
                last_index = len(rule_extensions) - 1
                if last_index == rule_extensions.index(rule):
                    rule_extensions_str += rule["key"] + ":" + rule["value"]
                    continue
                rule_extensions_str += rule["key"] + ":" + rule["value"] + ","

        domain_info["rule_extensions"] = rule_extensions_str

        if int(end_point.split(":")[1]) != default_port:
            domain_info["type"] = 1
        tcp_domain.add_service_tcpdomain(**domain_info)
        domain_info.update({"rule_extensions": rule_extensions})
        return domain_info

    def update_tcpdomain(self, tenant, user, service, end_point, container_port, tcp_rule_id, protocol, type, rule_extensions,
                         default_ip):

        ip = end_point.split(":")[0]
        ip.replace(' ', '')
        port = end_point.split(":")[1]
        data = dict()
        data["service_id"] = service.service_id
        data["container_port"] = int(container_port)
        data["ip"] = ip
        data["port"] = int(port)
        data["tcp_rule_id"] = tcp_rule_id
        if rule_extensions:
            data["rule_extensions"] = rule_extensions

        try:
            # 给数据中心传送数据修改策略
            region_api.updateTcpDomain(service.service_region, tenant.tenant_name, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        region = region_repo.get_region_by_region_name(service.service_region)
        # 先删除再添加
        service_tcp_domain = tcp_domain.get_service_tcpdomain_by_tcp_rule_id(tcp_rule_id)
        service_tcp_domain.delete()
        domain_info = dict()
        domain_info["tcp_rule_id"] = tcp_rule_id
        domain_info["service_id"] = service.service_id
        domain_info["service_name"] = service.service_alias
        domain_info["service_alias"] = service.service_cname
        domain_info["create_time"] = self.get_time_now()
        domain_info["container_port"] = int(container_port)
        domain_info["tenant_id"] = tenant.tenant_id
        domain_info["protocol"] = protocol
        domain_info["end_point"] = end_point
        domain_info["type"] = type
        rule_extensions_str = ""
        if rule_extensions:
            # 拼接字符串，存入数据库
            for rule in rule_extensions:
                last_index = len(rule_extensions) - 1
                if last_index == rule_extensions.index(rule):
                    rule_extensions_str += rule["key"] + ":" + rule["value"]
                    continue
                rule_extensions_str += rule["key"] + ":" + rule["value"] + ","
        domain_info["rule_extensions"] = rule_extensions_str
        domain_info["region_id"] = region.region_id
        tcp_domain.add_service_tcpdomain(**domain_info)
        return 200, "success"

    def unbind_tcpdomain(self, tenant, region, tcp_rule_id):
        service_tcp_domain = tcp_domain.get_service_tcpdomain_by_tcp_rule_id(tcp_rule_id)
        if not service_tcp_domain:
            raise ErrNotFoundStreamDomain
        data = dict()
        data["tcp_rule_id"] = tcp_rule_id
        try:
            # 给数据中心传送数据删除策略
            region_api.unbindTcpDomain(region, tenant.tenant_name, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        service_tcp_domain.delete()

    # get all http rules in define app
    def get_http_rules_by_app_id(self, app_id):
        services = group_service.get_group_services(app_id)
        service_ids = [s.service_id for s in services]
        return domain_repo.get_domains_by_service_ids(service_ids)

    # get http rule by rule_id
    # if not exist, return None
    def get_http_rule_by_id(self, tenant_id, rule_id):
        rule = domain_repo.get_service_domain_by_http_rule_id(rule_id)
        if rule and rule.tenant_id != tenant_id:
            return None
        return rule

    # 获取应用下策略列表
    def get_app_service_domain_list(self, region, tenant, app_id, search_conditions, page, page_size):
        # 查询分页排序
        if search_conditions:
            search_conditions = search_conditions.decode('utf-8')
            # 获取总数
            cursor = connection.cursor()
            cursor.execute("select count(sd.domain_name) \
                from service_domain sd \
                    left join service_group_relation sgr on sd.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id  \
                where sd.tenant_id='{0}' and sd.region_id='{1}' and  sgr.group_id='{3}'\
                    and (sd.domain_name like '%{2}%' \
                        or sd.service_alias like '%{2}%' \
                        or sg.group_name like '%{2}%');".format(tenant.tenant_id, region.region_id, search_conditions, app_id))
            domain_count = cursor.fetchall()
            total = domain_count[0][0]
            start = (page - 1) * page_size
            remaining_num = total - (page - 1) * page_size
            end = page_size
            if remaining_num < page_size:
                end = remaining_num
            cursor = connection.cursor()
            cursor.execute("select sd.domain_name, sd.type, sd.is_senior, sd.certificate_id, sd.service_alias, \
                    sd.protocol, sd.service_name, sd.container_port, sd.http_rule_id, sd.service_id, \
                    sd.domain_path, sd.domain_cookie, sd.domain_heander, sd.the_weight, \
                    sd.is_outer_service \
                from service_domain sd \
                    left join service_group_relation sgr on sd.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id \
                where sd.tenant_id='{0}' \
                    and sd.region_id='{1}' \
                    and sgr.group_id='{5}' \
                    and (sd.domain_name like '%{2}%' \
                        or sd.service_alias like '%{2}%' \
                        or sg.group_name like '%{2}%') \
                order by type desc LIMIT {3},{4};".format(tenant.tenant_id, region.region_id, search_conditions, start, end,
                                                          app_id))
            tenant_tuples = cursor.fetchall()
        else:
            # 获取总数
            cursor = connection.cursor()
            cursor.execute("select count(sd.domain_name) \
                                    from service_domain sd \
                                        left join service_group_relation sgr on sd.service_id = sgr.service_id \
                                        left join service_group sg on sgr.group_id = sg.id  \
                                    where sd.tenant_id='{0}' and \
                                    sd.region_id='{1}' and \
                                    sgr.group_id='{2}';".format(tenant.tenant_id, region.region_id, app_id))
            domain_count = cursor.fetchall()

            total = domain_count[0][0]
            cursor = connection.cursor()

            cursor.execute("select sd.domain_name, sd.type, sd.is_senior, sd.certificate_id, sd.service_alias, \
                    sd.protocol, sd.service_name, sd.container_port, sd.http_rule_id, sd.service_id, \
                    sd.domain_path, sd.domain_cookie, sd.domain_heander, sd.the_weight, \
                    sd.is_outer_service \
                from service_domain sd \
                    left join service_group_relation sgr on sd.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id \
                where sd.tenant_id='{0}' \
                    and sd.region_id='{1}' \
                    and sgr.group_id='{2}' \
                order by type desc;".format(tenant.tenant_id, region.region_id, app_id))
            tenant_tuples = cursor.fetchall()

        return tenant_tuples, total

    # 获取应用下tcp&udp策略列表
    def get_app_service_tcp_domain_list(self, region, tenant, app_id, search_conditions, page, page_size):
        # 查询分页排序
        if search_conditions:
            search_conditions = search_conditions.decode('utf-8')
            # 获取总数
            cursor = connection.cursor()
            cursor.execute("select count(1) from service_tcp_domain std \
                    left join service_group_relation sgr on std.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id  \
                where std.tenant_id='{0}' and std.region_id='{1}' and sgr.group_id='{3}' \
                    and (std.end_point like '%{2}%' \
                        or std.service_alias like '%{2}%' \
                        or sg.group_name like '%{2}%');".format(tenant.tenant_id, region.region_id, search_conditions, app_id))
            domain_count = cursor.fetchall()

            total = domain_count[0][0]
            start = (page - 1) * page_size
            remaining_num = total - (page - 1) * page_size
            end = page_size
            if remaining_num < page_size:
                end = remaining_num

            cursor = connection.cursor()
            cursor.execute("select std.end_point, std.type, std.protocol, std.service_name, std.service_alias, \
                    std.container_port, std.tcp_rule_id, std.service_id, std.is_outer_service \
                from service_tcp_domain std \
                    left join service_group_relation sgr on std.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id  \
                where std.tenant_id='{0}' and std.region_id='{1}' and sgr.group_id='{5}' \
                    and (std.end_point like '%{2}%' \
                        or std.service_alias like '%{2}%' \
                        or sg.group_name like '%{2}%') \
                order by type desc LIMIT {3},{4};".format(tenant.tenant_id, region.region_id, search_conditions, start, end,
                                                          app_id))
            tenant_tuples = cursor.fetchall()
        else:
            # 获取总数
            cursor = connection.cursor()
            cursor.execute("select count(1) from service_tcp_domain std \
                    left join service_group_relation sgr on std.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id  \
                where std.tenant_id='{0}' and std.region_id='{1}' and sgr.group_id='{2}';".format(
                tenant.tenant_id, region.region_id, app_id))
            domain_count = cursor.fetchall()

            total = domain_count[0][0]
            start = (page - 1) * page_size
            remaining_num = total - (page - 1) * page_size
            end = page_size
            if remaining_num < page_size:
                end = remaining_num

            cursor = connection.cursor()
            cursor.execute("select std.end_point, std.type, std.protocol, std.service_name, std.service_alias, \
                    std.container_port, std.tcp_rule_id, std.service_id, std.is_outer_service \
                from service_tcp_domain std \
                    left join service_group_relation sgr on std.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id  \
                where std.tenant_id='{0}' and std.region_id='{1}' and sgr.group_id='{4}' \
                order by type desc LIMIT {2},{3};".format(tenant.tenant_id, region.region_id, start, end, app_id))
            tenant_tuples = cursor.fetchall()
        return tenant_tuples, total

    def check_domain_exist(self, service_id, container_port, domain_name, protocol, domain_path, rule_extensions):
        rst = False
        http_exist = False
        add_httptohttps = False
        service_domain = domain_repo.get_domain_by_name_and_port_and_protocol(service_id, container_port, domain_name, protocol,
                                                                              domain_path)
        if service_domain:
            rst = True
        domains = domain_repo.get_domain_by_name_and_path(domain_name, domain_path)
        for domain in domains:
            if "http" == domain.protocol:
                http_exist = True
            if "httptohttps" in domain.rule_extensions:
                rst = True
        if rule_extensions:
            for rule in rule_extensions:
                if rule["key"] == "httptohttps":
                    add_httptohttps = True
        if http_exist and add_httptohttps:
            rst = True
        return rst

    # Get http gateway rule list by enterprise id
    # retun dict list
    def get_http_rules_by_enterprise_id(self, enterprise_id, is_auto_ssl=None):
        teams = team_repo.get_teams_by_enterprise_id(enterprise_id)
        if not teams:
            return []
        team_ids = []
        team_names = {}
        for team in teams:
            team_ids.append(team.tenant_id)
            team_names[team.tenant_id] = team.tenant_name
        domains = domain_repo.get_domains_by_tenant_ids(team_ids, is_auto_ssl)
        rules = []
        region_ids = []
        service_ids = []
        # append tenant name
        for domain in domains:
            rule = model_to_dict(domain)
            rule["create_time"] = domain.create_time
            rule["team_name"] = team_names[domain.tenant_id]
            region_ids.append(domain.region_id)
            service_ids.append(domain.service_id)
            rules.append(rule)
        # append region name
        region_ids_new = list(set(region_ids))
        regions = region_repo.get_regions_by_region_ids(enterprise_id, region_ids_new)
        region_names = {}
        for region in regions:
            region_names[region.region_id] = region.region_name
        # append app id
        app_ids = group_service.get_app_id_by_service_ids(service_ids)
        re_rules = []
        for rule in rules:
            rule["region_name"] = region_names.get(rule["region_id"])
            rule["app_id"] = app_ids.get(rule["service_id"])
            # ignore region name or app id not found rule
            if rule["region_name"] and rule["app_id"]:
                re_rules.append(rule)
        return re_rules

    def update_http_rule_config(self, team, region_name, rule_id, configs):
        self.check_set_header(configs["set_headers"])
        service_domain = get_object_or_404(ServiceDomain, msg="no domain", msg_show="策略不存在", http_rule_id=rule_id)
        service = get_object_or_404(TenantServiceInfo, msg="no service", msg_show="组件不存在", service_id=service_domain.service_id)
        cf = configuration_repo.get_configuration_by_rule_id(rule_id)
        gcc_dict = dict()
        gcc_dict["body"] = configs
        gcc_dict["rule_id"] = rule_id
        try:
            res, data = region_api.upgrade_configuration(region_name, team, service.service_alias, gcc_dict)
            if res.status == 200:
                if cf:
                    cf.value = json.dumps(configs)
                    cf.save()
                else:
                    cf_dict = dict()
                    cf_dict["rule_id"] = rule_id
                    cf_dict["value"] = json.dumps(configs)
                    configuration_repo.add_configuration(**cf_dict)
        except region_api.CallApiFrequentError as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="update http rule configuration failure", msg_show="更新HTTP策略的参数发生异常", status_code=500, error_code=500)

    def check_set_header(self, set_headers):
        r = re.compile('([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]')
        for header in set_headers:
            if header["key"] and not r.match(header["key"]):
                raise ServiceHandleException(
                    msg="forbidden key: {0}".format(header["key"]), msg_show="Header Key不合法", status_code=400, error_code=400)

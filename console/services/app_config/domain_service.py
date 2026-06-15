# -*- coding: utf8 -*-
"""
  Created on 18/1/23.
"""
import base64
import datetime
import json
import logging
import re
from typing import Any, List, Optional, Tuple

from console.constants import DomainType
from console.exception.main import ServiceHandleException
from console.models.main import RegionConfig
from console.repositories.app_config import (configuration_repo, domain_repo, port_repo, tcp_domain)
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.services.app_config.exceptoin import (err_cert_name_exists, err_cert_not_found, err_still_has_http_rules)
from console.services.gateway_api import gateway_api
from console.services.group_service import group_service
from console.services.region_services import region_services
from console.utils.certutil import analyze_cert, cert_is_effective
from console.utils.shortcuts import get_object_or_404
from django.db import connection, transaction
from django.forms.models import model_to_dict
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import (ServiceDomain, ServiceDomainCertificate, TenantServiceInfo)
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

ErrNotFoundDomain = ServiceHandleException(status_code=404, error_code=1404, msg="domain not found", msg_show="域名不存在")
ErrNotFoundStreamDomain = ServiceHandleException(status_code=404, error_code=2404, msg="domain not found", msg_show="策略不存在")


class DomainService(object):
    HTTP = "http"

    def get_time_now(self) -> str:
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def get_certificate(self, tenant: Any, page: int, page_size: int, search_key: Optional[str] = None) -> Tuple[list, Any]:
        end = page_size * page - 1  # 一页数据的开始索引
        start = end - page_size + 1  # 一页数据的结束索引
        certificate, nums = domain_repo.get_tenant_certificate_page(tenant.tenant_id, start, end, search_key)
        c_list = []
        for c in certificate:
            cert = base64.b64decode(c.certificate).decode('utf-8')
            data: dict = dict()
            data["alias"] = c.alias
            data["certificate_type"] = c.certificate_type
            data["id"] = c.ID
            data.update(analyze_cert(cert))
            c_list.append(data)
        return c_list, nums

    def __check_certificate_alias(self, tenant: Any, alias: str) -> None:
        if domain_repo.get_certificate_by_alias(tenant.tenant_id, alias):
            raise err_cert_name_exists

    def add_certificate(self, region: RegionConfig, tenant: Any, alias: str, certificate_id: str, certificate: str,
                        private_key: str, certificate_type: str) -> ServiceDomainCertificate:
        self.__check_certificate_alias(tenant, alias)
        cert_is_effective(certificate, private_key)
        if certificate_type == "gateway":
            gateway_api.create_gateway_tls(region.region_name, tenant.tenant_name, tenant.namespace, alias, private_key,
                                           certificate)
        certificate = base64.b64encode(certificate.encode('utf-8')).decode('utf-8')
        certificate = domain_repo.add_certificate(tenant.tenant_id, alias, certificate_id, certificate, private_key,
                                                  certificate_type)
        return certificate

    def delete_certificate_by_alias(self, tenant: Any, alias: str) -> Tuple[int, str]:
        certificate = domain_repo.get_certificate_by_alias(tenant.tenant_id, alias)
        if certificate:
            certificate.delete()
            return 200, "success"
        else:
            return 404, "证书不存在"

    def get_certificate_by_pk(self, pk: int) -> Tuple[int, str, Optional[dict]]:
        certificate = domain_repo.get_certificate_by_pk(pk)
        if not certificate:
            return 404, "证书不存在", None
        data: dict = dict()
        data["alias"] = certificate.alias
        data["certificate_type"] = certificate.certificate_type
        data["id"] = certificate.ID
        data["tenant_id"] = certificate.tenant_id
        data["certificate"] = base64.b64decode(certificate.certificate).decode('utf-8')
        data["private_key"] = certificate.private_key
        return 200, "success", data

    def delete_certificate_by_pk(self, region: str, tenant: Any, pk: int) -> None:
        cert = domain_repo.get_certificate_by_pk(pk)
        if not cert:
            raise err_cert_not_found

        # can't delete the cerificate that till has http rules
        # NOTE: pk is an int here but list_service_domains_by_cert_id expects str (certificate_id
        # column is str); pre-existing behavior relies on ORM coercion.
        http_rules = domain_repo.list_service_domains_by_cert_id(pk)  # type: ignore[arg-type]
        if http_rules:
            raise err_still_has_http_rules
        if cert.certificate_type == "gateway":
            gateway_api.delete_gateway_tls(region, tenant.tenant_name, tenant.namespace, cert.alias)
        cert.delete()

    @transaction.atomic
    def check_certificate(self, certificate_id: str, domain_name: str) -> str:
        certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
        # NOTE: potential latent None-bug — get_certificate_by_pk returns Optional and
        # certificate_info is dereferenced without a guard (AttributeError if pk missing).
        cert = base64.b64decode(certificate_info.certificate).decode('utf-8')  # type: ignore[union-attr]
        data = analyze_cert(cert)
        sans = data["issued_to"]
        for certificat_domain_name in sans:
            if certificat_domain_name.startswith('*'):
                domain_suffix = certificat_domain_name[2:]
            else:
                domain_suffix = certificat_domain_name
            if domain_name.endswith(domain_suffix):
                return "pass"
        return "un_pass"

    @transaction.atomic
    def update_certificate(self, region: RegionConfig, tenant: Any, certificate_id: str, alias: str, certificate: str,
                           private_key: str, certificate_type: str) -> ServiceDomainCertificate:
        cert_is_effective(certificate, private_key)
        # NOTE: certificate_id is str here while get_certificate_by_pk expects int; relies on
        # ORM coercion (other callers wrap with int()).
        cert = domain_repo.get_certificate_by_pk(certificate_id)  # type: ignore[arg-type]
        if cert is None:
            raise err_cert_not_found
        if cert.alias != alias:
            self.__check_certificate_alias(tenant, alias)
            cert.alias = alias
        if certificate:
            cert.certificate = base64.b64encode(certificate.encode('utf-8')).decode('utf-8')
        if certificate_type and certificate_type != cert.certificate_type:
            if certificate_type == "服务端证书":
                gateway_api.delete_gateway_tls(region.region_name, tenant.tenant_name, tenant.namespace, alias)
            cert.certificate_type = certificate_type
        if private_key:
            cert.private_key = private_key
        if certificate_type == "gateway":
            gateway_api.update_gateway_tls(region.region_name, tenant.tenant_name, tenant.namespace, alias, private_key,
                                           certificate)
        cert.save()

        # update all ingress related to the certificate
        body = {
            "certificate_id": cert.certificate_id,
            "certificate_name": "foobar",
            "certificate": base64.b64decode(cert.certificate).decode('utf-8'),
            "private_key": cert.private_key,
        }
        team_regions = region_services.get_team_usable_regions(tenant.tenant_name, tenant.enterprise_id)
        # NOTE: get_team_usable_regions is typed Optional; iterating without a guard would raise
        # TypeError if it ever returned None (invariant: it returns a QuerySet here).
        for team_region in team_regions:  # type: ignore[union-attr]
            try:
                region_api.update_ingresses_by_certificate(team_region.region_name, tenant.tenant_name, body)
            except Exception as e:
                logger.debug(e)
                continue
        return cert

    def __check_domain_name(
            self,
            team_id: str,
            region_id: str,
            domain_name: str,
            certificate_id: Optional[str] = None,
    ) -> None:
        if not domain_name:
            raise ServiceHandleException(status_code=400, error_code=400, msg="domain can not be empty", msg_show="域名不能为空")
        zh_pattern = re.compile('[\\u4e00-\\u9fa5]+')
        match = zh_pattern.search(domain_name)
        if match:
            raise ServiceHandleException(
                status_code=400, error_code=400, msg="domain can not be include chinese", msg_show="域名不能包含中文")
        # a租户绑定了域名manage.com,b租户就不可以在绑定该域名，只有a租户下可以绑定
        s_domain = domain_repo.get_domain_by_domain_name(domain_name)
        if s_domain and s_domain.tenant_id != team_id and s_domain.region_id == region_id:
            raise ServiceHandleException(
                status_code=400, error_code=400, msg="domain be used other team", msg_show="域名已经被其他团队使用")
        if len(domain_name) > 256:
            raise ServiceHandleException(
                status_code=400, error_code=400, msg="domain more than 256 bytes", msg_show="域名超过256个字符")

    def get_port_bind_domains(self, service: Any, container_port: int) -> Any:
        return domain_repo.get_service_domain_by_container_port(service.service_id, container_port)

    def get_tcp_port_bind_domains(self, service: Any, container_port: int) -> Any:
        return tcp_domain.get_service_tcp_domains_by_service_id_and_port(service.service_id, container_port)

        # get all http rules in define app
    def get_tcp_rules_by_app_id(self, region_name: str, app_id: str) -> Any:
        services = group_service.get_group_services(app_id)
        service_ids = [s.service_id for s in services]
        return self.get_tcp_rules_by_service_ids(region_name, service_ids)

    def get_sld_domains(self, service: Any, container_port: int) -> Any:
        return domain_repo.get_service_domain_by_container_port(service.service_id,
                                                                container_port).filter(domain_type=DomainType.SLD_DOMAIN)

    def is_domain_exist(self, domain_name: str) -> bool:
        domain = domain_repo.get_domain_by_domain_name(domain_name)
        return True if domain else False

    def bind_domain(self, tenant: Any, user: Any, service: Any, domain_name: str, container_port: int, protocol: str,
                    certificate_id: str, domain_type: str, rule_extensions: Any) -> ServiceDomain:
        region = region_repo.get_region_by_region_name(service.service_region)
        # NOTE: get_region_by_region_name is typed Optional; region.region_id is accessed without
        # a guard (invariant: service.service_region maps to an existing region).
        self.__check_domain_name(tenant.tenant_id, region.region_id, domain_name,  # type: ignore[union-attr]
                                 certificate_id)
        certificate_info = None
        http_rule_id = make_uuid(domain_name)
        if certificate_id:
            certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
        data: dict = dict()
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
            data["certificate"] = base64.b64decode(certificate_info.certificate).decode('utf-8')
            data["private_key"] = certificate_info.private_key
            data["certificate_name"] = certificate_info.alias
            data["certificate_id"] = certificate_info.certificate_id
        domain_info: dict = dict()
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
        domain_info["region_id"] = region.region_id  # type: ignore[union-attr]
        return domain_repo.add_service_domain(**domain_info)

    def unbind_domain(self, tenant: Any, service: Any, container_port: int, domain_name: str, is_tcp: bool = False,
                      app_id: Optional[str] = None) -> None:
        if not is_tcp:
            service_domains = domain_repo.get_domain_by_name_and_port(service.service_id, container_port, domain_name)
            if not service_domains:
                raise ErrNotFoundDomain
            for servicer_domain in service_domains:
                data: dict = dict()
                data["service_id"] = servicer_domain.service_id
                data["domain"] = servicer_domain.domain_name
                data["container_port"] = int(container_port)
                data["http_rule_id"] = servicer_domain.http_rule_id
                try:
                    # k8s 资源名 不能以 / * 特殊字符命名，故做替换
                    # p-p 对应 /
                    # s-s 对应 *
                    path_app_id = "/api-gateway/v1/" + tenant.tenant_name + "/routes/http/" + str(
                        app_id) + servicer_domain.domain_name + "p-ps-s"
                    region_api.api_gateway_delete_proxy(service.service_region, tenant.tenant_name, path_app_id)
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

    def unbind_domian_by_domain(self, tenant: Any, service: Any, domain_id: str) -> Tuple[bool, str]:
        domain = domain_repo.get_domain_by_id(domain_id)
        if domain and domain.service_id == service.service_id and tenant.tenant_id == domain.tenant_id:
            data: dict = dict()
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

    def bind_siample_http_domain(self, tenant: Any, user: Any, service: Any, domain_name: str,
                                 container_port: int) -> Optional[ServiceDomain]:
        # NOTE: bind_domain's certificate_id param is annotated str but None is passed here
        # (pre-existing behavior — bind_domain guards on `if certificate_id`).
        self.bind_domain(
            tenant, user, service, domain_name, container_port, "http", None,  # type: ignore[arg-type]
            DomainType.WWW, None)
        return domain_repo.get_domain_by_domain_name(domain_name)

    def bind_httpdomain(self, tenant: Any, user: Any, service: Any, httpdomain: dict,
                        return_model: bool = False) -> Any:
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
        path_rewrite = httpdomain.get("path_rewrite", False)
        rewrites = httpdomain["rewrites"] if httpdomain.get("rewrites") else []
        if isinstance(rewrites, str):
            rewrites = eval(rewrites)
        region = region_repo.get_region_by_region_name(service.service_region)
        # 校验域名格式
        # NOTE: get_region_by_region_name is typed Optional; region attrs are accessed without a
        # guard here and below (invariant: service.service_region maps to an existing region).
        self.__check_domain_name(tenant.tenant_id, region.region_id, domain_name,  # type: ignore[union-attr]
                                 certificate_id)
        http_rule_id = make_uuid(domain_name)
        domain_info: dict = dict()
        certificate_info = None
        if certificate_id:
            certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
        data: dict = dict()
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
            data["certificate"] = base64.b64decode(certificate_info.certificate).decode('utf-8')
            data["private_key"] = certificate_info.private_key
            data["certificate_name"] = certificate_info.alias
            data["certificate_id"] = certificate_info.certificate_id
        data["path_rewrite"] = path_rewrite
        data["rewrites"] = rewrites
        try:
            region_api.bind_http_domain(service.service_region, tenant.tenant_name, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
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
        domain_info["region_id"] = region.region_id  # type: ignore[union-attr]
        domain_info["path_rewrite"] = path_rewrite
        domain_info["rewrites"] = json.dumps(rewrites) if rewrites else []
        region = region_repo.get_region_by_region_name(service.service_region)
        # 判断类型（默认or自定义）
        if domain_name != "{0}-{1}-{2}.{3}".format(service.service_alias, httpdomain["container_port"], tenant.tenant_name,
                                                   region.httpdomain):  # type: ignore[union-attr]
            domain_info["type"] = 1
        # 高级路由
        model = domain_repo.add_service_domain(**domain_info)
        if return_model:
            return model
        domain_info.update({"rule_extensions": rule_extensions})
        if certificate_info:
            domain_info.update({"certificate_name": certificate_info.alias})
        return domain_info

    @transaction.atomic
    def update_httpdomain(self, tenant: Any, service: Any, http_rule_id: str, update_data: dict,
                          re_model: bool = False) -> Any:
        service_domain = domain_repo.get_service_domain_by_http_rule_id(http_rule_id)
        if not service_domain:
            raise ServiceHandleException(msg="no found", status_code=404)
        domain_info = service_domain.to_dict()
        domain_info.update(update_data)

        self.__check_domain_name(
            tenant.tenant_id,
            service_domain.region_id,
            domain_info["domain_name"],
            certificate_id=domain_info["certificate_id"])

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
            data["certificate"] = base64.b64decode(certificate_info.certificate).decode('utf-8')
            data["private_key"] = certificate_info.private_key
            data["certificate_name"] = certificate_info.alias
            data["certificate_id"] = certificate_info.certificate_id
        data["path_rewrite"] = domain_info.get("path_rewrite", False)
        data["rewrites"] = eval(service_domain.rewrites) if service_domain.rewrites else []
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
        if "rewrites" in list(update_data.keys()):
            domain_info["rewrites"] = json.dumps(update_data["rewrites"])
        model_data = ServiceDomain(**domain_info)
        model_data.save()
        if re_model:
            return model_data
        return domain_info

    def unbind_httpdomain(self, tenant: Any, region: str, http_rule_id: str) -> None:
        servicer_http_omain = domain_repo.get_service_domain_by_http_rule_id(http_rule_id)
        if not servicer_http_omain:
            # NOTE: potential latent bug — ErrNotFoundDomain is a module-level global, not a
            # class attribute; `self.ErrNotFoundDomain` raises AttributeError at runtime.
            raise self.ErrNotFoundDomain  # type: ignore[attr-defined]
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

    def bind_tcpdomain(self, tenant: Any, user: Any, service: Any, end_point: str, container_port: int,
                       default_port: int, rule_extensions: Any, default_ip: Optional[str]) -> dict:
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
        domain_info: dict = dict()
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
        # NOTE: region is Optional (get_region_by_region_name) and dereferenced without a guard.
        domain_info["region_id"] = region.region_id  # type: ignore[union-attr]
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

    @transaction.atomic
    def update_tcpdomain(self, tenant: Any, user: Any, service: Any, end_point: str, container_port: int, tcp_rule_id: str,
                         protocol: str, type: int, rule_extensions: Any, default_ip: Optional[str]) -> Tuple[int, str]:

        ip = end_point.split(":")[0]
        ip.replace(' ', '')
        port = end_point.split(":")[1]
        data: dict = dict()
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
        # NOTE: potential latent None-bug — Optional return dereferenced without a guard
        # (AttributeError if the tcp rule id does not exist).
        service_tcp_domain.delete()  # type: ignore[union-attr]
        domain_info: dict = dict()
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
        # NOTE: region is Optional (get_region_by_region_name) and dereferenced without a guard.
        domain_info["region_id"] = region.region_id  # type: ignore[union-attr]
        tcp_domain.add_service_tcpdomain(**domain_info)
        return 200, "success"

    def unbind_tcpdomain(self, tenant: Any, region: str, tcp_rule_id: str) -> None:
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
    def get_http_rules_by_app_id(self, app_id: str) -> Any:
        services = group_service.get_group_services(app_id)
        service_ids = [s.service_id for s in services]
        return domain_repo.get_domains_by_service_ids(service_ids)

    # get http rule by rule_id
    # if not exist, return None
    def get_http_rule_by_id(self, tenant_id: str, rule_id: str) -> Optional[ServiceDomain]:
        rule = domain_repo.get_service_domain_by_http_rule_id(rule_id)
        if rule and rule.tenant_id != tenant_id:
            return None
        return rule

    # 获取应用下策略列表
    def get_app_service_domain_list(self, region: RegionConfig, tenant: Any, app_id: str, search_conditions: Any, page: int,
                                    page_size: int) -> Tuple[Any, Any]:
        # 查询分页排序
        if search_conditions:
            if isinstance(search_conditions, bytes):
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
                    sd.is_outer_service, sd.path_rewrite, sd.rewrites \
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
                    sd.is_outer_service, sd.path_rewrite, sd.rewrites \
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
    def get_app_service_tcp_domain_list(self, region: RegionConfig, tenant: Any, app_id: str, search_conditions: Any,
                                        page: int, page_size: int) -> Tuple[Any, Any]:
        # 查询分页排序
        if search_conditions:
            if isinstance(search_conditions, bytes):
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

    def check_domain_exist(self, service_id: str, container_port: int, domain_name: str, protocol: str,
                           domain_path: Any, rule_extensions: Any) -> bool:
        rst = False
        http_exist = False
        add_httptohttps = False
        service_domain = domain_repo.get_domain_by_name_and_port_and_protocol(service_id, container_port, domain_name, protocol,
                                                                              domain_path)
        if service_domain:
            rst = True
        domains = domain_repo.get_domain_by_name_and_path(domain_name, domain_path)
        # NOTE: get_domain_by_name_and_path is typed Optional; iterating without a guard would
        # raise TypeError if it returned None (invariant: it returns a QuerySet).
        for domain in domains:  # type: ignore[union-attr]
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
    def get_http_rules_by_enterprise_id(self, enterprise_id: str, is_auto_ssl: Optional[bool] = None) -> List[dict]:
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

    def update_http_rule_config(self, team: Any, region_name: str, rule_id: str, configs: dict) -> None:
        self.check_set_header(configs["set_headers"])
        service_domain = get_object_or_404(ServiceDomain, msg="no domain", msg_show="策略不存在", http_rule_id=rule_id)
        service = get_object_or_404(TenantServiceInfo, msg="no service", msg_show="组件不存在", service_id=service_domain.service_id)
        cf = configuration_repo.get_configuration_by_rule_id(rule_id)
        gcc_dict: dict = dict()
        gcc_dict["body"] = configs
        gcc_dict["rule_id"] = rule_id
        try:
            res, data = region_api.upgrade_configuration(region_name, team.tenant_name, service.service_alias, gcc_dict)
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

    def check_set_header(self, set_headers: Any) -> None:
        r = re.compile('([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]')
        for header in set_headers:
            if "item_key" in header and not r.match(header["item_key"]):
                raise ServiceHandleException(
                    msg="forbidden key: {0}".format(header["item_key"]),
                    msg_show="Header Key不合法",
                    status_code=400,
                    error_code=400)

    @staticmethod
    def delete_by_port(component_id: str, port: int) -> None:
        http_rules = domain_repo.list_service_domain_by_port(component_id, port)
        http_rule_ids = [rule.http_rule_id for rule in http_rules]
        # delete rule extensions
        configuration_repo.delete_by_rule_ids(http_rule_ids)
        # delete http rules
        domain_repo.delete_service_domain_by_port(component_id, port)
        # delete tcp rules
        tcp_domain.delete_by_component_port(component_id, port)

    def create_default_gateway_rule(self, tenant: Any, region_info: RegionConfig, service: Any, port: Any,
                                    app_id: str) -> None:
        if port.protocol == "http":
            service_id = service.service_id
            service_name = service.service_alias
            container_port = port.container_port
            domain_name = str(service_name) + "-" + str(container_port) + "-" + str(tenant.tenant_name) + "." + str(
                region_info.httpdomain)

            create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            protocol = "http"
            http_rule_id = make_uuid(domain_name)
            tenant_id = tenant.tenant_id
            service_alias = service.service_cname
            region_id = region_info.region_id
            domain_repo.create_service_domains(service_id, service_name, domain_name, create_time, container_port, protocol,
                                               http_rule_id, tenant_id, service_alias, region_id)
            logger.debug("create default gateway http rule for component {0} port {1}".format(
                service.service_alias, port.container_port))
        else:
            svc = port_repo.get_service_port_by_port(tenant.tenant_id, service.service_id, port.container_port)
            # 默认创建成功一条tcp记录，端口随机
            # NOTE: potential latent None-bug — svc is Optional and dereferenced
            # (svc.container_port / svc.protocol) without a guard.
            data = region_api.api_gateway_bind_tcp_domain(
                region=service.service_region,
                tenant_name=tenant.tenant_name,
                k8s_service_name=service.service_alias,
                container_port=svc.container_port,  # type: ignore[union-attr]
                app_id=app_id,
                protocol=svc.protocol)  # type: ignore[union-attr]
            # NOTE: region_api Optional body dereferenced without a guard (index on None).
            end_point = "0.0.0.0:{0}".format(data["bean"])  # type: ignore[index]
            service_id = service.service_id
            service_name = service.service_alias
            create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            container_port = port.container_port
            protocol = port.protocol
            service_alias = service.service_cname
            tcp_rule_id = make_uuid(end_point)
            tenant_id = tenant.tenant_id
            region_id = region_info.region_id
            tcp_domain.create_service_tcp_domains(service_id, service_name, end_point, create_time, container_port, protocol,
                                                  service_alias, tcp_rule_id, tenant_id, region_id)
            logger.debug("create default gateway stream rule for component {0} port {1}, endpoint {2}".format(
                service.service_alias, port.container_port, end_point))

    def get_components_that_contains_gateway_rules(self, region_name: str, services: Any) -> Any:
        service_ids = [s.service_id for s in services]
        tcp_rules = self.get_tcp_rules_by_service_ids(region_name, service_ids)
        http_rules = domain_repo.get_domains_by_service_ids(service_ids)

        exist_tcp_rules: dict = dict()
        for tcp_rule in tcp_rules:
            if not exist_tcp_rules.get(tcp_rule.service_id):
                exist_tcp_rules[tcp_rule.service_id] = []
            exist_tcp_rules[tcp_rule.service_id].append(tcp_rule)

        exist_http_rules: dict = dict()
        for http_rule in http_rules:
            if not exist_http_rules.get(http_rule.service_id):
                exist_http_rules[http_rule.service_id] = []
            exist_http_rules[http_rule.service_id].append(http_rule)

        for service in services:
            gateway_rules = dict()
            gateway_rules["http"] = exist_http_rules.get(service.service_id, [])
            gateway_rules["tcp"] = exist_tcp_rules.get(service.service_id, [])
            service.gateway_rules = gateway_rules
        return services

    def get_tcp_rules_by_service_ids(self, region_name: str, service_ids: Any) -> Any:
        tcpdomains = tcp_domain.get_services_tcpdomains(service_ids)
        tcpdomain = region_services.get_region_tcpdomain(region_name=region_name)
        for domain in tcpdomains:
            arr = domain.end_point.split(":")
            if len(arr) != 2 or arr[0] != "0.0.0.0":
                continue
            domain.end_point = tcpdomain + ":" + arr[1]
        return tcpdomains

    def get_http_ruls_by_service_ids(self, service_ids: Any) -> Any:
        return domain_repo.get_domains_by_service_ids(service_ids)

    def get_component_access_infos(self, region_name: str, service_id: str) -> List[str]:
        http_domian = self.get_http_ruls_by_service_ids([service_id])
        stream_domian = self.get_tcp_rules_by_service_ids(region_name, [service_id])
        access_infos = []
        if http_domian:
            for domain in http_domian:
                access = "{0}://{1}".format("http" if domain.certificate_id == 0 else "https", domain.domain_name)
                if domain.domain_path:
                    access = access + domain.domain_path
                access_infos.append(access)
        if stream_domian:
            for sd in stream_domian:
                access_infos.append(sd.end_point)
        return access_infos


domain_service = DomainService()

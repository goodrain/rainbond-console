# -*- coding: utf8 -*-
"""
  Created on 18/1/23.
"""
import base64
import datetime
import logging
import re

from django.db import transaction
from django.db import connection

from console.constants import DomainType
from console.repositories.app_config import domain_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import tcp_domain
from console.repositories.region_repo import region_repo
from console.services.app_config.exceptoin import err_cert_name_exists
from console.services.app_config.exceptoin import err_cert_not_found
from console.services.app_config.exceptoin import err_still_has_http_rules
from console.services.group_service import group_service
from console.services.team_services import team_services
from console.utils.certutil import analyze_cert
from console.utils.certutil import cert_is_effective
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class DomainService(object):
    HTTP = "http"

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
        # r = re.compile("^[A-Za-z0-9]+$")
        # if not r.match(alias):
        #     return 400, u"证书别名只能是数字和字母的组合"
        if domain_repo.get_certificate_by_alias(tenant.tenant_id, alias):
            raise err_cert_name_exists

    def add_certificate(self, tenant, alias, certificate_id, certificate, private_key, certificate_type):
        self.__check_certificate_alias(tenant, alias)

        cert_is_effective(certificate)
        certificate = base64.b64encode(certificate)
        certificate = domain_repo.add_certificate(
            tenant.tenant_id, alias, certificate_id, certificate, private_key, certificate_type)
        return 200, "success", certificate

    def delete_certificate_by_alias(self, tenant, alias):
        certificate = domain_repo.get_certificate_by_alias(tenant.tenant_id, alias)
        if certificate:
            certificate.delete()
            return 200, "success"
        else:
            return 404, u"证书不存在"

    def get_certificate_by_pk(self, pk):
        certificate = domain_repo.get_certificate_by_pk(pk)
        if not certificate:
            return 404, u"证书不存在", None
        data = dict()
        data["alias"] = certificate.alias
        data["certificate_type"] = certificate.certificate_type
        data["id"] = certificate.ID
        data["tenant_id"] = certificate.tenant_id
        data["certificate"] = base64.b64decode(certificate.certificate)
        data["private_key"] = certificate.private_key
        return 200, u"success", data

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
    def update_certificate(
            self, region_name, tenant, certificate_id, new_alias, certificate, private_key, certificate_type):
        cert_is_effective(certificate)

        cert = domain_repo.get_certificate_by_pk(certificate_id)
        if cert is None:
            raise err_cert_not_found
        if cert.alias != new_alias:
            self.__check_certificate_alias(tenant, new_alias)
            cert.alias = new_alias
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
        region_api.update_ingresses_by_certificate(region_name, tenant.tenant_name, body)

    def __check_domain_name(self, team_name, domain_name, domain_type, certificate_id):
        if not domain_name:
            return 400, u"域名不能为空"
        zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
        match = zhPattern.search(domain_name.decode('utf-8'))
        if match:
            return 400, u"域名不能包含中文"
        # a租户绑定了域名manage.com,b租户就不可以在绑定该域名，只有a租户下可以绑定
        s_domain = domain_repo.get_domain_by_domain_name(domain_name)
        if s_domain:
            team = team_services.get_tenant_by_tenant_name(team_name)
            if team:
                if s_domain.tenant_id != team.tenant_id:
                    return 400, u"该域名已被其他团队使用"
        # re_exp = "^(?=^.{3,255}$)[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+$"
        # if not re.match(re_exp, domain_name):
        #     return 400, u"域名不规范（示例：www.example.com 域名不应包含协议头）"
        if len(domain_name) > 256:
            return 400, u"域名过长"
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
                logger.debug('---------domain_suffix-------->{0}'.format(domain_suffix))
                domain_str = domain_name.encode('utf-8')
                if domain_str.endswith(domain_suffix):
                    return 200, u"success"
            return 400, u"域名和证书不匹配"

        return 200, u"success"

    def __is_domain_conflict(self, domain_name, team_name):
        regions = region_repo.get_usable_regions()
        conflict_domains = ["{0}.{1}".format(team_name, region.httpdomain) for region in regions]
        for d in conflict_domains:
            if d in domain_name:
                return True, d
        return False, None

    def get_port_bind_domains(self, service, container_port):
        return domain_repo.get_service_domain_by_container_port(service.service_id, container_port)

    def get_tcp_port_bind_domains(self, service, container_port):
        return tcp_domain.get_service_tcp_domains_by_service_id_and_port(service.service_id, container_port)

    def get_sld_domains(self, service, container_port):
        return domain_repo.get_service_domain_by_container_port(
            service.service_id, container_port).filter(
            domain_type=DomainType.SLD_DOMAIN)

    def is_domain_exist(self, domain_name):
        domain = domain_repo.get_domain_by_domain_name(domain_name)
        return True if domain else False

    def bind_domain(self, tenant, user, service, domain_name, container_port, protocol, certificate_id, domain_type,
                    rule_extensions):
        code, msg = self.__check_domain_name(tenant.tenant_name, domain_name, domain_type, certificate_id)

        if code != 200:
            return code, msg
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
        domain_info["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
        domain_repo.add_service_domain(**domain_info)
        return 200, u"success"

    def unbind_domain(self, tenant, service, container_port, domain_name, is_tcp=False):
        if not is_tcp:
            servicerDomain = domain_repo.get_domain_by_name_and_port(service.service_id, container_port, domain_name)
            if not servicerDomain:
                return 404, u"域名不存在"
            for servicer_domain in servicerDomain:
                data = dict()
                data["service_id"] = servicer_domain.service_id
                data["domain"] = servicer_domain.domain_name
                data["container_port"] = int(container_port)
                data["http_rule_id"] = servicer_domain.http_rule_id
                try:
                    region_api.delete_http_domain(service.service_region, tenant.tenant_name, data)
                    servicer_domain.delete()
                    return 200, u"success"
                except region_api.CallApiError as e:
                    if e.status != 404:
                        raise e

        else:
            servicer_tcp_domain = tcp_domain.get_service_tcp_domain_by_service_id_and_port(
                service.service_id, container_port, domain_name)
            if not servicer_tcp_domain:
                return 404, u"域名不存在"
            data = dict()
            data["tcp_rule_id"] = servicer_tcp_domain.tcp_rule_id
            try:
                region_api.unbindTcpDomain(service.service_region, tenant.tenant_name, data)
                servicer_tcp_domain.delete()
                return 200, u"success"
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
            return True, u"success"
        else:
            return False, u"do not delete this domain id {0} service_id {1}".format(domain_id, service.service_id)

    def bind_siample_http_domain(self, tenant, user, service, domain_name, container_port):

        res, msg = self.bind_domain(tenant, user, service, domain_name,
                                    container_port, "http", None, DomainType.WWW, None)
        if res == 200:
            return domain_repo.get_domain_by_domain_name(domain_name)
        return None

    def bind_httpdomain(self, tenant, user, service, domain_name, container_port, protocol, certificate_id, domain_type,
                        domain_path, domain_cookie, domain_heander, the_weight, rule_extensions):
        # 校验域名格式
        code, msg = self.__check_domain_name(tenant.tenant_name, domain_name, domain_type, certificate_id)
        http_rule_id = make_uuid(domain_name)
        domain_info = dict()
        if code != 200:
            return code, msg, domain_info
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
        data["container_port"] = int(container_port)
        data["add_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data["add_user"] = user.nick_name if user else ""
        data["enterprise_id"] = tenant.enterprise_id
        data["http_rule_id"] = http_rule_id
        data["path"] = domain_path if domain_path else None
        data["cookie"] = domain_cookie if domain_cookie else None
        data["header"] = domain_heander if domain_heander else None
        data["weight"] = int(the_weight)
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
            # 给数据中心传送数据绑定域名
            logger.debug('---------------------------->{0}'.format(data))
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
        domain_info["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        domain_info["container_port"] = int(container_port)
        domain_info["certificate_id"] = certificate_info.ID if certificate_info else 0
        domain_info["domain_path"] = domain_path if domain_path else '/'
        domain_info["domain_cookie"] = domain_cookie if domain_cookie else ""
        domain_info["domain_heander"] = domain_heander if domain_heander else ""
        domain_info["the_weight"] = the_weight
        domain_info["tenant_id"] = tenant.tenant_id

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
        if domain_name != str(container_port) + "." + str(service.service_alias) + "." + str(tenant.tenant_name) + "." + str(
                region.httpdomain):
            domain_info["type"] = 1
        # 高级路由
        domain_repo.add_service_domain(**domain_info)
        domain_info.update({"rule_extensions": rule_extensions})
        if certificate_info:
            domain_info.update({"certificate_name": certificate_info.alias})
        return 200, u"success", domain_info

    def update_httpdomain(
            self, tenant, user, service, domain_name, container_port, certificate_id, domain_type, domain_path,
            domain_cookie, domain_heander, http_rule_id, the_weight, rule_extensions):
        # 校验域名格式
        code, msg = self.__check_domain_name(tenant.tenant_name, domain_name, domain_type, certificate_id)
        domain_info = dict()
        if code != 200:
            return code, msg, domain_info
        certificate_info = None
        if certificate_id:
            certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
        data = dict()
        data["domain"] = domain_name
        data["service_id"] = service.service_id
        data["tenant_id"] = tenant.tenant_id
        data["tenant_name"] = tenant.tenant_name
        data["container_port"] = int(container_port)
        data["enterprise_id"] = tenant.enterprise_id
        data["http_rule_id"] = http_rule_id
        data["path"] = domain_path if domain_path else None
        data["cookie"] = domain_cookie if domain_cookie else None
        data["header"] = domain_heander if domain_heander else None
        data["weight"] = int(the_weight)
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
        service_domain = domain_repo.get_service_domain_by_http_rule_id(http_rule_id)
        service_domain.delete()
        region = region_repo.get_region_by_region_name(service.service_region)
        # 高级路由
        if domain_path and domain_path != "/" or domain_cookie or domain_heander:
            domain_info["is_senior"] = True
        domain_info["protocol"] = "http"
        if certificate_id:
            domain_info["protocol"] = "https"
        domain_info["http_rule_id"] = http_rule_id
        domain_info["service_id"] = service.service_id
        domain_info["service_name"] = service.service_alias
        domain_info["domain_name"] = domain_name
        domain_info["domain_type"] = domain_type
        domain_info["service_alias"] = service.service_cname
        domain_info["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        domain_info["container_port"] = int(container_port)
        domain_info["certificate_id"] = certificate_info.ID if certificate_info else 0
        domain_info["domain_path"] = domain_path if domain_path else '/'
        domain_info["domain_cookie"] = domain_cookie if domain_cookie else ""
        domain_info["domain_heander"] = domain_heander if domain_heander else ""
        domain_info["the_weight"] = the_weight
        domain_info["tenant_id"] = tenant.tenant_id
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
        if domain_name != str(container_port) + "." + str(service.service_alias) + "." + str(tenant.tenant_name) + "." + str(
                region.httpdomain):
            domain_info["type"] = 1

        domain_repo.add_service_domain(**domain_info)
        domain_info.update({"rule_extensions": rule_extensions})
        if certificate_info:
            domain_info.update({"certificate_name": certificate_info.alias})
        return 200, u"success", domain_info

    def unbind_httpdomain(self, tenant, region, http_rule_id):
        servicer_http_omain = domain_repo.get_service_domain_by_http_rule_id(http_rule_id)

        if not servicer_http_omain:
            return 404, u"域名不存在"
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
        return 200, u"success"

    def bind_tcpdomain(self, tenant, user, service, end_point, container_port, default_port, rule_extensions, default_ip):
        tcp_rule_id = make_uuid(tenant.tenant_name)
        ip = str(end_point.split(":")[0])
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
        domain_info["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
        return 200, u"success", domain_info

    def update_tcpdomain(
            self, tenant, user, service, end_point, container_port, tcp_rule_id, protocol, type, rule_extensions,
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
        domain_info["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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

        domain_info["region_id"] = region.region_id

        tcp_domain.add_service_tcpdomain(**domain_info)
        return 200, u"success"

    def unbind_tcpdomain(self, tenant, region, tcp_rule_id):
        service_tcp_domain = tcp_domain.get_service_tcpdomain_by_tcp_rule_id(tcp_rule_id)
        if not service_tcp_domain:
            return 404, u"策略不存在"
        data = dict()
        data["tcp_rule_id"] = tcp_rule_id
        try:
            # 给数据中心传送数据删除策略
            region_api.unbindTcpDomain(region, tenant.tenant_name, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        service_tcp_domain.delete()
        return 200, u"success"

    # get all http rules in define app
    def get_http_rules_by_app_id(self, app_id):
        services = group_service.get_group_services(app_id)
        service_ids = [s.service_id for s in services]
        return domain_repo.get_domains_by_service_ids(service_ids)

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
                        or sg.group_name like '%{2}%');".format(
                tenant.tenant_id, region.region_id, search_conditions, app_id))
            domain_count = cursor.fetchall()
            total = domain_count[0][0]
            start = (page - 1) * page_size
            remaining_num = total - (page - 1) * page_size
            end = page_size
            if remaining_num < page_size:
                end = remaining_num
            cursor = connection.cursor()
            cursor.execute(
                "select sd.domain_name, sd.type, sd.is_senior, sd.certificate_id, sd.service_alias, \
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
                order by type desc LIMIT {3},{4};".format(
                    tenant.tenant_id, region.region_id, search_conditions, start, end, app_id))
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
                                    sgr.group_id='{2}';".format(
                tenant.tenant_id, region.region_id, app_id))
            domain_count = cursor.fetchall()

            total = domain_count[0][0]
            start = (page - 1) * page_size
            remaining_num = total - (page - 1) * page_size
            end = page_size
            if remaining_num < page_size:
                end = remaining_num

            cursor = connection.cursor()

            cursor.execute(
                "select sd.domain_name, sd.type, sd.is_senior, sd.certificate_id, sd.service_alias, \
                    sd.protocol, sd.service_name, sd.container_port, sd.http_rule_id, sd.service_id, \
                    sd.domain_path, sd.domain_cookie, sd.domain_heander, sd.the_weight, \
                    sd.is_outer_service \
                from service_domain sd \
                    left join service_group_relation sgr on sd.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id \
                where sd.tenant_id='{0}' \
                    and sd.region_id='{1}' \
                    and sgr.group_id='{2}' \
                order by type desc;".format(
                    tenant.tenant_id, region.region_id, app_id))
            tenant_tuples = cursor.fetchall()

        return tenant_tuples, total

    # 获取应用下tcp&udp策略列表
    def get_app_service_tcp_domain_list(self, region, tenant, app_id, search_conditions, page, page_size):
        # 查询分页排序
        if search_conditions:
            search_conditions = search_conditions.decode('utf-8')
            # 获取总数
            cursor = connection.cursor()
            cursor.execute(
                "select count(1) from service_tcp_domain std \
                    left join service_group_relation sgr on std.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id  \
                where std.tenant_id='{0}' and std.region_id='{1}' and sgr.group_id='{3}' \
                    and (std.end_point like '%{2}%' \
                        or std.service_alias like '%{2}%' \
                        or sg.group_name like '%{2}%');".format(
                    tenant.tenant_id, region.region_id, search_conditions, app_id))
            domain_count = cursor.fetchall()

            total = domain_count[0][0]
            start = (page - 1) * page_size
            remaining_num = total - (page - 1) * page_size
            end = page_size
            if remaining_num < page_size:
                end = remaining_num

            cursor = connection.cursor()
            cursor.execute(
                "select std.end_point, std.type, std.protocol, std.service_name, std.service_alias, \
                    std.container_port, std.tcp_rule_id, std.service_id, std.is_outer_service \
                from service_tcp_domain std \
                    left join service_group_relation sgr on std.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id  \
                where std.tenant_id='{0}' and std.region_id='{1}' and sgr.group_id='{5}' \
                    and (std.end_point like '%{2}%' \
                        or std.service_alias like '%{2}%' \
                        or sg.group_name like '%{2}%') \
                order by type desc LIMIT {3},{4};".format(
                    tenant.tenant_id, region.region_id, search_conditions, start, end, app_id))
            tenant_tuples = cursor.fetchall()
        else:
            # 获取总数
            cursor = connection.cursor()
            cursor.execute(
                "select count(1) from service_tcp_domain std \
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
            cursor.execute(
                "select std.end_point, std.type, std.protocol, std.service_name, std.service_alias, \
                    std.container_port, std.tcp_rule_id, std.service_id, std.is_outer_service \
                from service_tcp_domain std \
                    left join service_group_relation sgr on std.service_id = sgr.service_id \
                    left join service_group sg on sgr.group_id = sg.id  \
                where std.tenant_id='{0}' and std.region_id='{1}' and sgr.group_id='{4}' \
                order by type desc LIMIT {2},{3};".format(
                    tenant.tenant_id, region.region_id, start, end, app_id))
            tenant_tuples = cursor.fetchall()
        return tenant_tuples, total

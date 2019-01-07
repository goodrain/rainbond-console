# -*- coding: utf8 -*-
"""
  Created on 18/1/23.
"""
from console.repositories.app_config import domain_repo, tcp_domain
import re
import datetime
import logging
import base64

from console.repositories.region_repo import region_repo
from console.constants import DomainType
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid
from console.utils.certutil import analyze_cert, cert_is_effective
from console.services.app_config import port_service
from console.repositories.app_config import port_repo


region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class DomainService(object):
    HTTP = "http"

    def get_certificate(self, tenant, page, page_size):
        end = page_size * page - 1 # 一页数据的开始索引
        start = end - page_size + 1 # 一页数据的结束索引
        print(start, end)
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
        r = re.compile("^[A-Za-z0-9]+$")
        if not r.match(alias):
            return 400, u"证书别名只能是数字和字母的组合"
        if domain_repo.get_certificate_by_alias(tenant.tenant_id, alias):
            return 412, u"证书别名已存在"
        return 200, "success"

    def add_certificate(self, tenant, alias,certificate_id, certificate, private_key,certificate_type):
        code, msg = self.__check_certificate_alias(tenant, alias)
        if code != 200:
            return code, msg, None
        if cert_is_effective(certificate):
            certificate = base64.b64encode(certificate)
            certificate = domain_repo.add_certificate(tenant.tenant_id, alias, certificate_id,certificate, private_key,certificate_type)
            return 200, "success", certificate
        return 400, u'证书无效',certificate

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
        certificate = domain_repo.get_certificate_by_pk(pk)
        if certificate:
            certificate.delete()
            return 200, u"success"
        else:
            return 404, u"证书不存在"

    def update_certificate(self, tenant, certificate_id, new_alias, certificate, private_key,certificate_type):
        if not cert_is_effective(certificate):
            return 400, u'证书无效'
        certif = domain_repo.get_certificate_by_pk(certificate_id)
        if certif.alias != new_alias:
            code, msg = self.__check_certificate_alias(tenant, new_alias)
            if code != 200:
                return code, msg
            certif.alias = new_alias
        if certif:
            certif.certificate = base64.b64encode(certificate)
        if certif.certificate_type != certificate_type:
            certif.certificate_type = certificate_type
        if private_key:
            certif.private_key = private_key
        certif.save()
        return 200, "success"

    def __check_domain_name(self, team_name, domain_name, domain_type, certificate_id):
        if not domain_name:
            return 400, u"域名不能为空"
        zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
        match = zhPattern.search(domain_name.decode('utf-8'))
        if match:
            return 400, u"域名不能包含中文"
        # re_exp = "^(?=^.{3,255}$)[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+$"
        # if not re.match(re_exp, domain_name):
        #     return 400, u"域名不规范（示例：www.example.com 域名不应包含协议头）"
        if len(domain_name) > 256:
            return 400, u"域名过长"
        if certificate_id:
            certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
            cert = base64.b64decode(certificate_info.certificate)
            data = analyze_cert(cert)
            certificat_domain_name = data["issued_to"]
            if not certificat_domain_name.startswith("*"):
                if certificat_domain_name != domain_name:
                    return 400, u"域名和证书不匹配"
            else:
                domain_suffix = certificat_domain_name[2:]
                if not domain_name.endwith(domain_suffix):
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
        return domain_repo.get_service_domain_by_container_port(service.service_id, container_port).filter(
            domain_type=DomainType.SLD_DOMAIN)

    def is_domain_exist(self, domain_name):
        domain = domain_repo.get_domain_by_domain_name(domain_name)
        return True if domain else False

    def bind_domain(self, tenant, user, service, domain_name, container_port, protocol, certificate_id, domain_type, g_id, rule_extensions):
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
        domain_info["g_id"] = str(g_id)
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
            servicer_tcp_domain = tcp_domain.get_service_tcp_domain_by_service_id_and_port(service.service_id, container_port, domain_name)
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

    def bind_httpdomain(self, tenant, user, service, domain_name, container_port, protocol, certificate_id, domain_type,
                    group_name, domain_path, domain_cookie, domain_heander, the_weight, g_id, rule_extensions):
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
        data["add_user"] = user.nick_name
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
        domain_info["group_name"] = group_name
        domain_info["domain_path"] = domain_path if domain_path else None
        domain_info["domain_cookie"] = domain_cookie if domain_cookie else None
        domain_info["domain_heander"] = domain_heander if domain_heander else None
        domain_info["the_weight"] = the_weight
        domain_info["tenant_id"] = tenant.tenant_id
        domain_info["g_id"] = str(g_id)

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
        if domain_name != str(container_port) + "." + str(service.service_alias) + "." + str(tenant.tenant_name) + "." + str(region.httpdomain):
            domain_info["type"] = 1
        # 高级路由
        domain_repo.add_service_domain(**domain_info)
        domain_info.update({"rule_extensions": rule_extensions})
        if certificate_info:
            domain_info.update({"certificate_name": certificate_info.alias})
        return 200, u"success", domain_info

    def update_httpdomain(self, tenant, user, service, domain_name, container_port, certificate_id, domain_type,
                    group_name, domain_path, domain_cookie, domain_heander, http_rule_id, the_weight, g_id, rule_extensions):
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
        domain_info["group_name"] = group_name
        domain_info["domain_path"] = domain_path if domain_path else None
        domain_info["domain_cookie"] = domain_cookie if domain_cookie else None
        domain_info["domain_heander"] = domain_heander if domain_heander else None
        domain_info["the_weight"] = the_weight
        domain_info["tenant_id"] = tenant.tenant_id
        domain_info["g_id"] = str(g_id)
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
        if domain_name != str(container_port) + "." + str(service.service_alias) + "." + str(
                tenant.tenant_name) + "." + str(region.httpdomain):
            domain_info["type"] = 1

        domain_repo.add_service_domain(**domain_info)
        domain_info.update({"rule_extensions": rule_extensions})
        if certificate_info:
            domain_info.update({"certificate_name": certificate_info.alias})
        return 200, u"success", domain_info

    def unbind_httpdomain(self, tenant, service, http_rule_id):
        servicer_http_omain = domain_repo.get_service_domain_by_http_rule_id(http_rule_id)

        if not servicer_http_omain:
            return 404, u"域名不存在"
        data = dict()
        data["service_id"] = servicer_http_omain.service_id
        data["domain"] = servicer_http_omain.domain_name
        data["http_rule_id"] = http_rule_id
        try:
            region_api.delete_http_domain(service.service_region, tenant.tenant_name, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        servicer_http_omain.delete()
        return 200, u"success"

    def bind_tcpdomain(self, tenant, user, service, end_point, container_port, group_name,
                       default_port, g_id, rule_extensions, default_ip):
        tcp_rule_id = make_uuid(group_name)
        ip = str(end_point.split(":")[0])
        ip.replace(' ', '')
        port = end_point.split(":")[1]
        data = dict()
        data["service_id"] = service.service_id
        data["container_port"] = int(container_port)
        if default_ip != ip:
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
        domain_info["group_name"] = group_name
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
        domain_info["g_id"] = str(g_id)
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

    def update_tcpdomain(self, tenant, user, service, end_point, container_port, group_name,
                         tcp_rule_id, protocol, type, g_id, rule_extensions, default_ip):
        ip = end_point.split(":")[0]
        ip.replace(' ', '')
        port = end_point.split(":")[1]
        data = dict()
        data["service_id"] = service.service_id
        data["container_port"] = int(container_port)
        if default_ip != ip:
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
        domain_info["group_name"] = group_name
        domain_info["tenant_id"] = tenant.tenant_id
        domain_info["protocol"] = protocol
        domain_info["end_point"] = end_point
        domain_info["type"] = type
        domain_info["g_id"] = str(g_id)
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

    def unbind_tcpdomain(self, tenant, service, tcp_rule_id):
        service_tcp_domain = tcp_domain.get_service_tcpdomain_by_tcp_rule_id(tcp_rule_id)
        if not service_tcp_domain:
            return 404, u"策略不存在"
        data = dict()
        data["tcp_rule_id"] = tcp_rule_id
        try:
            # 给数据中心传送数据删除策略
            region_api.unbindTcpDomain(service.service_region, tenant.tenant_name, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        service_tcp_domain.delete()
        return 200, u"success"

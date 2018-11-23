# -*- coding: utf8 -*-
"""
  Created on 18/1/23.
"""
from console.repositories.app_config import domain_repo
import re
import datetime
from console.repositories.region_repo import region_repo
from console.constants import DomainType
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid
from console.utils.certutil import analyze_cert
import base64


region_api = RegionInvokeApi()


class DomainService(object):
    HTTP = "http"

    def get_certificate(self, tenant):
        certificate = domain_repo.get_tenant_certificate(tenant.tenant_id)
        c_list = []
        for c in certificate:
            cert = base64.b64decode(c.certificate)
            data = dict()
            data["alias"] = c.alias
            data["id"] = c.ID
            data["certificate_info"] = analyze_cert(cert)
            c_list.append(data)
        return c_list

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
        certificate = base64.b64encode(certificate)
        certificate = domain_repo.add_certificate(tenant.tenant_id, alias, certificate_id,certificate, private_key,certificate_type)
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
        certificate = base64.b64decode(certificate)
        return 200, u"success", certificate

    def delete_certificate_by_pk(self, pk):
        certificate = domain_repo.get_certificate_by_pk(pk)
        if certificate:
            certificate.delete()
            return 200, u"success"
        else:
            return 404, u"证书不存在"

    def update_certificate(self, tenant, certificate_id, new_alias, certificate, private_key):
        certif = domain_repo.get_certificate_by_pk(certificate_id)
        if certif.alias != new_alias:
            code, msg = self.__check_certificate_alias(tenant, new_alias)
            if code != 200:
                return code, msg
            certif.alias = new_alias
        if certif:
            certif.certificate = base64.b64encode(certificate)
        if private_key:
            certif.private_key = private_key
        certif.save()
        return 200, "success"

    def __check_domain_name(self, team_name, domain_name, domain_type):
        if not domain_name:
            return 400, u"域名不能为空"
        zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
        match = zhPattern.search(domain_name.decode('utf-8'))
        if match:
            return 400, u"域名不能包含中文"
        re_exp = "^(?=^.{3,255}$)[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+$"
        if not re.match(re_exp, domain_name):
            return 400, u"域名不规范（示例：www.example.com 域名不应包含协议头）"
        if len(domain_name) > 256:
            return 400, u"域名过长"
        domain = domain_repo.get_domain_by_domain_name(domain_name)
        if domain:
            return 412, u"域名已存在"
        if domain_type == DomainType.WWW:
            is_domain_conflict, conflict_domain = self.__is_domain_conflict(domain_name, team_name)
            if is_domain_conflict:
                return 409, u"域名中不能该域名{0}".format(conflict_domain)

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

    def get_sld_domains(self, service, container_port):
        return domain_repo.get_service_domain_by_container_port(service.service_id, container_port).filter(
            domain_type=DomainType.SLD_DOMAIN)

    def is_domain_exist(self, domain_name):
        domain = domain_repo.get_domain_by_domain_name(domain_name)
        return True if domain else False

    def bind_domain(self, tenant, user, service, domain_name, container_port, protocol, certificate_id, domain_type,
                    group_name, domain_path, domain_cookie, domain_heander, rule_extensions, the_weight):
        code, msg = self.__check_domain_name(tenant.tenant_name, domain_name, domain_type)
        http_rule_id = make_uuid(domain_name)
        if code != 200:
            return code, msg
        certificate_info = None
        if certificate_id:
            certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
        data = {}
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
        data["heander"] = domain_heander if domain_heander else None
        data["weight"] = the_weight
        if len(rule_extensions) > 0:
            data["rule_extensions"] = rule_extensions

        # 证书信息
        data["certificate"] = ""
        data["private_key"] = ""
        data["certificate_name"] = ""
        data["certificate_id"] = ""
        if certificate_info:
            data["certificate"] = certificate_info.certificate
            data["private_key"] = certificate_info.private_key
            data["certificate_name"] = certificate_info.alias
            data["certificate_id"] = certificate_info.certificate_id
        try:
            # 给数据中心传送数据绑定域名
            region_api.bindDomain(service.service_region, tenant.tenant_name, service.service_alias, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        domain_info = dict()
        if domain_path and domain_path != "/":
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

        domain_repo.add_service_domain(**domain_info)
        return 200, u"success"

    def update_domain(self, tenant, user, service, domain_name, container_port, certificate_id, domain_type,
                    group_name, domain_path, domain_cookie, domain_heander, rule_extensions, http_rule_id, protocol, the_weight):
        certificate_info = None
        if certificate_id:
            certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
        data = {}
        data["domain"] = domain_name
        data["service_id"] = service.service_id
        data["tenant_id"] = tenant.tenant_id
        data["tenant_name"] = tenant.tenant_name
        data["container_port"] = int(container_port)
        data["protocol"] = protocol
        data["enterprise_id"] = tenant.enterprise_id
        data["http_rule_id"] = http_rule_id
        data["path"] = domain_path if domain_path else None
        data["cookie"] = domain_cookie if domain_cookie else None
        data["heander"] = domain_heander if domain_heander else None
        data["weight"] = the_weight
        if len(rule_extensions) > 0:
            data["rule_extensions"] = rule_extensions

        # 证书信息
        data["certificate"] = ""
        data["private_key"] = ""
        data["certificate_name"] = ""
        data["certificate_id"] = ""
        if certificate_info:
            data["certificate"] = certificate_info.certificate
            data["private_key"] = certificate_info.private_key
            data["certificate_name"] = certificate_info.alias
            data["certificate_id"] = certificate_info.certificate_id
        try:
            # 给数据中心传送数据更新域名
            region_api.updateDomain(service.service_region, tenant.tenant_name, service.service_alias, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        service_domain = domain_repo.get_service_domain_by_container_port(service.service_id, container_port)
        if not service_domain:
            return 400, u"策略不存在"
        service_domain.service_id = service.service_id
        service_domain.service_name = service.service_alias
        service_domain.service_alias = service.service_cname
        service_domain.domain_name = domain_name
        service_domain.domain_type = domain_type
        service_domain.container_port = int(container_port)
        service_domain.certificate_id = certificate_info.ID if certificate_info else 0
        service_domain.group_name = group_name
        service_domain.domain_path = domain_path if domain_path else None
        service_domain.domain_cookie = domain_cookie if domain_cookie else None
        service_domain.domain_heander = domain_heander if domain_heander else None
        service_domain.the_weight = the_weight
        if protocol:
            service_domain.protocol = protocol
        else:
            service_domain.protocol = "http"
            if certificate_id:
                service_domain.protocol = "https"
        if domain_path and domain_path != "/":
            service_domain.is_senior = True
        service_domain.save()
        return 200, u"success"

    def unbind_domain(self, tenant, service, container_port, domain_name):
        servicerDomain = domain_repo.get_domain_by_name_and_port(service.service_id, container_port, domain_name)
        if not servicerDomain:
            return 404, u"域名不存在"
        data = {}
        data["service_id"] = servicerDomain.service_id
        data["domain"] = servicerDomain.domain_name
        data["pool_name"] = tenant.tenant_name + "@" + service.service_alias + ".Pool"
        data["container_port"] = int(container_port)
        data["enterprise_id"] = tenant.enterprise_id
        try:
            region_api.unbindDomain(service.service_region, tenant.tenant_name, service.service_alias, data)
        except region_api.CallApiError as e:
            if e.status != 404:
                raise e
        servicerDomain.delete()
        return 200, u"success"

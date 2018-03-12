# -*- coding: utf8 -*-
"""
  Created on 18/1/23.
"""
from console.repositories.app_config import domain_repo
import re
import datetime

from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()


class DomainService(object):
    HTTP = "http"

    def get_certificate(self, tenant):
        certificate = domain_repo.get_tenant_certificate(tenant.tenant_id)
        c_list = []
        for c in certificate:
            data = dict()
            data["alias"] = c.alias
            data["id"] = c.ID
            c_list.append(data)
        return c_list

    def __check_certificate_alias(self, tenant, alias):
        r = re.compile("^[A-Za-z0-9]+$")
        if not r.match(alias):
            return 400, u"证书别名只能是数字和字母的组合"
        if domain_repo.get_certificate_by_alias(tenant.tenant_id, alias):
            return 412, u"证书别名已存在"
        return 200, "success"

    def add_certificate(self, tenant, alias, certificate, private_key):
        code, msg = self.__check_certificate_alias(tenant, alias)
        if code != 200:
            return code, msg, None
        certificate = domain_repo.add_certificate(tenant.tenant_id, alias, certificate, private_key)
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
            certif.certificate = certificate
        if private_key:
            certif.private_key = private_key
        certif.save()
        return 200, "success"

    def __check_domain_name(self, domain_name):
        if not domain_name:
            return 400, u"域名不能为空"
        zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
        match = zhPattern.search(domain_name.decode('utf-8'))
        if match:
            return 400, u"域名不能包含中文"
        re_exp = "^(?=^.{3,255}$)[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+$"
        if not re.match(re_exp,domain_name):
            return 400, u"域名不规范（示例：www.example.com 域名不应包含协议头）"
        domain = domain_repo.get_domain_by_domain_name(domain_name)
        if domain:
            return 412, u"域名已存在"
        return 200, u"success"

    def get_port_bind_domains(self, service, container_port):
        return domain_repo.get_service_domain_by_container_port(service.service_id, container_port)

    def is_domain_exist(self, domain_name):
        domain = domain_repo.get_domain_by_domain_name(domain_name)
        return True if domain else False

    def bind_domain(self, tenant, user, service, domain_name, container_port, protocol, certificate_id):
        code, msg = self.__check_domain_name(domain_name)
        if code != 200:
            return code, msg
        certificate_info = None
        if protocol != self.HTTP:
            if not certificate_id:
                return 400, u"证书不能为空"

            certificate_info = domain_repo.get_certificate_by_pk(int(certificate_id))
        data = {}
        data["uuid"] = make_uuid(domain_name)
        data["domain_name"] = domain_name
        data["service_alias"] = service.service_alias
        data["tenant_id"] = tenant.tenant_id
        data["tenant_name"] = tenant.tenant_name
        data["service_port"] = int(container_port)
        data["protocol"] = protocol
        data["add_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data["add_user"] = user.nick_name
        data["enterprise_id"] = tenant.enterprise_id
        # 证书信息
        data["certificate"] = ""
        data["private_key"] = ""
        data["certificate_name"] = ""
        if certificate_info:
            data["certificate"] = certificate_info.certificate
            data["private_key"] = certificate_info.private_key
            data["certificate_name"] = certificate_info.alias
        region_api.bindDomain(service.service_region, tenant.tenant_name, service.service_alias, data)

        domain_info = {}
        domain_info["service_id"] = service.service_id
        domain_info["service_name"] = service.service_alias
        domain_info["domain_name"] = domain_name
        domain_info["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        domain_info["container_port"] = int(container_port)
        domain_info["protocol"] = protocol
        domain_info["certificate_id"] = certificate_info.ID if certificate_info else 0
        domain_repo.add_service_domain(**domain_info)
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

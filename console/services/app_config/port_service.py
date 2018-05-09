# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
from console.constants import ServicePortConstants
from console.repositories.app_config import port_repo
import re

from www.apiclient.regionapi import RegionInvokeApi

from console.services.app_config.env_service import AppEnvVarService
import logging
from console.repositories.app_config import domain_repo
from django.conf import settings
from console.services.region_services import region_services

region_api = RegionInvokeApi()
env_var_service = AppEnvVarService()
logger = logging.getLogger("default")


class AppPortService(object):
    def check_port(self, service, container_port):
        port = port_repo.get_service_port_by_port(service.tenant_id, service.service_id, container_port)
        if port:
            return 400, u"端口{0}已存在".format(container_port)
        if not (1 <= container_port <= 65535):
            return 412, u"端口必须为1到65535的整数"
        return 200, "success"

    def check_port_alias(self, port_alias):
        if not port_alias:
            return 400, u"端口别名不能为空"
        if not re.match(r'^[A-Z][A-Z0-9_]*$', port_alias):
            return 400, u"端口别名不合法"
        return 200, "success"

    def is_open_outer_steam_port(self, tenant_id, service_id):
        """判断是否有对外打开的非http协议端口"""
        ports = port_repo.get_service_ports(tenant_id, service_id).filter(is_outer_service=True).exclude(
            protocol="http")
        if ports:
            return True
        return False

    def add_service_port(self, tenant, service, container_port=0, protocol='', port_alias='',
                         is_inner_service=False, is_outer_service=False):
        container_port = int(container_port)
        code, msg = self.check_port(service, container_port)
        if code != 200:
            return code, msg, None
        if not port_alias:
            port_alias = service.service_alias.upper()+str(container_port)
        code, msg = self.check_port_alias(port_alias)
        if code != 200:
            return code, msg, None
        env_prefix = port_alias.upper() if bool(port_alias) else service.service_key.upper()

        mapping_port = container_port
        if is_inner_service:
            if not port_alias:
                return 400, u"端口别名不能为空", None

            code, msg, data = env_var_service.add_service_env_var(tenant, service, container_port, u"连接地址",
                                                                  env_prefix + "_HOST", "127.0.0.1", False,
                                                                  scope="outer")
            if code != 200:
                return code, msg, None
            code, msg, data = env_var_service.add_service_env_var(tenant, service, container_port, u"端口",
                                                                  env_prefix + "_PORT", mapping_port, False,
                                                                  scope="outer")
            if code != 200:
                return code, msg, None
        if is_outer_service:
            if protocol != "http":
                if self.is_open_outer_steam_port(tenant.tenant_id, service.service_id):
                    return 412, u"非http协议端口只能对外开放一个"

        service_port = {"tenant_id": tenant.tenant_id, "service_id": service.service_id,
                        "container_port": container_port, "mapping_port": container_port,
                        "protocol": protocol, "port_alias": port_alias,
                        "is_inner_service": bool(is_inner_service),
                        "is_outer_service": bool(is_outer_service)}

        if service.create_status == "complete":
            region_api.add_service_port(service.service_region, tenant.tenant_name,
                                        service.service_alias,
                                        {"port": [service_port], "enterprise_id": tenant.enterprise_id})

        new_port = port_repo.add_service_port(**service_port)
        return 200, "success", new_port

    def get_service_ports(self, service):
        if service:
            return port_repo.get_service_ports(service.tenant_id, service.service_id)

    def get_service_port_by_port(self, service, port):
        if service:
            return port_repo.get_service_port_by_port(service.tenant_id, service.service_id, port)

    def get_port_variables(self, tenant, service, port_info):
        data = {"environment": []}
        if port_info.is_inner_service:
            envs = env_var_service.get_env_by_container_port(tenant, service, port_info.container_port)
            for env in envs:
                val = {"desc": env.name, "name": env.attr_name, "value": env.attr_value}
                data["environment"].append(val)
        if port_info.is_outer_service:
            service_region = service.service_region
            if port_info.protocol != 'http' and port_info.protocol != "https":
                cur_region = service_region.replace("-1", "")
                tcpdomain = region_services.get_region_tcpdomain(region_name=cur_region)
                # domain = "{0}.{1}.{2}.{3}".format(port_info.container_port, service.service_alias, tenant.tenant_name,
                #                                   tcpdomain)
                # if port_info.protocol == "tcp":
                #     domain = tcpdomain
                domain = tcpdomain
                data["outer_service"] = {
                    "domain": domain,
                    "port": port_info.mapping_port,
                }
                if port_info.lb_mapping_port != 0:
                    data["outer_service"]["port"] = port_info.lb_mapping_port
            elif port_info.protocol == 'http':
                httpdomain = region_services.get_region_httpdomain(service.service_region)
                domain = httpdomain
                port = 80
                if httpdomain and ":" in httpdomain:
                    info = httpdomain.split(":", 1)
                    if len(info) == 2:
                        port = int(info[1])
                        domain = str(info[0])
                data["outer_service"] = {
                    "domain": "{0}.{1}.{2}.{3}".format(port_info.container_port, service.service_alias,
                                                       tenant.tenant_name, domain),
                    "port": port
                }
        return data

    def delete_port_by_container_port(self, tenant, service, container_port):
        service_domain = domain_repo.get_service_domain_by_container_port(service.service_id, container_port)
        if service_domain:
            return 412, u"请先解绑该端口绑定的域名", None
        port_info = port_repo.get_service_port_by_port(tenant.tenant_id, service.service_id, container_port)
        if not port_info:
            return 404, u"端口{0}不存在".format(container_port), None
        if port_info.is_inner_service:
            return 409, u"请关闭对外服务", None
        if port_info.is_outer_service:
            return 409, u"请关闭外部服务", None
        if service.create_status == "complete":
            # 删除env
            env_var_service.delete_env_by_container_port(tenant, service, container_port)
            # 删除数据中心端口
            region_api.delete_service_port(service.service_region, tenant.tenant_name, service.service_alias,
                                           container_port, tenant.enterprise_id)

        # 删除端口
        port_repo.delete_serivce_port_by_port(tenant.tenant_id, service.service_id, container_port)
        # 删除端口绑定的域名
        domain_repo.delete_service_domain_by_port(service.service_id, container_port)
        return 200, u"删除成功", port_info

    def delete_service_port(self, tenant, service):
        port_repo.delete_service_port(tenant.tenant_id, service.service_id)

    def delete_region_port(self, tenant, service):
        if service.create_status == "complete":
            # 删除数据中心端口
            ports = self.get_service_ports(service)
            for port in ports:
                try:
                    region_api.delete_service_port(service.service_region, tenant.tenant_name, service.service_alias,
                                                   port.container_port, tenant.enterprise_id)
                except Exception as e:
                    logger.exception(e)

    def __check_params(self, action, protocol, port_alias, service_id):
        standard_actions = (
            "open_outer", "close_outer", "open_inner", "close_inner", "change_protocol", "change_port_alias")
        if not action:
            return 400, u"操作类型不能为空"
        if action not in standard_actions:
            return 400, u"不允许的操作类型"
        if action == "change_port_alias":
            if not port_alias:
                return 400, u"端口别名不能为空"
            if port_repo.get_service_port_by_alias(service_id, port_alias):
                return 400, u"别名已存在"
        if action == "change_protocol":
            if not protocol:
                return 400, u"端口协议不能为空"
        if port_alias:
            code, msg = self.check_port_alias(port_alias)
            if code != 200:
                return code, msg
        return 200, u"检测成功"

    def manage_port(self, tenant, service, container_port, action, protocol, port_alias):
        code, msg = self.__check_params(action, protocol, port_alias, service.service_id)
        if code != 200:
            return code, msg, None
        deal_port = port_repo.get_service_port_by_port(tenant.tenant_id, service.service_id, container_port)
        if action == "open_outer":
            code, msg = self.__open_outer(tenant, service, deal_port)
        elif action == "close_outer":
            code, msg = self.__close_outer(tenant, service, deal_port)
        elif action == "open_inner":
            code, msg = self.__open_inner(tenant, service, deal_port)
        elif action == "close_inner":
            code, msg = self.__close_inner(tenant, service, deal_port)
        elif action == "change_protocol":
            code, msg = self.__change_protocol(tenant, service, deal_port, protocol)
        elif action == "change_port_alias":
            code, msg = self.__change_port_alias(tenant, service, deal_port, port_alias)
        new_port = port_repo.get_service_port_by_port(tenant.tenant_id, service.service_id, container_port)
        if code != 200:
            return code, msg, None
        return 200, u"操作成功", new_port
    
    def __open_outer(self, tenant, service, deal_port):
        if deal_port.protocol != "http":
            if self.is_open_outer_steam_port(tenant.tenant_id, service.service_id):
                return 412, u"非http协议端口只能对外开放一个"
        deal_port.is_outer_service = True
        if service.create_status == "complete":
            body = region_api.manage_outer_port(service.service_region, tenant.tenant_name,
                                                service.service_alias,
                                                deal_port.container_port,
                                                {"operation": "open", "enterprise_id": tenant.enterprise_id})
            logger.debug("open outer port body {}".format(body))
            lb_mapping_port = body["bean"]["port"]

            deal_port.lb_mapping_port = lb_mapping_port
        deal_port.save()
        return 200, "success"

    def __close_outer(self, tenant, service, deal_port):
        deal_port.is_outer_service = False
        if service.create_status == "complete":
            region_api.manage_outer_port(service.service_region, tenant.tenant_name, service.service_alias,
                                         deal_port.container_port,
                                         {"operation": "close", "enterprise_id": tenant.enterprise_id})

        deal_port.save()
        return 200, "success"

    def __open_inner(self, tenant, service, deal_port):
        if not deal_port.port_alias:
            return 409, "请先为端口设置别名"
        deal_port.is_inner_service = True
        mapping_port = deal_port.container_port
        deal_port.mapping_port = mapping_port
        # 删除原有环境变量
        env_var_service.delete_env_by_container_port(tenant, service, deal_port.container_port)

        env_prefix = deal_port.port_alias.upper() if bool(deal_port.port_alias) else service.service_key.upper()
        # 添加环境变量
        code, msg, data = env_var_service.add_service_env_var(tenant, service, deal_port.container_port, u"连接地址",
                                                              env_prefix + "_HOST", "127.0.0.1", False,
                                                              scope="outer")
        if code != 200:
            return code, msg
        code, msg, data = env_var_service.add_service_env_var(tenant, service, deal_port.container_port, u"端口",
                                                              env_prefix + "_PORT", mapping_port, False,
                                                              scope="outer")
        if code != 200:
            return code, msg

        if service.create_status == "complete":
            body = region_api.manage_inner_port(service.service_region, tenant.tenant_name, service.service_alias,
                                                deal_port.container_port,
                                                {"operation": "open", "enterprise_id": tenant.enterprise_id})
            logger.debug("open inner port {0}".format(body))

        deal_port.save()
        return 200, "success"

    def __close_inner(self, tenant, service, deal_port):
        deal_port.is_inner_service = False
        if service.create_status == "complete":
            region_api.manage_inner_port(service.service_region, tenant.tenant_name, service.service_alias,
                                         deal_port.container_port,
                                         {"operation": "close", "enterprise_id": tenant.enterprise_id})
        deal_port.save()
        return 200, "success"

    def __change_protocol(self, tenant, service, deal_port, protocol):
        if deal_port.protocol == protocol:
            return 200, u"协议未发生变化"
        deal_port.protocol = protocol
        if protocol != "http":
            if deal_port.is_outer_service:
                return 400, u"请关闭外部访问"
            if self.is_open_outer_steam_port(tenant.tenant_id, service.service_id):
                return 412, u"非http协议端口只能对外开放一个"

        if service.create_status == "complete":
            body = {"container_port": deal_port.container_port, "is_inner_service": deal_port.is_inner_service,
                    "is_outer_service": deal_port.is_outer_service, "mapping_port": deal_port.mapping_port,
                    "port_alias": deal_port.port_alias, "protocol": protocol,
                    "tenant_id": tenant.tenant_id, "service_id": service.service_id}
            region_api.update_service_port(service.service_region, tenant.tenant_name, service.service_alias,
                                           {"port": [body], "enterprise_id": tenant.enterprise_id})
        deal_port.save()

        return 200, "success"

    def __change_port_alias(self, tenant, service, deal_port, new_port_alias):
        old_port_alias = deal_port.port_alias
        deal_port.port_alias = new_port_alias
        envs = env_var_service.get_env_by_container_port(tenant, service, deal_port.container_port)
        for env in envs:
            old_env_attr_name = env.attr_name
            new_attr_name = new_port_alias + env.attr_name.replace(old_port_alias, '')
            env.attr_name = new_attr_name
            if service.create_status == "complete":
                region_api.delete_service_env(service.service_region,
                                              tenant.tenant_name,
                                              service.service_alias,
                                              {"env_name": old_env_attr_name,
                                               "enterprise_id": tenant.enterprise_id})
                # step 2 添加新的
                add_env = {"container_port": env.container_port, "env_name": env.attr_name,
                           "env_value": env.attr_value, "is_change": env.is_change, "name": env.name,
                           "scope": env.scope, "enterprise_id": tenant.enterprise_id}
                region_api.add_service_env(service.service_region,
                                           tenant.tenant_name,
                                           service.service_alias,
                                           add_env)
            env.save()
        body = {"container_port": deal_port.container_port, "is_inner_service": deal_port.is_inner_service,
                "is_outer_service": deal_port.is_outer_service, "mapping_port": deal_port.mapping_port,
                "port_alias": new_port_alias, "protocol": deal_port.protocol,
                "tenant_id": tenant.tenant_id, "service_id": service.service_id}
        if service.create_status == "complete":
            region_api.update_service_port(service.service_region, tenant.tenant_name, service.service_alias,
                                           {"port": [body], "enterprise_id": tenant.enterprise_id})
        deal_port.save()
        return 200, "success"

    def get_access_info(self, tenant, service):
        access_type = ""
        data = {}
        service_ports = port_repo.get_service_ports(tenant.tenant_id, service.service_id)
        # ①是否有端口
        if not service_ports:
            access_type = ServicePortConstants.NO_PORT
            return access_type, data
        # 对内和对外都没打开的端口
        unopened_port = []
        # http 对外打开的端口
        http_outer_port = []
        # http 对内打开的端口
        http_inner_port = []
        # stream 对外打开的端口
        stream_outer_port = []
        # stream 对内打开的端口
        stream_inner_port = []
        for port in service_ports:
            if port.protocol == ServicePortConstants.HTTP:
                if port.is_outer_service:
                    http_outer_port.append(port)
                if port.is_inner_service:
                    http_inner_port.append(port)
            else:
                if port.is_outer_service:
                    stream_outer_port.append(port)
                if port.is_inner_service:
                    stream_inner_port.append(port)
            if not port.is_outer_service and (not port.is_inner_service):
                unopened_port.append(port)
        access_type, data = self.__handle_port_info(tenant, service, unopened_port, http_outer_port, http_inner_port,
                                                    stream_outer_port,
                                                    stream_inner_port)
        return access_type, data

    def __handle_port_info(self, tenant, service, unopened_port, http_outer_port, http_inner_port, stream_outer_port,
                           stream_inner_port):
        # 有http对外访问端口
        if http_outer_port:
            access_type = ServicePortConstants.HTTP_PORT
            port_info_list = []
            for p in http_outer_port:
                port_dict = p.to_dict()
                port_dict["access_urls"] = self.__get_port_access_url(tenant, service, p.container_port)
                port_info_list.append(port_dict)
            return access_type, port_info_list
        # 非http对外端口
        if stream_outer_port:
            access_type = ServicePortConstants.NOT_HTTP_OUTER
            port_info_list = []
            for p in stream_outer_port:
                port_and_url = self.__get_stream_outer_url(tenant, service, p)
                associate_info = self.get_port_associated_env(tenant, service, p.container_port)
                port_dict = p.to_dict()
                # associate_info[0:0] = port_and_url
                port_dict["access_urls"] = [port_and_url]
                port_dict["connect_info"] = associate_info
                port_info_list.append(port_dict)
            return access_type, port_info_list
        # 非http对内端口
        if stream_inner_port:
            access_type = ServicePortConstants.NOT_HTTP_INNER
            port_info_list = []
            for p in stream_inner_port:
                port_dict = p.to_dict()
                env_list = self.get_port_associated_env(tenant, service, p.container_port)
                port_dict["connect_info"] = env_list
                port_info_list.append(port_dict)
            return access_type, port_info_list
        if http_inner_port:
            http_inner_map = {}
            access_type = ServicePortConstants.HTTP_INNER
            for p in http_inner_port:
                env_list = self.get_port_associated_env(tenant, service, p.container_port)
                http_inner_map[p.container_port] = env_list
            return access_type, http_inner_map

        if unopened_port:
            access_type = ServicePortConstants.NO_PORT
            return access_type, {}

    def __get_stream_outer_url(self, tenant, service, port):
        cur_region = service.service_region.replace("-1", "")
        connect_url = "{0}.{1}.{2}-s1.goodrain.net".format(service.service_alias, tenant.tenant_name,
                                                           cur_region)

        tcp_domain_url = region_services.get_region_tcpdomain(service.service_region)
        connect_url = "{0}.{1}.{2}.{3}".format(port.container_port, service.service_alias, tenant.tenant_name, tcp_domain_url)
        if port.protocol != 'http' and port.protocol != "https":
            connect_url = tcp_domain_url
        if port.lb_mapping_port != 0:
            port_value = port.lb_mapping_port
        else:
            port_value = port.mapping_port

        url_map = {"name": "对外访问连接地址", "attr_name": "outer_url", "attr_value": connect_url}
        port_map = {"name": "对外访问连接端口", "attr_name": "outer_port", "attr_value": port_value}

        # return [url_map, port_map]
        return "{0}:{1}".format(url_map["attr_value"], port_map["attr_value"])

    def get_port_associated_env(self, tenant, service, port):

        env_var = env_var_service.get_env_by_container_port(tenant, service, port)
        env_list = [{"name": e.name, "attr_name": e.attr_name, "attr_value": e.attr_value} for e in env_var]
        attr_names = [e.attr_name for e in env_var]
        # 对外且不可改env
        both_outer_fix_env = env_var_service.get_self_define_env(service) \
            .filter(scope__in=("outer", "both"),
                    is_change=False).exclude(attr_name__in=attr_names)
        for e in both_outer_fix_env:
            env_list.append({"name": e.name, "attr_name": e.attr_name, "attr_value": e.attr_value})
        return env_list
   

    def __get_port_access_url(self, tenant, service, port):
        domain = region_services.get_region_httpdomain(service.service_region)
        suf_port = 80
        if domain:
            if ":" in domain:
                domain_split = domain.split(":")
                if len(domain_split) == 2:
                    suf_port = int(domain_split[1])
                    domain = str(domain_split[0])

            url = "http://{0}.{1}.{2}.{3}:{4}".format(port, service.service_alias, tenant.tenant_name,
                                                     domain,
                                                      suf_port)
        urls = [url]
        domains = domain_repo.get_service_domain_by_container_port(service.service_id, port)
        if domains:
            for d in domains:
                if d.protocol != "http":
                    urls.insert(0, "https://{0}".format(d.domain_name))
                else:
                    urls.insert(0, "http://{0}".format(d.domain_name))

        return urls

    def get_outer_port_opend_services_ids(self, tenant, service_ids):
        service_ports = port_repo.get_http_opend_services_ports(tenant.tenant_id, service_ids)
        ids = [p.service_id for p in service_ports]
        return list(set(ids))
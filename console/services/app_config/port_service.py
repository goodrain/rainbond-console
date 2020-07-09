# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
import datetime
import logging
import re
import validators

from django.db import transaction

from console.exception.main import AbortRequest
from console.exception.main import CheckThirdpartEndpointFailed
from console.exception.main import ServiceHandleException

from console.constants import ServicePortConstants
from console.repositories.app import service_repo
from console.repositories.app_config import service_endpoints_repo
from console.repositories.app_config import domain_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import tcp_domain
from console.repositories.probe_repo import probe_repo
from console.repositories.region_repo import region_repo
from console.services.app_config.env_service import AppEnvVarService
from console.services.app_config.probe_service import ProbeService
from console.services.region_services import region_services
from www.apiclient.regionapi import RegionInvokeApi
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.utils.crypt import make_uuid

pros = ProbeService()
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
        logger.debug('-------------------11111111111111111111111----------')
        if not port_alias:
            return 400, u"端口别名不能为空"
        if not re.match(r'^[A-Z][A-Z0-9_]*$', port_alias):
            return 400, u"端口别名不合法"
        return 200, "success"

    def add_service_port(self,
                         tenant,
                         service,
                         container_port=0,
                         protocol='',
                         port_alias='',
                         is_inner_service=False,
                         is_outer_service=False):
        # 第三方组件暂时只允许添加一个端口
        tenant_service_ports = self.get_service_ports(service)
        logger.debug('======tenant_service_ports======>{0}'.format(type(tenant_service_ports)))
        if tenant_service_ports and service.service_source == "third_party":
            return 400, u"第三方组件只支持配置一个端口", None

        container_port = int(container_port)
        code, msg = self.check_port(service, container_port)
        if code != 200:
            return code, msg, None
        if not port_alias:
            port_alias = service.service_alias.upper() + str(container_port)
        code, msg = self.check_port_alias(port_alias)
        if code != 200:
            return code, msg, None
        env_prefix = port_alias.upper() if bool(port_alias) else service.service_key.upper()

        mapping_port = container_port
        if is_inner_service:
            if not port_alias:
                return 400, u"端口别名不能为空", None

            code, msg, data = env_var_service.add_service_env_var(
                tenant, service, container_port, u"连接地址", env_prefix + "_HOST", "127.0.0.1", False, scope="outer")
            if code != 200:
                return code, msg, None
            code, msg, data = env_var_service.add_service_env_var(
                tenant, service, container_port, u"端口", env_prefix + "_PORT", mapping_port, False, scope="outer")
            if code != 200:
                return code, msg, None

        service_port = {
            "tenant_id": tenant.tenant_id,
            "service_id": service.service_id,
            "container_port": container_port,
            "mapping_port": container_port,
            "protocol": protocol,
            "port_alias": port_alias,
            "is_inner_service": bool(is_inner_service),
            "is_outer_service": bool(is_outer_service)
        }

        if service.create_status == "complete":
            region_api.add_service_port(service.service_region, tenant.tenant_name, service.service_alias, {
                "port": [service_port],
                "enterprise_id": tenant.enterprise_id
            })

        new_port = port_repo.add_service_port(**service_port)
        # 第三方组件在添加端口是添加一条默认的健康检测数据
        if service.service_source == "third_party":
            tenant_service_ports = self.get_service_ports(service)
            port_list = []
            for tenant_service_port in tenant_service_ports:
                port_list.append(tenant_service_port.container_port)
            if len(port_list) <= 1:
                probe = probe_repo.get_probe(service.service_id)
                if not probe:
                    params = {
                        "http_header": "",
                        "initial_delay_second": 4,
                        "is_used": True,
                        "mode": "ignore",
                        "path": "",
                        "period_second": 3,
                        "port": int(new_port.container_port),
                        "scheme": "tcp",
                        "success_threshold": 1,
                        "timeout_second": 5
                    }
                    code, msg, probe = pros.add_service_probe(tenant, service, params)
                    if code != 200:
                        logger.debug('------111----->{0}'.format(msg))
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
                    "domain": "{0}.{1}.{2}.{3}".format(port_info.container_port, service.service_alias, tenant.tenant_name,
                                                       domain),
                    "port": port
                }
        return data

    @transaction.atomic
    def delete_port_by_container_port(self, tenant, service, container_port):
        service_domain = domain_repo.get_service_domain_by_container_port(service.service_id, container_port)

        if len(service_domain) > 1 or len(service_domain) == 1 and service_domain[0].type != 0:
            return 412, u"该端口有自定义域名，请先解绑域名", None

        port_info = port_repo.get_service_port_by_port(tenant.tenant_id, service.service_id, container_port)
        if not port_info:
            return 404, u"端口{0}不存在".format(container_port), None
        if port_info.is_inner_service:
            return 409, u"请关闭对内服务", None
        if port_info.is_outer_service:
            return 409, u"请关闭对外服务", None
        if service.create_status == "complete":
            # 删除数据中心端口
            region_api.delete_service_port(service.service_region, tenant.tenant_name, service.service_alias, container_port,
                                           tenant.enterprise_id)

        # 删除端口时禁用相关组件
        self.disable_service_when_delete_port(tenant, service, container_port)

        # 删除env
        env_var_service.delete_env_by_container_port(tenant, service, container_port)
        # 删除端口
        port_repo.delete_serivce_port_by_port(tenant.tenant_id, service.service_id, container_port)
        # 删除端口绑定的域名
        domain_repo.delete_service_domain_by_port(service.service_id, container_port)
        return 200, u"删除成功", port_info

    def disable_service_when_delete_port(self, tenant, service, container_port):
        """删除端口时禁用相关组件"""
        # 禁用健康检测
        from console.services.app_config import probe_service
        probe = probe_repo.get_service_probe(service.service_id).filter(is_used=True).first()
        if probe and container_port == probe.port:
            probe.is_used = False
            try:
                probe_service.update_service_probea(tenant=tenant, service=service, data=probe.to_dict())
            except RegionApiBaseHttpClient.CallApiError as e:
                logger.exception(e)
                if e.status != 404:
                    raise AbortRequest(msg=e.message, status_code=e.status)

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
        standard_actions = ("open_outer", "only_open_outer", "close_outer", "open_inner", "close_inner", "change_protocol",
                            "change_port_alias")
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

    def manage_port(self, tenant, service, region_name, container_port, action, protocol, port_alias):
        if port_alias:
            port_alias = str(port_alias).strip()
        region = region_repo.get_region_by_region_name(region_name)
        code, msg = self.__check_params(action, protocol, port_alias, service.service_id)
        if code != 200:
            return code, msg, None
        deal_port = port_repo.get_service_port_by_port(tenant.tenant_id, service.service_id, container_port)
        if action == "open_outer":
            code, msg = self.__open_outer(tenant, service, region, deal_port)
        elif action == "only_open_outer":
            code, msg = self.__only_open_outer(tenant, service, region, deal_port)
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

    def __open_outer(self, tenant, service, region, deal_port):
        if deal_port.protocol == "http":
            service_domains = domain_repo.get_service_domain_by_container_port(service.service_id, deal_port.container_port)
            # 在domain表中保存数据
            if service_domains:
                for service_domain in service_domains:
                    service_domain.is_outer_service = True
                    service_domain.save()
            else:
                # 在service_domain表中保存数据
                service_id = service.service_id
                service_name = service.service_alias
                container_port = deal_port.container_port
                domain_name = str(container_port) + "." + str(service_name) + "." + str(tenant.tenant_name) + "." + str(
                    region.httpdomain)
                create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                protocol = "http"
                http_rule_id = make_uuid(domain_name)
                tenant_id = tenant.tenant_id
                service_alias = service.service_cname
                region_id = region.region_id
                domain_repo.create_service_domains(service_id, service_name, domain_name, create_time, container_port, protocol,
                                                   http_rule_id, tenant_id, service_alias, region_id)
                # 给数据中心发请求添加默认域名
                data = dict()
                data["domain"] = domain_name
                data["service_id"] = service.service_id
                data["tenant_id"] = tenant.tenant_id
                data["tenant_name"] = tenant.tenant_name
                data["protocol"] = protocol
                data["container_port"] = int(container_port)
                data["http_rule_id"] = http_rule_id
                try:
                    region_api.bind_http_domain(service.service_region, tenant.tenant_name, data)
                except Exception as e:
                    logger.exception(e)
                    domain_repo.delete_http_domains(http_rule_id)
                    return 412, u"数据中心添加策略失败"

        else:
            service_tcp_domains = tcp_domain.get_service_tcp_domains_by_service_id_and_port(
                service.service_id, deal_port.container_port)
            if service_tcp_domains:
                for service_tcp_domain in service_tcp_domains:
                    # 改变tcpdomain表中状态
                    service_tcp_domain.is_outer_service = True
                    service_tcp_domain.save()
            else:
                # ip+port
                # 在service_tcp_domain表中保存数据
                res, data = region_api.get_port(region.region_name, tenant.tenant_name)
                if int(res.status) != 200:
                    return 400, u"请求数据中心异常"
                end_point = "0.0.0.0:{0}".format(data["bean"])
                service_id = service.service_id
                service_name = service.service_alias
                create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                container_port = deal_port.container_port
                protocol = deal_port.protocol
                service_alias = service.service_cname
                tcp_rule_id = make_uuid(end_point)
                tenant_id = tenant.tenant_id
                region_id = region.region_id
                tcp_domain.create_service_tcp_domains(service_id, service_name, end_point, create_time, container_port,
                                                      protocol, service_alias, tcp_rule_id, tenant_id, region_id)
                port = end_point.split(":")[1]
                data = dict()
                data["service_id"] = service.service_id
                data["container_port"] = int(container_port)
                data["ip"] = "0.0.0.0"
                data["port"] = int(port)
                data["tcp_rule_id"] = tcp_rule_id
                try:
                    # 给数据中心传送数据添加策略
                    region_api.bindTcpDomain(service.service_region, tenant.tenant_name, data)
                except Exception as e:
                    logger.exception(e)
                    tcp_domain.delete_tcp_domain(tcp_rule_id)
                    return 412, u"数据中心添加策略失败"

        deal_port.is_outer_service = True
        if service.create_status == "complete":
            body = region_api.manage_outer_port(service.service_region, tenant.tenant_name, service.service_alias,
                                                deal_port.container_port, {
                                                    "operation": "open",
                                                    "enterprise_id": tenant.enterprise_id
                                                })
            logger.debug("open outer port body {}".format(body))
            lb_mapping_port = body["bean"]["port"]

            deal_port.lb_mapping_port = lb_mapping_port
        deal_port.save()
        # component port change, will change entrance network governance plugin configuration
        if service.create_status == "complete":
            from console.services.plugin import app_plugin_service
            app_plugin_service.update_config_if_have_entrance_plugin(tenant, service)
        return 200, "success"

    def __only_open_outer(self, tenant, service, region, deal_port):
        deal_port.is_outer_service = True
        if service.create_status == "complete":
            body = region_api.manage_outer_port(service.service_region, tenant.tenant_name, service.service_alias,
                                                deal_port.container_port, {
                                                    "operation": "open",
                                                    "enterprise_id": tenant.enterprise_id
                                                })
            logger.debug("open outer port body {}".format(body))
            lb_mapping_port = body["bean"]["port"]

            deal_port.lb_mapping_port = lb_mapping_port
        deal_port.save()

        service_domains = domain_repo.get_service_domain_by_container_port(service.service_id, deal_port.container_port)
        # 改变httpdomain表中端口状态
        if service_domains:
            for service_domain in service_domains:
                service_domain.is_outer_service = True
                service_domain.save()

        service_tcp_domains = tcp_domain.get_service_tcp_domains_by_service_id_and_port(service.service_id,
                                                                                        deal_port.container_port)
        if service_tcp_domains:
            for service_tcp_domain in service_tcp_domains:
                # 改变tcpdomain表中状态
                service_tcp_domain.is_outer_service = True
                service_tcp_domain.save()

        return 200, "success"

    def close_thirdpart_outer(self, tenant, service, deal_port):
        try:
            self.__close_outer(tenant, service, deal_port)
        except region_api.CallApiError as e:
            logger.exception(e)
            raise ServiceHandleException(msg="close outer port failed", msg_show="关闭对外服务失败")

    def __close_outer(self, tenant, service, deal_port):
        deal_port.is_outer_service = False
        if service.create_status == "complete":
            region_api.manage_outer_port(service.service_region, tenant.tenant_name, service.service_alias,
                                         deal_port.container_port, {
                                             "operation": "close",
                                             "enterprise_id": tenant.enterprise_id
                                         })

        deal_port.save()
        # 改变httpdomain表中端口状态
        if deal_port.protocol == "http":
            service_domains = domain_repo.get_service_domain_by_container_port(service.service_id, deal_port.container_port)
            if service_domains:
                for service_domain in service_domains:
                    service_domain.is_outer_service = False
                    service_domain.save()
        else:
            service_tcp_domains = tcp_domain.get_service_tcp_domains_by_service_id_and_port(
                service.service_id, deal_port.container_port)
            # 改变tcpdomain表中状态
            if service_tcp_domains:
                for service_tcp_domain in service_tcp_domains:
                    service_tcp_domain.is_outer_service = False
                    service_tcp_domain.save()
        # component port change, will change entrance network governance plugin configuration
        if service.create_status == "complete":
            from console.services.plugin import app_plugin_service
            app_plugin_service.update_config_if_have_entrance_plugin(tenant, service)
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
        code, msg, data = env_var_service.add_service_env_var(
            tenant, service, deal_port.container_port, u"连接地址", env_prefix + "_HOST", "127.0.0.1", False, scope="outer")
        if code != 200:
            return code, msg
        code, msg, data = env_var_service.add_service_env_var(
            tenant, service, deal_port.container_port, u"端口", env_prefix + "_PORT", mapping_port, False, scope="outer")
        if code != 200:
            return code, msg

        if service.create_status == "complete":
            body = region_api.manage_inner_port(service.service_region, tenant.tenant_name, service.service_alias,
                                                deal_port.container_port, {
                                                    "operation": "open",
                                                    "enterprise_id": tenant.enterprise_id
                                                })
            logger.debug("open inner port {0}".format(body))

        deal_port.save()
        # component port change, will change entrance network governance plugin configuration
        if service.create_status == "complete":
            from console.services.plugin import app_plugin_service
            app_plugin_service.update_config_if_have_entrance_plugin(tenant, service)
        return 200, "success"

    def __close_inner(self, tenant, service, deal_port):
        deal_port.is_inner_service = False
        if service.create_status == "complete":
            region_api.manage_inner_port(service.service_region, tenant.tenant_name, service.service_alias,
                                         deal_port.container_port, {
                                             "operation": "close",
                                             "enterprise_id": tenant.enterprise_id
                                         })
        deal_port.save()
        # component port change, will change entrance network governance plugin configuration
        if service.create_status == "complete":
            from console.services.plugin import app_plugin_service
            app_plugin_service.update_config_if_have_entrance_plugin(tenant, service)
        return 200, "success"

    def __change_protocol(self, tenant, service, deal_port, protocol):
        if deal_port.protocol == protocol:
            return 200, u"协议未发生变化"
        deal_port.protocol = protocol
        if protocol != "http":
            if deal_port.is_outer_service:
                return 400, u"请关闭外部访问"

        if service.create_status == "complete":
            body = {
                "container_port": deal_port.container_port,
                "is_inner_service": deal_port.is_inner_service,
                "is_outer_service": deal_port.is_outer_service,
                "mapping_port": deal_port.mapping_port,
                "port_alias": deal_port.port_alias,
                "protocol": protocol,
                "tenant_id": tenant.tenant_id,
                "service_id": service.service_id
            }
            region_api.update_service_port(service.service_region, tenant.tenant_name, service.service_alias, {
                "port": [body],
                "enterprise_id": tenant.enterprise_id
            })
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
                region_api.delete_service_env(service.service_region, tenant.tenant_name, service.service_alias, {
                    "env_name": old_env_attr_name,
                    "enterprise_id": tenant.enterprise_id
                })
                # step 2 添加新的
                add_env = {
                    "container_port": env.container_port,
                    "env_name": env.attr_name,
                    "env_value": env.attr_value,
                    "is_change": env.is_change,
                    "name": env.name,
                    "scope": env.scope,
                    "enterprise_id": tenant.enterprise_id
                }
                region_api.add_service_env(service.service_region, tenant.tenant_name, service.service_alias, add_env)
            env.save()
        body = {
            "container_port": deal_port.container_port,
            "is_inner_service": deal_port.is_inner_service,
            "is_outer_service": deal_port.is_outer_service,
            "mapping_port": deal_port.mapping_port,
            "port_alias": new_port_alias,
            "protocol": deal_port.protocol,
            "tenant_id": tenant.tenant_id,
            "service_id": service.service_id
        }
        if service.create_status == "complete":
            region_api.update_service_port(service.service_region, tenant.tenant_name, service.service_alias, {
                "port": [body],
                "enterprise_id": tenant.enterprise_id
            })
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
                                                    stream_outer_port, stream_inner_port)
        return access_type, data

    def __handle_port_info(self, tenant, service, unopened_port, http_outer_port, http_inner_port, stream_outer_port,
                           stream_inner_port):
        # 有http对外访问端口
        if http_outer_port:
            access_type = ServicePortConstants.HTTP_PORT
            port_info_list = []
            for p in http_outer_port:
                port_dict = p.to_dict()
                access_urls = self.__get_port_access_url(tenant, service, p.container_port)
                if not access_urls:
                    port_and_url = self.__get_stream_outer_url(tenant, service, p)
                    if port_and_url:
                        access_type = ServicePortConstants.NOT_HTTP_OUTER
                        access_urls = [port_and_url]
                port_dict["access_urls"] = access_urls
                port_dict["service_cname"] = service.service_cname
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
                port_dict["service_cname"] = service.service_cname
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
                port_dict["service_cname"] = service.service_cname
                port_info_list.append(port_dict)
            return access_type, port_info_list
        if http_inner_port:
            # http_inner_map = {}

            access_type = ServicePortConstants.HTTP_INNER
            port_info_list = []
            for p in http_inner_port:
                port_dict = p.to_dict()
                env_list = self.get_port_associated_env(tenant, service, p.container_port)
                port_dict["connect_info"] = env_list
                port_dict["service_cname"] = service.service_cname
                port_info_list.append(port_dict)
            return access_type, port_info_list

        if unopened_port:
            access_type = ServicePortConstants.NO_PORT
            return access_type, {}

    def __get_stream_outer_url(self, tenant, service, port):
        region = region_repo.get_region_by_region_name(service.service_region)
        if region:
            service_tcp_domain = tcp_domain.get_service_tcpdomain(tenant.tenant_id, region.region_id, service.service_id,
                                                                  port.container_port)

            if service_tcp_domain:
                return service_tcp_domain.end_point
            else:
                return None

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
        urls = []
        domains = domain_repo.get_service_domain_by_container_port(service.service_id, port)
        if domains:
            for d in domains:
                domain_path = d.domain_path if d.domain_path else "/"
                if d.protocol != "http":
                    urls.insert(0, "https://{0}{1}".format(d.domain_name, domain_path))
                else:
                    urls.insert(0, "http://{0}{1}".format(d.domain_name, domain_path))

        return urls

    def get_team_region_usable_tcp_ports(self, tenant, service):
        services = service_repo.get_service_by_region_and_tenant(service.service_region, tenant.tenant_id)
        current_service_tcp_ports = port_repo.get_service_ports(
            tenant.tenant_id, service.service_id).filter(is_outer_service=True).exclude(protocol__in=("http", "https"))
        lb_mapping_ports = [p.lb_mapping_port for p in current_service_tcp_ports]
        service_ids = [s.service_id for s in services]
        res = port_repo.get_tcp_outer_opend_ports(service_ids).exclude(lb_mapping_port__in=lb_mapping_ports)
        return res

    def check_domain_thirdpart(self, tenant, service):
        from console.utils.validation import validate_endpoints_info
        res, body = region_api.get_third_party_service_pods(service.service_region, tenant.tenant_name,
                                                            service.service_alias)
        if res.status != 200:
            return "region error", "数据中心查询失败", 412
        endpoint_list = body["list"]
        endpoint_info = [endpoint.address for endpoint in endpoint_list]
        validate_endpoints_info(endpoint_info)
        return "", "", 200


class EndpointService(object):
    @transaction.atomic()
    def add_endpoint(self, tenant, service, address, is_online):

        try:
            _, body = region_api.get_third_party_service_pods(service.service_region, tenant.tenant_name, service.service_alias)
        except region_api.CallApiError as e:
            logger.exception(e)
            raise CheckThirdpartEndpointFailed()
        if not body:
            raise CheckThirdpartEndpointFailed()

        endpoint_list = body.get("list", [])
        endpoints = [endpoint.address for endpoint in endpoint_list]
        endpoints.append(address)
        is_domain = self.check_endpoints(endpoints)

        # close outer port
        if is_domain:
            from console.services.app_config import port_service
            ports = port_service.get_service_ports(service)
            if ports:
                logger.debug("close third part port: {0}".format(ports[0].container_port))
                port_service.close_thirdpart_outer(tenant, service, ports[0])

        data = {"address": address, "is_online": is_online}

        try:
            res, _ = region_api.post_third_party_service_endpoints(service.service_region, tenant.tenant_name,
                                                                   service.service_alias, data)
            # 保存endpoints数据
            service_endpoints_repo.update_or_create_endpoints(tenant, service, endpoints)
        except region_api.CallApiError as e:
            logger.exception(e)
            raise CheckThirdpartEndpointFailed(msg="add endpoint failed", msg_show="数据中心添加实例地址失败")
        if res and res.status != 200:
            raise CheckThirdpartEndpointFailed(msg="add endpoint failed", msg_show="数据中心添加实例地址失败")

    def check_endpoints(self, endpoints):
        is_domain = False
        for endpoint in endpoints:
            if "https://" in endpoint:
                endpoint = endpoint.partition("https://")[2]
            if "http://" in endpoint:
                endpoint = endpoint.partition("http://")[2]
            if ":" in endpoint:
                endpoint = endpoint.rpartition(":")[0]
            is_domain = self.check_endpoint(endpoint)
            if is_domain and len(endpoints) > 1:
                raise CheckThirdpartEndpointFailed(msg="do not support multi domain endpoint", msg_show="不允许添加多个域名实例地址")
        return is_domain

    # check endpoint do not start with protocol and do not end with port, just hostname or ip
    def check_endpoint(self, endpoint):
        is_ipv4 = validators.ipv4(endpoint)
        is_ipv6 = validators.ipv6(endpoint)
        if is_ipv4 or is_ipv6:
            return False
        if validators.domain(endpoint):
            return True
        raise CheckThirdpartEndpointFailed(msg="invalid endpoint")

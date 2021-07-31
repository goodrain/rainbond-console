# -*- coding: utf8 -*-
from datetime import datetime
import logging
import json

from .component import Component
# model
from www.models.main import ServiceDomain
from www.models.main import GatewayCustomConfiguration
# enum
from console.constants import DomainType
# www
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


def get_component_template(component: Component, app_template):
    templates = app_template.get("apps", [])
    for tmpl in templates:
        if is_same_component(component, tmpl):
            return tmpl
    return None


def is_same_component(component: Component, tmpl):
    # 1. service_key
    if component.component.service_key == tmpl.get("service_key"):
        return True
    # 2. service_share_uuid
    component_key = component.component_source.service_share_uuid
    tmpl_key = tmpl.get("service_share_uuid")
    if component_key == tmpl_key:
        return True
    # 3. service_share_uuid = xxx + service_id
    component_key = component_key.split("+")
    if len(component_key) != 2:
        return False
    tmpl_key = tmpl_key.split("+")
    if len(tmpl_key) != 2:
        return False
    return component_key[1] == tmpl_key[1]


def parse_ingress_http_routes(tenant, region, component, ingress_http_routes, ports):
    service_domains = []
    configs = []
    for ingress in ingress_http_routes:
        port = ports.get(ingress["port"])
        if not port:
            logger.warning("component id: {}; port not found for ingress {}".format(component.component_id,
                                                                                    ingress["ingress_key"]))
            continue

        service_domain = ServiceDomain(
            http_rule_id=make_uuid(),
            ingress_key=ingress["ingress_key"],
            tenant_id=tenant.tenant_id,
            region_id=region.region_id,
            service_id=component.component_id,
            service_name=component.service_alias,
            create_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            container_port=ingress["port"],
            protocol="http",
            domain_type=DomainType.WWW,
            service_alias=component.service_cname,
            domain_path=ingress["location"],
            domain_cookie=_domain_cookie_or_header(ingress["cookies"]),
            domain_heander=_domain_cookie_or_header(ingress["headers"]),
            type=0 if ingress["default_domain"] else 1,
            the_weight=100,
            is_outer_service=port.is_outer_service,
            auto_ssl=False,
            rule_extensions=_ingress_load_balancing(ingress["load_balancing"]),
        )
        if service_domain.type == 0:
            service_domain.domain_name = str(port.container_port) + "." + str(component.service_alias) + "." + str(
                tenant.tenant_name) + "." + str(region.httpdomain)
        else:
            service_domain.domain_name = make_uuid()[:6] + str(port.container_port) + "." + str(
                component.service_alias) + "." + str(tenant.tenant_name) + "." + str(region.httpdomain)
        service_domain.is_senior = len(service_domain.domain_cookie) > 0 or len(service_domain.domain_heander) > 0
        service_domains.append(service_domain)

        # config
        config = _ingress_config(service_domain.http_rule_id, ingress)
        configs.append(config)
    return service_domains, configs


def _domain_cookie_or_header(items):
    res = []
    for key in items:
        res.append(key + "=" + items[key])
    return ";".join(res)


def _ingress_load_balancing(lb):
    if lb == "cookie-session-affinity":
        return "lb-type:cookie-session-affinity"
    # round-robin is the default value of load balancing
    return "lb-type:round-robin"


def _ingress_config(rule_id, ingress):
    return GatewayCustomConfiguration(
        rule_id=rule_id,
        value=json.dumps({
            "proxy_buffer_numbers": ingress["proxy_buffer_numbers"] if ingress["proxy_buffer_numbers"] else 4,
            "proxy_buffer_size": ingress["proxy_buffer_size"] if ingress["proxy_buffer_size"] else 4,
            "proxy_body_size": ingress["request_body_size_limit"] if ingress["request_body_size_limit"] else 0,
            "proxy_connect_timeout": ingress["connection_timeout"] if ingress["connection_timeout"] else 5,
            "proxy_read_timeout": ingress["response_timeout"] if ingress["response_timeout"] else 60,
            "proxy_send_timeout": ingress["request_timeout"] if ingress["request_timeout"] else 60,
            "proxy_buffering": "off",
            "WebSocket": ingress["websocket"] if ingress["websocket"] else False,
            "set_headers": ingress["set_headers"],
        }))

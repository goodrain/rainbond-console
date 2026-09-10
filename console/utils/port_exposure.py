"""Shared interpretation of component capabilities and actual gateway mappings."""
from urllib.parse import urlencode


COMPONENT_PROTOCOLS = ("http", "https", "grpc", "mysql", "tcp", "udp", "tcp+udp")


def transports(protocol):
    protocol = (protocol or "tcp").lower()
    if protocol == "tcp+udp":
        return {"tcp", "udp"}
    if protocol == "udp":
        return {"udp"}
    if protocol in COMPONENT_PROTOCOLS:
        return {"tcp"}
    return set()


def supports(component, requested):
    wanted = transports(requested)
    return bool(wanted) and wanted.issubset(transports(component))


def get_bindings(api, region, tenant, service, port, app_id=None):
    """Read both rule kinds. Never change saved flags as a side effect of reading."""
    query = urlencode({"service_alias": service.service_alias, "port": port.container_port})
    base = "/api-gateway/v1/{}/routes/".format(tenant.tenant_name)
    http = api.api_gateway_get_proxy(region, tenant.tenant_id, base + "http/domains?" + query, app_id)
    stream = api.api_gateway_get_proxy(region, tenant.tenant_id, base + "tcp/domains?" + query + "&details=true", app_id)
    if not isinstance(http, dict) or not isinstance(http.get("list"), list):
        raise ValueError("HTTP gateway bindings could not be read")
    if not isinstance(stream, dict) or not isinstance(stream.get("list"), list):
        raise ValueError("TCP/UDP gateway bindings could not be read")
    domains = [{"protocol": "http", "domain_type": "www", "ID": -1, "domain_name": host,
                "container_port": port.container_port} for host in http["list"]]
    mappings = []
    for rule in stream["list"]:
        if not isinstance(rule, dict) or not rule.get("service_name") or not rule.get("nodePort"):
            raise ValueError("TCP/UDP gateway returned an incomplete mapping")
        protocols = rule.get("protocols") or [rule.get("protocol", "TCP")]
        protocols = {p.lower() for p in protocols}
        protocol = "tcp+udp" if {"tcp", "udp"}.issubset(protocols) else next(iter(protocols))
        endpoint = "0.0.0.0:{}".format(rule["nodePort"])
        mappings.append(dict(rule, protocol=protocol, domain_name=endpoint, end_point=endpoint,
                             container_port=port.container_port, service_id=service.service_id,
                             service_alias=service.service_alias, is_outer_service=True))
    return {"bind_domains": domains, "bind_tcp_domains": mappings, "is_outer_service": bool(domains or mappings)}

from console.repositories.group import group_repo
from console.repositories.k8s_resources import k8s_resources_repo
from console.repositories.region_app import region_app_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()


class GatewayAPI(object):
    def list_gateways(self, eid, region_name):
        res, body = region_api.list_gateways(eid, region_name)
        return body

    def list_http_routes(self, region, tenant_name, namespace, app_id):
        region_app_id = ""
        if app_id:
            region_app_id = region_app_repo.get_region_app_id(region, app_id)
        body = region_api.list_gateway_http_route(
            region,
            tenant_name,
            namespace,
            region_app_id,
        )
        return body["list"]

    def create_gateway_tls(self, region, tenant_name, namespace, name, private_key, certificate):
        body = dict()
        body["namespace"] = namespace
        body["name"] = name
        body["private_key"] = private_key
        body["certificate"] = certificate
        body = region_api.create_gateway_certificate(region, tenant_name, body)
        return body["bean"]

    def update_gateway_tls(self, region, tenant_name, namespace, name, private_key, certificate):
        body = dict()
        body["namespace"] = namespace
        body["name"] = name
        body["private_key"] = private_key
        body["certificate"] = certificate
        body = region_api.update_gateway_certificate(region, tenant_name, body)
        return body["bean"]

    def delete_gateway_tls(self, region, tenant_name, namespace, name):
        body = region_api.delete_gateway_certificate(region, tenant_name, namespace, name)
        return body["bean"]

    def get_http_route(self, region, tenant_name, namespace, name):
        body = region_api.get_gateway_http_route(region, tenant_name, namespace, name)
        region_app_id = body["bean"].get("app_id")
        app_id = region_app_repo.get_app_id(region, region_app_id)
        body["bean"]["app_id"] = app_id
        return body["bean"]

    def add_http_route(self, region, tenant_name, app_id, namespace, gateway_name, gateway_namespace, hosts, rules,
                       section_name):
        body = dict()
        app = group_repo.get_group_by_id(app_id)
        region_app_id = region_app_repo.get_region_app_id(region, app_id)
        body["name"] = app.k8s_app + "-" + make_uuid()[:6]
        body["app_id"] = region_app_id
        body["namespace"] = namespace
        body["section_name"] = section_name
        body["gateway_name"] = gateway_name
        body["gateway_namespace"] = gateway_namespace
        body["hosts"] = hosts
        body["rules"] = rules
        body = region_api.add_gateway_http_route(region, tenant_name, body)
        if body["bean"]:
            data = {
                "app_id": app_id,
                "name": body["bean"].get("name"),
                "kind": body["bean"].get("kind", "HTTPRoute"),
                "content": body["bean"].get("content"),
                "state": 1,
            }
            k8s_resources_repo.create(**data)
        return body["bean"]

    def update_http_route(self, region, tenant_name, name, app_id, namespace, gateway_name, gateway_namespace, hosts, rules,
                          section_name):
        region_app_id = region_app_repo.get_region_app_id(region, app_id)
        body = dict()
        body["name"] = name
        body["app_id"] = region_app_id
        body["namespace"] = namespace
        body["section_name"] = section_name
        body["gateway_name"] = gateway_name
        body["gateway_namespace"] = gateway_namespace
        body["hosts"] = hosts
        body["rules"] = rules
        body = region_api.update_gateway_http_route(region, tenant_name, body)
        return body["bean"]

    def delete_http_route(self, region, tenant_name, namespace, name, region_app_id):
        body = region_api.delete_gateway_http_route(region, tenant_name, namespace, name, region_app_id)
        return body["bean"]


gateway_api = GatewayAPI()

from typing import Any, Optional

from console.repositories.group import group_repo
from console.repositories.k8s_resources import k8s_resources_repo
from console.repositories.region_app import region_app_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()


class GatewayAPI(object):
    def list_gateways(self, eid: str, region_name: str) -> Optional[Any]:
        res, body = region_api.list_gateways(eid, region_name)
        return body

    def list_http_routes(self, region: str, tenant_name: str, namespace: str, app_id: Any) -> Any:
        region_app_id = ""
        if app_id:
            region_app_id = region_app_repo.get_region_app_id(region, app_id)
        body = region_api.list_gateway_http_route(
            region,
            tenant_name,
            namespace,
            region_app_id,
        )
        return body["list"]  # type: ignore[index]  # NOTE: caller guarantees body is not None

    def create_gateway_tls(self, region: str, tenant_name: str, namespace: str, name: str, private_key: str,
                           certificate: str) -> Any:
        body = dict()
        body["namespace"] = namespace
        body["name"] = name
        body["private_key"] = private_key
        body["certificate"] = certificate
        body = region_api.create_gateway_certificate(region, tenant_name, body)
        return body["bean"]  # type: ignore[index]  # NOTE: caller guarantees body is not None

    def update_gateway_tls(self, region: str, tenant_name: str, namespace: str, name: str, private_key: str,
                           certificate: str) -> Any:
        body = dict()
        body["namespace"] = namespace
        body["name"] = name
        body["private_key"] = private_key
        body["certificate"] = certificate
        body = region_api.update_gateway_certificate(region, tenant_name, body)
        return body["bean"]  # type: ignore[index]  # NOTE: caller guarantees body is not None

    def delete_gateway_tls(self, region: str, tenant_name: str, namespace: str, name: str) -> Any:
        body = region_api.delete_gateway_certificate(region, tenant_name, namespace, name)
        return body["bean"]  # type: ignore[index]  # NOTE: caller guarantees body is not None

    def get_http_route(self, region: str, tenant_name: str, namespace: str, name: str) -> Any:
        body = region_api.get_gateway_http_route(region, tenant_name, namespace, name)
        region_app_id = body["bean"].get("app_id")  # type: ignore[index]  # NOTE: caller guarantees body is not None
        app_id = region_app_repo.get_app_id(region, region_app_id)
        body["bean"]["app_id"] = app_id  # type: ignore[index]  # NOTE: caller guarantees body is not None
        return body["bean"]  # type: ignore[index]  # NOTE: caller guarantees body is not None

    def add_http_route(self, region: str, tenant_name: str, app_id: Any, namespace: str, gateway_name: str,
                       gateway_namespace: str, hosts: Any, rules: Any, section_name: str) -> Any:
        body = dict()
        app = group_repo.get_group_by_id(app_id)
        region_app_id = region_app_repo.get_region_app_id(region, app_id)
        body["name"] = make_uuid()[:6]
        if app.k8s_app:  # type: ignore[union-attr]  # NOTE: app may be None if group not found; pre-existing behaviour
            body["name"] = app.k8s_app + "-" + make_uuid()[:6]  # type: ignore[union-attr]
        body["app_id"] = region_app_id
        body["namespace"] = namespace
        body["section_name"] = section_name
        body["gateway_name"] = gateway_name
        body["gateway_namespace"] = gateway_namespace
        body["hosts"] = hosts
        body["rules"] = rules
        body = region_api.add_gateway_http_route(region, tenant_name, body)
        if body["bean"]:  # type: ignore[index]  # NOTE: caller guarantees body is not None
            data = {
                "app_id": app_id,
                "name": body["bean"].get("name"),  # type: ignore[index]
                "kind": body["bean"].get("kind", "HTTPRoute"),  # type: ignore[index]
                "content": body["bean"].get("content"),  # type: ignore[index]
                "state": 1,
            }
            k8s_resources_repo.create(**data)
        return body["bean"]  # type: ignore[index]  # NOTE: caller guarantees body is not None

    def update_http_route(self, region: str, tenant_name: str, name: str, app_id: Any, namespace: str,
                          gateway_name: str, gateway_namespace: str, hosts: Any, rules: Any, section_name: str) -> Any:
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
        return body["bean"]  # type: ignore[index]  # NOTE: caller guarantees body is not None

    def delete_http_route(self, region: str, tenant_name: str, namespace: str, name: str, region_app_id: str,
                          operator: str = "") -> Any:
        body = region_api.delete_gateway_http_route(region, tenant_name, namespace, name, region_app_id, operator)
        return body["bean"]  # type: ignore[index]  # NOTE: caller guarantees body is not None


gateway_api = GatewayAPI()

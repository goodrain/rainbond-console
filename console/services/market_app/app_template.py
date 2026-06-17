# -*- coding: utf8 -*-
from typing import Any, Dict, List


class AppTemplate(object):
    def __init__(self, app_template: dict) -> None:
        self.app_template = app_template
        self._ingress_http_routes = self._component_key_2_ingress_routes("ingress_http_routes")
        self._ingress_stream_routes = self._component_key_2_ingress_routes("ingress_stream_routes")

    def list_ingress_http_routes_by_component_key(self, component_key: str) -> List[Any]:
        return self._ingress_http_routes.get(component_key, [])

    def component_templates(self) -> List[Any]:
        return self.app_template.get("apps") or []

    def _component_key_2_ingress_routes(self, ingress_type: str) -> Dict[str, List[Any]]:
        ingress_routes = self.app_template.get(ingress_type)
        if not ingress_routes:
            return {}
        result: Dict[str, List[Any]] = {}
        for ingress in ingress_routes:
            ingresses = result.get(ingress["component_key"], [])
            ingresses.append(ingress)
            result[ingress["component_key"]] = ingresses
        return result

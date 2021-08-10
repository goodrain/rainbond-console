# -*- coding: utf8 -*-


class AppTemplate(object):
    def __init__(self, app_template):
        self.app_template = app_template
        self._ingress_http_routes = self._component_key_2_ingress_routes("ingress_http_routes")
        self._ingress_stream_routes = self._component_key_2_ingress_routes("ingress_stream_routes")

    def list_ingress_http_routes_by_component_key(self, component_key):
        return self._ingress_http_routes.get(component_key, [])

    def component_templates(self):
        return self.app_template.get("apps") if self.app_template.get("apps") else []

    def _component_key_2_ingress_routes(self, ingress_type):
        ingress_routes = self.app_template.get(ingress_type)
        if not ingress_routes:
            return {}
        result = {}
        for ingress in ingress_routes:
            ingresses = result.get(ingress["component_key"], [])
            ingresses.append(ingress)
            result[ingress["component_key"]] = ingresses
        return result

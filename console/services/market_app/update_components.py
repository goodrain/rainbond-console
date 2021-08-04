# -*- coding: utf8 -*-
import copy
import json
from datetime import datetime

from .utils import get_component_template
from .component import Component
from console.services.market_app.original_app import OriginalApp
from console.models.main import ServiceSourceInfo


class UpdateComponents(object):
    """
    components that need to be updated.
    """

    def __init__(self, original_app: OriginalApp, app_model_key, app_template, version, components_keys, property_changes):
        """
        components_keys: component keys that the user select.
        """
        self.original_app = original_app
        self.app_model_key = app_model_key
        self.app_template = app_template
        self.version = version
        self.components_keys = components_keys
        self.property_changes = property_changes
        # update service_key and service_share_uuid based on the new app template
        self._ensure_component_keys(self.original_app.components())
        self.components = self._create_update_components()

    def _create_update_components(self):
        """
        component templates + existing components => update components
        """
        # filter by self.components_keys
        components = []
        for cpt in self.original_app.components():
            if self.components_keys and cpt.component.service_key not in self.components_keys:
                continue
            cpt = copy.deepcopy(cpt)
            cpt.component_source.version = self.version
            components.append(cpt)

        cpt_changes = {change["component_id"]: change for change in self.property_changes.changes}
        for cpt in components:
            component_tmpl = get_component_template(cpt, self.app_template)
            if not component_tmpl:
                continue

            cpt.set_changes(self.original_app.tenant, self.original_app.region, cpt_changes[cpt.component.component_id],
                            self.original_app.governance_mode)

            cpt.component.image = component_tmpl["share_image"]
            cpt.component.cmd = component_tmpl.get("cmd", "")
            cpt.component.version = component_tmpl["version"]

            self._update_component_source(cpt.component_source, component_tmpl, self.version)

        return components

    def _ensure_component_keys(self, components: [Component]):
        for component in components:
            self._ensure_component_key(component)

    def _ensure_component_key(self, component: [Component]):
        tmpl = get_component_template(component, self.app_template)
        if not tmpl:
            return
        component.component.service_key = tmpl.get("service_key", component.component.service_key)
        component.component_source.service_share_uuid = tmpl.get("service_share_uuid",
                                                                 component.component_source.service_share_uuid)

    def _update_component_source(self, component_source: ServiceSourceInfo, tmpl: map, version):
        extend_info = json.loads(component_source.extend_info)

        service_image = tmpl.get("service_image")
        if type(service_image) is dict:
            for key in service_image:
                extend_info[key] = service_image[key]

        extend_info["source_deploy_version"] = tmpl.get("deploy_version")
        extend_info["source_service_share_uuid"] = tmpl.get("service_share_uuid") if tmpl.get(
            "service_share_uuid", None) else tmpl.get("service_key", "")
        update_time = self.app_template.get("update_time")
        if update_time:
            if type(update_time) == datetime:
                extend_info["update_time"] = update_time.strftime('%Y-%m-%d %H:%M:%S')
            elif type(update_time) == str:
                extend_info["update_time"] = update_time

        component_source.extend_info = json.dumps(extend_info)
        component_source.version = version

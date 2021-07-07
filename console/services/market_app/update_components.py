# -*- coding: utf8 -*-
import copy

from .utils import get_component_template
from .component import Component
from console.services.market_app.original_app import OriginalApp


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
            components.append(cpt)

        cpt_changes = {change["component_id"]: change for change in self.property_changes.changes}
        for cpt in components:
            component_tmpl = get_component_template(cpt, self.app_template)
            if not component_tmpl:
                continue

            cpt.set_changes(cpt_changes[cpt.component.component_id], self.original_app.governance_mode)

            cpt.component.image = component_tmpl["share_image"]
            cpt.component.cmd = component_tmpl.get("cmd", "")
            cpt.component.version = component_tmpl["version"]

            cpt.component_source.version = self.version

        return components

    def _ensure_component_keys(self, components: [Component]):
        for component in components:
            self._ensure_component_key(component)

    def _ensure_component_key(self, component: [Component]):
        tmpl = get_component_template(component, self.app_template)
        if not tmpl:
            return
        component.component.service_key = tmpl.get("service_key", component.component.service_key)
        component.component_source.service_share_uuid = tmpl.get("service_share_uuid", component.component_source.service_share_uuid)

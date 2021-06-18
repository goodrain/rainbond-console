# -*- coding: utf8 -*-
import copy

from .utils import get_component_template
from console.services.market_app.original_app import OriginalApp
from console.exception.main import AbortRequest


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
            component_tmpl = get_component_template(cpt.component_source, self.app_template)
            if not component_tmpl:
                continue

            cpt.set_changes(cpt_changes[cpt.component.component_id], self.original_app.governance_mode)

            cpt.component.image = component_tmpl["share_image"]
            cpt.component.cmd = component_tmpl.get("cmd", "")
            cpt.component.version = component_tmpl["version"]

            cpt.component_source.version = self.version

        return components

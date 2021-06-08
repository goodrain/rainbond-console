# -*- coding: utf8 -*-

from console.services.market_app.property_changes import PropertyChanges


class UpdateComponents(object):
    """
    components that need to be updated.
    """

    def __init__(self, original_app, app_template, components_keys):
        """
        components_keys: component keys that the user select.
        """
        self.original_app = original_app
        self.app_template = app_template
        self.components_keys = components_keys
        self.components = self._create_update_components()

    def _create_update_components(self):
        """
        component templates + existing components => update components
        """
        # filter by self.components_keys
        components = []
        for cpt in self.original_app.components:
            if self.components_keys and cpt.component.service_key not in self.components_keys:
                continue
            components.append(cpt)

        pc = PropertyChanges(components, self.app_template)
        changes = {change["component_id"]: change for change in pc.changes}

        for cpt in components:
            cpt.set_changes(changes[cpt.component.component_id])

        return components

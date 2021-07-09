# -*- coding: utf8 -*-
def get_component_template(component_source, app_template):
    component_tmpls = app_template.get("apps")

    def func(x):
        result = x.get("service_share_uuid", None) == component_source.service_share_uuid \
                 or x.get("service_key", None) == component_source.service_share_uuid

        return result

    return next(iter([x for x in component_tmpls if func(x)]), None)

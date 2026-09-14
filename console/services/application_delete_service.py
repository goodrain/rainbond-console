# -*- coding: utf-8 -*-
import json
from types import SimpleNamespace
from typing import Any, Dict

from console.services.group_service import group_service
from console.services.k8s_resource import k8s_resource_service
from console.services.operation_log import operation_log_service


class ApplicationDeleteService(object):
    def delete_app(self,
                   user: Any,
                   tenant: Any,
                   region_name: str,
                   app: Any,
                   log_context: Any = None,
                   cascade_crd: bool = False,
                   is_enterprise_admin: bool = False) -> Dict[str, Any]:
        """Delete an application through the same complete Console workflow."""
        k8s_resources = k8s_resource_service.list_by_app_id(str(app.ID))
        resource_ids = [resource.ID for resource in k8s_resources]
        services = group_service.delete_app_with_resources(user,
                                                           tenant,
                                                           region_name,
                                                           app,
                                                           cascade_crd=cascade_crd,
                                                           is_enterprise_admin=is_enterprise_admin)
        service_ids = [service.service_id for service in services]

        component_names = [service.service_cname for service in services]
        old_information = json.dumps(
            [{
                "组件名": name,
                "操作": "删除"
            } for name in component_names],
            ensure_ascii=False,
        )
        comment = ""
        if component_names:
            app_name = operation_log_service.process_app_name(app.app_name, region_name, tenant.tenant_name, app.app_id)
            names_text = (",".join(component_names[:2]) + "等" if len(component_names) > 2 else ",".join(component_names))
            comment = "删除了应用 {app}, 以及应用下的组件 {components}".format(app=app_name, components=names_text)

        context = log_context or SimpleNamespace(
            user=user,
            tenant=tenant,
            tenant_name=tenant.tenant_name,
            team_name=tenant.tenant_name,
            region_name=region_name,
            app=app,
        )
        operation_log_service.create_app_log(
            ctx=context,
            comment=comment,
            format_app=False,
            old_information=old_information,
        )
        return {
            "app_id": app.ID,
            "service_ids": service_ids,
            "resource_ids": resource_ids,
        }


application_delete_service = ApplicationDeleteService()

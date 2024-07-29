from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.services.app_actions import app_manage_service
from console.services.k8s_resource import k8s_resource_service
from console.views.base import BaseApiView
from www.utils.return_message import general_message
from rest_framework.response import Response


class RegionRecover(BaseApiView):
    def post(self, request, *args, **kwargs):
        recover_range = request.data.get("recover_range", "all")
        region_name = request.data.get("region_name", "all")

        tenant_ids = region_repo.get_tenants_by_region_name(region_name)
        tenants = team_repo.get_team_by_team_ids(tenant_ids)
        for tenant in tenants:
            if recover_range == "all" or recover_range == "component":
                app_manage_service.batch_start(region_name, tenant.tenant_name)
            if recover_range == "all" or recover_range == "resource":
                k8s_resource_service.create_tenant_k8s_resource(region_name, tenant.namespace, tenant.tenant_id)
        result = general_message(200, "success", None, bean="成功")
        return Response(result, status=200)

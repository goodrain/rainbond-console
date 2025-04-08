from django.views.decorators.cache import never_cache

from console.repositories.app_config import domain_repo, port_repo
from console.repositories.service_group_relation_repo import ServiceGroupRelationRepositry
from console.views.base import RegionTenantHeaderView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message
from rest_framework.response import Response

region_api = RegionInvokeApi()
service_group_relation_repo = ServiceGroupRelationRepositry()


class AppApiGatewayView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):
        app_id = request.query_params.get('appID', "")
        service_alias = request.query_params.get('service_alias', "")
        port = request.query_params.get('port', "")
        path = request.get_full_path().replace("/console", "")
        resp = region_api.api_gateway_post_proxy(self.region, self.tenant_name, path, request.data, app_id, service_alias, port)
        result = general_message(200, "success", "创建成功", bean=resp)
        return Response(result, status=result["code"])

    @never_cache
    def get(self, request, *args, **kwargs):
        app_id = request.query_params.get('appID', "")
        query = request.query_params.get('query', "")
        path = request.get_full_path().replace("/console", "")
        resp = region_api.api_gateway_get_proxy(self.region, self.tenant.tenant_id, path, app_id, query)
        result = general_message(200, "success", "查询成功", bean=resp['bean'], list=resp['list'])
        return Response(result, status=result["code"])

    @never_cache
    def delete(self, request, *args, **kwargs):
        path = request.get_full_path().replace("/console", "")
        # app_id = request.query_params.get('appID', "")
        resp = region_api.api_gateway_delete_proxy(self.response_region, self.tenant_name, path)
        result = general_message(200, "success", "删除成功", bean=resp)
        return Response(result, status=result["code"])


class AppApiGatewayConvertView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        all = domain_repo.get_all_domain()
        list = []
        for e in all:
            svc = port_repo.get_service_port_by_port(e.tenant_id, e.service_id, e.container_port)
            app_id = service_group_relation_repo.get_group_id_by_service_tenant(svc)
            region_api.api_gateway_bind_http_domain_convert(e.service_name, self.region, self.tenant_name,
                                                            [e.domain_name], svc, app_id)
            list.append(e.domain_name)

        result = general_message(200, "success", "创建成功", list=list)
        return Response(result, status=result["code"])

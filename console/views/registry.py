from django.views.decorators.cache import never_cache
from console.services.team_services import team_services
from www.utils.return_message import general_message
from rest_framework.response import Response
from console.repositories.team_repo import team_registry_auth_repo
from console.utils.reqparse import parse_item

from console.views.base import JWTAuthApiView


class HubRegistryView(JWTAuthApiView):
    @never_cache
    def get(self, request, *args, **kwargs):
        result = team_services.list_registry_auths('', '')
        auths = [auth.to_dict() for auth in result]
        result = general_message(200, "success", "查询成功", list=auths)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        domain = parse_item(request, "domain", required=True)
        username = parse_item(request, "username", required=True)
        password = parse_item(request, "password", required=True)
        secret_id = parse_item(request, "secret_id", required=True)
        params = {
            "tenant_id": '',
            "region_name": '',
            "secret_id": secret_id,
            "domain": domain,
            "username": username,
            "password": password,
        }
        team_registry_auth_repo.create_team_registry_auth(**params)

        result = general_message(200, "success", "创建成功")
        return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        secret_id = request.GET.get("secret_id")
        data = {
            "username": parse_item(request, "username", required=True),
            "password": parse_item(request, "password", required=True)
        }
        auth = team_registry_auth_repo.get_by_secret_id(secret_id)
        if not auth:
            result = general_message(400, "bad request", "您要更新的镜像仓库不存在")
            return Response(result, status=result["code"])
        team_registry_auth_repo.update_team_registry_auth('', '', secret_id, **data)

        result = general_message(200, "success", "更新成功")
        return Response(result, status=result["code"])

    def delete(self, request, *args, **kwargs):
        secret_id = request.GET.get("secret_id")
        team_registry_auth_repo.delete_team_registry_auth('', '', secret_id)
        result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])

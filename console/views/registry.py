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
        result = team_services.list_registry_auths('', '', self.user.user_id)
        auths = [auth.to_dict() for auth in result]
        result = general_message(200, "success", "查询成功", list=auths)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        domain = parse_item(request, "domain", required=True)
        username = parse_item(request, "username", required=True)
        password = parse_item(request, "password", required=True)
        hub_type = parse_item(request, "hub_type", required=True)
        secret_id = parse_item(request, "secret_id", required=True)
        ra = team_registry_auth_repo.check_exist_registry_auth(secret_id, self.user.user_id)
        if ra.exists():
            result = general_message(400, "error", "资源已存在")
            return Response(result, status=result["code"])
        params = {
            "tenant_id": '',
            "region_name": '',
            "secret_id": secret_id,
            "domain": domain,
            "username": username,
            "password": password,
            "hub_type": hub_type,
            "user_id": self.user.user_id,
        }
        team_registry_auth_repo.create_team_registry_auth(**params)

        result = general_message(200, "success", "创建成功")
        return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        secret_id = request.GET.get("secret_id")
        data = {
            "username": parse_item(request, "username", required=True),
            "password": parse_item(request, "password", required=True),
            "hub_type": parse_item(request, "hub_type", required=True),
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
        team_registry_auth_repo.delete_team_registry_auth('', '', secret_id, self.user.user_id)
        result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])


class HubRegistryImageView(JWTAuthApiView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取镜像仓库的命名空间、镜像名称、标签列表或完整镜像地址
        """
        secret_id = request.GET.get("secret_id")
        namespace = request.GET.get("namespace")
        name = request.GET.get("name")
        tag = request.GET.get("tag")
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        search_key = request.GET.get("search_key")
        
        if not secret_id:
            result = general_message(400, "error", "缺少secret_id参数")
            return Response(result, status=result["code"])
            
        auths = team_registry_auth_repo.get_by_secret_id(secret_id)
        if not auths:
            result = general_message(404, "error", "镜像仓库不存在")
            return Response(result, status=result["code"])
            
        try:
            auth = auths[0]
            if not namespace:
                # 获取命名空间列表
                namespaces = team_services.get_registry_namespaces(
                    domain=auth.domain,
                    username=auth.username,
                    password=auth.password,
                    hub_type=auth.hub_type
                )
                result = general_message(200, "success", "查询成功", list=namespaces)
            elif not name:
                # 获取指定命名空间下的镜像列表(分页)
                data = team_services.get_registry_images(
                    domain=auth.domain,
                    username=auth.username,
                    password=auth.password,
                    hub_type=auth.hub_type,
                    namespace=namespace,
                    page=page,
                    page_size=page_size,
                    search_key=search_key
                )
                result = general_message(200, "success", "查询成功", 
                                      list=data["images"],
                                      total=data["total"],
                                      page=data["page"],
                                      page_size=data["page_size"])
            elif not tag:
                # 获取指定镜像的标签列表(分页)
                data = team_services.get_registry_tags(
                    domain=auth.domain,
                    username=auth.username,
                    password=auth.password,
                    hub_type=auth.hub_type,
                    namespace=namespace,
                    name=name,
                    page=page,
                    page_size=page_size,
                    search_key=search_key
                )
                result = general_message(200, "success", "查询成功", 
                                      list=data["tags"],
                                      total=data["total"],
                                      page=data["page"],
                                      page_size=data["page_size"])
            else:
                # 获取完整的镜像地址
                full_image = team_services.get_full_image_name(
                    domain=auth.domain,
                    hub_type=auth.hub_type,
                    namespace=namespace,
                    name=name,
                    tag=tag
                )
                result = general_message(200, "success", "查询成功", bean={"image": full_image})

            return Response(result, status=result["code"])
        except Exception as e:
            result = general_message(500, "error", "查询失败: {}".format(str(e)))
            return Response(result, status=result["code"])

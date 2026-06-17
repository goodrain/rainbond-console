from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.main import ServiceHandleException
from console.repositories.team_repo import team_registry_auth_repo
from console.services.team_services import team_services
from console.utils.reqparse import parse_item
from console.views.base import EnterpriseAdminView, JWTAuthApiView
from www.utils.return_message import general_message
import logging

logger = logging.getLogger('default')


def _parse_registry_credentials(request, hub_type):
    hub_type = team_services.normalize_registry_hub_type(hub_type)
    if hub_type in team_services.CLOUD_REGISTRY_HUB_TYPES:
        username = parse_item(request, "access_key", default=None) or parse_item(request, "username", required=True)
        password = parse_item(request, "access_secret", default=None) or parse_item(request, "password", required=True)
        return username, password
    return (
        parse_item(request, "username", required=True),
        parse_item(request, "password", required=True),
    )


class HubRegistryView(JWTAuthApiView):
    @never_cache
    def get(self, request, *args, **kwargs):
        result = team_services.list_accessible_registry_auths(self.user)
        auths = [team_services.serialize_registry_auth(auth) for auth in result]
        result = general_message(200, "success", "查询成功", list=auths)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        domain = parse_item(request, "domain", required=True)
        hub_type = parse_item(request, "hub_type", required=True)
        hub_type = team_services.normalize_registry_hub_type(hub_type)
        username, password = _parse_registry_credentials(request, hub_type)
        secret_id = parse_item(request, "secret_id", required=True)
        ra = team_registry_auth_repo.check_exist_registry_auth(secret_id, self.user.user_id)
        if ra.exists():
            result = general_message(400, "error", "资源已存在")
            return Response(result, status=result["code"])

        try:
            team_services.check_registry_connection(domain, username, password, hub_type)
            params = {
                "tenant_id": '',
                "region_name": '',
                "secret_id": secret_id,
                "domain": domain,
                "username": username,
                "password": password,
                "hub_type": hub_type,
                "user_id": self.user.user_id,
                "scope": team_services.USER_REGISTRY_SCOPE,
                "enterprise_id": "",
            }
            team_registry_auth_repo.create_team_registry_auth(**params)
            result = general_message(200, "success", "创建成功")
            return Response(result, status=result["code"])
        except ServiceHandleException as e:
            result = general_message(e.status_code, e.msg, e.msg_show)
            return Response(result, status=result["code"])
        except Exception as e:
            logger.exception(e)
            result = general_message(500, "creation failed", "创建失败: {}".format(str(e)))
            return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        secret_id = request.GET.get("secret_id")
        auth = team_registry_auth_repo.get_user_registry_auth(secret_id, self.user.user_id)
        if not auth:
            result = general_message(400, "bad request", "您要更新的镜像仓库不存在")
            return Response(result, status=result["code"])
        data = {
            "hub_type": parse_item(request, "hub_type", required=True),
        }
        data["hub_type"] = team_services.normalize_registry_hub_type(data["hub_type"])
        data["username"], data["password"] = _parse_registry_credentials(request, data["hub_type"])
        try:
            team_services.validate_registry_hub_type(data["hub_type"])
        except ServiceHandleException as e:
            result = general_message(e.status_code, e.msg, e.msg_show)
            return Response(result, status=result["code"])
        team_registry_auth_repo.update_user_registry_auth(secret_id, self.user.user_id, **data)

        result = general_message(200, "success", "更新成功")
        return Response(result, status=result["code"])

    def delete(self, request, *args, **kwargs):
        secret_id = request.GET.get("secret_id")
        team_registry_auth_repo.delete_user_registry_auth(secret_id, self.user.user_id)
        result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])


class EnterpriseHubRegistryView(EnterpriseAdminView):
    def _check_enterprise_admin(self, enterprise_id):
        if enterprise_id != getattr(self.user, "enterprise_id", "") or not getattr(self, "is_enterprise_admin", False):
            result = general_message(403, "permission denied", "无权限操作企业镜像仓库")
            return Response(result, status=result["code"])
        return None

    @never_cache
    def get(self, request, enterprise_id, *args, **kwargs):
        denied = self._check_enterprise_admin(enterprise_id)
        if denied:
            return denied
        result = team_registry_auth_repo.list_enterprise_registry_auths(enterprise_id)
        auths = [team_services.serialize_registry_auth(auth) for auth in result]
        result = general_message(200, "success", "查询成功", list=auths)
        return Response(result, status=result["code"])

    def post(self, request, enterprise_id, *args, **kwargs):
        denied = self._check_enterprise_admin(enterprise_id)
        if denied:
            return denied
        domain = parse_item(request, "domain", required=True)
        hub_type = parse_item(request, "hub_type", required=True)
        hub_type = team_services.normalize_registry_hub_type(hub_type)
        username, password = _parse_registry_credentials(request, hub_type)
        secret_id = parse_item(request, "secret_id", required=True)
        if team_registry_auth_repo.check_exist_enterprise_registry_auth(enterprise_id, secret_id).exists():
            result = general_message(400, "error", "资源已存在")
            return Response(result, status=result["code"])
        try:
            team_services.check_registry_connection(domain, username, password, hub_type)
            params = {
                "tenant_id": '',
                "region_name": '',
                "secret_id": secret_id,
                "domain": domain,
                "username": username,
                "password": password,
                "hub_type": hub_type,
                "user_id": 0,
                "scope": team_services.ENTERPRISE_REGISTRY_SCOPE,
                "enterprise_id": enterprise_id,
            }
            team_registry_auth_repo.create_team_registry_auth(**params)
            result = general_message(200, "success", "创建成功")
            return Response(result, status=result["code"])
        except ServiceHandleException as e:
            result = general_message(e.status_code, e.msg, e.msg_show)
            return Response(result, status=result["code"])
        except Exception as e:
            logger.exception(e)
            result = general_message(500, "creation failed", "创建失败: {}".format(str(e)))
            return Response(result, status=result["code"])

    def put(self, request, enterprise_id, secret_id, *args, **kwargs):
        denied = self._check_enterprise_admin(enterprise_id)
        if denied:
            return denied
        auth = team_registry_auth_repo.get_enterprise_registry_auth(secret_id, enterprise_id)
        if not auth:
            result = general_message(400, "bad request", "您要更新的镜像仓库不存在")
            return Response(result, status=result["code"])
        data = {
            "domain": request.data.get("domain") or auth.domain,
            "hub_type": parse_item(request, "hub_type", required=True),
        }
        data["hub_type"] = team_services.normalize_registry_hub_type(data["hub_type"])
        data["username"], data["password"] = _parse_registry_credentials(request, data["hub_type"])
        try:
            team_services.check_registry_connection(data["domain"], data["username"], data["password"], data["hub_type"])
        except ServiceHandleException as e:
            result = general_message(e.status_code, e.msg, e.msg_show)
            return Response(result, status=result["code"])
        team_registry_auth_repo.update_enterprise_registry_auth(enterprise_id, secret_id, **data)
        result = general_message(200, "success", "更新成功")
        return Response(result, status=result["code"])

    def delete(self, request, enterprise_id, secret_id, *args, **kwargs):
        denied = self._check_enterprise_admin(enterprise_id)
        if denied:
            return denied
        team_registry_auth_repo.delete_enterprise_registry_auth(enterprise_id, secret_id)
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

        try:
            auth = team_services.resolve_registry_auth(self.user, secret_id)
            if not namespace:
                namespaces = team_services.get_registry_namespaces(
                    domain=auth.domain,
                    username=auth.username,
                    password=auth.password,
                    hub_type=auth.hub_type
                )
                result = general_message(200, "success", "查询成功", list=namespaces)
            elif not name:
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
                full_image = team_services.get_full_image_name(
                    domain=auth.domain,
                    hub_type=auth.hub_type,
                    namespace=namespace,
                    name=name,
                    tag=tag
                )
                result = general_message(200, "success", "查询成功", bean={"image": full_image})

            return Response(result, status=result["code"])
        except ServiceHandleException as e:
            result = general_message(e.status_code, e.msg, e.msg_show)
            return Response(result, status=result["code"])
        except Exception as e:
            result = general_message(500, "error", "查询失败: {}".format(str(e)))
            return Response(result, status=result["code"])

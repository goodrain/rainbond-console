# -*- coding: utf8 -*-
import os
import json
import logging
from typing import Any
from urllib.parse import urlsplit

from console.exception.main import ServiceHandleException, AbortRequest
from console.repositories.oauth_repo import oauth_repo, oauth_user_repo
from console.services.config_service import EnterpriseConfigService
from console.services.oauth_service import oauth_sev_user_service
from console.services.operation_log import Operation, operation_log_service, OperationModule
from console.utils.oauth.oauth_types import (NoSupportOAuthType, get_oauth_instance, support_oauth_type)
from console.views.base import (AlowAnyApiView, EnterpriseAdminView, JWTAuthApiView)
from console.models.main import OAuthServices
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants
from www.utils.return_message import error_message
from console.login.jwt_manager import JwtManager
from console.utils.reqparse import parse_item

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class OauthType(JWTAuthApiView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            data = list(support_oauth_type.keys())
        except Exception as e:
            logger.debug(e)
            return Response(error_message(e), status=status.HTTP_200_OK)
        rst = {"data": {"bean": {"oauth_type": data}}}
        return Response(rst, status=status.HTTP_200_OK)


class OauthConfig(EnterpriseAdminView):
    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        data = request.data.get("oauth_services")
        # NOTE: request.data.get may return None; legacy assumes present (backlog).
        enable = data.get("enable")  # type: ignore[union-attr]
        # NOTE: user_id int AutoField (systemic str); request.user is User|AnonymousUser, auth guarantees user (backlog).
        EnterpriseConfigService(request.user.enterprise_id, self.user.user_id).update_config_enable_status(key="OAUTH_SERVICES", enable=enable)  # type: ignore[arg-type, union-attr]
        rst = {"data": {"bean": {"oauth_services": data}}}
        op = Operation.ENABLE if enable else Operation.DISABLE
        comment = operation_log_service.generate_generic_comment(
            operation=op, module=OperationModule.OAUTHCONNECT, module_name="")
        # NOTE: enterprise_id nullable; create_enterprise_log takes str (systemic, backlog).
        operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                    enterprise_id=self.user.enterprise_id)  # type: ignore[arg-type]
        return Response(rst, status=status.HTTP_200_OK)


class OauthService(EnterpriseAdminView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        all_services_list = []
        # NOTE: request.user is User|AnonymousUser; auth guarantees authenticated user (backlog).
        eid = request.user.enterprise_id  # type: ignore[union-attr]
        # NOTE: user_id is int AutoField; repo signatures take str (systemic int-as-str, backlog).
        service = oauth_repo.get_conosle_oauth_service(eid, self.user.user_id)  # type: ignore[arg-type]
        all_services = oauth_repo.get_all_oauth_services(eid, self.user.user_id)  # type: ignore[arg-type]
        svc_ids = [svc.ID for svc in all_services]
        user_oauth_list = oauth_user_repo.get_by_oauths_user_id(svc_ids, self.user.user_id)  # type: ignore[arg-type]
        user_oauth_dict = {uol.service_id: uol for uol in user_oauth_list}
        if all_services is not None:
            for l_service in all_services:
                api = get_oauth_instance(l_service.oauth_type, service, None)
                authorize_url = api.get_authorize_url()
                all_services_list.append({
                    "service_id": l_service.ID,
                    "enable": l_service.enable,
                    "name": l_service.name,
                    "client_id": l_service.client_id,
                    "auth_url": l_service.auth_url,
                    "redirect_uri": l_service.redirect_uri,
                    "oauth_type": l_service.oauth_type,
                    "home_url": l_service.home_url,
                    "eid": l_service.eid,
                    "access_token_url": l_service.access_token_url,
                    "api_url": l_service.api_url,
                    "client_secret": l_service.client_secret,
                    "is_auto_login": l_service.is_auto_login,
                    "is_git": l_service.is_git,
                    "authorize_url": authorize_url,
                    "enterprise_id": l_service.eid,
                    # NOTE: dict.get may return None; ternary guards it but mypy can't narrow (backlog).
                    "is_authenticated": user_oauth_dict.get(l_service.ID).is_authenticated if user_oauth_dict.get(l_service.ID) else False,  # type: ignore[union-attr]
                    "is_expired": user_oauth_dict.get(l_service.ID).is_expired if user_oauth_dict.get(l_service.ID) else False,  # type: ignore[union-attr]
                })
        rst = {"data": {"list": all_services_list}}
        return Response(rst, status=status.HTTP_200_OK)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        values = request.data.get("oauth_services")
        system = request.data.get("system")
        eid = request.user.enterprise_id  # type: ignore[union-attr]
        try:
            services = oauth_repo.create_or_update_console_oauth_services(values, eid, self.user.user_id, system)  # type: ignore[arg-type]
        except Exception as e:
            logger.exception(e)
            # NOTE: py2-era Exception.message; preserved for behavior compat (backlog).
            return Response({"msg": e.message}, status=status.HTTP_400_BAD_REQUEST)  # type: ignore[attr-defined]
        # NOTE: get_conosle_oauth_service may return None; legacy assumes present (backlog).
        service = oauth_repo.get_conosle_oauth_service(eid, self.user.user_id)  # type: ignore[arg-type]
        api = get_oauth_instance(service.oauth_type, service, None)  # type: ignore[union-attr]
        authorize_url = api.get_authorize_url()
        data = []
        # NOTE: services may be None; legacy assumes iterable result (backlog).
        for service in services:  # type: ignore[union-attr]
            data.append({
                "service_id": service.ID,
                "name": service.name,
                "oauth_type": service.oauth_type,
                "client_id": service.client_id,
                "client_secret": service.client_secret,
                "enable": service.enable,
                "eid": service.eid,
                "redirect_uri": service.redirect_uri,
                "home_url": service.home_url,
                "auth_url": service.auth_url,
                "access_token_url": service.access_token_url,
                "api_url": service.api_url,
                "is_auto_login": service.is_auto_login,
                "is_git": service.is_git,
                "authorize_url": authorize_url,
            })
        rst = {"data": {"bean": {"oauth_services": data}}}
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.UPDATE, module=OperationModule.OAUTHCONFIG, module_name="")
        operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                    enterprise_id=self.user.enterprise_id)  # type: ignore[arg-type]
        return Response(rst, status=status.HTTP_200_OK)


class EnterpriseOauthService(EnterpriseAdminView):
    def get(self, request: Request, enterprise_id: str, *args: Any, **kwargs: Any) -> Response:
        all_services_list = []
        public_only = request.GET.get('system', 'false').lower() == 'true'
        if public_only:
            # Only get public services
            all_services = oauth_repo.get_all_oauth_services_by_system(enterprise_id, True)
        else:
            # Get both public services and user's private services
            public_services = oauth_repo.get_all_oauth_services_by_system(enterprise_id, True)
            private_services = oauth_repo.get_all_oauth_services(enterprise_id, self.user.user_id)  # type: ignore[arg-type]
            # Combine both querysets
            all_services = public_services | private_services
        
        if all_services is not None:
            svc_ids = [svc.ID for svc in all_services]
            user_oauth_list = [] if public_only else oauth_user_repo.get_by_oauths_user_id(svc_ids, self.user.user_id)  # type: ignore[arg-type]
            user_oauth_dict = {uol.service_id: uol for uol in user_oauth_list}
            
            for l_service in all_services:
                api = get_oauth_instance(l_service.oauth_type, l_service, None)
                authorize_url = api.get_authorize_url()
                is_authenticated = False
                is_expired = False
                if not public_only and user_oauth_dict.get(l_service.ID):
                    # NOTE: dict.get may return None; guard above, mypy can't narrow (backlog).
                    is_authenticated = user_oauth_dict.get(l_service.ID).is_authenticated  # type: ignore[union-attr, assignment]
                    is_expired = user_oauth_dict.get(l_service.ID).is_expired  # type: ignore[union-attr, assignment]
                
                all_services_list.append({
                    "service_id": l_service.ID,
                    "enable": l_service.enable,
                    "name": l_service.name,
                    "client_id": l_service.client_id,
                    "auth_url": l_service.auth_url,
                    "redirect_uri": l_service.redirect_uri,
                    "oauth_type": l_service.oauth_type,
                    "home_url": l_service.home_url,
                    "eid": l_service.eid,
                    "access_token_url": l_service.access_token_url,
                    "api_url": l_service.api_url,
                    "client_secret": l_service.client_secret,
                    "is_auto_login": l_service.is_auto_login,
                    "is_git": l_service.is_git,
                    "authorize_url": authorize_url,
                    "enterprise_id": l_service.eid,
                    "system": l_service.system,
                    "is_authenticated": is_authenticated,
                    "is_expired": is_expired,
                })
        rst = {"data": {"list": all_services_list}}
        return Response(rst, status=status.HTTP_200_OK)

    def post(self, request: Request, enterprise_id: str, *args: Any, **kwargs: Any) -> Response:
        values = request.data.get("oauth_services")
        services = oauth_repo.create_or_update_oauth_services(values, enterprise_id, self.user.user_id)  # type: ignore[arg-type]

        data = []
        for service in services:
            api = get_oauth_instance(service.oauth_type, service, None)
            authorize_url = api.get_authorize_url()
            data.append({
                "service_id": service.ID,
                "name": service.name,
                "oauth_type": service.oauth_type,
                "client_id": service.client_id,
                "client_secret": service.client_secret,
                "enable": service.enable,
                "eid": service.eid,
                "redirect_uri": service.redirect_uri,
                "home_url": service.home_url,
                "auth_url": service.auth_url,
                "access_token_url": service.access_token_url,
                "api_url": service.api_url,
                "is_auto_login": service.is_auto_login,
                "is_git": service.is_git,
                "authorize_url": authorize_url,
            })
        rst = {"data": {"bean": {"oauth_services": data}}}
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.UPDATE, module=OperationModule.OAUTHCONFIG, module_name="")
        operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                    enterprise_id=self.user.enterprise_id)  # type: ignore[arg-type]
        return Response(rst, status=status.HTTP_200_OK)


class OauthServiceInfo(EnterpriseAdminView):
    def delete(self, request: Request, service_id: str, *args: Any, **kwargs: Any) -> Response:
        try:
            oauth_repo.delete_oauth_service(service_id)
            oauth_user_repo.delete_users_by_services_id(service_id)
            rst = {"data": {"bean": None}, "status": 200}
            return Response(rst, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务"}
            return Response(rst, status=status.HTTP_200_OK)


class OAuthServiceRedirect(AlowAnyApiView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        code = request.GET.get("code")
        state = request.GET.get("state")
        service_id = request.GET.get("service_id")

        # 如果 URL 参数中没有 service_id，尝试从 state 参数中解析（OAuth2 标准方式）
        if not service_id and state:
            try:
                state_data = json.loads(state)
                service_id = state_data.get("service_id")
            except Exception as e:
                logger.error(f"Failed to parse state parameter: {e}")

        # 检查 OAuth 错误
        error = request.GET.get("error")
        if error:
            error_description = request.GET.get("error_description")
            logger.error(f"OAuth error: {error} - {error_description}")

        if not code:
            logger.warning("Missing code parameter in OAuth callback")
            return HttpResponseRedirect("/")

        try:
            # NOTE: service_id from query params is str|None; ORM lookup expects str|int (backlog).
            service = OAuthServices.objects.get(ID=service_id)  # type: ignore[misc]
        except OAuthServices.DoesNotExist:
            logger.error(f"OAuth service not found: {service_id}")
            return HttpResponseRedirect("/")
        except Exception as e:
            logger.exception(f"Error retrieving OAuth service: {e}")
            return HttpResponseRedirect("/")

        route_mode = os.getenv("ROUTE_MODE", "hash")

        # 构建重定向 URL，包含 service_id、code 和 state（state 包含 PKCE 的 code_verifier）
        from urllib.parse import urlencode
        params = {"service_id": service.ID, "code": code}
        if state:
            params["state"] = state

        query_string = urlencode(params)
        redirect_url = f"/oauth/callback?{query_string}" if route_mode == "history" else f"/#/oauth/callback?{query_string}"

        return HttpResponseRedirect(redirect_url)


class OAuthServerAuthorize(AlowAnyApiView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        code = request.GET.get("code")
        service_id = request.GET.get("service_id")
        domain = request.GET.get("domain")
        state = request.GET.get("state")

        # 尝试从 state 中解析 code_verifier（用于 PKCE）
        code_verifier = None
        if state:
            try:
                # 检查 state 是否是 URL 编码的（以 %7B 开头，即 { 的编码）
                if state.startswith('%7B') or state.startswith('%7b'):
                    from urllib.parse import unquote
                    state = unquote(state)
                    logger.debug(f"Decoded URL-encoded state")

                state_data = json.loads(state)
                code_verifier = state_data.get("code_verifier")
                # 如果 state 中有 service_id 但 URL 参数中没有，使用 state 中的
                if not service_id:
                    service_id = state_data.get("service_id")
            except Exception as e:
                logger.warning(f"Failed to parse state: {e}")

        home_split_url = None
        try:
            oauth_service = OAuthServices.objects.get(ID=service_id)  # type: ignore[misc]
            if not oauth_service.enable:
                 raise ServiceHandleException(msg="OAuth service disabled", msg_show="该 OAuth 服务已被禁用")
            if oauth_service.oauth_type == "enterprisecenter" and domain:
                home_split_url = urlsplit(oauth_service.home_url)
                # NOTE: proxy_home_url is a dynamic attr; urlsplit may yield bytes (legacy, backlog).
                oauth_service.proxy_home_url = home_split_url.scheme + "://" + domain + home_split_url.path  # type: ignore[attr-defined, operator]
        except OAuthServices.DoesNotExist:
            logger.debug(f"OAuth service with ID {service_id} not found.")
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            api = get_oauth_instance(oauth_service.oauth_type, oauth_service, None)
        except NoSupportOAuthType as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            # 只有 Gitea 需要 PKCE 的 code_verifier 参数
            if oauth_service.oauth_type == 'gitea':
                oauth_user, access_token, refresh_token = api.get_user_info(code=code, code_verifier=code_verifier)
            else:
                oauth_user, access_token, refresh_token = api.get_user_info(code=code)
        except Exception as e:
            logger.exception(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": str(e)}
            return Response(rst, status=status.HTTP_200_OK)
        if api.is_communication_oauth():
            logger.debug(oauth_user.enterprise_domain)
            # NOTE: domain from query params may be None; legacy assumes str (backlog).
            logger.debug(domain.split(".")[0])  # type: ignore[union-attr]
            # NOTE: home_split_url may be None / netloc may be bytes; legacy assumes str (backlog).
            logger.debug(home_split_url.netloc.split("."))  # type: ignore[union-attr, arg-type]
            if (oauth_user.enterprise_domain != domain.split(".")[0]  # type: ignore[union-attr]
                    and domain.split(".")[0] != home_split_url.netloc.split(".")[0]):  # type: ignore[union-attr, arg-type]
                raise ServiceHandleException(msg="Domain Inconsistent", msg_show="登录失败", status_code=401, error_code=10405)
            oauth_sev_user_service.get_or_create_user_and_enterprise(oauth_user)
        # NOTE: code from query params may be None; set_oauth_user_relation takes str (backlog).
        return oauth_sev_user_service.set_oauth_user_relation(api, oauth_service, oauth_user, access_token, refresh_token, code)  # type: ignore[arg-type]


class OauthUserLogoutView(AlowAnyApiView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        client_id = parse_item(request, "client_id", required=True)
        client_secret = parse_item(request, "client_secret", required=True)
        user_id = parse_item(request, "user_id", required=True)

        oauth_service = oauth_repo.get_by_client_id(client_id, user_id)
        if oauth_service.oauth_type != "dbox":
            raise AbortRequest("unsupported oauth type {} for oauth user logout".format(oauth_service.oauth_type))
        if oauth_service.client_secret != client_secret:
            raise AbortRequest("the requested client key does not match")

        # NOTE: ID is int AutoField; get_by_oauth_user_id takes str (systemic int-as-str, backlog).
        oauth_user = oauth_user_repo.get_by_oauth_user_id(oauth_service.ID, user_id)  # type: ignore[arg-type]

        # Go to Oauth2 Server to check if the user has logged out
        api = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
        api.is_logout()

        # logout
        JwtManager().delete_user_id(oauth_user.user_id)
        return Response(status=status.HTTP_200_OK)


class OAuthUserInfo(AlowAnyApiView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        id = request.GET.get("id")
        code = request.GET.get("code")
        service_id = request.GET.get("service_id")
        if code is not None:
            # NOTE: service_id from query params is str|None; repo expects str (backlog).
            user_info = oauth_user_repo.get_user_oauth_by_code(code=code, service_id=service_id)  # type: ignore[arg-type]
        elif id is not None:
            user_info = oauth_user_repo.get_user_oauth_by_id(id=id, service_id=service_id)  # type: ignore[arg-type]
        else:
            user_info = None
        if user_info:
            if user_info.user_id:
                is_link = True
            else:
                is_link = False
            data = {
                "oauth_user_id": user_info.oauth_user_id,
                "oauth_user_name": user_info.oauth_user_name,
                "oauth_user_email": user_info.oauth_user_email,
                "is_authenticated": user_info.is_authenticated,
                "is_expired": user_info.is_expired,
                "is_link": is_link,
                "service_id": service_id,
            }
            rst = {"data": {"bean": {"user_info": data}}}
            return Response(rst, status=status.HTTP_200_OK)
        # NOTE: rst reused with a differently-shaped dict literal; legacy value-type inference (backlog).
        rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务"}  # type: ignore[dict-item]
        return Response(rst, status=status.HTTP_404_NOT_FOUND)


class OAuthServerUserAuthorize(JWTAuthApiView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        login_user = request.user
        code = request.data.get("code")
        service_id = request.data.get("service_id")
        state = request.data.get("state")

        # 尝试从 state 中解析 code_verifier（用于 PKCE）
        code_verifier = None
        if state:
            try:
                # 检查 state 是否是 URL 编码的（以 %7B 开头，即 { 的编码）
                if state.startswith('%7B') or state.startswith('%7b'):
                    from urllib.parse import unquote
                    state = unquote(state)
                    logger.debug(f"Decoded URL-encoded state")

                state_data = json.loads(state)
                code_verifier = state_data.get("code_verifier")
            except Exception as e:
                logger.warning(f"Failed to parse state: {e}")

        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            # NOTE: get_oauth_services_by_service_id may return None; legacy assumes present (backlog).
            api = get_oauth_instance(oauth_service.oauth_type, oauth_service, None)  # type: ignore[union-attr]
        except NoSupportOAuthType as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            # 只有 Gitea 需要 PKCE 的 code_verifier 参数
            if oauth_service.oauth_type == 'gitea':  # type: ignore[union-attr]
                user, access_token, refresh_token = api.get_user_info(code=code, code_verifier=code_verifier)
            else:
                user, access_token, refresh_token = api.get_user_info(code=code)
        except Exception as e:
            logger.exception(e)
            # NOTE: py2-era Exception.message; preserved for behavior compat (backlog).
            rst = {"data": {"bean": None}, "status": 404, "msg_show": e.message}  # type: ignore[attr-defined]
            return Response(rst, status=status.HTTP_200_OK)

        user_name = user.name
        user_id = str(user.id)
        user_email = user.email
        # NOTE: service_id is str|None & login_user is User|AnonymousUser; legacy assumes str/user (backlog).
        authenticated_user = oauth_user_repo.user_oauth_exists(service_id=service_id, oauth_user_id=user_id)  # type: ignore[arg-type]
        link_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=login_user.user_id)  # type: ignore[arg-type, union-attr]
        if link_user is not None and link_user.oauth_user_id != user_id:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "该用户已绑定其他账号"}
            return Response(rst, status=status.HTTP_200_OK)

        if authenticated_user is not None and authenticated_user.user_id is None:
            authenticated_user.oauth_user_id = user_id
            authenticated_user.oauth_user_name = user_name
            authenticated_user.oauth_user_email = user_email
            authenticated_user.access_token = access_token
            authenticated_user.refresh_token = refresh_token
            authenticated_user.code = code
            authenticated_user.is_authenticated = True
            authenticated_user.is_expired = True
            authenticated_user.user_id = login_user.user_id  # type: ignore[union-attr]
            authenticated_user.save()
            return Response(None, status=status.HTTP_200_OK)
        else:
            oauth_user_repo.save_oauth(
                oauth_user_id=user_id,
                oauth_user_name=user_name,
                oauth_user_email=user_email,
                user_id=login_user.user_id,  # type: ignore[union-attr]
                code=code,
                service_id=service_id,
                access_token=access_token,
                refresh_token=refresh_token,
                is_authenticated=True,
                is_expired=False,
            )
            rst = {"data": {"bean": None}, "status": 200, "msg_show": "绑定成功"}
            return Response(rst, status=status.HTTP_200_OK)


class UserOAuthLink(JWTAuthApiView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        oauth_user_id = str(request.data.get("oauth_user_id"))
        service_id = request.data.get("service_id")
        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service_id)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        # NOTE: request.user is User|AnonymousUser; auth guarantees authenticated user (backlog).
        user_id = request.user.user_id  # type: ignore[union-attr]
        # NOTE: service_id is str|None; repo expects str (backlog).
        oauth_user = oauth_user_repo.user_oauth_exists(service_id=service_id, oauth_user_id=oauth_user_id)  # type: ignore[arg-type]
        link_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)  # type: ignore[arg-type]
        if link_user is not None and link_user.oauth_user_id != oauth_user_id:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "绑定失败， 该用户已绑定其他账号"}
            return Response(rst, status=status.HTTP_200_OK)
        if oauth_user:
            oauth_user.user_id = user_id
            oauth_user.save()
            data = {
                "oauth_user_id": oauth_user.oauth_user_id,
                "oauth_user_name": oauth_user.oauth_user_name,
                "oauth_user_email": oauth_user.oauth_user_email,
                "is_authenticated": oauth_user.is_authenticated,
                "is_expired": oauth_user.is_expired,
                "is_link": True,
                "service_id": service_id,
                # NOTE: oauth_service may be None; legacy assumes present (backlog).
                "oauth_type": oauth_service.oauth_type,  # type: ignore[union-attr]
            }
            rst = {"data": {"bean": data}, "status": 200, "msg_show": "绑定成功"}
            return Response(rst, status=status.HTTP_200_OK)
        else:
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "绑定失败，请重新认证"}
            return Response(rst, status=status.HTTP_200_OK)


class OAuthGitUserRepositories(JWTAuthApiView):
    def get(self, request: Request, service_id: str, *args: Any, **kwargs: Any) -> Response:
        user_id = request.user.user_id  # type: ignore[union-attr]
        page = request.GET.get("page", 1)
        search = request.GET.get("search", '')
        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service_id)
            oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": {"repositories": []}}, "status": 404, "msg_show": "未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        if oauth_user is None:
            rst = {"data": {"bean": {"repositories": []}}, "status": 400, "msg_show": "未成功获取第三方用户信息"}
            return Response(rst, status=status.HTTP_200_OK)
        # NOTE: oauth_service may be None; legacy assumes present (backlog).
        service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)  # type: ignore[union-attr]
        if not service.is_git_oauth():
            rst = {"data": {"bean": {"repositories": []}}, "status": 400, "msg_show": "该OAuth服务不是代码仓库类型"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            if len(search) > 0 and search is not None:
                # NOTE: oauth_user_name may be None; legacy assumes str (backlog).
                true_search = oauth_user.oauth_user_name + '/' + search.split("/")[-1]  # type: ignore[operator]
                data, total = service.search_repos(true_search, page=page)
            else:
                data, total = service.get_repos(page=page)
            rst = {
                "data": {
                    "bean": {
                        "repositories": data,
                        "user_id": user_id,
                        "service_id": service_id,
                        "service_type": oauth_service.oauth_type,  # type: ignore[union-attr]
                        "service_name": oauth_service.name,  # type: ignore[union-attr]
                        "total": total
                    }
                }
            }
            return Response(rst, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(e)
            rst = {"data": {"bean": {"repositories": []}}, "status": 400, "msg_show": "Access Token 已过期"}
            return Response(rst, status=status.HTTP_200_OK)


class OAuthGitUserRepository(JWTAuthApiView):
    def get(self, request: Request, service_id: str, path: str, name: str, *args: Any, **kwargs: Any) -> Response:
        full_name = '/'.join([path, name])
        user_id = request.user.user_id  # type: ignore[union-attr]
        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service_id)
            oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        if oauth_user is None:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "未成功获取第三方用户信息"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            # NOTE: oauth_service may be None; legacy assumes present (backlog).
            service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)  # type: ignore[union-attr]
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "未找到OAuth服务"}
            return Response(rst, status=status.HTTP_200_OK)
        if not service.is_git_oauth():
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "该OAuth服务不是代码仓库类型"}
            return Response(rst, status=status.HTTP_200_OK)

        repo_list = []

        try:
            for data in service.get_repo_detail(full_name):
                repo_list.append(data)
            rst = {
                "data": {
                    "bean": {
                        "repositories": repo_list,
                        "user_id": user_id,
                        "service_id": service_id,
                        "service_type": oauth_service.oauth_type,  # type: ignore[union-attr]
                        "service_name": oauth_service.name,  # type: ignore[union-attr]
                        "total": 10
                    }
                }
            }
            return Response(rst, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "Access Token 已过期"}
            return Response(rst, status=status.HTTP_200_OK)


class OAuthGitUserRepositoryBranches(JWTAuthApiView):
    def get(self, request: Request, service_id: str, *args: Any, **kwargs: Any) -> Response:
        user_id = request.user.user_id  # type: ignore[union-attr]
        type = request.GET.get("type")
        full_name = request.GET.get("full_name")
        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id)
            oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        if oauth_user is None:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "未成功获取第三方用户信息"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            # NOTE: oauth_service may be None; legacy assumes present (backlog).
            service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)  # type: ignore[union-attr]
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "未找到OAuth服务"}
            return Response(rst, status=status.HTTP_200_OK)
        if not service.is_git_oauth():
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "该OAuth服务不是代码仓库类型"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            data = service.get_branches_or_tags(type, full_name)
            rst = {"data": {"bean": {type: data, "total": len(data)}}}
            return Response(rst, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "Access Token 已过期"}
            return Response(rst, status=status.HTTP_200_OK)


class OAuthGitCodeDetection(JWTAuthApiView):
    def post(self, request: Request, service_id: str, *args: Any, **kwargs: Any) -> Response:
        region = request.data.get("region_name")
        tenant_name = request.data.get("tenant_name", None)
        git_url = request.data.get("project_url")
        version = request.data.get("version")
        user_id = request.user.user_id  # type: ignore[union-attr]
        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id)
            oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
        except Exception as e:
            logger.exception(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        if oauth_user is None:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "未成功获取第三方用户信息"}
            return Response(rst, status=status.HTTP_200_OK)

        try:
            # NOTE: oauth_service may be None; legacy assumes present (backlog).
            service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)  # type: ignore[union-attr]
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "未找到OAuth服务"}
            return Response(rst, status=status.HTTP_200_OK)
        if not service.is_git_oauth():
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "该OAuth服务不是代码仓库类型"}
            return Response(rst, status=status.HTTP_200_OK)
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        service_code_version = version
        try:
            service_code_clone_url = service.get_clone_url(git_url)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": "Access Token 已过期"}
            return Response(rst, status=status.HTTP_200_OK)
        sb = {
            "server_type": 'git',
            "repository_url": service_code_clone_url,
            "branch": service_code_version,
            "tenant_id": tenant.tenant_id
        }

        source_body = json.dumps(sb)
        body: dict = dict()
        body["tenant_id"] = tenant.tenant_id
        body["source_type"] = "sourcecode"
        body["namespace"] = tenant.namespace
        body["username"] = None
        body["password"] = None
        body["source_body"] = source_body
        try:
            # NOTE: region from request.data may be None & region result may be None; legacy assumes present (backlog).
            res, body = region_api.service_source_check(region, tenant.tenant_name, body)  # type: ignore[arg-type, assignment]
            return Response({"data": {"data": body}}, status=status.HTTP_200_OK)
        except (region_api.CallApiError, ServiceHandleException) as e:
            logger.debug(e)
            raise ServiceHandleException(msg="region error", msg_show="访问数据中心失败")

    def get(self, request: Request, service_id: str) -> Response:
        region = request.GET.get("region")
        tenant_name = request.GET.get("tenant_name")
        check_uuid = request.GET.get("check_uuid")
        try:
            # NOTE: query params are str|None; region client expects str (backlog).
            res, body = region_api.get_service_check_info(region, tenant_name, check_uuid)  # type: ignore[arg-type]
            return Response({"data": body}, status=status.HTTP_200_OK)
        except (region_api.CallApiError, ServiceHandleException) as e:
            logger.debug(e)
            raise ServiceHandleException(msg="region error", msg_show="访问数据中心失败")


class OverScore(EnterpriseAdminView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # 获取超分比例配置
        # NOTE: user_id int AutoField; EnterpriseConfigService takes str (systemic int-as-str, backlog).
        ss_config = EnterpriseConfigService(request.user.enterprise_id, self.user.user_id).get_config_by_key(  # type: ignore[arg-type, union-attr]
            key="OVER_SCORE")
        over_score_rate = {"CPU": 1.0, "MEMORY": 1.0}

        # 如果配置不存在，则初始化
        if not ss_config:
            EnterpriseConfigService(request.user.enterprise_id, self.user.user_id).add_config(  # type: ignore[arg-type, union-attr]
                key="OVER_SCORE",
                default_value=json.dumps({"CPU": 1.0, "MEMORY": 1.0}),
                type="json",
                desc="超分比例",
                enable=True
            )
            region_api.set_over_score_rate({"over_score_rate": json.dumps(over_score_rate)})
        else:
            # NOTE: ss_config.value may be None; legacy assumes str (backlog).
            over_score_rate = json.loads(ss_config.value)  # type: ignore[arg-type]

        # 返回规范化结构
        rst = {
            "code": 200,
            "msg": "",
            "msg_show": "获取超分比例成功",
            "data": {
                "bean": {
                    "over_score_rate": over_score_rate
                }
            }
        }
        return Response(rst, status=status.HTTP_200_OK)

    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # 获取用户提交的新超分比例
        over_score_rate = request.data.get("over_score_rate")

        # 更新超分比例配置
        EnterpriseConfigService(request.user.enterprise_id, self.user.user_id).update_config_value(  # type: ignore[arg-type, union-attr]
            key="OVER_SCORE",
            value=over_score_rate
        )
        region_api.set_over_score_rate({"over_score_rate": over_score_rate})
        # 返回规范化结构
        rst = {
            "code": 200,
            "msg": "",
            "msg_show": "更新超分比例成功",
            "data": {
                "bean": {
                    "over_score_rate": json.loads(over_score_rate)  # type: ignore[arg-type]
                }
            }
        }
        return Response(rst, status=status.HTTP_200_OK)

# -*- coding: utf8 -*-
import os
import json
import logging
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
from rest_framework.response import Response
from rest_framework_jwt.settings import api_settings
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants
from www.utils.return_message import error_message
from console.login.jwt_manager import JwtManager
from console.utils.reqparse import parse_item

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class OauthType(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        try:
            data = list(support_oauth_type.keys())
        except Exception as e:
            logger.debug(e)
            return Response(error_message(e), status=status.HTTP_200_OK)
        rst = {"data": {"bean": {"oauth_type": data}}}
        return Response(rst, status=status.HTTP_200_OK)


class OauthConfig(EnterpriseAdminView):
    def put(self, request, *args, **kwargs):
        data = request.data.get("oauth_services")
        enable = data.get("enable")
        EnterpriseConfigService(request.user.enterprise_id, self.user.user_id).update_config_enable_status(key="OAUTH_SERVICES", enable=enable)
        rst = {"data": {"bean": {"oauth_services": data}}}
        op = Operation.ENABLE if enable else Operation.DISABLE
        comment = operation_log_service.generate_generic_comment(
            operation=op, module=OperationModule.OAUTHCONNECT, module_name="")
        operation_log_service.create_enterprise_log(user=self.user, comment=comment,
                                                    enterprise_id=self.user.enterprise_id)
        return Response(rst, status=status.HTTP_200_OK)


class OauthService(EnterpriseAdminView):
    def get(self, request, *args, **kwargs):
        all_services_list = []
        eid = request.user.enterprise_id
        service = oauth_repo.get_conosle_oauth_service(eid, self.user.user_id)
        all_services = oauth_repo.get_all_oauth_services(eid, self.user.user_id)
        svc_ids = [svc.ID for svc in all_services]
        user_oauth_list = oauth_user_repo.get_by_oauths_user_id(svc_ids, self.user.user_id)
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
                    "is_authenticated": user_oauth_dict.get(l_service.ID).is_authenticated if user_oauth_dict.get(l_service.ID) else False,
                    "is_expired": user_oauth_dict.get(l_service.ID).is_expired if user_oauth_dict.get(l_service.ID) else False,
                })
        rst = {"data": {"list": all_services_list}}
        return Response(rst, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        values = request.data.get("oauth_services")
        system = request.data.get("system")
        eid = request.user.enterprise_id
        try:
            services = oauth_repo.create_or_update_console_oauth_services(values, eid, self.user.user_id, system)
        except Exception as e:
            logger.exception(e)
            return Response({"msg": e.message}, status=status.HTTP_400_BAD_REQUEST)
        service = oauth_repo.get_conosle_oauth_service(eid, self.user.user_id)
        api = get_oauth_instance(service.oauth_type, service, None)
        authorize_url = api.get_authorize_url()
        data = []
        for service in services:
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
                                                    enterprise_id=self.user.enterprise_id)
        return Response(rst, status=status.HTTP_200_OK)


class EnterpriseOauthService(EnterpriseAdminView):
    def get(self, request, enterprise_id, *args, **kwargs):
        all_services_list = []
        public_only = request.GET.get('system', 'false').lower() == 'true'
        if public_only:
            # Only get public services
            all_services = oauth_repo.get_all_oauth_services_by_system(enterprise_id, True)
        else:
            # Get both public services and user's private services
            public_services = oauth_repo.get_all_oauth_services_by_system(enterprise_id, True)
            private_services = oauth_repo.get_all_oauth_services(enterprise_id, self.user.user_id)
            # Combine both querysets
            all_services = public_services | private_services
        
        if all_services is not None:
            svc_ids = [svc.ID for svc in all_services]
            user_oauth_list = [] if public_only else oauth_user_repo.get_by_oauths_user_id(svc_ids, self.user.user_id)
            user_oauth_dict = {uol.service_id: uol for uol in user_oauth_list}
            
            for l_service in all_services:
                api = get_oauth_instance(l_service.oauth_type, l_service, None)
                authorize_url = api.get_authorize_url()
                is_authenticated = False
                is_expired = False
                if not public_only and user_oauth_dict.get(l_service.ID):
                    is_authenticated = user_oauth_dict.get(l_service.ID).is_authenticated
                    is_expired = user_oauth_dict.get(l_service.ID).is_expired
                
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

    def post(self, request, enterprise_id, *args, **kwargs):
        values = request.data.get("oauth_services")
        services = oauth_repo.create_or_update_oauth_services(values, enterprise_id, self.user.user_id)

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
                                                    enterprise_id=self.user.enterprise_id)
        return Response(rst, status=status.HTTP_200_OK)


class OauthServiceInfo(EnterpriseAdminView):
    def delete(self, request, service_id, *args, **kwargs):
        try:
            oauth_repo.delete_oauth_service(service_id, self.user.user_id)
            oauth_user_repo.delete_users_by_services_id(service_id)
            rst = {"data": {"bean": None}, "status": 200}
            return Response(rst, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务"}
            return Response(rst, status=status.HTTP_200_OK)


class OAuthServiceRedirect(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        if not code:
            return HttpResponseRedirect("/")
        service_id = request.GET.get("service_id")
        service = OAuthServices.objects.get(ID=service_id)
        route_mode = os.getenv("ROUTE_MODE", "hash")
        path = "/#/oauth/callback?service_id={}&code={}"
        if route_mode == "history":
            path = "/oauth/callback?service_id={}&code={}"
        return HttpResponseRedirect(path.format(service.ID, code))


class OAuthServerAuthorize(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        service_id = request.GET.get("service_id")
        domain = request.GET.get("domain")
        home_split_url = None
        try:
            oauth_service = OAuthServices.objects.get(ID=service_id)
            if not oauth_service.enable:
                 raise ServiceHandleException(msg="OAuth service disabled", msg_show="该 OAuth 服务已被禁用")
            if oauth_service.oauth_type == "enterprisecenter" and domain:
                home_split_url = urlsplit(oauth_service.home_url)
                oauth_service.proxy_home_url = home_split_url.scheme + "://" + domain + home_split_url.path
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
            oauth_user, access_token, refresh_token = api.get_user_info(code=code)
        except Exception as e:
            logger.exception(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": str(e)}
            return Response(rst, status=status.HTTP_200_OK)
        if api.is_communication_oauth():
            logger.debug(oauth_user.enterprise_domain)
            logger.debug(domain.split(".")[0])
            logger.debug(home_split_url.netloc.split("."))
            if oauth_user.enterprise_domain != domain.split(".")[0] and \
                    domain.split(".")[0] != home_split_url.netloc.split(".")[0]:
                raise ServiceHandleException(msg="Domain Inconsistent", msg_show="登录失败", status_code=401, error_code=10405)
            oauth_sev_user_service.get_or_create_user_and_enterprise(oauth_user)
        return oauth_sev_user_service.set_oauth_user_relation(api, oauth_service, oauth_user, access_token, refresh_token, code)


class OauthUserLogoutView(AlowAnyApiView):
    def post(self, request, *args, **kwargs):
        client_id = parse_item(request, "client_id", required=True)
        client_secret = parse_item(request, "client_secret", required=True)
        user_id = parse_item(request, "user_id", required=True)

        oauth_service = oauth_repo.get_by_client_id(client_id, user_id)
        if oauth_service.oauth_type != "dbox":
            raise AbortRequest("unsupported oauth type {} for oauth user logout".format(oauth_service.oauth_type))
        if oauth_service.client_secret != client_secret:
            raise AbortRequest("the requested client key does not match")

        oauth_user = oauth_user_repo.get_by_oauth_user_id(oauth_service.ID, user_id)

        # Go to Oauth2 Server to check if the user has logged out
        api = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
        api.is_logout()

        # logout
        JwtManager().delete_user_id(oauth_user.user_id)
        return Response(status=status.HTTP_200_OK)


class OAuthUserInfo(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        id = request.GET.get("id")
        code = request.GET.get("code")
        service_id = request.GET.get("service_id")
        if code is not None:
            user_info = oauth_user_repo.get_user_oauth_by_code(code=code, service_id=service_id)
        elif id is not None:
            user_info = oauth_user_repo.get_user_oauth_by_id(id=id, service_id=service_id)
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
        rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务"}
        return Response(rst, status=status.HTTP_404_NOT_FOUND)


class OAuthServerUserAuthorize(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        login_user = request.user
        code = request.data.get("code")
        service_id = request.data.get("service_id")
        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id)
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
            user, access_token, refresh_token = api.get_user_info(code=code)
        except Exception as e:
            logger.exception(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": e.message}
            return Response(rst, status=status.HTTP_200_OK)

        user_name = user.name
        user_id = str(user.id)
        user_email = user.email
        authenticated_user = oauth_user_repo.user_oauth_exists(service_id=service_id, oauth_user_id=user_id)
        link_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=login_user.user_id)
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
            authenticated_user.user_id = login_user.user_id
            authenticated_user.save()
            return Response(None, status=status.HTTP_200_OK)
        else:
            oauth_user_repo.save_oauth(
                oauth_user_id=user_id,
                oauth_user_name=user_name,
                oauth_user_email=user_email,
                user_id=login_user.user_id,
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
    def post(self, request, *args, **kwargs):
        oauth_user_id = str(request.data.get("oauth_user_id"))
        service_id = request.data.get("service_id")
        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service_id)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        user_id = request.user.user_id
        oauth_user = oauth_user_repo.user_oauth_exists(service_id=service_id, oauth_user_id=oauth_user_id)
        link_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
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
                "oauth_type": oauth_service.oauth_type,
            }
            rst = {"data": {"bean": data}, "status": 200, "msg_show": "绑定成功"}
            return Response(rst, status=status.HTTP_200_OK)
        else:
            rst = {"data": {"bean": None}, "status": 404, "msg_show": "绑定失败，请重新认证"}
            return Response(rst, status=status.HTTP_200_OK)


class OAuthGitUserRepositories(JWTAuthApiView):
    def get(self, request, service_id, *args, **kwargs):
        user_id = request.user.user_id
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
        service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
        if not service.is_git_oauth():
            rst = {"data": {"bean": {"repositories": []}}, "status": 400, "msg_show": "该OAuth服务不是代码仓库类型"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            if len(search) > 0 and search is not None:
                true_search = oauth_user.oauth_user_name + '/' + search.split("/")[-1]
                data, total = service.search_repos(true_search, page=page)
            else:
                data, total = service.get_repos(page=page)
            rst = {
                "data": {
                    "bean": {
                        "repositories": data,
                        "user_id": user_id,
                        "service_id": service_id,
                        "service_type": oauth_service.oauth_type,
                        "service_name": oauth_service.name,
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
    def get(self, request, service_id, path, name, *args, **kwargs):
        full_name = '/'.join([path, name])
        user_id = request.user.user_id
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
            service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
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
                        "service_type": oauth_service.oauth_type,
                        "service_name": oauth_service.name,
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
    def get(self, request, service_id, *args, **kwargs):
        user_id = request.user.user_id
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
            service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
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
    def post(self, request, service_id, *args, **kwargs):
        region = request.data.get("region_name")
        tenant_name = request.data.get("tenant_name", None)
        git_url = request.data.get("project_url")
        version = request.data.get("version")
        user_id = request.user.user_id
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
            service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
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
        body = dict()
        body["tenant_id"] = tenant.tenant_id
        body["source_type"] = "sourcecode"
        body["namespace"] = tenant.namespace
        body["username"] = None
        body["password"] = None
        body["source_body"] = source_body
        try:
            res, body = region_api.service_source_check(region, tenant.tenant_name, body)
            return Response({"data": {"data": body}}, status=status.HTTP_200_OK)
        except (region_api.CallApiError, ServiceHandleException) as e:
            logger.debug(e)
            raise ServiceHandleException(msg="region error", msg_show="访问数据中心失败")

    def get(self, request, service_id):
        region = request.GET.get("region")
        tenant_name = request.GET.get("tenant_name")
        check_uuid = request.GET.get("check_uuid")
        try:
            res, body = region_api.get_service_check_info(region, tenant_name, check_uuid)
            return Response({"data": body}, status=status.HTTP_200_OK)
        except (region_api.CallApiError, ServiceHandleException) as e:
            logger.debug(e)
            raise ServiceHandleException(msg="region error", msg_show="访问数据中心失败")


class OverScore(EnterpriseAdminView):
    def get(self, request, *args, **kwargs):
        # 获取超分比例配置
        ss_config = EnterpriseConfigService(request.user.enterprise_id, self.user.user_id).get_config_by_key(
            key="OVER_SCORE")
        over_score_rate = {"CPU": 1.0, "MEMORY": 1.0}

        # 如果配置不存在，则初始化
        if not ss_config:
            EnterpriseConfigService(request.user.enterprise_id, self.user.user_id).add_config(
                key="OVER_SCORE",
                default_value=json.dumps({"CPU": 1.0, "MEMORY": 1.0}),
                type="json",
                desc="超分比例",
                enable=True
            )
            region_api.set_over_score_rate({"over_score_rate": json.dumps(over_score_rate)})
        else:
            over_score_rate = json.loads(ss_config.value)

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

    def put(self, request, *args, **kwargs):
        # 获取用户提交的新超分比例
        over_score_rate = request.data.get("over_score_rate")

        # 更新超分比例配置
        EnterpriseConfigService(request.user.enterprise_id, self.user.user_id).update_config_value(
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
                    "over_score_rate": json.loads(over_score_rate)
                }
            }
        }
        return Response(rst, status=status.HTTP_200_OK)

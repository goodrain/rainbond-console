# -*- coding: utf8 -*-
import json
import logging
import datetime

from django.shortcuts import redirect

from rest_framework.response import Response
from rest_framework import status
from rest_framework_jwt.settings import api_settings

from console.services.config_service import EnterpriseConfigService
from console.views.base import JWTAuthApiView, AlowAnyApiView, EnterpriseAdminView
from console.repositories.oauth_repo import oauth_repo
from console.repositories.oauth_repo import oauth_user_repo
from console.repositories.user_repo import user_repo
from console.utils.oauth.oauth_types import get_oauth_instance
from console.utils.oauth.oauth_types import NoSupportOAuthType
from console.utils.oauth.oauth_types import support_oauth_type
from www.utils.return_message import error_message

from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class OauthType(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        try:
            data = support_oauth_type.keys()
        except Exception as e:
            logger.debug(e)
            return Response(error_message(e), status=status.HTTP_200_OK)
        rst = {"data": {"bean": {"oauth_type": data}}}
        return Response(rst, status=status.HTTP_200_OK)


class OauthConfig(EnterpriseAdminView):
    def put(self, request, *args, **kwargs):
        data = request.data.get("oauth_services")
        enable = data.get("enable")
        EnterpriseConfigService(request.user.enterprise_id).update_config_enable_status(key="OAUTH_SERVICES", enable=enable)

        rst = {"data": {"bean": {"oauth_services": data}}}
        return Response(rst, status=status.HTTP_200_OK)


class OauthService(EnterpriseAdminView):
    def get(self, request, *args, **kwargs):
        all_services_list = []
        eid = request.user.enterprise_id
        service = oauth_repo.get_conosle_oauth_service(eid)
        all_services = oauth_repo.get_all_oauth_services(eid)
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
                })
        rst = {"data": {"list": all_services_list}}
        return Response(rst, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        values = request.data.get("oauth_services")
        eid = request.user.enterprise_id
        try:
            services = oauth_repo.create_or_update_console_oauth_services(values, eid)
        except Exception as e:
            logger.debug(e.message)
            return Response({"msg": e.message}, status=status.HTTP_400_BAD_REQUEST)
        service = oauth_repo.get_conosle_oauth_service(eid)
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
        return Response(rst, status=status.HTTP_200_OK)


class EnterpriseOauthService(EnterpriseAdminView):
    def get(self, request, enterprise_id, *args, **kwargs):
        all_services_list = []
        service = oauth_repo.get_conosle_oauth_service(enterprise_id)
        all_services = oauth_repo.get_all_oauth_services(enterprise_id)
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
                })
        rst = {"data": {"list": all_services_list}}
        return Response(rst, status=status.HTTP_200_OK)

    def post(self, request, enterprise_id, *args, **kwargs):
        values = request.data.get("oauth_services")
        try:
            services = oauth_repo.create_or_update_console_oauth_services(values, enterprise_id)
        except Exception as e:
            logger.debug(e.message)
            return Response({"msg": e.message}, status=status.HTTP_400_BAD_REQUEST)
        service = oauth_repo.get_conosle_oauth_service(enterprise_id)
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
        return Response(rst, status=status.HTTP_200_OK)


class OauthServiceInfo(EnterpriseAdminView):
    def delete(self, request, service_id, *args, **kwargs):
        try:
            oauth_repo.delete_oauth_service(service_id)
            oauth_user_repo.delete_users_by_services_id(service_id)
            rst = {"data": {"bean": None}, "status": 200}
            return Response(rst, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务"}
            return Response(rst, status=status.HTTP_200_OK)


class OAuthServiceRedirect(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        service_id = request.GET.get("service_id")
        path = "/#/oauth/callback?service_id={}&code={}"
        return redirect(to=path.format(service_id, code))


class OAuthServerAuthorize(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        service_id = request.GET.get("service_id")
        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            api = get_oauth_instance(oauth_service.oauth_type, oauth_service, None)
        except NoSupportOAuthType as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            user, access_token, refresh_token = api.get_user_info(code=code)
        except Exception as e:
            logger.debug(e.message)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": e.message}
            return Response(rst, status=status.HTTP_200_OK)
        user_name = user.name
        user_id = str(user.id)
        user_email = user.email
        authenticated_user = oauth_user_repo.user_oauth_exists(service_id=service_id, oauth_user_id=user_id)

        if authenticated_user is not None:
            authenticated_user.oauth_user_id = user_id
            authenticated_user.oauth_user_name = user_name
            authenticated_user.oauth_user_email = user_email
            authenticated_user.access_token = access_token
            authenticated_user.refresh_token = refresh_token
            authenticated_user.code = code
            authenticated_user.save()
            if authenticated_user.user_id is not None:
                login_user = user_repo.get_by_user_id(authenticated_user.user_id)
                payload = jwt_payload_handler(login_user)
                token = jwt_encode_handler(payload)
                response = Response({"data": {"bean": {"token": token}}}, status=status.HTTP_200_OK)
                if api_settings.JWT_AUTH_COOKIE:
                    expiration = (datetime.datetime.now() + api_settings.JWT_EXPIRATION_DELTA)
                    response.set_cookie(api_settings.JWT_AUTH_COOKIE, token, expires=expiration, httponly=True)
                return response

            else:
                rst = {
                    "oauth_user_name": user_name,
                    "oauth_user_id": user_id,
                    "oauth_user_email": user_email,
                    "service_id": authenticated_user.service_id,
                    "oauth_type": oauth_service.oauth_type,
                    "is_authenticated": authenticated_user.is_authenticated,
                    "code": code,
                }
                msg = "user is not authenticated"
                return Response({"data": {"bean": {"result": rst, "msg": msg}}}, status=status.HTTP_200_OK)
        else:
            usr = oauth_user_repo.save_oauth(
                oauth_user_id=user_id,
                oauth_user_name=user_name,
                oauth_user_email=user_email,
                code=code,
                service_id=service_id,
                access_token=access_token,
                refresh_token=refresh_token,
                is_authenticated=True,
                is_expired=False,
            )
            rst = {
                "oauth_user_name": usr.oauth_user_name,
                "oauth_user_id": usr.oauth_user_id,
                "oauth_user_email": usr.oauth_user_email,
                "service_id": usr.service_id,
                "oauth_type": oauth_service.oauth_type,
                "is_authenticated": usr.is_authenticated,
                "code": code,
            }
            msg = "user is not authenticated"
            return Response({"data": {"bean": {"result": rst, "msg": msg}}}, status=status.HTTP_200_OK)


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
        rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务"}
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
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            api = get_oauth_instance(oauth_service.oauth_type, oauth_service, None)
        except NoSupportOAuthType as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            user, access_token, refresh_token = api.get_user_info(code=code)
        except Exception as e:
            logger.debug(e.message)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": e.message}
            return Response(rst, status=status.HTTP_200_OK)

        user_name = user.name
        user_id = str(user.id)
        user_email = user.email
        authenticated_user = oauth_user_repo.user_oauth_exists(service_id=service_id, oauth_user_id=user_id)
        link_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=login_user.user_id)
        if link_user is not None and link_user.oauth_user_id != user_id:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"该用户已绑定其他账号"}
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
            rst = {"data": {"bean": None}, "status": 200, "msg_show": u"绑定成功"}
            return Response(rst, status=status.HTTP_200_OK)


class UserOAuthLink(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        oauth_user_id = str(request.data.get("oauth_user_id"))
        service_id = request.data.get("service_id")
        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service_id)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        user_id = request.user.user_id
        oauth_user = oauth_user_repo.user_oauth_exists(service_id=service_id, oauth_user_id=oauth_user_id)
        link_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
        if link_user is not None and link_user.oauth_user_id != oauth_user_id:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"绑定失败， 该用户已绑定其他账号"}
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
            rst = {"data": {"bean": data}, "status": 200, "msg_show": u"绑定成功"}
            return Response(rst, status=status.HTTP_200_OK)
        else:
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"绑定失败，请重新认证"}
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
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        if oauth_user is None:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"未成功获取第三方用户信息"}
            return Response(rst, status=status.HTTP_200_OK)
        service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
        if not service.is_git_oauth():
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"该OAuth服务不是代码仓库类型"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            if len(search) > 0 and search is not None:
                true_search = oauth_user.oauth_user_name + '/' + search.split("/")[-1]
                data = service.search_repos(true_search, page=page)
            else:
                data = service.get_repos(page=page)
            rst = {
                "data": {
                    "bean": {
                        "repositories": data,
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
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"Access Token 已过期"}
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
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        if oauth_user is None:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"未成功获取第三方用户信息"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"未找到OAuth服务"}
            return Response(rst, status=status.HTTP_200_OK)
        if not service.is_git_oauth():
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"该OAuth服务不是代码仓库类型"}
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
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"Access Token 已过期"}
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
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        if oauth_user is None:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"未成功获取第三方用户信息"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"未找到OAuth服务"}
            return Response(rst, status=status.HTTP_200_OK)
        if not service.is_git_oauth():
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"该OAuth服务不是代码仓库类型"}
            return Response(rst, status=status.HTTP_200_OK)
        try:
            data = service.get_branches_or_tags(type, full_name)
            rst = {"data": {"bean": {type: data, "total": len(data)}}}
            return Response(rst, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"Access Token 已过期"}
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
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务, 请检查该服务是否存在且属于开启状态"}
            return Response(rst, status=status.HTTP_200_OK)
        if oauth_user is None:
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"未成功获取第三方用户信息"}
            return Response(rst, status=status.HTTP_200_OK)

        try:
            service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"未找到OAuth服务"}
            return Response(rst, status=status.HTTP_200_OK)
        if not service.is_git_oauth():
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"该OAuth服务不是代码仓库类型"}
            return Response(rst, status=status.HTTP_200_OK)
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        service_code_version = version
        try:
            service_code_clone_url = service.get_clone_url(git_url)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"bean": None}, "status": 400, "msg_show": u"Access Token 已过期"}
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
        body["username"] = None
        body["password"] = None
        body["source_body"] = source_body
        res, body = region_api.service_source_check(region, tenant, body)
        return Response({"data": {"data": body}}, status=status.HTTP_200_OK)

    def get(self, request, service_id):
        region = request.GET.get("region")
        tenant_name = request.GET.get("tenant_name")
        check_uuid = request.GET.get("check_uuid")
        res, body = region_api.get_service_check_info(region, tenant_name, check_uuid)
        return Response({"data": body}, status=status.HTTP_200_OK)

# -*- coding: utf8 -*-
import json
import logging
import datetime

from django.shortcuts import redirect

from rest_framework.response import Response
from rest_framework import status
from rest_framework_jwt.settings import api_settings

from console.views.base import JWTAuthApiView, AlowAnyApiView
from console.repositories.oauth_repo import oauth_repo
from console.repositories.oauth_repo import oauth_user_repo
from console.repositories.user_repo import user_repo

from console.services.oauth_service import Oauth2
from console.services.oauth_service import GitApi
from console.services.config_service import config_service

from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants


region_api = RegionInvokeApi()
logger = logging.getLogger("default")

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class OauthConfig(JWTAuthApiView):
    def put(self, request, *args, **kwargs):
        data = request.data.get("oauth_services")
        enable = data.get("enable")
        config_service.update_config_enable_status(key="OAUTH_SERVICES", enable=enable)
        return Response(None, status=status.HTTP_200_OK)


class OauthService(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        eid = request.user.enterprise_id
        service = oauth_repo.get_conosle_oauth_service(eid)
        if service is not None:
            data = {
                "service_id": service.ID,
                "enable": service.enable,
                "name": service.name,
                "client_id": service.client_id,
                "auth_url": service.auth_url,
                "redirect_uri": service.redirect_uri,
                "oauth_type": service.oauth_type,
                "home_url": service.home_url,
                "eid": service.eid,
                "access_token_url": service.access_token_url,
                "api_url": service.api_url,
                "client_secret": service.client_secret,
                "is_auto_login": service.is_auto_login
            }
            rst = {"data": {"data": {"bean": {"oauth_services": data}}}}
            return Response(rst, status=status.HTTP_200_OK)
        else:
            rst = {"data": {"data": {"bean": {"oauth_services": None}}}}
            return Response(rst, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        values = request.data.get("oauth_services")
        eid = request.user.enterprise_id
        try:
            services = oauth_repo.create_or_update_console_oauth_services(values, eid)
        except Exception as e:
            logger.debug(e)
            return Response(e, status=status.HTTP_400_BAD_REQUEST)
        data = []
        for service in services:
            data.append(
                {
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
                    "is_auto_login": service.is_auto_login
                }
            )
        rst = {"data": {"data": {"bean": {"oauth_services": data}}}}
        return Response(rst, status=status.HTTP_200_OK)


class OauthServiceInfo(JWTAuthApiView):
    def delete(self, request):
        service_id = request.data.get("service_id")
        try:
            oauth_repo.delete_oauth_service(service_id)
            return Response(None, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(e)
            return Response(e, status=status.HTTP_400_BAD_REQUEST)


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
            rst = {"data": {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务"}}
            return Response(rst, status=status.HTTP_200_OK)
        service = Oauth2(oauth_service, code=code)
        data = service.get_access_token()
        if data is None:
            rst = {"data": {"data": {"bean": None}, "status": 400, "msg_show": u"未成功获取access_token"}}
            return Response(rst, status=status.HTTP_200_OK)
        else:
            user = service.get_user().json()
            if oauth_service.oauth_type == "github":
                user_name = user["login"]
            elif oauth_service.oauth_type == "gitlab":
                user_name = user["name"]
            elif oauth_service.oauth_type == "gitee":
                user_name = user["name"]
            else:
                user_name =None

            user_id = str(user["id"])
            user_email = user["email"]
            authenticated_user = oauth_user_repo.user_oauth_exists(service_id=service_id,
                                                                   oauth_user_id=user_id)

            if authenticated_user is not None:
                authenticated_user.oauth_user_id = user_id
                authenticated_user.oauth_user_name = user_name
                authenticated_user.oauth_user_email = user_email
                authenticated_user.access_token = data["access_token"]
                authenticated_user.refresh_token = data.get('refresh_token')
                authenticated_user.code = code
                authenticated_user.save()
                if authenticated_user.user_id is not None:
                    login_user = user_repo.get_by_user_id(authenticated_user.user_id)
                    payload = jwt_payload_handler(login_user)
                    token = jwt_encode_handler(payload)
                    response = Response({"data": {"data": {"bean": {"token": token}}}},
                                        status=status.HTTP_200_OK)
                    if api_settings.JWT_AUTH_COOKIE:
                        expiration = (datetime.datetime.now() +
                                      api_settings.JWT_EXPIRATION_DELTA)
                        response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                            token,
                                            expires=expiration,
                                            httponly=True)
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
                    return Response({"data": {"data": {"bean": {"result": rst, "msg": msg}}}},
                                    status=status.HTTP_200_OK)
            else:
                usr = oauth_user_repo.save_oauth(
                    oauth_user_id=user_id,
                    oauth_user_name=user_name,
                    oauth_user_email=user_email,
                    code=code,
                    service_id=service_id,
                    access_token=data["access_token"],
                    refresh_token=data.get('refresh_token'),
                    is_authenticated=True,
                    is_expired=False,
                )
                rst = {
                    "oauth_user_name" : usr.oauth_user_name,
                    "oauth_user_id": usr.oauth_user_id,
                    "oauth_user_email": usr.oauth_user_email,
                    "service_id": usr.service_id,
                    "oauth_type": oauth_service.oauth_type,
                    "is_authenticated": usr.is_authenticated,
                    "code": code,
                }
                msg = "user is not authenticated"
                return Response({"data": {"data": {"bean": {"result": rst, "msg": msg}}}}, status=status.HTTP_200_OK)


class OAuthUserInfo(AlowAnyApiView):
    def get(self, request):
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
            rst = {"data": {"data": {"bean": {"user_info": data}}}}
            return Response(rst, status=status.HTTP_200_OK)
        rst = {"data": {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务"}}
        return Response(rst, status=status.HTTP_404_NOT_FOUND)


class OAuthServerUserAuthorize(JWTAuthApiView):
    def post(self,request):
        login_user = request.user
        code = request.data.get("code")
        service_id = request.data.get("service_id")
        try:
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id)
        except Exception as e:
            logger.debug(e)
            rst = {"data": {"data": {"bean": None}, "status": 404, "msg_show": u"未找到oauth服务"}}
            return Response(rst, status=status.HTTP_200_OK)
        service = Oauth2(oauth_service, code=code)
        data = service.get_access_token()
        if data is None:
            rst = {"data": {"data": {"bean": None}, "status": 400, "msg_show": u"未成功获取access_token"}}
            return Response(rst, status=status.HTTP_200_OK)
        else:
            user = service.get_user()
            if oauth_service.oauth_type == "github":
                user_name = user["login"]
            elif oauth_service.oauth_type == "gitlab":
                user_name = user["name"]
            elif oauth_service.oauth_type == "gitee":
                user_name = user["name"]
            else:
                user_name = None

            user_id = str(user["id"])
            user_email = user["email"]
            authenticated_user = oauth_user_repo.user_oauth_exists(service_id=service_id,
                                                                   oauth_user_id=user_id)

            if authenticated_user is not None:
                authenticated_user.oauth_user_id = user_id
                authenticated_user.oauth_user_name = user_name
                authenticated_user.oauth_user_email = user_email
                authenticated_user.access_token = data["access_token"]
                authenticated_user.refresh_token = data.get('refresh_token')
                authenticated_user.code = code
                authenticated_user.user_id = login_user.user_id
                authenticated_user.save()
                return Response(None, status=status.HTTP_200_OK)
            else:
                oauth_user_repo.save_oauth(
                    oauth_user_id=user_id,
                    oauth_user_name=user_name,
                    oauth_user_email=user_email,
                    user_id = login_user.user_id,
                    code=code,
                    service_id=service_id,
                    access_token=data["access_token"],
                    refresh_token=data.get('refresh_token'),
                    is_authenticated=True,
                    is_expired=False,
                )
                rst = {"data": {"data": {"bean": None}, "status": 200, "msg_show": u"绑定成功"}}
                return Response(rst, status=status.HTTP_200_OK)


class UserOAuthLink(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        oauth_user_id = request.data.get("oauth_user_id")
        service_id = request.data.get("service_id")
        oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service_id)
        user_id = request.user.user_id
        oauth_user = oauth_user_repo.user_oauth_exists(service_id=service_id, oauth_user_id=oauth_user_id)
        if oauth_user:
            oauth_user.user_id=user_id
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
            rst = {"data": {"data": {"bean": data}, "status": 200, "msg_show": u"link success"}}
            return Response(rst, status=status.HTTP_200_OK)
        else:
            rst = {"data": {"data": {"bean": None}, "status": 404, "msg_show": u"link fail"}}
            return Response(rst, status=status.HTTP_200_OK)

class UserOAuthRefresh(JWTAuthApiView):
    def get(self, request, service_id, *args, **kwargs):
        user_id = request.user.user_id
        oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service_id)
        oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)

        try:
            GitApi(oauth_service=oauth_service, oauth_user=oauth_user)
        except:
            return Response({"data": {"data": {"bean": None}, "status": 400, "msg_show": u"refresh failed"}},
                            status=status.HTTP_200_OK)
        return Response({"data": {"data": {"bean": None}, "status": 200, "msg_show": u"refresh success"}},
                        status=status.HTTP_200_OK)



class OAuthGitUserRepositories(JWTAuthApiView):
    def get(self, request, service_id, *args, **kwargs):
        user_id = request.user.user_id
        page = request.GET.get("page", 1)
        search = request.GET.get("search", '')
        oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service_id)
        oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
        service = GitApi(oauth_service=oauth_service, oauth_user=oauth_user)
        if len(search) > 0 and search is not None:
            data = service.api.search_repo(search, page=page)
        else:
            data = service.api.get_repos(page=page)
        rst = {"data": {"data": {"bean": {"repositories": data,
                                          "user_id": user_id,
                                          "service_id": service_id,
                                          "service_type": oauth_service.oauth_type,
                                          "service_name": oauth_service.name,
                                          "total": 10}}}}
        return Response(rst, status=status.HTTP_200_OK)


class OAuthGitUserRepository(JWTAuthApiView):
    def get(self, request, service_id, path, name, *args, **kwargs):
        full_name = '/'.join([path, name])
        user_id = request.user.user_id
        oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service_id)
        oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
        service = GitApi(oauth_service=oauth_service, oauth_user=oauth_user)
        repo_list = []
        for data in service.api.get_repo(full_name):
            repo_list.append(data)
        rst = {"data": {"data": {"bean": {"repositories": repo_list,
                                          "user_id": user_id,
                                          "service_id": service_id,
                                          "service_type": oauth_service.oauth_type,
                                          "service_name": oauth_service.name,
                                          "total": 10}}}}
        return Response(rst, status=status.HTTP_200_OK)


class OAuthGitUserRepositoryBranches(JWTAuthApiView):
    def get(self, request, service_id, *args, **kwargs):
        user_id = request.user.user_id
        type = request.GET.get("type")
        full_name = request.GET.get("full_name")
        oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id)
        oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
        service = GitApi(oauth_service=oauth_service, oauth_user=oauth_user)
        data = service.api.get_project_branches_or_tags(full_name, type)
        rst = {"data": {"data": {"bean": {type: data, "total": len(data)}}}}
        return Response(rst, status=status.HTTP_200_OK)


class OAuthGitUserHooks(JWTAuthApiView):
    def post(self, request, service_id, *args, **kwargs):
        user_id = request.user.user_id
        oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id)
        oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
        service = GitApi(oauth_service=oauth_service, oauth_user=oauth_user)
        service.api.creat_hooks()


class OAuthGitCodeDetection(JWTAuthApiView):
    def post(self, request, service_id, **kwargs):
        region = request.data.get("region_name")
        tenant_name = request.data.get("tenant_name", None)
        git_url = request.data.get("project_url")
        version = request.data.get("version")
        user_id = request.user.user_id
        oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id)
        oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
        Oauth2(oauth_service=oauth_service, oauth_user=oauth_user).check_and_refresh_access_token()
        access_token = oauth_user.access_token
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        service_code_version = version
        urls = git_url.split("//")
        if oauth_service.oauth_type == "github" or oauth_service.oauth_type == "gitee":
            service_code_clone_url = urls[0] + '//' + oauth_user.oauth_user_name \
                                     + ':' + access_token + '@' + urls[-1]
        elif oauth_service.oauth_type == "gitlab":
            service_code_clone_url = urls[0] + '//oauth2:' + access_token + '@' + urls[-1]
        else:
            service_code_clone_url = None
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
        return Response({"data": {"data": body}}, status=status.HTTP_200_OK)

# -*- coding: utf-8 -*-

import datetime
import logging
from rest_framework.response import Response
from rest_framework_jwt.settings import api_settings
from django.db.transaction import atomic
from console.repositories.user_repo import user_repo
from console.repositories.oauth_repo import oauth_user_repo

from console.services.enterprise_services import enterprise_services
from console.services.user_services import user_services

from www.models.main import Users

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

logger = logging.getLogger("default")


class OAuthService(object):
    pass


class OAuthUserService(object):
    @atomic
    def get_or_create_user_and_enterprise(self, oauth_user):
        try:
            user = user_repo.get_enterprise_user_by_username(oauth_user.enterprise_id, oauth_user.name)
        except Users.DoesNotExist:
            user_info = dict()
            user_info["email"] = oauth_user.email
            user_info["nick_name"] = oauth_user.name
            user_info["client_ip"] = oauth_user.client_ip
            user_info["phone"] = oauth_user.phone
            user_info["real_name"] = oauth_user.real_name
            user_info["is_active"] = 1
            password = "goodrain"
            user_info["enterprise_center_user_id"] = oauth_user.id
            user = Users(**user_info)
            user.set_password(password)
            user.save()
        enterprise = enterprise_services.get_enterprise_by_enterprise_id(oauth_user.enterprise_id)
        if not enterprise:
            enterprise = enterprise_services.create_oauth_enterprise(oauth_user.enterprise_domain, oauth_user.enterprise_name,
                                                                     oauth_user.enterprise_id)
            user_services.make_user_as_admin_for_enterprise(user.user_id, enterprise.enterprise_id)
        user.enterprise_id = enterprise.enterprise_id
        user.save()
        return user

    def set_oauth_user_relation(self, api, oauth_service, oauth_user, access_token, refresh_token, code, user=None):
        oauth_user.id = str(oauth_user.id)
        if api.is_communication_oauth():
            logger.debug(oauth_user.name)
            user = user_repo.get_enterprise_user_by_username(oauth_user.enterprise_id, oauth_user.name)
        authenticated_user = oauth_user_repo.user_oauth_exists(service_id=oauth_service.ID, oauth_user_id=oauth_user.id)
        if authenticated_user is not None:
            authenticated_user.oauth_user_id = oauth_user.id
            authenticated_user.oauth_user_name = oauth_user.name
            authenticated_user.oauth_user_email = oauth_user.email
            authenticated_user.access_token = access_token
            authenticated_user.refresh_token = refresh_token
            authenticated_user.code = code
            if user:
                authenticated_user.user_id = user.user_id
            authenticated_user.save()
            if authenticated_user.user_id is not None:
                login_user = user_repo.get_by_user_id(authenticated_user.user_id)
                payload = jwt_payload_handler(login_user)
                token = jwt_encode_handler(payload)
                response = Response({"data": {"bean": {"token": token}}}, status=200)
                if api_settings.JWT_AUTH_COOKIE:
                    expiration = (datetime.datetime.now() + datetime.timedelta(days=30))
                    response.set_cookie(api_settings.JWT_AUTH_COOKIE, token, expires=expiration)
                return response

            else:
                rst = {
                    "oauth_user_name": oauth_user.name,
                    "oauth_user_id": oauth_user.id,
                    "oauth_user_email": oauth_user.email,
                    "service_id": authenticated_user.service_id,
                    "oauth_type": oauth_service.oauth_type,
                    "is_authenticated": authenticated_user.is_authenticated,
                    "code": code,
                }
                msg = "user is not authenticated"
                return Response({"data": {"bean": {"result": rst, "msg": msg}}}, status=200)
        else:
            usr = oauth_user_repo.save_oauth(
                oauth_user_id=oauth_user.id,
                oauth_user_name=oauth_user.name,
                oauth_user_email=oauth_user.email,
                user_id=(user.user_id if user else None),
                code=code,
                service_id=oauth_service.ID,
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
            if user:
                payload = jwt_payload_handler(user)
                token = jwt_encode_handler(payload)
                response = Response({"data": {"bean": {"token": token}}}, status=200)
                if api_settings.JWT_AUTH_COOKIE:
                    expiration = (datetime.datetime.now() + api_settings.JWT_EXPIRATION_DELTA)
                    response.set_cookie(api_settings.JWT_AUTH_COOKIE, token, expires=expiration, httponly=True)
                return response
            msg = "user is not authenticated"
            return Response({"data": {"bean": {"result": rst, "msg": msg}}}, status=200)


oauth_sev_user_service = OAuthUserService()
oauth_sev_service = OAuthService()

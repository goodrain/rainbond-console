# -*- coding: utf-8 -*-

from console.repositories.user_repo import user_repo
from console.repositories.oauth_repo import oauth_user_repo

from console.services.enterprise_services import enterprise_services
from console.services.user_services import user_services
from console.models.main import UserOAuthServices

from www.models.main import Users
from www.models.main import SuperAdminUser


class OAuthService(object):
    pass


class OAuthUserService(object):
    def get_or_create_user_and_enterprise(self, oauth_user):
        try:
            user = user_repo.get_by_username(oauth_user.name)
        except Exception:
            user_info = dict()
            user_info["email"] = oauth_user.email
            user_info["nick_name"] = oauth_user.name
            user_info["client_ip"] = oauth_user.client_ip
            user_info["phone"] = oauth_user.phone
            user_info["is_active"] = 1
            password = "goodrain"
            user = Users(**user_info)
            user.set_password(password)
            user.save()
            enterprise = enterprise_services.get_enterprise_by_enterprise_id(oauth_user.enterprise_id)
            if not enterprise:
                enterprise = enterprise_services.create_oauth_enterprise(
                    oauth_user.enterprise_domain, oauth_user.enterprise_name, oauth_user.enterprise_id)
                user_services.make_user_as_admin_for_enterprise(user.user_id, enterprise.enterprise_id)
                if oauth_user.enterprise_domain == "goodrain":
                    SuperAdminUser.objects.create(user_id=user.user_id)
            user.enterprise_id = enterprise.enterprise_id
            user.save()
            return user
        return user

    def get_or_add_oauth_user(self, user, service_id, oauth_user_id, access_token, refresh_token, code):
        authenticated_user = oauth_user_repo.user_oauth_exists(service_id, oauth_user_id)
        if not authenticated_user:
            authenticated_user = UserOAuthServices()
            authenticated_user.service_id = service_id
            authenticated_user.oauth_user_id = oauth_user_id
            authenticated_user.oauth_user_name = user.nick_name
            authenticated_user.oauth_user_email = user.email
            authenticated_user.access_token = access_token
            authenticated_user.refresh_token = refresh_token
            authenticated_user.code = code
            authenticated_user.user_id = user.user_id
            authenticated_user.save()
            return user
        else:
            if not authenticated_user.user_id:
                authenticated_user.user_id = user.user_id
                authenticated_user.save()
        return user


oauth_sev_user_service = OAuthUserService()
oauth_sev_service = OAuthService()

# -*- coding: utf-8 -*-
import logging

from console.models.main import OAuthServices
from console.models.main import UserOAuthServices
from console.utils.oauth.oauth_types import support_oauth_type
from console.utils.oauth.oauth_types import get_oauth_instance

logger = logging.getLogger('default')


class OAuthRepo(object):
    def get_conosle_oauth_service(self, eid):
        return OAuthServices.objects.filter(eid=eid, is_deleted=False, is_console=True).first()

    def get_all_oauth_services(self, eid):
        return OAuthServices.objects.filter(eid=eid, is_deleted=False)

    def get_oauth_services(self, eid):
        return OAuthServices.objects.filter(eid=eid, is_deleted=False, enable=True)

    def get_oauth_services_by_type(self, oauth_type, eid):
        return OAuthServices.objects.filter(oauth_type=oauth_type, eid=eid, enable=True, is_deleted=False)

    def get_oauth_services_by_service_id(self, service_id):
        return OAuthServices.objects.get(ID=service_id, enable=True, is_deleted=False)

    def open_get_oauth_services_by_service_id(self, service_id):
        return OAuthServices.objects.filter(ID=service_id, is_deleted=False).first()

    def create_or_update_oauth_services(self, values, eid=None):
        querysetlist = []
        for value in values:
            instance = get_oauth_instance(value["oauth_type"])
            auth_url = instance.get_auth_url(home_url=value["home_url"])
            access_token_url = instance.get_access_token_url(home_url=value["home_url"])
            api_url = instance.get_user_url(home_url=value["home_url"])
            is_git = instance.is_git_oauth()
            if value.get("service_id") is None:
                querysetlist.append(
                    OAuthServices(
                        name=value["name"], client_id=value["client_id"], eid=value["eid"],
                        client_secret=value["client_secret"], redirect_uri=value["redirect_uri"],
                        oauth_type=value["oauth_type"], home_url=value["home_url"],
                        auth_url=auth_url,  access_token_url=access_token_url, api_url=api_url,
                        is_auto_login=value["is_auto_login"], is_console=value["is_console"],
                        is_deleted=value.get("is_deleted", False), is_git=is_git

                    )
                )
            else:
                if value.get("is_deleted"):
                    self.delete_oauth_service(service_id=value.get("service_id"))
                else:
                    old_service = self.open_get_oauth_services_by_service_id(service_id=value.get("service_id"))
                    if old_service.home_url != value["home_url"]:
                        UserOAuthServices.objects.filter(service_id=value.get("service_id")).delete()
                    OAuthServices.objects.filter(ID=value["service_id"]).update(
                        name=value["name"], eid=value["eid"], redirect_uri=value["redirect_uri"],
                        home_url=value["home_url"], auth_url=auth_url,
                        access_token_url=auth_url, api_url=auth_url,
                        enable=value["enable"], is_auto_login=value["is_auto_login"],
                        is_console=value["is_console"]
                    )
            if eid is None:
                eid = value["eid"]
        OAuthServices.objects.bulk_create(querysetlist)
        rst = OAuthServices.objects.filter(eid=eid)
        return rst

    def create_or_update_console_oauth_services(self, values, eid):
        old_oauth_service = OAuthServices.objects.filter(eid=eid, is_console=True).first()
        for value in values[:1]:
            if value["oauth_type"] in support_oauth_type.keys():
                instance = get_oauth_instance(value["oauth_type"])
                auth_url = instance.get_auth_url(home_url=value["home_url"])
                access_token_url = instance.get_access_token_url(home_url=value["home_url"])
                api_url = instance.get_user_url(home_url=value["home_url"])
                is_git = instance.is_git_oauth()
                if value.get("service_id") is None and old_oauth_service is None:
                    OAuthServices.objects.create(
                        name=value["name"], client_id=value["client_id"], eid=value["eid"],
                        client_secret=value["client_secret"], redirect_uri=value["redirect_uri"],
                        oauth_type=value["oauth_type"], home_url=value["home_url"],
                        auth_url=auth_url, access_token_url=access_token_url,
                        api_url=api_url, enable=value["enable"],
                        is_auto_login=value["is_auto_login"], is_console=value["is_console"],
                        is_git=is_git

                    )
                elif old_oauth_service is not None and value.get("service_id") == old_oauth_service.ID:
                    OAuthServices.objects.filter(ID=value["service_id"]).update(
                        name=value["name"], eid=value["eid"], redirect_uri=value["redirect_uri"],
                        home_url=value["home_url"], auth_url=auth_url,
                        access_token_url=access_token_url, api_url=api_url,
                        enable=value["enable"], is_auto_login=value["is_auto_login"],
                        is_console=value["is_console"]
                    )
            else:
                raise Exception(u"未找到该OAuth类型")
            rst = OAuthServices.objects.filter(eid=eid, is_console=True)
            return rst

    def delete_oauth_service(self, service_id):
        OAuthServices.objects.filter(ID=service_id).delete()


class UserOAuthRepo(object):
    def save_oauth(self, *args, **kwargs):
        try:
            user = UserOAuthServices.objects.get(
                oauth_user_id=kwargs.get("oauth_user_id"),
                service_id=kwargs.get("service_id"),
            )
        except Exception:
            user = UserOAuthServices.objects.create(
                oauth_user_id=kwargs.get("oauth_user_id"),
                oauth_user_name=kwargs.get("oauth_user_name"),
                oauth_user_email=kwargs.get("oauth_user_email"),
                service_id=kwargs.get("service_id"),
                is_auto_login=kwargs.get("is_auto_login"),
                is_authenticated=kwargs.get("is_authenticated"),
                is_expired=kwargs.get("is_expired"),
                access_token=kwargs.get("access_token"),
                refresh_token=kwargs.get("refresh_token"),
                user_id=kwargs.get("user_id"),
                code=kwargs.get("code")
            )
        return user

    def update_oauth(self, *args, **kwargs):
        user = self.get_user_by_oauth_user_id(service_id=kwargs.get("service_id"),
                                              oauth_user_id=kwargs.get("oauth_user_id"))
        if user is not None:
            user.oauth_user_id = kwargs.get("oauth_user_id")
            user.oauth_user_name = kwargs.get("oauth_user_name")
            user.oauth_user_email = kwargs.get("oauth_user_email")
            user.access_token = kwargs.get("access_token")
            user.refresh_token = kwargs.get("refresh_token")
            user.save()
        return user

    def get_user_by_oauth_user_id(self, service_id, oauth_user_id):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id,
                                                       oauth_user_id=oauth_user_id)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def user_oauth_exists(self, service_id, oauth_user_id):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id,
                                                       oauth_user_id=oauth_user_id)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def get_user_oauth_by_user_id(self, service_id, user_id):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id,
                                                       user_id=user_id)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def get_user_oauth_by_id(self, service_id, id):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id,
                                                       ID=id)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def get_user_oauth_by_code(self, service_id, code):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id,
                                                       code=code)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def get_user_oauth_by_oauth_user_name(self, service_id, oauth_user_name):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id,
                                                       oauth_user_name=oauth_user_name)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def user_oauth_is_link(self, service_id, oauth_user_id):
        data = UserOAuthServices.objects.get(service_id=service_id,
                                             oauth_user_id=oauth_user_id)
        if data["user_id"]:
            return True
        else:
            return False

    def get_user_oauth_services_info(self, eid, user_id):
        oauth_services = []
        services = OAuthServices.objects.filter(eid=eid, is_deleted=False, enable=True)
        for service in services:
            user_service = self.get_user_oauth_by_user_id(service_id=service.ID,
                                                          user_id=user_id)
            if user_service:
                oauth_services.append(
                    {
                        "service_id": service.ID,
                        "service_name": service.name,
                        "oauth_type": service.oauth_type,
                        "is_authenticated": user_service.is_authenticated,
                        "is_expired": user_service.is_expired,
                        "auth_url": service.auth_url,
                        "client_id": service.client_id,
                        "redirect_uri": service.redirect_uri,
                        "is_git": service.is_git,

                    })
            else:
                oauth_services.append(
                    {
                        "service_id": service.ID,
                        "service_name": service.name,
                        "oauth_type": service.oauth_type,
                        "is_authenticated": False,
                        "is_expired": False,
                        "auth_url": service.auth_url,
                        "client_id": service.client_id,
                        "redirect_uri": service.redirect_uri,
                        "is_git": service.is_git,
                    }
                )
        return oauth_services

    def delete_users_by_services_id(self, service_id):
        users = UserOAuthServices.objects.filter(service_id=service_id)
        users.delete()


oauth_repo = OAuthRepo()
oauth_user_repo = UserOAuthRepo()

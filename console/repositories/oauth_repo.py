# -*- coding: utf-8 -*-
import logging
import os

from console.exception.bcode import ErrOauthServiceExists, ErrOauthUserNotFound, ErrOauthServiceNotFound
from console.models.main import OAuthServices, UserOAuthServices
from console.utils.oauth.oauth_types import (get_oauth_instance, support_oauth_type)

logger = logging.getLogger('default')


class OAuthRepo(object):
    def get_conosle_oauth_service(self, eid, user_id):
        return OAuthServices.objects.filter(eid=eid, is_deleted=False, is_console=True, user_id=user_id).first()

    def get_all_oauth_services(self, eid, user_id):
        return OAuthServices.objects.filter(eid=eid, is_deleted=False, user_id=user_id)

    def get_oauth_services(self, eid, user_id):
        return OAuthServices.objects.filter(eid=eid, is_deleted=False, enable=True, user_id=user_id)

    def get_oauth_services_by_type(self, oauth_type, eid, user_id):
        return OAuthServices.objects.filter(oauth_type=oauth_type, eid=eid, enable=True, is_deleted=False, user_id=user_id)

    def get_all_oauth_services_by_system(self, eid, is_system=True):
        """
        Get all OAuth services filtered by system status
        :param eid: enterprise ID
        :param is_system: if True, get only system (public) services; if False, get non-system (private) services
        :return: QuerySet of OAuthServices
        """
        return OAuthServices.objects.filter(eid=eid, is_deleted=False, system=is_system)

    def get_oauth_services_by_service_id(self, service_id=None):
        if not service_id:
            pre_enterprise_center = os.getenv("PRE_ENTERPRISE_CENTER", None)
            if pre_enterprise_center:
                return OAuthServices.objects.get(name=pre_enterprise_center, oauth_type="enterprisecenter")
            return OAuthServices.objects.filter(oauth_type="enterprisecenter", enable=True, is_deleted=False).first()
        return OAuthServices.objects.get(ID=service_id, enable=True, is_deleted=False)

    @staticmethod
    def get_by_client_id(client_id, user_id):
        try:
            return OAuthServices.objects.get(client_id=client_id, enable=True, is_deleted=False, user_id=user_id)
        except OAuthServices.DoesNotExist:
            raise ErrOauthServiceNotFound

    def open_get_oauth_services_by_service_id(self, service_id):
        return OAuthServices.objects.filter(ID=service_id, is_deleted=False).first()

    @staticmethod
    def get_by_name(name, user_id):
        return OAuthServices.objects.get(name=name, user_id=user_id)

    def create_or_update_oauth_services(self, values, eid=None, user_id=""):
        querysetlist = []
        for value in values:
            instance = get_oauth_instance(value["oauth_type"])
            value["home_url"] = value["home_url"].strip().strip("/")
            auth_url = instance.get_auth_url(home_url=value["home_url"])
            access_token_url = instance.get_access_token_url(home_url=value["home_url"])
            api_url = instance.get_user_url(home_url=value["home_url"])
            is_git = instance.is_git_oauth()
            if value.get("service_id") is None:
                # check if the name exists
                try:
                    self.get_by_name(value["name"], user_id)
                    raise ErrOauthServiceExists
                except OAuthServices.DoesNotExist:
                    pass

                querysetlist.append(
                    OAuthServices(
                        name=value["name"],
                        client_id=value["client_id"],
                        eid=value["eid"],
                        client_secret=value["client_secret"],
                        redirect_uri=value["redirect_uri"],
                        oauth_type=value["oauth_type"],
                        home_url=value["home_url"],
                        auth_url=auth_url,
                        access_token_url=access_token_url,
                        api_url=api_url,
                        is_auto_login=value["is_auto_login"],
                        is_console=value["is_console"],
                        is_deleted=value.get("is_deleted", False),
                        is_git=is_git,
                        user_id=user_id,
                        system=value.get("system", False),
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
                        name=value["name"],
                        eid=value["eid"],
                        redirect_uri=value["redirect_uri"],
                        home_url=value["home_url"],
                        auth_url=auth_url,
                        access_token_url=auth_url,
                        api_url=auth_url,
                        enable=value["enable"],
                        is_auto_login=value["is_auto_login"],
                        is_console=value["is_console"])
            if eid is None:
                eid = value["eid"]
        OAuthServices.objects.bulk_create(querysetlist)
        rst = OAuthServices.objects.filter(eid=eid, user_id=user_id)
        return rst

    def create_or_update_console_oauth_services(self, values, eid, user_id, system):
        old_oauth_service = OAuthServices.objects.filter(eid=eid, is_console=True, user_id=user_id).first()
        for value in values[:1]:
            if value["oauth_type"] in list(support_oauth_type.keys()):
                instance = get_oauth_instance(value["oauth_type"])
                auth_url = instance.get_auth_url(home_url=value["home_url"])
                access_token_url = instance.get_access_token_url(home_url=value["home_url"])
                api_url = instance.get_user_url(home_url=value["home_url"])
                is_git = instance.is_git_oauth()
                if value.get("service_id") is None and old_oauth_service is None:
                    OAuthServices.objects.create(
                        name=value["name"],
                        client_id=value["client_id"],
                        eid=value["eid"],
                        client_secret=value["client_secret"],
                        redirect_uri=value["redirect_uri"],
                        oauth_type=value["oauth_type"],
                        home_url=value["home_url"],
                        auth_url=auth_url,
                        access_token_url=access_token_url,
                        api_url=api_url,
                        enable=value["enable"],
                        is_auto_login=value["is_auto_login"],
                        is_console=value["is_console"],
                        is_git=is_git,
                        user_id=user_id,
                        system=system,
                    )
                elif old_oauth_service is not None and value.get("service_id") == old_oauth_service.ID:
                    OAuthServices.objects.filter(ID=value["service_id"], user_id=user_id).update(
                        name=value["name"],
                        eid=value["eid"],
                        redirect_uri=value["redirect_uri"],
                        home_url=value["home_url"],
                        auth_url=auth_url,
                        access_token_url=access_token_url,
                        api_url=api_url,
                        enable=value["enable"],
                        is_auto_login=value["is_auto_login"],
                        is_console=value["is_console"])
            else:
                raise Exception("未找到该OAuth类型")
            rst = OAuthServices.objects.filter(eid=eid, is_console=True, user_id=user_id)
            return rst

    def delete_oauth_service(self, service_id, user_id):
        OAuthServices.objects.filter(ID=service_id, user_id=user_id).delete()


class UserOAuthRepo(object):
    def save_oauth(self, *args, **kwargs):
        try:
            user = UserOAuthServices.objects.get(
                oauth_user_id=kwargs.get("oauth_user_id"), service_id=kwargs.get("service_id"), user_id=kwargs.get("user_id"))
        except UserOAuthServices.DoesNotExist:
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
                code=kwargs.get("code"))
        except Exception as e:
            logger.exception(e)
        return user

    def update_oauth(self, *args, **kwargs):
        user = self.get_user_by_oauth_user_id(service_id=kwargs.get("service_id"), oauth_user_id=kwargs.get("oauth_user_id"))
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
            oauth_user = UserOAuthServices.objects.get(service_id=service_id, oauth_user_id=oauth_user_id)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def get_by_oauth_user_id(selfself, service_id, oauth_user_id):
        try:
            return UserOAuthServices.objects.get(service_id=service_id, oauth_user_id=oauth_user_id)
        except UserOAuthServices.DoesNotExist:
            raise ErrOauthUserNotFound

    def user_oauth_exists(self, service_id, oauth_user_id):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id, oauth_user_id=oauth_user_id)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def get_by_oauths_user_id(self, service_ids, user_id):
        return UserOAuthServices.objects.filter(service_id__in=service_ids, user_id=user_id)


    def get_all_user_oauth(self, user_id):
        return UserOAuthServices.objects.filter(user_id=user_id)

    def get_user_oauth_by_user_id(self, service_id, user_id):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id, user_id=user_id)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def get_enterprise_center_user_by_user_id(self, user_id):
        try:
            oauth_service = OAuthServices.objects.get(oauth_type="enterprisecenter", ID=1)
            pre_enterprise_center = os.getenv("PRE_ENTERPRISE_CENTER", None)
            if pre_enterprise_center:
                oauth_service = OAuthServices.objects.get(name=pre_enterprise_center, oauth_type="enterprisecenter")
            logger.debug(oauth_service.ID, user_id)
            oauth_user = UserOAuthServices.objects.filter(service_id=oauth_service.ID, user_id=user_id).first()
            return oauth_user, oauth_service
        except (OAuthServices.DoesNotExist, UserOAuthServices.DoesNotExist):
            return None, None

    def get_user_oauth_by_id(self, service_id, id):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id, ID=id)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def get_user_oauth_by_code(self, service_id, code):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id, code=code)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def get_user_oauth_by_oauth_user_name(self, service_id, oauth_user_name):
        try:
            oauth_user = UserOAuthServices.objects.get(service_id=service_id, oauth_user_name=oauth_user_name)
            return oauth_user
        except UserOAuthServices.DoesNotExist:
            return None

    def user_oauth_is_link(self, service_id, oauth_user_id):
        data = UserOAuthServices.objects.get(service_id=service_id, oauth_user_id=oauth_user_id)
        if data["user_id"]:
            return True
        else:
            return False

    def get_user_oauth_services_info(self, eid, user_id):
        oauth_services = []
        system_services = OAuthServices.objects.filter(eid=eid, is_deleted=False, enable=True, system=True)
        user_services = OAuthServices.objects.filter(eid=eid, is_deleted=False, enable=True, user_id=user_id)
        services = system_services.union(user_services)
        for service in services:
            user_service = self.get_user_oauth_by_user_id(service_id=service.ID, user_id=user_id)
            api = get_oauth_instance(service.oauth_type, service, None)
            authorize_url = api.get_authorize_url()
            if user_service:
                oauth_services.append({
                    "service_id": service.ID,
                    "service_name": service.name,
                    "oauth_type": service.oauth_type,
                    "is_authenticated": user_service.is_authenticated,
                    "is_expired": user_service.is_expired,
                    "auth_url": service.auth_url,
                    "client_id": service.client_id,
                    "redirect_uri": service.redirect_uri,
                    "is_git": service.is_git,
                    "authorize_url": authorize_url,
                    "oauth_user_name": user_service.oauth_user_name,
                })
            else:
                oauth_services.append({
                    "service_id": service.ID,
                    "service_name": service.name,
                    "oauth_type": service.oauth_type,
                    "is_authenticated": False,
                    "is_expired": False,
                    "auth_url": service.auth_url,
                    "client_id": service.client_id,
                    "redirect_uri": service.redirect_uri,
                    "is_git": service.is_git,
                    "authorize_url": authorize_url,
                    "oauth_user_name": "",
                })
        return oauth_services

    def delete_users_by_services_id(self, service_id):
        users = UserOAuthServices.objects.filter(service_id=service_id)
        users.delete()


oauth_repo = OAuthRepo()
oauth_user_repo = UserOAuthRepo()

# -*- coding: utf8 -*-
import logging
from urlparse import urlsplit
import functools

from console.utils.oauth.base.oauth import OAuth2User
from console.utils.oauth.base.communication_oauth import CommunicationOAuth2Interface
from console.utils.restful_client import get_enterprise_server_auth_client
from console.utils.restful_client import get_enterprise_server_ent_client
from console.utils.restful_client import get_order_server_ent_client
from console.utils.restful_client import get_pay_server_ent_client
from console.exception.main import ServiceHandleException

from console.utils.oauth.base.exception import NoOAuthServiceErr
from console.utils.urlutil import set_get_url

logger = logging.getLogger("default")


def check_enterprise_center_code():
    """
    检测权限装饰器
    """

    def wrapper(func):
        @functools.wraps(func)
        def __wrapper(self, *args, **kwargs):
            rst = func(self, *args, **kwargs)
            if hasattr(rst, "code"):
                raise ServiceHandleException(status_code=rst.code, msg="enterprise center operate error", msg_show="操作失败")
            return rst

        return __wrapper

    return wrapper


class EnterpriseCenterV1MiXin(object):
    def set_api(self, home_url, oauth_token):
        self.auth_api = get_enterprise_server_auth_client(home_url, oauth_token)
        self.ent_api = get_enterprise_server_ent_client(home_url, oauth_token)
        self.order_api = get_order_server_ent_client(home_url, oauth_token)
        self.pay_api = get_pay_server_ent_client(home_url, oauth_token)


class EnterpriseCenterV1(EnterpriseCenterV1MiXin, CommunicationOAuth2Interface):
    def __init__(self):
        super(EnterpriseCenterV1, self).set_session()
        self.request_params = {
            "response_type": "code",
        }

    def get_auth_url(self, home_url=None):
        return home_url + "/enterprise-server/oauth/authorize"

    def get_access_token_url(self, home_url=None):
        return home_url + "/enterprise-server/oauth/token"

    def get_user_url(self, home_url=""):
        return home_url + "/enterprise-server/api/v1/oauth/user"

    def _get_access_token(self, code=None):
        '''
        private function, get access_token
        :return: access_token, refresh_token
        '''
        if not self.oauth_service:
            raise NoOAuthServiceErr("no found oauth service")
        try:
            home_split_url = urlsplit(self.oauth_service.proxy_home_url)
        except Exception:
            home_split_url = urlsplit(self.oauth_service.home_url)
        redirect_split_url = urlsplit(self.oauth_service.redirect_uri)
        self.oauth_service.redirect_uri = home_split_url.scheme + "://" + home_split_url.netloc + redirect_split_url.path
        logger.debug(self.oauth_service.redirect_uri)
        if code:
            headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded", "Connection": "close"}
            params = {
                "client_id": self.oauth_service.client_id,
                "client_secret": self.oauth_service.client_secret,
                "code": code,
                "redirect_uri": self.oauth_service.redirect_uri + '?service_id=' + str(self.oauth_service.ID),
                "grant_type": "authorization_code"
            }
            url = self.get_access_token_url(self.oauth_service.home_url)
            logger.debug(url)
            try:
                rst = self._session.request(method='POST', url=url, headers=headers, params=params)
                logger.debug(rst.content)
            except Exception as e:
                logger.debug(e)
                raise ServiceHandleException(msg="can not get access key", error_code=10405, status_code=401)
            if rst.status_code == 200:
                logger.debug(rst.content)
                try:
                    data = rst.json()
                except ValueError:
                    raise ServiceHandleException(msg="return value error", msg_show="enterprise center 服务不正常",
                                                 error_code=10405, status_code=401)
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                if self.access_token is None:
                    return None, None
                self.set_api(self.oauth_service.home_url, self.access_token)
                self.update_access_token(self.access_token, self.refresh_token)
                return self.access_token, self.refresh_token
            else:
                raise ServiceHandleException(msg="can not get access key", error_code=10405, status_code=401)
        else:
            if self.oauth_user:
                self.set_api(self.oauth_service.home_url, self.oauth_user.access_token)
                try:
                    user = self.auth_api.oauth_user()
                    if user.real_name:
                        return self.oauth_user.access_token, self.oauth_user.refresh_token
                except Exception:
                    if self.oauth_user.refresh_token:
                        try:
                            self.refresh_access_token()
                            return self.access_token, self.refresh_token
                        except Exception:
                            self.oauth_user.delete()
                            raise ServiceHandleException(msg="refresh key expired", error_code=10405, status_code=401)
                    else:
                        self.oauth_user.delete()
                        raise ServiceHandleException(msg="access key expired", error_code=10405, status_code=401)
            raise ServiceHandleException(msg="no found oauth user record in db", error_code=10405, status_code=401)

    def refresh_access_token(self):
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        params = {
            "refresh_token": self.oauth_user.refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.oauth_service.client_id,
            "client_secret": self.oauth_service.client_secret,
        }
        rst = self._session.request(method='POST', url=self.oauth_service.access_token_url, headers=headers, params=params)
        data = rst.json()
        if rst.status_code == 200:
            self.oauth_user.refresh_token = data.get("refresh_token")
            self.oauth_user.access_token = data.get("access_token")
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.set_api(self.oauth_service.home_url, self.oauth_user.access_token)
            self.oauth_user = self.oauth_user.save()

    def get_user_info(self, code=None):
        access_token, refresh_token = self._get_access_token(code=code)
        user = self.auth_api.oauth_user()
        communication_user = OAuth2User(user.username, user.user_id, user.email)
        communication_user.phone = user.phone
        communication_user.real_name = user.real_name
        communication_user.enterprise_id = user.enterprise.id
        communication_user.enterprise_name = user.enterprise.name
        communication_user.enterprise_domain = user.enterprise.domain
        return communication_user, access_token, refresh_token

    def get_authorize_url(self):
        if self.oauth_service:
            params = {
                "client_id": self.oauth_service.client_id,
                "redirect_uri": self.oauth_service.redirect_uri + "?service_id=" + str(self.oauth_service.ID),
            }
            params.update(self.request_params)
            return set_get_url(self.oauth_service.auth_url, params)
        else:
            raise NoOAuthServiceErr("no found oauth service")

    @check_enterprise_center_code()
    def create_user(self, eid, body):
        self._get_access_token()
        return self.ent_api.create_user(eid, body=body)

    @check_enterprise_center_code()
    def list_user(self, eid):
        self._get_access_token()
        return self.ent_api.list_user(eid)

    @check_enterprise_center_code()
    def delete_user(self, eid, uid):
        self._get_access_token()
        return self.ent_api.delete_user(eid, uid)

    @check_enterprise_center_code()
    def update_user(self, eid, uid, body):
        self._get_access_token()
        return self.ent_api.update_user(eid, uid, body=body)

    @check_enterprise_center_code()
    def get_ent_subscribe(self, eid):
        self._get_access_token()
        return self.ent_api.get_enterprise(eid)

    @check_enterprise_center_code()
    def list_ent_order(self, eid, **kwargs):
        self._get_access_token()
        return self.order_api.list_orders(eid, **kwargs)

    @check_enterprise_center_code()
    def get_ent_order(self, eid, order_id):
        self._get_access_token()
        return self.order_api.get_order(eid, order_id)

    @check_enterprise_center_code()
    def create_ent_order(self, eid, body):
        self._get_access_token()
        return self.order_api.create_order(eid, body=body)

    @check_enterprise_center_code()
    def get_bank_info(self):
        self._get_access_token()
        return self.pay_api.bankinfo()

    @check_enterprise_center_code()
    def check_ent_memory(self, eid, body):
        self._get_access_token()
        return self.ent_api.check_memory(eid, body=body)

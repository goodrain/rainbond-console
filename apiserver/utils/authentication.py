# coding: utf-8
"""认证"""
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.authentication import get_authorization_header
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from apiserver.acl import acl
from apiserver.acl import CLIENTS


class AclPermissions(BasePermission):
    def has_permission(self, request, view):
        if not view.RESOURCE:
            raise ValueError("{} hasn't RESOURCE attribute".format(view))

        cli = request.user.key
        res = view.RESOURCE
        act = self.method_to_act(request.method)

        return acl.enforce(cli, res, act)

    @staticmethod
    def method_to_act(method):
        act_mapping = {
            "GET": "read",
            "POST": "write",
            "PUT": "write",
            "PATCH": "write",
            "DELETE": "write",
        }
        return act_mapping.get(method, '')


class ClientAuthentication(BaseAuthentication):
    """
     Simple token based authentication.

     Clients should authenticate by passing the token key in the "Authorization"
     HTTP header, prepended with the string "Token ".  For example:

         Authorization: Token 401f7ac837da42b97f613d789819ff93537bee6a
     """

    keyword = 'Token'

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        class Client(object):
            def __init__(self, key):
                self.key = key

        from rest_framework.authtoken.models import Token
        if key in CLIENTS:
            return Client(key), Token()
        else:
            raise exceptions.AuthenticationFailed(_('Invalid token.'))

    def authenticate_header(self, request):
        return self.keyword


class BaseView(APIView):
    RESOURCE = None
    authentication_classes = (ClientAuthentication,)
    permission_classes = (AclPermissions,)

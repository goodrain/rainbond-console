from addict import Dict
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from oauth2_provider.ext.rest_framework import TokenHasScope
from oauth2_provider.ext.rest_framework.authentication import OAuth2Authentication


class BaseAPIView(APIView):

    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated, TokenHasScope]
    required_scopes = ['groups']

    def __init__(self, *args, **kwargs):
        APIView.__init__(self, *args, **kwargs)
        self.report = Dict({"ok": True})

from addict import Dict
from rest_framework.views import APIView


class BaseAPIView(APIView):

    # authentication_classes = [OAuth2Authentication]
    # permission_classes = [IsAuthenticated, TokenHasScope]
    # required_scopes = ['groups']

    def __init__(self, *args, **kwargs):
        APIView.__init__(self, *args, **kwargs)
        self.report = Dict({"ok": True})


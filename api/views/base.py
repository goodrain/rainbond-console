from addict import Dict
from rest_framework.views import APIView


class BaseAPIView(APIView):

    def __init__(self, *args, **kwargs):
        APIView.__init__(self, *args, **kwargs)
        self.report = Dict({"ok": True})

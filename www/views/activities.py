from django.http import HttpResponse
from base import BaseView


class ActivityIndexView(BaseView):

    def get(self, request, *args, **kwargs):
        return HttpResponse("waiting")


class ActivityView(BaseView):

    def get(self, request, version, *args, **kwargs):
        if version == '1501':
            return self.redirect_to('/register?rf=wx')
        else:
            return HttpResponse("waiting")

from django.http import HttpResponse
from base import BaseView, AuthedView, GrRedirectView
from mixin import RegionOperateMixin, LoginRedirectMixin, LeftSideBarMixin
from account import *

__all__ = ('BaseView', 'AuthedView', 'LeftSideBarMixin', 'RegionOperateMixin', 'GrRedirectView',
           'LoginRedirectMixin')


def monitor(request):
    return HttpResponse("ok")


def ssl_crv(request):
    return HttpResponse("Ea7e1ps5")

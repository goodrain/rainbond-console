from django.http import HttpResponse
from base import BaseView, AuthedView, LeftSideBarMixin
from account import *

__all__ = ('BaseView', 'AuthedView', 'LeftSideBarMixin')


def monitor(request):
    return HttpResponse("ok")


def ssl_crv(request):
    return HttpResponse("Ea7e1ps5")

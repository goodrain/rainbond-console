# -*- coding: utf-8 -*-
from django.test import Client


def get_client():
    return Client(HTTP_AUTHORIZATION='6923642f067b3cc8e4b7f2194cb25917')

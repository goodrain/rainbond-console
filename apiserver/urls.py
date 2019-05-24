# coding: utf-8
from django.conf.urls import url

from apiserver.views import demo

urlpatterns = [
    url(r'^demo$', demo.DemoView.as_view()),
]

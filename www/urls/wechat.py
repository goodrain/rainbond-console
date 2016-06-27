# -*- coding: utf8 -*-

from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from www.views.wechat import WeChatLogin, WeChatCallBack, \
    WeChatCheck, WeChatInfoView, UnbindView, BindView, WeChatCallBackBind

urlpatterns = patterns(
    '',
    url(r'^$', WeChatCheck.as_view()),
    url(r'^login$', WeChatLogin.as_view()),
    url(r'^callback$', WeChatCallBack.as_view()),
    url(r'^callbackbind$', WeChatCallBackBind.as_view()),

    url(r'^info$', WeChatInfoView.as_view()),
    url(r'^unbind$', UnbindView.as_view()),
    url(r'^bind$', BindView.as_view()),
)




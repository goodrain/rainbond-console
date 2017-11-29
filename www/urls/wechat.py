# -*- coding: utf8 -*-

from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from www.views.wechat import WeChatLogin, WeChatCallBack, WeChatLogout,\
    WeChatCheck, WeChatInfoView, UnbindView, BindView, WeChatCallBackBind

urlpatterns = patterns(
    '',
    url(r'^login$', WeChatLogin.as_view()),
    url(r'^logout$', WeChatLogout.as_view()),
    url(r'^callback$', WeChatCallBack.as_view()),
    url(r'^callbackbind$', WeChatCallBackBind.as_view()),

    url(r'^info$', login_required(WeChatInfoView.as_view())),
    url(r'^unbind$', login_required(UnbindView.as_view())),
    url(r'^bind$', login_required(BindView.as_view())),
)




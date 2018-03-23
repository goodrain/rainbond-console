# -*- coding: utf8 -*-
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.decorators.csrf import csrf_exempt

import www.views as views
from www.app_services_view import GitLabWebHook, GitHubWebHook, GitCheckCode
from www.services_view import ServiceGitHub
from www.views import GrRedirectView
from www.views.alimns import *
import sys
from console.views.account import GoodrainSSONotify

reload(sys)  # Python2.5 初始化后会删除 sys.setdefaultencoding 这个方法，我们需要重新载入
sys.setdefaultencoding('utf-8')


def openapi_urlpatterns():
    """
    Helper function to return a URL pattern for serving static files.
    """
    if settings.IS_OPEN_API:
        return [
            url(r'^openapi/', include('openapi.urls')),
        ]
    else:
        return []


urlpatterns = patterns(
    '',
    # url(r'^$', views.Index.as_view()),
    url(r'^favicon\.ico$',
        GrRedirectView.as_view(url='/static/www/favicon.ico')),
    url(r'^$', views.IndexTemplateView.as_view()),
    url(r'^github/callback$', views.GithubCallBackView.as_view()),
    url(r'^console/', include('console.urls')),
    url(r'^data/media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),
    url(r'^oauth/githup/$', login_required(ServiceGitHub.as_view())),
    url(r'^service/gitlabhook/$', csrf_exempt(GitLabWebHook.as_view())),
    url(r'^service/githubhook/$', csrf_exempt(GitHubWebHook.as_view())),
    url(r'^service/codecheck/$', csrf_exempt(GitCheckCode.as_view())),
    url(r'^api/', include('api.urls')),
    url(r'^auth/', include('www.urls.auth')),
    url(r'^select$', login_required(views.TenantSelectView.as_view())),
    url(r'^payed/(?P<tenantName>[\w\-]+)/', include('www.urls.payedpackage')),
    url(r'^license', views.LicenceView.as_view()),
    url(r'^backend/', include('backends.urls')),
    # url(r'^backend/account/', include('backends.accounturls')),
    url(r'^marketapi/', include('marketapi.urls')),
    url(r'^sso_callback$', csrf_exempt(views.GoorainSSOCallBack.as_view())),
    # url(r'^sso_notify$', csrf_exempt(views.GoodrainSSONotify.as_view())),
    url(r'^sso_notify$', GoodrainSSONotify.as_view()),
) + staticfiles_urlpatterns() + openapi_urlpatterns()

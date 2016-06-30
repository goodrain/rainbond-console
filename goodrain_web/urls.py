from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.decorators.csrf import csrf_exempt
import www.views as views
from www.services_view import ServiceGitHub
from www.app_services_view import GitLabWebHook, GitHubWebHook, GitCheckCode
from www.views import GrRedirectView
from www.captcha.CodeImage import ChekcCodeImage
from www.tests import TestView
from django.conf import settings

def openapi_urlpatterns():
    """
    Helper function to return a URL pattern for serving static files.
    """
    if settings.IS_OPEN_API:
        return [url(r'^openapi/', include('openapi.urls')),]
    else:
        return []

urlpatterns = patterns(
    '',
    url(r'^$', views.Index.as_view()), url(r'^favicon\.ico$', GrRedirectView.as_view(url='/static/www/favicon.ico')),

    url(r'^monitor$', views.monitor),
    url(r'^login$', views.Login.as_view()),
    url(r'^app_login$', csrf_exempt(views.AppLogin.as_view())),
    url(r'^logout$', views.Logout.as_view()),
    url(r'^wechat/', include('www.urls.wechat')),
    # url(r'^send_invite', views.SendInviteView.as_view()),
    url(r'^phone_code', views.PhoneCodeView.as_view()),
    url(r'^captcha', ChekcCodeImage.as_view()),
    url(r'^invite$', views.InviteRegistation.as_view()),
    url(r'^register$', views.Registation.as_view()),
    url(r'^account/', include('www.urls.account')),
    url(r'^apps/(?P<tenantName>[\w\-]+)', include('www.urls.service')),
    url(r'^ajax/', include('www.urls.ajax')),
    url(r'^oauth/githup/$', login_required(ServiceGitHub.as_view())),
    url(r'^service/gitlabhook/$', csrf_exempt(GitLabWebHook.as_view())),
    url(r'^service/githubhook/$', csrf_exempt(GitHubWebHook.as_view())),
    url(r'^service/codecheck/$', csrf_exempt(GitCheckCode.as_view())),
    url(r'^api/', include('api.urls')),
    url(r'^auth/', include('www.urls.auth')),
    url(r'^huodong', include('www.urls.activity')),
    url(r'^partners/', include('www.partners.urls')),
    url(r'^Ea7e1ps5.html$', views.ssl_crv),
    url(r'^select$', login_required(views.TenantSelectView.as_view())),
    url(r'^payed/(?P<tenantName>[\w\-]+)/', include('www.urls.payedpackage')),
    url(r'^tests/(?P<templateName>[\w\-]+)/', TestView.as_view()),
    url(r'^data/media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
) + staticfiles_urlpatterns() + openapi_urlpatterns()

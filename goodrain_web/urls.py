from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.decorators.csrf import csrf_exempt
import www.views as views
import www.views.ajax as ajax
from www.services_view import ServiceStaticsManager,ServiceGitHub,ServiceLanguage,GitWebHook,GitCheckCode
from www.service_delete_view import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = patterns(
    '',
    url(r'^$', views.Index.as_view()),
    url(r'^monitor$', views.monitor),
    url(r'^login$', views.Login.as_view()),
    url(r'^logout$', views.Logout.as_view()),
    url(r'^send_invite', views.SendInviteView.as_view()),
    url(r'^invite$', views.InviteRegistation.as_view()),
    url(r'^register$', views.Registation.as_view()),
    url(r'^statics$', ServiceStaticsManager.as_view()),
    url(r'^apps/(?P<tenantName>[\w\-]+)/', include('www.url_service')),
    url(r'^ajax/', include('www.url_ajax')),    
    url(r'^service_delete/', ServiceDeleteView.as_view()), 
    url(r'^oauth/githup/$', login_required(ServiceGitHub.as_view())),   
    url(r'^service/language/$', ServiceLanguage.as_view()),
    url(r'^service/webhook/$', csrf_exempt(GitWebHook.as_view())),
    url(r'^service/codecheck/$', csrf_exempt(GitCheckCode.as_view())),
)  + staticfiles_urlpatterns()

from django.conf.urls import patterns, url
#from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from www.views.market import AppList, AppInfo, AppAdvantage, AdvantageVote

urlpatterns = patterns(
    '',
    url(r'^$', AppList.as_view()),
    url(r'^/category/(?P<category_id>\d+)$', AppList.as_view()),
    url(r'^/(?P<app_id>\d+)$', AppInfo.as_view()),
    url(r'^/(?P<app_id>\d+)/advantages$', csrf_exempt(AppAdvantage.as_view())),
    url(r'^/(?P<app_id>\d+)/advantages/(?P<liner_id>\d+)$', csrf_exempt(AdvantageVote.as_view())),
)

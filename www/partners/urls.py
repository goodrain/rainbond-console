from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt

from www.partners.ucloud import EntranceView, UserInfoView

urlpatterns = patterns(
    '',
    url(r'^ucloud/$', csrf_exempt(EntranceView.as_view())),
    url(r'^ucloud/update_userinfo/$', UserInfoView.as_view()),
)

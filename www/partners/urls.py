from django.conf.urls import patterns, url

from www.partners.ucloud import UcloudView

urlpatterns = patterns(
    '',
    url(r'^ucloud/$', UcloudView.as_view()),
)
